"""
TDrive Storage Analytics Routes.
"""

import logging
from typing import List, Annotated, Dict
from datetime import datetime, timezone, timedelta
from pathlib import Path

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select, func, and_

from api.dependencies import get_db_session, get_manager, validate_csrf, validate_integrity
from api.schemas import (
    StructuredResponse, 
    StorageOverview, 
    FileTypeStats, 
    FileSchema, 
    FolderAnalytics, 
    GrowthMetrics
)
from core.db.session import DatabaseSession
from core.db.models import FileModel
from core.db.manager import DBManager

router = APIRouter(prefix="/analytics", tags=["analytics"])

@router.get("/overview", response_model=StructuredResponse[StorageOverview])
async def get_storage_overview(
    db: Annotated[DatabaseSession, Depends(get_db_session)]
):
    """Returns high-level storage statistics."""
    try:
        with db.get_session() as session:
            total_files = session.scalar(
                select(func.count(FileModel.file_id)).where(
                    and_(FileModel.is_folder == False, FileModel.is_trashed == False)
                )
            ) or 0

            total_size = session.scalar(
                select(func.sum(FileModel.size)).where(
                    and_(FileModel.is_folder == False, FileModel.is_trashed == False)
                )
            ) or 0

            trash_size = session.scalar(
                select(func.sum(FileModel.size)).where(
                    and_(FileModel.is_folder == False, FileModel.is_trashed == True)
                )
            ) or 0

        return StructuredResponse(
            success=True,
            data=StorageOverview(
                total_files=total_files,
                total_size=total_size,
                trash_size=trash_size,
                estimated_capacity=4 * 1024 * 1024 * 1024 * 1024  
            )
        )
    except Exception as e:
        logging.error(f"Analytics overview failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/file-types", response_model=StructuredResponse[List[FileTypeStats]])
async def get_file_type_breakdown(
    db: Annotated[DatabaseSession, Depends(get_db_session)]
):
    """Categorizes storage usage by file extension."""
    categories = {
        "Video": [".mp4", ".mkv", ".avi", ".mov", ".wmv", ".webm"],
        "Images": [".jpg", ".jpeg", ".png", ".gif", ".webp", ".bmp", ".svg"],
        "Documents": [".pdf", ".doc", ".docx", ".txt", ".xls", ".xlsx", ".ppt", ".pptx", ".csv", ".json"],
        "Archives": [".zip", ".rar", ".7z", ".tar", ".gz"],
        "Audio": [".mp3", ".wav", ".flac", ".ogg", ".m4a"]
    }

    try:
        with db.get_session() as session:
            stmt = select(FileModel.filename, FileModel.size).where(
                and_(FileModel.is_folder == False, FileModel.is_trashed == False)
            )
            files = session.execute(stmt).all()

        total_active_size = sum(f.size for f in files) or 1 
        
        stats: Dict[str, Dict] = {cat: {"count": 0, "size": 0} for cat in categories}
        stats["Other"] = {"count": 0, "size": 0}

        for f in files:
            ext = Path(f.filename).suffix.lower()
            matched = False
            for cat, extensions in categories.items():
                if ext in extensions:
                    stats[cat]["count"] += 1
                    stats[cat]["size"] += f.size
                    matched = True
                    break
            if not matched:
                stats["Other"]["count"] += 1
                stats["Other"]["size"] += f.size

        result = []
        for cat, data in stats.items():
            if data["count"] > 0:
                result.append(FileTypeStats(
                    category=cat,
                    count=data["count"],
                    size=data["size"],
                    percentage=(data["size"] / total_active_size) * 100
                ))
        
        return StructuredResponse(success=True, data=sorted(result, key=lambda x: x.size, reverse=True))
    except Exception as e:
        logging.error(f"File type analytics failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/largest-files", response_model=StructuredResponse[List[FileSchema]])
async def get_largest_files(
    db: Annotated[DatabaseSession, Depends(get_db_session)]
):
    """Returns top 20 largest active files."""
    try:
        with db.get_session() as session:
            stmt = select(FileModel).where(
                and_(FileModel.is_folder == False, FileModel.is_trashed == False)
            ).order_by(FileModel.size.desc()).limit(20)
            files = session.execute(stmt).scalars().all()
            data = [FileSchema.model_validate(f) for f in files]
            
        return StructuredResponse(success=True, data=data)
    except Exception as e:
        logging.error(f"Largest files analytics failed: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/largest-folders", response_model=StructuredResponse[List[FolderAnalytics]])
async def get_largest_folders(
    db: Annotated[DatabaseSession, Depends(get_db_session)]
):
    """Aggregates storage by top-level or primary directories."""
    try:
        with db.get_session() as session:
            stmt = select(FileModel.virtual_path, FileModel.size).where(
                and_(FileModel.is_folder == False, FileModel.is_trashed == False)
            )
            files = session.execute(stmt).all()

        folder_map: Dict[str, Dict] = {}
        for f in files:
            parts = [p for p in f.virtual_path.split("/") if p]
            root = "/" + parts[0] if parts else "/"
            
            if root not in folder_map:
                folder_map[root] = {"total_files": 0, "total_size": 0}
            
            folder_map[root]["total_files"] += 1
            folder_map[root]["total_size"] += f.size

        result = [
            FolderAnalytics(path=path, **data) 
            for path, data in folder_map.items()
        ]
        
        return StructuredResponse(success=True, data=sorted(result, key=lambda x: x.total_size, reverse=True))
    except Exception as e:
        logging.error(f"Folder analytics failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/growth", response_model=StructuredResponse[GrowthMetrics])
async def get_storage_growth(
    db: Annotated[DatabaseSession, Depends(get_db_session)]
):
    """Calculates storage growth over time intervals."""
    now = datetime.now(timezone.utc)
    today_start = now.replace(hour=0, minute=0, second=0, microsecond=0)
    week_start = now - timedelta(days=7)
    month_start = now - timedelta(days=30)

    try:
        with db.get_session() as session:
            def get_sum_since(date):
                return session.scalar(
                    select(func.sum(FileModel.size)).where(
                        and_(
                            FileModel.is_folder == False,
                            FileModel.created_at >= date
                        )
                    )
                ) or 0

            return StructuredResponse(
                success=True,
                data=GrowthMetrics(
                    today=get_sum_since(today_start),
                    last_7_days=get_sum_since(week_start),
                    last_30_days=get_sum_since(month_start)
                )
            )
    except Exception as e:
        logging.error(f"Growth analytics failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/recent", response_model=StructuredResponse[List[FileSchema]])
async def get_recently_uploaded(
    db: Annotated[DatabaseSession, Depends(get_db_session)]
):
    """Returns top 20 most recently uploaded files."""
    try:
        with db.get_session() as session:
            stmt = select(FileModel).where(
                and_(FileModel.is_folder == False, FileModel.is_trashed == False)
            ).order_by(FileModel.created_at.desc()).limit(20)
            files = session.execute(stmt).scalars().all()
            data = [FileSchema.model_validate(f) for f in files]
            
        return StructuredResponse(success=True, data=data)
    except Exception as e:
        logging.error(f"Recent files analytics failed: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))
