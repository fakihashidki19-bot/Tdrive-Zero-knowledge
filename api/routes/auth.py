"""
TDrive Auth Routes.
"""

from typing import Annotated
from fastapi import APIRouter, Depends, HTTPException, status
from api.schemas import LoginRequest, LoginResponse, StructuredResponse
from api.dependencies import create_session, clear_session, check_login_brute_force, record_login_failure, reset_login_failures, _state, get_session_manager
from core.session import SessionManager

router = APIRouter(prefix="/auth", tags=["auth"])

@router.post("/login", response_model=StructuredResponse[LoginResponse])
async def login(
    request: LoginRequest,
    sm: Annotated[SessionManager, Depends(get_session_manager)]
):
    """
    Sets the master password and generates a dynamic session token.
    Includes brute-force protection and password verification.
    """
    check_login_brute_force()

    if not request.password:
        record_login_failure()
        raise HTTPException(status_code=400, detail="Password required")
    
    if not sm.verify_password(request.password):
        record_login_failure()
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED, 
            detail="Invalid master password"
        )

    reset_login_failures()
    token = create_session(request.password)
    
    return StructuredResponse(
        success=True,
        data=LoginResponse(
            access_token=token,
            csrf_token=_state.csrf_token
        )
    )

@router.post("/logout", response_model=StructuredResponse[None])
async def logout():
    """Clears the session."""
    clear_session()
    return StructuredResponse(success=True)
