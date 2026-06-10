"""
TDrive File Routes.
"""

import shutil
import tempfile
import uuid
import base64
import logging
from io import BytesIO
from pathlib import Path
from typing import Annotated, List, Optional

from fastapi import APIRouter, Depends, File, HTTPException, UploadFile, status, BackgroundTasks, Form
from fastapi.responses import StreamingResponse

from api.dependencies import get_manager, get_db_session, get_session_manager
from api.schemas import FileSchema, FileDetailSchema, StructuredResponse, ChunkSchema, FolderCreateRequest, BulkActionRequest
from core.db.manager import DBManager
from core.db.session import DatabaseSession
from core.manager import TDriveManager, ManagerError
from core.session import SessionManager

router = APIRouter(prefix="/files", tags=["files"])

def generate_thumbnail(file_path: Path) -> Optional[str]:
    """Generates a small base64 thumbnail for image and video files."""
    try:
        from PIL import Image
        import ffmpeg
        
        ext = file_path.suffix.lower()
        image_exts = [".jpg", ".jpeg", ".png", ".webp", ".gif"]
        video_exts = [".mp4", ".mkv", ".mov", ".avi", ".wmv", ".flv", ".webm"]

        # --- Case 1: Image Files ---
        if ext in image_exts:
            with Image.open(file_path) as img:
                img.thumbnail((200, 200))
                if img.mode in ("RGBA", "P"):
                    img = img.convert("RGB")
                
                buffered = BytesIO()
                img.save(buffered, format="JPEG", quality=70)
                return base64.b64encode(buffered.getvalue()).decode()

        # --- Case 2: Video Files ---
        elif ext in video_exts:
            out, _ = (
                ffmpeg
                .input(str(file_path), ss=1)
                .filter('scale', 200, -1)
                .output('pipe:', vframes=1, format='image2', vcodec='mjpeg')
                .run(capture_stdout=True, capture_stderr=True, quiet=True)
            )
            if out:
                return base64.b64encode(out).decode()
            
        return None
    except Exception as e:
        logging.error(f"Thumbnail generation failed: {e}")
        return None

@router.get("", response_model=StructuredResponse[List[FileSchema]])
async def list_files(
    db_session: Annotated[DatabaseSession, Depends(get_db_session)],
    manager: Annotated[TDriveManager, Depends(get_manager)],
    path: str = "/"
):
    with db_session.get_session() as session:
        db = DBManager(session)
        files = db.list_files(path)
        return StructuredResponse(success=True, data=[FileSchema.model_validate(f) for f in files])

@router.get("/{file_id}", response_model=StructuredResponse[FileDetailSchema])
async def get_file_detail(
    file_id: str,
    db_session: Annotated[DatabaseSession, Depends(get_db_session)],
    manager: Annotated[TDriveManager, Depends(get_manager)]
):
    with db_session.get_session() as session:
        db = DBManager(session)
        f = db.get_file(file_id)
        if not f:
            raise HTTPException(status_code=404, detail="File not found")
        
        chunks = db.get_chunks(file_id)
        
        data = FileDetailSchema.model_validate(f)
        data.chunks = [
            ChunkSchema(
                chunk_id=c.chunk_id,
                sequence=c.sequence,
                msg_id=c.msg_id,
                chunk_size=c.chunk_size,
                chunk_sha256=c.chunk_sha256
            ) for c in chunks
        ]
        return StructuredResponse(success=True, data=data)

@router.post("/folder", response_model=StructuredResponse[FileSchema])
async def create_folder(
    request: FolderCreateRequest,
    db_session_factory: Annotated[DatabaseSession, Depends(get_db_session)],
    manager: Annotated[TDriveManager, Depends(get_manager)]
):
    """Creates a new virtual folder."""
    with db_session_factory.get_session() as session:
        db = DBManager(session)
        folder = db.create_folder(request.name, request.vpath)
        session.commit()
        return StructuredResponse(success=True, data=FileSchema.model_validate(folder))

@router.patch("/{file_id}", response_model=StructuredResponse[FileSchema])
async def rename_file(
    file_id: str,
    new_name: str,
    db_session: Annotated[DatabaseSession, Depends(get_db_session)],
    manager: Annotated[TDriveManager, Depends(get_manager)]
):
    """Renames a file or folder."""
    with db_session.get_session() as session:
        db = DBManager(session)
        f = db.get_file(file_id)
        if not f:
            raise HTTPException(status_code=404, detail="Item not found")
        f.filename = new_name
        session.commit()
        return StructuredResponse(success=True, data=FileSchema.model_validate(f))

@router.post("/upload", response_model=StructuredResponse[str])
async def upload_file(
    background_tasks: BackgroundTasks,
    db_session_factory: Annotated[DatabaseSession, Depends(get_db_session)],
    manager_factory: Annotated[TDriveManager, Depends(get_manager)],
    sm: Annotated[SessionManager, Depends(get_session_manager)],
    file: UploadFile = File(...),
    vpath: str = Form("/")
):
    job_id = uuid.uuid4().hex
    file_ext = Path(file.filename).suffix
    safe_filename = f"upload_{uuid.uuid4().hex}{file_ext}"
    temp_storage_path = sm.tmp_dir / safe_filename
    
    try:
        with open(temp_storage_path, "wb") as buffer:
            shutil.copyfileobj(file.file, buffer)
        total_size = temp_storage_path.stat().st_size
    except Exception as e:
        if temp_storage_path.exists():
            temp_storage_path.unlink()
        raise HTTPException(status_code=500, detail=f"Failed to buffer upload: {str(e)}")
    finally:
        file.file.close()

    thumbnail_b64 = generate_thumbnail(temp_storage_path)

    # 3. Create the job record
    with db_session_factory.get_session() as session:
        db = DBManager(session)
        db.create_job(job_id=job_id, job_type="upload", total_size=total_size)

    # 4. Define the background worker
    async def run_upload():
        try:
            def progress_hook(current, total):
                with db_session_factory.get_session() as session:
                    db = DBManager(session)
                    percent = (current / total) * 100 if total > 0 else 100
                    db.update_job_progress(job_id, current * (20 * 1024 * 1024), percent)

            with db_session_factory.get_session() as session:
                db = DBManager(session)
                db.update_job_status(job_id, "running")

            file_id = await manager_factory.upload_file(temp_storage_path, virtual_path=vpath, progress_callback=progress_hook)

            with db_session_factory.get_session() as session:
                db = DBManager(session)
                f_rec = db.get_file(file_id)
                if f_rec:
                    f_rec.filename = file.filename
                    f_rec.thumbnail = thumbnail_b64
                    session.add(f_rec)
                    session.commit() 
                db.update_job_status(job_id, "completed", file_id=file_id)
                db.update_job_progress(job_id, total_size, 100.0)

        except Exception as e:
            logging.error(f"Upload task failed: {e}")
            with db_session_factory.get_session() as session:
                db = DBManager(session)
                db.update_job_status(job_id, "failed", error=str(e))
        finally:
            if temp_storage_path.exists():
                temp_storage_path.unlink()

    background_tasks.add_task(run_upload)
    return StructuredResponse(success=True, data=job_id)

@router.post("/{file_id}/ticket", response_model=StructuredResponse[dict])
async def create_download_ticket(
    file_id: str,
    manager: Annotated[TDriveManager, Depends(get_manager)]
):
    from api.dependencies import download_tickets
    with manager.db_session.get_session() as session:
        db = DBManager(session)
        if not db.file_exists(file_id):
            raise HTTPException(status_code=404, detail="File not found")
        
    tid = download_tickets.create(file_id)
    return StructuredResponse(success=True, data={"ticket": tid, "expires_in": 300})

@router.delete("/{file_id}", response_model=StructuredResponse[dict])
async def delete_file(
    file_id: str,
    manager: Annotated[TDriveManager, Depends(get_manager)]
):
    try:
        deleted_count = await manager.delete_file(file_id)
        return StructuredResponse(
            success=True, 
            data={
                "file_id": file_id,
                "deleted_chunks": deleted_count
            }
        )
    except ManagerError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/bulk-trash", response_model=StructuredResponse[dict])
async def bulk_trash_files(
    req: BulkActionRequest,
    manager: Annotated[TDriveManager, Depends(get_manager)]
):
    """Moves multiple files to trash."""
    count = 0
    for fid in req.file_ids:
        try:
            if await manager.trash_file(fid):
                count += 1
                logging.info(f"BULK_TRASH: Item {fid} moved to trash.")
        except Exception as e:
            logging.error(f"Bulk trash failed for {fid}: {e}")
            
    return StructuredResponse(success=True, data={"count": count})

@router.post("/bulk-download")
async def bulk_download_files(
    req: BulkActionRequest,
    manager: Annotated[TDriveManager, Depends(get_manager)],
    sm: Annotated[SessionManager, Depends(get_session_manager)]
):
    """Generates a ZIP of multiple files and streams it."""
    import zipfile
    
    if not req.file_ids:
        raise HTTPException(status_code=400, detail="No files selected")

    # 1. Create a temporary ZIP file
    zip_filename = f"tdrive_bulk_{uuid.uuid4().hex[:8]}.zip"
    temp_zip_path = sm.tmp_dir / zip_filename
    
    try:
        with zipfile.ZipFile(temp_zip_path, 'w', zipfile.ZIP_DEFLATED) as zf:
            for fid in req.file_ids:
                with manager.db_session.get_session() as session:
                    db = DBManager(session)
                    f_rec = db.get_file(fid)
                    if not f_rec or f_rec.is_folder:
                        continue 
                    
                    filename = f_rec.filename
                
                temp_file_path = sm.tmp_dir / f"dl_{uuid.uuid4().hex[:8]}_{filename}"
                try:
                    await manager.download_file(fid, temp_file_path)
                    zf.write(temp_file_path, filename)
                    logging.info(f"BULK_DOWNLOAD: Added {filename} to ZIP")
                finally:
                    if temp_file_path.exists():
                        temp_file_path.unlink()
        
        # 2. Stream the ZIP file and then delete it
        from fastapi.responses import FileResponse
        
        bt = BackgroundTasks()
        bt.add_task(lambda p: Path(p).unlink(missing_ok=True) if Path(p).exists() else None, str(temp_zip_path))

        return FileResponse(
            temp_zip_path, 
            media_type="application/zip", 
            filename=zip_filename,
            background=bt
        )

    except Exception as e:
        if temp_zip_path.exists():
            temp_zip_path.unlink()
        logging.error(f"Bulk download failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))
