"""
TDrive Orchestration Manager.

The central brain of TDrive. Manages the high-level workflows for uploading
and downloading files, handling encryption, chunking, and database persistence.
"""

import base64
import json
import logging
import math
import uuid
import tempfile
import asyncio
import time
from pathlib import Path
from typing import Any, AsyncGenerator, Callable, List, Optional

from sqlalchemy import select, and_
from core.client import TDriveClient
from core.crypto import decrypt, derive_key, encrypt, CryptoError, sign_data, verify_signature
from core.db.manager import DBManager, DBError
from core.db.session import DatabaseSession
from core.utils import (
    chunk_file_iterator,
    get_bytes_sha256,
    get_file_sha256,
    get_file_size,
)

logger = logging.getLogger(__name__)

DEFAULT_CHUNK_SIZE = 20 * 1024 * 1024 


class ManagerError(Exception):
    """Base exception for Manager operations."""
    pass


class TDriveManager:
    """
    Orchestrates file operations between local storage, SQLite, and Telegram.
    """

    def __init__(
        self,
        db_session: DatabaseSession,
        tg_client: TDriveClient,
        channel_id: int,
        master_password: str,
        master_salt: bytes,
    ):
        """
        Initializes the TDriveManager.
        """
        self.db_session = db_session
        self.tg_client = tg_client
        self.channel_id = channel_id
        self.master_password = master_password
        self.master_salt = master_salt
        self.key = derive_key(master_password, master_salt)

    def _generate_metadata_tag(self, file_id: str, file_uuid: str, filename: str, sequence: int, total_chunks: int) -> str:
        """
        Generates a Base64-encoded compact JSON tag for Telegram captions.
        Includes an HMAC signature for integrity.
        """
        data = {
            "v": 1,
            "fid": file_id,
            "uuid": file_uuid,
            "seq": sequence,
            "tot": total_chunks,
            "name": filename,
            "salt": self.master_salt.hex()
        }
        json_bytes = json.dumps(data, separators=(",", ":")).encode()
        signature = sign_data(json_bytes, self.key)
        
        payload = bytes([len(signature)]) + signature + json_bytes
        return base64.b64encode(payload).decode()

    async def upload_file(
        self,
        local_path: str | Path,
        virtual_path: str = "/",
        progress_callback: Optional[Callable[[int, int], None]] = None
    ) -> str:
        """
        Uploads a file to Telegram in chunks.
        Supports resuming interrupted uploads.
        """
        path = Path(local_path)
        if not path.exists():
            raise ManagerError(f"File not found: {local_path}")

        file_size = get_file_size(path)
        file_sha256 = get_file_sha256(path)
        filename = path.name
        
        file_id = file_sha256
        chunk_count = math.ceil(file_size / DEFAULT_CHUNK_SIZE) if file_size > 0 else 1
        file_uuid = uuid.uuid4().hex

        # Phase 1: Initialize or Resume File Record
        with self.db_session.get_session() as session:
            db = DBManager(session)
            file_record = db.get_file(file_id)

            if file_record and file_record.status == "completed":
                logger.info(f"File {filename} already fully uploaded.")
                return file_id

            if not file_record:
                file_record = db.create_file_record(
                    file_id=file_id,
                    file_uuid=file_uuid,
                    filename=filename,
                    virtual_path=virtual_path,
                    size=file_size,
                    sha256=file_sha256,
                    chunk_count=chunk_count
                )
            else:
                file_record.status = "uploading"
                file_uuid = file_record.file_uuid
            
            existing_chunks = {c.sequence for c in db.get_chunks(file_id)}

        # Phase 2: Upload Chunks
        for seq, chunk_data in enumerate(chunk_file_iterator(path, DEFAULT_CHUNK_SIZE)):
            if seq in existing_chunks:
                continue

            # 1. Encrypt
            nonce, ciphertext = encrypt(chunk_data, self.key)
            encrypted_blob = nonce + ciphertext
            chunk_sha256 = get_bytes_sha256(encrypted_blob)
            
            # 2. Upload
            metadata = self._generate_metadata_tag(file_id, file_uuid, filename, seq, chunk_count)
            caption = f"tdrive:{metadata}"
            
            try:
                message = await self.tg_client.send_document(
                    self.channel_id,
                    encrypted_blob,
                    caption=caption
                )
            except Exception as e:
                with self.db_session.get_session() as session:
                    db = DBManager(session)
                    db.update_file_status(file_id, "error")
                raise ManagerError(f"Failed to upload chunk {seq}: {str(e)}")

            # 3. Record Chunk in its own transaction
            with self.db_session.get_session() as session:
                db = DBManager(session)
                db.add_chunk(
                    chunk_id=uuid.uuid4().hex,
                    file_id=file_id,
                    sequence=seq,
                    msg_id=message.id,
                    channel_id=self.channel_id,
                    chunk_size=len(encrypted_blob),
                    chunk_sha256=chunk_sha256
                )

            if progress_callback:
                progress_callback(seq + 1, chunk_count)

        # Phase 3: Finalize
        with self.db_session.get_session() as session:
            db = DBManager(session)
            db.update_file_status(file_id, "completed")
            
        return file_id

    async def download_file(
        self,
        file_id: str,
        output_path: str | Path,
        progress_callback: Optional[Callable[[int, int], None]] = None
    ) -> Path:
        """
        Downloads a file from Telegram and assembles it locally.
        Uses the streaming generator internally.
        """
        out_path = Path(output_path)
        out_path.parent.mkdir(parents=True, exist_ok=True)

        with open(out_path, "wb") as f:
            async for chunk_data in self.download_file_stream(file_id, progress_callback):
                f.write(chunk_data)

        with self.db_session.get_session() as session:
            db = DBManager(session)
            file_record = db.get_file(file_id)
            actual_sha256 = get_file_sha256(out_path)
            
            if file_record.sha256 in ["pending", "unknown", file_id]:
                file_record.sha256 = actual_sha256
            elif actual_sha256 != file_record.sha256:
                out_path.unlink()
                raise ManagerError(f"Final file integrity verification failed. Expected {file_record.sha256}, got {actual_sha256}")

        return out_path

    async def upload_file_stream(
        self,
        stream: Any,
        filename: str,
        total_size: int,
        virtual_path: str = "/",
        progress_callback: Optional[Callable[[int, int], None]] = None
    ) -> str:
        """
        Uploads a file by reading from a stream in chunks.
        Never stores the full file on disk.
        """
        import hashlib
        temp_fid_content = f"{filename}:{total_size}:{time.time()}".encode()
        temp_fid = hashlib.sha256(temp_fid_content).hexdigest()
        file_uuid = uuid.uuid4().hex
        
        chunk_count = math.ceil(total_size / DEFAULT_CHUNK_SIZE) if total_size > 0 else 1
        
        # 1. Initialize record
        with self.db_session.get_session() as session:
            db = DBManager(session)
            file_record = db.create_file_record(
                file_id=temp_fid,
                file_uuid=file_uuid,
                filename=filename,
                virtual_path=virtual_path,
                size=total_size,
                sha256="pending", 
                chunk_count=chunk_count
            )
            file_record.status = "uploading"

        full_hash = hashlib.sha256()
        current_seq = 0
        
        # 2. Read stream in chunks
        try:
            while True:
                if asyncio.iscoroutinefunction(stream.read):
                    chunk_data = await stream.read(DEFAULT_CHUNK_SIZE)
                else:
                    chunk_data = stream.read(DEFAULT_CHUNK_SIZE)

                if not chunk_data:
                    break
                
                full_hash.update(chunk_data)
                
                nonce, ciphertext = encrypt(chunk_data, self.key)
                encrypted_blob = nonce + ciphertext
                chunk_sha256 = get_bytes_sha256(encrypted_blob)
                
                metadata = self._generate_metadata_tag(temp_fid, file_uuid, filename, current_seq, chunk_count)
                caption = f"tdrive:{metadata}"
                
                message = await self.tg_client.send_document(
                    self.channel_id,
                    encrypted_blob,
                    caption=caption
                )
                
                with self.db_session.get_session() as session:
                    db = DBManager(session)
                    db.add_chunk(
                        chunk_id=uuid.uuid4().hex,
                        file_id=temp_fid,
                        sequence=current_seq,
                        msg_id=message.id,
                        channel_id=self.channel_id,
                        chunk_size=len(encrypted_blob),
                        chunk_sha256=chunk_sha256
                    )
                
                current_seq += 1
                if progress_callback:
                    progress_callback(current_seq, chunk_count)

            final_sha256 = full_hash.hexdigest()
            
            with self.db_session.get_session() as session:
                db = DBManager(session)
                file_record = db.get_file(temp_fid)
                if file_record:
                    file_record.sha256 = final_sha256
                    file_record.status = "completed"
                    
            return temp_fid

        except Exception as e:
            logger.error(f"Stream upload failed: {e}")
            with self.db_session.get_session() as session:
                db = DBManager(session)
                try:
                    db.update_file_status(temp_fid, "error")
                except:
                    pass
            raise

    async def download_file_stream(
        self,
        file_id: str,
        progress_callback: Optional[Callable[[int, int], None]] = None
    ) -> AsyncGenerator[bytes, None]:
        """
        Downloads chunks from Telegram and yields decrypted bytes.
        No full file is stored on disk during this process.
        """
        # Phase 1: Load metadata
        with self.db_session.get_session() as session:
            db = DBManager(session)
            file_record = db.get_file(file_id)
            if not file_record:
                raise ManagerError(f"File {file_id} not found in database.")
            
            expected_chunk_count = file_record.chunk_count
            chunks_data = []
            for c in db.get_chunks(file_id):
                chunks_data.append({
                    "msg_id": c.msg_id,
                    "sha256": c.chunk_sha256,
                    "seq": c.sequence
                })

        if len(chunks_data) != expected_chunk_count:
            raise ManagerError(f"Missing chunks for file {file_id}. Expected {expected_chunk_count}, got {len(chunks_data)}.")

        # Phase 2: Stream chunks
        for i, chunk_info in enumerate(chunks_data):
            seq = chunk_info["seq"]
            msg_id = chunk_info["msg_id"]
            expected_chunk_sha = chunk_info["sha256"]

            with tempfile.NamedTemporaryFile(delete=True) as tmp_chunk:
                temp_chunk_path = Path(tmp_chunk.name)
                
                msg = await self.tg_client.get_message(self.channel_id, msg_id)
                if not msg:
                    raise ManagerError(f"Message {msg_id} not found on Telegram.")
                
                await self.tg_client.download_document(msg, temp_chunk_path)
                
                encrypted_data = temp_chunk_path.read_bytes()
                
                if expected_chunk_sha != "unknown":
                    if get_bytes_sha256(encrypted_data) != expected_chunk_sha:
                        raise ManagerError(f"Integrity failure for encrypted chunk {seq}.")
                else:
                    try:
                        actual_chunk_sha = get_bytes_sha256(encrypted_data)
                        with self.db_session.get_session() as session:
                            from core.db.models import ChunkModel
                            stmt = select(ChunkModel).where(and_(ChunkModel.file_id == file_id, ChunkModel.sequence == seq))
                            c_rec = session.execute(stmt).scalar_one_or_none()
                            if c_rec:
                                c_rec.chunk_sha256 = actual_chunk_sha
                    except Exception as e:
                        logger.debug(f"Failed to update recovered chunk hash: {e}")

                nonce = encrypted_data[:12]
                ciphertext = encrypted_data[12:]
                try:
                    decrypted_data = decrypt(nonce, ciphertext, self.key)
                except CryptoError as e:
                    raise ManagerError(f"Decryption failed for chunk {seq}: {str(e)}")

                yield decrypted_data

                if progress_callback:
                    progress_callback(i + 1, expected_chunk_count)

    async def trash_file(self, file_id: str) -> bool:
        """Moves a file to trash (soft delete)."""
        with self.db_session.get_session() as session:
            db = DBManager(session)
            return db.trash_file(file_id)

    async def restore_file(self, file_id: str) -> bool:
        """Restores a file from trash."""
        with self.db_session.get_session() as session:
            db = DBManager(session)
            return db.restore_file(file_id)

    async def delete_file_permanently(self, file_id: str) -> int:
        """
        Deletes a file from both Telegram and the local database permanently.
        """
        with self.db_session.get_session() as session:
            db = DBManager(session)
            file_record = db.get_file(file_id)
            if not file_record:
                raise ManagerError(f"File {file_id} not found.")
            
            chunks = db.get_chunks(file_id)
            msg_ids = [c.msg_id for c in chunks]
            deleted_chunks_count = len(msg_ids)

            # 1. Delete from Telegram
            if msg_ids:
                try:
                    await self.tg_client.delete_messages(self.channel_id, msg_ids)
                except Exception as e:
                    logger.error(f"Failed to delete chunks from Telegram: {e}")

            # 2. Delete from Database
            db.delete_file_permanently(file_id)
            
            return deleted_chunks_count

    async def delete_file(self, file_id: str) -> bool:
        """
        Compatibility method. Now defaults to soft delete (trash).
        """
        return await self.trash_file(file_id)

    async def get_preview_file(self, file_id: str, cache_dir: Path) -> Path:
        """
        Retrieves a decrypted file for preview, using a local cache.
        """
        with self.db_session.get_session() as session:
            db = DBManager(session)
            file_record = db.get_file(file_id)
            if not file_record:
                raise ManagerError(f"File {file_id} not found.")
            
            ext = Path(file_record.filename).suffix
            cache_path = cache_dir / f"{file_record.sha256}{ext}"

            if cache_path.exists():
                cache_path.touch()
                return cache_path

            cache_path.parent.mkdir(parents=True, exist_ok=True)
            
            with open(cache_path, "wb") as f:
                async for chunk_data in self.download_file_stream(file_id):
                    f.write(chunk_data)
            
            calculated_sha = get_file_sha256(cache_path)
            
            await self.heal_metadata(file_id, cache_path, calculated_sha)

            return cache_path

    async def heal_metadata(self, file_id: str, local_path: Path, actual_sha256: Optional[str] = None) -> bool:
        """
        Recomputes and updates metadata (size, hash, thumbnail) for a file.
        Essential for fully materializing recovered files.
        """
        if not actual_sha256:
            actual_sha256 = get_file_sha256(local_path)
            
        try:
            with self.db_session.get_session() as session:
                db = DBManager(session)
                f_rec = db.get_file(file_id)
                if not f_rec:
                    return False
                
                # 1. Update SHA256 if it was a placeholder
                if f_rec.sha256 in ["pending", "unknown", file_id]:
                    f_rec.sha256 = actual_sha256
                    logger.info(f"Healed SHA256 for {f_rec.filename}")
                
                # 2. Update Size if 0 or mismatch
                actual_size = local_path.stat().st_size
                if f_rec.size != actual_size:
                    f_rec.size = actual_size
                
                # 3. Generate Thumbnail if missing
                if not f_rec.thumbnail:
                    from api.routes.files import generate_thumbnail
                    thumb = generate_thumbnail(local_path)
                    if thumb:
                        f_rec.thumbnail = thumb
                        logger.info(f"Healed Thumbnail for {f_rec.filename}")
                
                f_rec.is_materialized = True
                f_rec.status = "completed"
                return True
        except Exception as e:
            logger.error(f"Metadata healing failed for {file_id}: {e}")
            return False
