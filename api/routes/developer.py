"""
TDrive Developer Mode Routes.
"""

import logging
import time
import os
import psutil
import platform
import zipfile
import shutil
import tempfile
import json
from typing import Annotated, List, Optional
from datetime import datetime, timezone, timedelta
from pathlib import Path

from fastapi import APIRouter, Depends, HTTPException, status, Query
from fastapi.responses import FileResponse
from pydantic import BaseModel

from api.dependencies import get_manager, get_session_manager, validate_csrf, get_db_session
from api.schemas import StructuredResponse
from core.manager import TDriveManager
from core.session import SessionManager
from core.db.manager import DBManager
from core.db.session import DatabaseSession

router = APIRouter(prefix="/developer", tags=["developer"])

# --- Models ---

class LogEntry(BaseModel):
    timestamp: str
    level: str
    module: str
    message: str

class DriveMetrics(BaseModel):
    mountpoint: str
    total: float
    used: float
    free: float
    percent: float

class SystemMetrics(BaseModel):
    cpu_percent: float
    ram_usage: float 
    ram_total: float
    disk_usage: float
    disk_total: float
    drives: List[DriveMetrics] = []
    uptime: float
    timestamp: datetime

class DevStatus(BaseModel):
    api_version: str
    python_version: str
    os_info: str
    arch: str
    dev_mode: bool
    db_size: int
    db_wal: bool

class TrashStats(BaseModel):
    total_files: int
    total_size: int
    oldest_item_at: Optional[datetime] = None
    retention_days: int

class PreviewStats(BaseModel):
    requests: int
    cache_hits: int
    cache_misses: int
    cache_usage: int 

# --- Global Trackers (Memory-based for MVP) ---

class PreviewTracker:
    def __init__(self):
        self.requests = 0
        self.cache_hits = 0
        self.cache_misses = 0

preview_tracker = PreviewTracker()

# --- Log Buffer ---

class MemoryLogHandler(logging.Handler):
    def __init__(self, capacity=500):
        super().__init__()
        self.capacity = capacity
        self.buffer: List[LogEntry] = []

    def emit(self, record):
        try:
            entry = LogEntry(
                timestamp=datetime.fromtimestamp(record.created, tz=timezone.utc).strftime("%H:%M:%S"),
                level=record.levelname,
                module=record.module,
                message=self.format(record)
            )
            self.buffer.append(entry)
            if len(self.buffer) > self.capacity:
                self.buffer.pop(0)
        except Exception:
            self.handleError(record)

log_handler = MemoryLogHandler()
log_handler.setFormatter(logging.Formatter('%(message)s'))
logging.getLogger().addHandler(log_handler)

# --- Helpers ---

def check_dev_mode(sm: SessionManager = Depends(get_session_manager)):
    if not sm.is_developer_mode():
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Developer Mode is disabled in configuration."
        )

# --- Routes ---

@router.get("/status", response_model=StructuredResponse[DevStatus])
async def get_dev_status(
    sm: Annotated[SessionManager, Depends(get_session_manager)],
    db_session: Annotated[DatabaseSession, Depends(get_db_session)]
):
    db_path = sm.config_dir / "tdrive.db"
    db_size = db_path.stat().st_size if db_path.exists() else 0
    dev_enabled = sm.is_developer_mode()
    
    is_healthy = False
    try:
        with db_session.get_session() as session:
            from sqlalchemy import text
            session.execute(text("SELECT 1"))
            is_healthy = True
    except Exception:
        is_healthy = False

    return StructuredResponse(
        success=True,
        data=DevStatus(
            api_version="1.3.3",
            python_version=platform.python_version(),
            os_info=f"{platform.system()} {platform.release()}",
            arch=platform.machine(),
            dev_mode=dev_enabled,
            db_size=db_size if dev_enabled else 0,
            db_wal=is_healthy 
        )
    )

@router.get("/logs", response_model=StructuredResponse[List[LogEntry]], dependencies=[Depends(check_dev_mode)])
async def get_logs(
    level: Optional[str] = None,
    limit: int = 100
):
    logs = log_handler.buffer
    if level:
        logs = [l for l in logs if l.level == level.upper()]
    
    return StructuredResponse(success=True, data=logs[-limit:])

@router.get("/metrics", response_model=StructuredResponse[SystemMetrics], dependencies=[Depends(check_dev_mode)])
async def get_metrics():
    mem = psutil.virtual_memory()
    
    drives = []
    if platform.system() == "Windows":
        for part in psutil.disk_partitions(all=False):
            if 'cdrom' in part.opts or part.fstype == '':
                continue
            try:
                usage = psutil.disk_usage(part.mountpoint)
                drives.append(DriveMetrics(
                    mountpoint=part.mountpoint,
                    total=usage.total / (1024**3),
                    used=usage.used / (1024**3),
                    free=usage.free / (1024**3),
                    percent=usage.percent
                ))
            except PermissionError:
                continue
    else:
        usage = psutil.disk_usage('/')
        drives.append(DriveMetrics(
            mountpoint="/",
            total=usage.total / (1024**3),
            used=usage.used / (1024**3),
            free=usage.free / (1024**3),
            percent=usage.percent
        ))

    main_disk = drives[0] if drives else DriveMetrics(mountpoint="N/A", total=0, used=0, free=0, percent=0)

    return StructuredResponse(
        success=True,
        data=SystemMetrics(
            cpu_percent=psutil.cpu_percent(),
            ram_usage=mem.used / (1024 * 1024),
            ram_total=mem.total / (1024 * 1024),
            disk_usage=main_disk.used,
            disk_total=main_disk.total,
            drives=drives,
            uptime=time.time() - psutil.boot_time(),
            timestamp=datetime.now(timezone.utc)
        )
    )

@router.get("/trash/stats", response_model=StructuredResponse[TrashStats], dependencies=[Depends(check_dev_mode)])
async def get_trash_stats(
    db_session: Annotated[DatabaseSession, Depends(get_db_session)],
    sm: Annotated[SessionManager, Depends(get_session_manager)]
):
    with db_session.get_session() as session:
        db = DBManager(session)
        files = db.list_trashed_files()
        
        total_size = sum(f.size for f in files)
        oldest = None
        if files:
            oldest = files[-1].deleted_at
            
        config = sm.load_config()
        
        return StructuredResponse(
            success=True,
            data=TrashStats(
                total_files=len(files),
                total_size=total_size,
                oldest_item_at=oldest,
                retention_days=config.get("trash_retention_days", 30)
            )
        )

@router.get("/preview/stats", response_model=StructuredResponse[PreviewStats], dependencies=[Depends(check_dev_mode)])
async def get_preview_stats(
    sm: Annotated[SessionManager, Depends(get_session_manager)]
):
    cache_usage = 0
    if sm.preview_cache_dir.exists():
        for item in sm.preview_cache_dir.iterdir():
            if item.is_file():
                cache_usage += item.stat().st_size
                
    return StructuredResponse(
        success=True,
        data=PreviewStats(
            requests=preview_tracker.requests,
            cache_hits=preview_tracker.cache_hits,
            cache_misses=preview_tracker.cache_misses,
            cache_usage=cache_usage
        )
    )

@router.post("/preview/clear-cache", response_model=StructuredResponse[int], dependencies=[Depends(check_dev_mode)])
async def clear_preview_cache(
    sm: Annotated[SessionManager, Depends(get_session_manager)]
):
    deleted = sm.cleanup_preview_cache(max_age_minutes=0)
    return StructuredResponse(success=True, data=deleted)

@router.post("/database/optimize", response_model=StructuredResponse[dict], dependencies=[Depends(check_dev_mode)])
async def optimize_db(
    manager: Annotated[TDriveManager, Depends(get_manager)]
):
    try:
        engine = manager.db_session.engine
        with engine.connect() as connection:
            connection.execution_options(isolation_level="AUTOCOMMIT")
            from sqlalchemy import text
            connection.execute(text("VACUUM"))
            connection.execute(text("ANALYZE"))
            
        return StructuredResponse(success=True, data={"message": "Database optimized and vacuumed successfully"})
    except Exception as e:
        logging.error(f"Database optimization failed: {e}")
        raise HTTPException(status_code=500, detail=f"Optimization failed: {str(e)}")

@router.get("/telegram/diagnostic", response_model=StructuredResponse[dict], dependencies=[Depends(check_dev_mode)])
async def telegram_diagnostic(
    manager: Annotated[TDriveManager, Depends(get_manager)]
):
    try:
        me = await manager.tg_client.client.get_me()
        channel = await manager.tg_client.client.get_entity(manager.channel_id)
        return StructuredResponse(
            success=True,
            data={
                "account": me.username or str(me.id),
                "channel_name": channel.title,
                "channel_id": manager.channel_id,
                "connected": manager.tg_client.client.is_connected()
            }
        )
    except Exception as e:
        return StructuredResponse(success=False, error={"code": "TG_DIAG_FAIL", "message": str(e)})

@router.post("/config/dev-mode", response_model=StructuredResponse[bool])
async def toggle_dev_mode(
    enabled: bool,
    sm: Annotated[SessionManager, Depends(get_session_manager)]
):
    sm.set_developer_mode(enabled)
    return StructuredResponse(success=True, data=enabled)

@router.post("/system/restart", dependencies=[Depends(check_dev_mode)])
async def restart_api():
    """Triggers a graceful shutdown (assumes systemd restart)."""
    logging.warning("Developer requested system restart via API.")
    import threading
    import signal
    def shutdown():
        time.sleep(1)
        os.kill(os.getpid(), signal.SIGINT)
    threading.Thread(target=shutdown).start()
    return StructuredResponse(success=True, data={"message": "System restart initiated."})

@router.get("/support-bundle", dependencies=[Depends(check_dev_mode)])
async def generate_support_bundle(
    sm: Annotated[SessionManager, Depends(get_session_manager)]
):
    """Generates a ZIP bundle for troubleshooting."""
    bundle_path = sm.tmp_dir / f"tdrive_bundle_{int(time.time())}.zip"
    with zipfile.ZipFile(bundle_path, 'w') as zf:
        logs_text = "\n".join([f"[{l.timestamp}] {l.level} {l.module}: {l.message}" for l in log_handler.buffer])
        zf.writestr("agent_live_logs.txt", logs_text)
        sys_info = {"version": "1.3.3", "os": platform.system(), "arch": platform.machine(), "python": platform.python_version()}
        zf.writestr("system_info.json", json.dumps(sys_info, indent=4))
        db_path = sm.config_dir / "tdrive.db"
        if db_path.exists():
            temp_db = Path(tempfile.gettempdir()) / "tdrive_snap.db"
            shutil.copy2(db_path, temp_db)
            zf.write(temp_db, "tdrive_snapshot.db")
            temp_db.unlink()
    return FileResponse(path=bundle_path, filename=f"tdrive_support_bundle.zip", media_type="application/zip")

@router.post("/jobs/clear", response_model=StructuredResponse[int], dependencies=[Depends(check_dev_mode)])
async def clear_all_jobs(
    db_session: Annotated[DatabaseSession, Depends(get_db_session)]
):
    """Deletes all job history records."""
    with db_session.get_session() as session:
        from core.db.models import JobModel
        from sqlalchemy import delete
        result = session.execute(delete(JobModel))
        return StructuredResponse(success=True, data=result.rowcount)

@router.post("/audit/full", response_model=StructuredResponse[dict], dependencies=[Depends(check_dev_mode)])
async def full_audit(
    manager: Annotated[TDriveManager, Depends(get_manager)]
):
    """Performs a deep integrity audit."""
    from core.recovery import RecoveryEngine
    engine = RecoveryEngine(manager.db_session, manager.tg_client, manager.channel_id, master_password=manager.master_password)
    report = await engine.audit_integrity()
    return StructuredResponse(success=True, data=report)
