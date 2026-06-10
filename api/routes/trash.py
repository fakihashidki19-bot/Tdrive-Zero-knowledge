"""
TDrive Trash Bin Routes.
"""

from typing import Annotated, List
from fastapi import APIRouter, Depends, HTTPException, status
from api.dependencies import get_db_session, get_manager, validate_csrf
from api.schemas import StructuredResponse, FileSchema
from core.db.manager import DBManager
from core.db.session import DatabaseSession
from core.manager import TDriveManager, ManagerError

router = APIRouter(prefix="/trash", tags=["trash"])

@router.get("", response_model=StructuredResponse[List[FileSchema]])
async def list_trash(
    db_session: Annotated[DatabaseSession, Depends(get_db_session)]
):
    """Lists all items in the trash."""
    with db_session.get_session() as session:
        db = DBManager(session)
        files = db.list_trashed_files()
        return StructuredResponse(success=True, data=[FileSchema.model_validate(f) for f in files])

@router.post("/{file_id}/restore", response_model=StructuredResponse[bool])
async def restore_file(
    file_id: str,
    manager: Annotated[TDriveManager, Depends(get_manager)]
):
    """Restores a file from the trash."""
    success = await manager.restore_file(file_id)
    if not success:
        raise HTTPException(status_code=404, detail="File not found in trash")
    return StructuredResponse(success=True, data=True)

@router.delete("/{file_id}", response_model=StructuredResponse[dict])
async def permanent_delete(
    file_id: str,
    manager: Annotated[TDriveManager, Depends(get_manager)]
):
    """Permanently deletes a file and its Telegram chunks."""
    try:
        deleted_count = await manager.delete_file_permanently(file_id)
        return StructuredResponse(
            success=True, 
            data={
                "file_id": file_id,
                "deleted_chunks": deleted_count
            }
        )
    except ManagerError as e:
        raise HTTPException(status_code=404, detail=str(e))

@router.post("/cleanup", response_model=StructuredResponse[int])
async def empty_trash(
    manager: Annotated[TDriveManager, Depends(get_manager)]
):
    """Permanently deletes all files in the trash."""
    with manager.db_session.get_session() as session:
        db = DBManager(session)
        trashed_files = db.list_trashed_files()
    
    total_deleted = 0
    for f in trashed_files:
        try:
            await manager.delete_file_permanently(f.file_id)
            total_deleted += 1
        except Exception:
            pass
            
    return StructuredResponse(success=True, data=total_deleted)
