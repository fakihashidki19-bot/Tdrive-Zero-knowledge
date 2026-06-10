"""
TDrive Job Routes.
"""

from typing import Annotated, List
from fastapi import APIRouter, Depends, HTTPException, status
from api.dependencies import get_db_session, get_manager
from api.schemas import StructuredResponse, JobSchema
from core.db.manager import DBManager
from core.db.session import DatabaseSession

router = APIRouter(prefix="/jobs", tags=["jobs"])

@router.get("", response_model=StructuredResponse[List[JobSchema]])
async def list_jobs(
    db_session: Annotated[DatabaseSession, Depends(get_db_session)],
    status: str = None
):
    with db_session.get_session() as session:
        db = DBManager(session)
        jobs = db.list_jobs(status=status)
        return StructuredResponse(success=True, data=[JobSchema.model_validate(j) for j in jobs])

@router.get("/{job_id}", response_model=StructuredResponse[JobSchema])
async def get_job(
    job_id: str,
    db_session: Annotated[DatabaseSession, Depends(get_db_session)]
):
    with db_session.get_session() as session:
        db = DBManager(session)
        job = db.get_job(job_id)
        if not job:
            raise HTTPException(status_code=404, detail="Job not found")
        return StructuredResponse(success=True, data=JobSchema.model_validate(job))

@router.delete("/{job_id}", response_model=StructuredResponse[None])
async def delete_job(
    job_id: str,
    db_session: Annotated[DatabaseSession, Depends(get_db_session)]
):
    with db_session.get_session() as session:
        db = DBManager(session)
        if db.delete_job(job_id):
            return StructuredResponse(success=True)
        raise HTTPException(status_code=404, detail="Job not found")
