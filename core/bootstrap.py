"""
TDrive Bootstrap Service.

Unified logic for system initialization and Telegram authentication
shared between CLI and Web interfaces.
"""

import os
import asyncio
from typing import Optional, Dict, Any
from pathlib import Path

from core.session import SessionManager, SessionError
from core.crypto import generate_salt
from telethon import TelegramClient
from telethon.errors import SessionPasswordNeededError


class BootstrapService:
    """
    Handles the onboarding and setup flow for TDrive.
    """

    def __init__(self, sm: Optional[SessionManager] = None):
        self.sm = sm or SessionManager()
        self._temp_client: Optional[TelegramClient] = None
        self._phone_code_hash: Optional[str] = None

    def get_status(self) -> Dict[str, Any]:
        """Returns the current setup status."""
        config = self.sm.load_config()
        is_initialized = bool(config and config.get("api_id") and config.get("api_hash"))
        
        session_file = self.sm.config_dir / "tdrive.session"
        is_logged_in = session_file.exists()
        
        has_password = bool(config.get("password_verification"))
        
        return {
            "is_initialized": is_initialized,
            "is_logged_in": is_logged_in,
            "has_master_password": has_password,
            "config_path": str(self.sm.config_file),
            "session_path": str(session_file)
        }

    def initialize_config(self, api_id: int, api_hash: str, channel_id: int, master_password: str) -> None:
        """
        Creates the initial config.json and sets up encryption.
        """
        master_salt = generate_salt().hex()
        
        config = {
            "api_id": api_id,
            "api_hash": api_hash,
            "channel_id": channel_id,
            "master_salt": master_salt
        }
        
        self.sm.save_config(config)
        self.sm.setup_password_verification(master_password)

    async def send_login_code(self, phone: str) -> str:
        """
        Starts the Telegram login process by sending a code.
        Returns the phone_code_hash needed for verification.
        """
        config = self.sm.load_config()
        if not config:
            raise SessionError("TDrive not initialized")

        session_path = self.sm.config_dir / "tdrive.session"
        client = TelegramClient(str(session_path), config["api_id"], config["api_hash"])
        await client.connect()
        
        try:
            sent_code = await client.send_code_request(phone)
            self._phone_code_hash = sent_code.phone_code_hash
            await client.disconnect()
            return self._phone_code_hash
        except Exception as e:
            await client.disconnect()
            raise SessionError(f"Failed to send code: {str(e)}")

    async def verify_login_code(self, phone: str, code: str, phone_code_hash: str, password: Optional[str] = None) -> bool:
        """
        Completes the Telegram login with the received code.
        Supports 2FA if password is provided.
        """
        config = self.sm.load_config()
        session_path = self.sm.config_dir / "tdrive.session"
        client = TelegramClient(str(session_path), config["api_id"], config["api_hash"])
        await client.connect()

        try:
            try:
                await client.sign_in(phone=phone, code=code, phone_code_hash=phone_code_hash)
            except SessionPasswordNeededError:
                if not password:
                    raise SessionError("2FA_REQUIRED")
                await client.sign_in(password=password)
            
            await client.disconnect()
            return True
        except Exception as e:
            await client.disconnect()
            if "2FA_REQUIRED" in str(e):
                raise
            raise SessionError(f"Login failed: {str(e)}")
