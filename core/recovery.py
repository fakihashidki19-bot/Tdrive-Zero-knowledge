"""
TDrive Recovery & Maintenance Engine.

Provides tools for database reconstruction, integrity auditing,
and disaster recovery from Telegram metadata.
"""

import base64
import json
import logging
import os
import shutil
import time
import zipfile
import uuid
import hashlib
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

from telethon.tl.types import Message, DocumentAttributeFilename
from Crypto.Cipher import AES
from Crypto.Protocol.KDF import PBKDF2
from Crypto.Random import get_random_bytes

from core.client import TDriveClient
from core.crypto import decrypt as aes_decrypt, encrypt as aes_encrypt, generate_salt, CryptoError, verify_signature, derive_key
from core.db.manager import DBManager, DBError
from core.db.session import DatabaseSession
from core.utils import get_bytes_sha256, get_file_sha256

logger = logging.getLogger(__name__)

# --- Metadata Parsers ---

class MetadataParser:
    """Base class for metadata versioning."""
    def parse(self, text: str, key: Optional[bytes] = None) -> Optional[Dict[str, Any]]:
        raise NotImplementedError

class MetadataV1Parser(MetadataParser):
    """Parses tdrive:base64(payload) metadata tags with signature verification."""
    def parse(self, text: str, key: Optional[bytes] = None) -> Optional[Dict[str, Any]]:
        if not text or not text.startswith("tdrive:"):
            return None
        try:
            b64_data = text.split(":", 1)[1]
            payload = base64.b64decode(b64_data)
            
            sig_len = payload[0]
            signature = payload[1:1+sig_len]
            json_bytes = payload[1+sig_len:]
            
            if key and not verify_signature(json_bytes, signature, key):
                logger.warning("Metadata signature verification failed!")
                return None
                
            return json.loads(json_bytes.decode())
        except Exception as e:
            logger.debug(f"Failed to parse metadata: {e}")
            return None

class RecoveryEngine:
    """
    Handles index rebuilding and integrity maintenance.
    """

    def __init__(self, db_session: DatabaseSession, tg_client: TDriveClient, channel_id: int, master_password: Optional[str] = None, session_manager: Optional[Any] = None):
        self.db_session = db_session
        self.tg_client = tg_client
        self.channel_id = channel_id
        self.parser = MetadataV1Parser()
        self.master_password = master_password
        if session_manager is not None:
            self.sm = session_manager
        else:
            from core.session import SessionManager
            self.sm = SessionManager()
        self.key: Optional[bytes] = None

    async def rebuild_index(self, full: bool = False) -> Dict[str, Any]:
        """
        Scans Telegram channel and reconstructs the SQLite index.
        """
        stats = {"scanned": 0, "recovered_files": 0, "recovered_chunks": 0, "errors": 0}
        
        last_id = 0
        if not full:
            with self.db_session.get_session() as session:
                db = DBManager(session)
                last_id_str = db.get_setting("last_scanned_msg_id")
                last_id = int(last_id_str) if last_id_str else 0

        current_max_id = 0
        
        logger.info(f"Starting rebuild scan on channel {self.channel_id} from msg_id > {last_id}")
        
        # 1. Initialize local key if possible
        if self.master_password:
            local_salt = self.sm.get_salt()
            if local_salt:
                self.key = derive_key(self.master_password, bytes.fromhex(local_salt))

        async for message in self.tg_client.client.iter_messages(self.channel_id, min_id=last_id):
            stats["scanned"] += 1
            current_max_id = max(current_max_id, message.id)
            
            if stats["scanned"] % 50 == 0:
                logger.info(f"Scan progress: {stats['scanned']} messages checked...")

            if not message.text:
                continue

            meta = self.parser.parse(message.text, self.key)
            
            if not meta and self.master_password:
                raw_meta = self.parser.parse(message.text)
                if raw_meta and "salt" in raw_meta:
                    msg_salt = raw_meta["salt"]
                    temp_key = derive_key(self.master_password, bytes.fromhex(msg_salt))
                    
                    meta = self.parser.parse(message.text, temp_key)
                    if meta:
                        logger.warning(f"Detected valid system salt in Telegram ({msg_salt}). Synchronizing local state...")
                        if self._sync_system_salt(msg_salt):
                            self.key = temp_key
                            logger.info("Local configuration synchronized with Telegram metadata.")
                        else:
                            logger.error("Failed to sync local salt. Integrity check blocked.")

            if not meta:
                continue

            try:
                chunk_recovered = self._process_recovered_chunk(meta, message)
                if chunk_recovered:
                    stats["recovered_chunks"] += 1
                    if stats["recovered_chunks"] % 10 == 0:
                        logger.info(f"Recovered {stats['recovered_chunks']} chunks so far...")
            except Exception as e:
                logger.error(f"Error recovering message {message.id}: {e}")
                stats["errors"] += 1

        logger.info(f"Rebuild finished. Scanned: {stats['scanned']}, Recovered chunks: {stats['recovered_chunks']}, Errors: {stats['errors']}")
        if current_max_id > 0:
            with self.db_session.get_session() as session:
                db = DBManager(session)
                db.set_setting("last_scanned_msg_id", str(current_max_id))
                db.set_setting("last_rebuild_at", datetime.now(timezone.utc).isoformat())

        return stats

    def _sync_system_salt(self, salt_hex: str) -> bool:
        """Updates the local config.json with the salt found in Telegram."""
        if not self.master_password:
            return False
        try:
            old_config = self.sm.load_config()
            temp_config = old_config.copy()
            temp_config["master_salt"] = salt_hex
            self.sm.save_config(temp_config)
            self.sm.setup_password_verification(self.master_password)
            return True
        except Exception as e:
            logger.error(f"Failed to sync salt: {e}")
            return False

    def _process_recovered_chunk(self, meta: Dict[str, Any], message: Message) -> bool:
        fid = meta.get("fid")
        f_uuid = meta.get("uuid")
        seq = meta.get("seq")
        tot = meta.get("tot")
        name = meta.get("name")
        
        if not all([fid, f_uuid, seq is not None, tot]):
            return False

        with self.db_session.get_session() as session:
            db = DBManager(session)
            file_rec = db.get_file(fid)
            if not file_rec:
                file_rec = db.get_file_by_uuid(f_uuid)
                
            if not file_rec:
                file_rec = db.create_file_record(
                    file_id=fid,
                    file_uuid=f_uuid,
                    filename=name or "recovered_file",
                    virtual_path="/",
                    size=0,
                    sha256=fid, 
                    chunk_count=tot
                )
                file_rec.status = "recovering"
                file_rec.is_materialized = False
            
            existing_chunks = db.get_chunks(fid)
            if any(c.sequence == seq for c in existing_chunks):
                return False
                
            db.add_chunk(
                chunk_id=uuid.uuid4().hex,
                file_id=fid,
                sequence=seq,
                msg_id=message.id,
                channel_id=self.channel_id,
                chunk_size=message.file.size if message.file else 0,
                chunk_sha256="unknown" 
            )
            session.flush() 
            
            all_chunks = db.get_chunks(fid)
            actual_size = sum(max(0, c.chunk_size - 12) for c in all_chunks)
            file_rec.size = actual_size

            if len(all_chunks) == tot:
                file_rec.status = "completed"
                logger.info(f"File {file_rec.filename} fully reconstructed ({actual_size} bytes).")
                
            return True

    async def audit_integrity(self) -> Dict[str, Any]:
        report = {"total_files": 0, "missing_chunks": 0, "orphans_detected": 0}
        with self.db_session.get_session() as session:
            db = DBManager(session)
            files = db.list_files()
            report["total_files"] = len(files)
            for f in files:
                chunks = db.get_chunks(f.file_id)
                if len(chunks) < f.chunk_count:
                    report["missing_chunks"] += (f.chunk_count - len(chunks))
                    db.update_file_status(f.file_id, "error")
        return report

    async def detect_orphans(self) -> List[int]:
        orphans = []
        with self.db_session.get_session() as session:
            db = DBManager(session)
            known_msg_ids = set()
            for f in db.list_files():
                for c in db.get_chunks(f.file_id):
                    known_msg_ids.add(c.msg_id)
                    
        async for message in self.tg_client.client.iter_messages(self.channel_id):
            meta = self.parser.parse(message.text)
            if meta and message.id not in known_msg_ids:
                orphans.append(message.id)
        return orphans

    async def cleanup_orphans(self) -> int:
        """
        Deletes orphaned TDrive messages from Telegram.
        """
        orphan_ids = await self.detect_orphans()
        if orphan_ids:
            await self.tg_client.delete_messages(self.channel_id, orphan_ids)
        return len(orphan_ids)

# --- Backup Engine ---

class BackupEngine:
    """Handles AES-256-GCM encrypted backups of TDrive state."""
    
    def __init__(self, config_dir: Path):
        self.config_dir = config_dir

    def create_backup(self, output_path: Path, password: str) -> Path:
        """Creates a truly encrypted zip of the .tdrive folder."""
        temp_zip = output_path.with_suffix(".tmp.zip")
        files_to_backup = ["config.json", "tdrive.db", "tdrive.session"]
        
        with zipfile.ZipFile(temp_zip, 'w', zipfile.ZIP_DEFLATED) as zf:
            for f in files_to_backup:
                f_path = self.config_dir / f
                if f_path.exists():
                    zf.write(f_path, f)
                    
        try:
            salt = get_random_bytes(16)
            key = PBKDF2(password, salt, 32, count=100000, hmac_hash_module=hashlib.sha256)
            
            with open(temp_zip, "rb") as f:
                data = f.read()
            
            cipher = AES.new(key, AES.MODE_GCM)
            ciphertext, tag = cipher.encrypt_and_digest(data)
            
            with open(output_path, "wb") as f:
                f.write(salt)
                f.write(cipher.nonce)
                f.write(tag)
                f.write(ciphertext)
                
        finally:
            if temp_zip.exists():
                temp_zip.unlink()
                
        return output_path

    def restore_backup(self, backup_path: Path, password: str) -> bool:
        """Restores config and DB from an encrypted backup zip."""
        if not backup_path.exists():
            return False
            
        try:
            with open(backup_path, "rb") as f:
                salt = f.read(16)
                nonce = f.read(16)
                tag = f.read(16)
                ciphertext = f.read()
                
            key = PBKDF2(password, salt, 32, count=100000, hmac_hash_module=hashlib.sha256)
            cipher = AES.new(key, AES.MODE_GCM, nonce=nonce)
            data = cipher.decrypt_and_verify(ciphertext, tag)
            
            temp_zip = backup_path.with_suffix(".restoring.zip")
            temp_zip.write_bytes(data)
            
            with zipfile.ZipFile(temp_zip, 'r') as zf:
                zf.extractall(self.config_dir)
                
            temp_zip.unlink()
            return True
        except Exception as e:
            logger.error(f"Backup restoration failed: {e}")
            return False
