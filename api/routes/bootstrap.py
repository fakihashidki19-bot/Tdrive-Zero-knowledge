"""
TDrive Bootstrap Routes.

Handles system initialization and Telegram authentication via Web UI.
"""

from typing import Annotated
from fastapi import APIRouter, Depends, HTTPException, status
from api.schemas import (
    StructuredResponse, 
    BootstrapStatus, 
    InitRequest, 
    TGSendCodeRequest, 
    TGVerifyCodeRequest,
    ErrorDetail
)
from core.bootstrap import BootstrapService
from core.session import SessionError

router = APIRouter(prefix="/bootstrap", tags=["bootstrap"])

def get_bootstrap_service():
    return BootstrapService()

@router.get("/status", response_model=StructuredResponse[BootstrapStatus])
async def get_status(
    service: Annotated[BootstrapService, Depends(get_bootstrap_service)]
):
    """Returns the current setup status of the agent."""
    return StructuredResponse(success=True, data=service.get_status())

@router.post("/init", response_model=StructuredResponse[bool])
async def initialize_system(
    req: InitRequest,
    service: Annotated[BootstrapService, Depends(get_bootstrap_service)]
):
    """Initializes the TDrive configuration."""
    status = service.get_status()
    if status["is_initialized"]:
        raise HTTPException(
            status_code=400, 
            detail="System is already initialized. Manual config deletion required to re-init."
        )
    
    try:
        service.initialize_config(req.api_id, req.api_hash, req.channel_id, req.master_password)
        
        from api.dependencies import get_db_session
        from core.session import SessionManager
        db_factory = get_db_session(SessionManager())
        db_factory.create_tables()
        
        return StructuredResponse(success=True, data=True)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Initialization failed: {str(e)}")

@router.post("/send-code", response_model=StructuredResponse[str])
async def send_tg_code(
    req: TGSendCodeRequest,
    service: Annotated[BootstrapService, Depends(get_bootstrap_service)]
):
    """Sends a login code to the user's Telegram."""
    try:
        phone_code_hash = await service.send_login_code(req.phone)
        return StructuredResponse(success=True, data=phone_code_hash)
    except SessionError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to send code: {str(e)}")

@router.post("/verify-code", response_model=StructuredResponse[bool])
async def verify_tg_code(
    req: TGVerifyCodeRequest,
    service: Annotated[BootstrapService, Depends(get_bootstrap_service)]
):
    """Verifies the Telegram login code and creates a session."""
    try:
        await service.verify_login_code(req.phone, req.code, req.phone_code_hash, req.password)
        return StructuredResponse(success=True, data=True)
    except SessionError as e:
        if "2FA_REQUIRED" in str(e):
             return StructuredResponse(
                 success=False, 
                 error=ErrorDetail(code="2FA_REQUIRED", message="Two-factor authentication required.")
             )
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Verification failed: {str(e)}")
