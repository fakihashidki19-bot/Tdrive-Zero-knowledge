"""
TDrive Session & Configuration Manager.

Handles secure storage of Telegram credentials, encryption salts,
and application settings in the user's home directory.
"""

import json
import os
import shutil
import platform
from pathlib import Path
from typing import Any, Dict, Optional, Tuple

from core.utils import secure_permissions


class SessionError(Exception):
    """Base exception for session-related errors."""
    pass


class SessionManager:
    """
    Manages TDrive configuration and session files in ~/.tdrive/
    """

    def __init__(self, config_dir: Optional[str] = None):
        """
        Initializes the SessionManager.

        Args:
            config_dir: Optional override for the configuration directory.
                        Defaults to TDRIVE_CONFIG_DIR env var or ~/.tdrive/
        """
        if config_dir:
            self.config_dir = Path(config_dir).expanduser().resolve()
        else:
            env_dir = os.getenv("TDRIVE_CONFIG_DIR")
            if env_dir:
                self.config_dir = Path(env_dir).expanduser().resolve()
            else:
                self.config_dir = Path.home() / ".tdrive"

        self.config_file = self.config_dir / "config.json"
        self.tmp_dir = self.config_dir / "tmp"
        self.cache_dir = self.config_dir / "cache"
        self.preview_cache_dir = self.cache_dir / "previews"
        self._ensure_dirs()

    def _ensure_config_dir(self) -> None:
        """Deprecated: use _ensure_dirs instead."""
        self._ensure_dirs()

    def _ensure_dirs(self) -> None:
        """Creates config and tmp directories with secure permissions."""
        for d in [self.config_dir, self.tmp_dir, self.cache_dir, self.preview_cache_dir]:
            if not d.exists():
                d.mkdir(parents=True, exist_ok=True)
                secure_permissions(d, is_dir=True)

    def cleanup_tmp(self, max_age_hours: int = 24) -> int:
        """
        Removes files in the tmp directory older than max_age_hours.
        Returns the number of files deleted.
        """
        import time
        deleted_count = 0
        now = time.time()
        max_age_seconds = max_age_hours * 3600

        if not self.tmp_dir.exists():
            return 0

        for item in self.tmp_dir.iterdir():
            if item.is_file():
                if (now - item.stat().st_mtime) > max_age_seconds:
                    try:
                        item.unlink()
                        deleted_count += 1
                    except Exception:
                        pass
        return deleted_count

    def cleanup_preview_cache(self, max_age_minutes: int = 30) -> int:
        """
        Removes files in the preview cache older than max_age_minutes.
        """
        import time
        deleted_count = 0
        now = time.time()
        max_age_seconds = max_age_minutes * 60

        if not self.preview_cache_dir.exists():
            return 0

        for item in self.preview_cache_dir.iterdir():
            if item.is_file():
                if (now - item.stat().st_mtime) > max_age_seconds:
                    try:
                        item.unlink()
                        deleted_count += 1
                    except Exception:
                        pass
        return deleted_count

    def save_config(self, config_data: Dict[str, Any]) -> None:
        """
        Saves configuration data to config.json atomically.

        Args:
            config_data: Dictionary containing configuration key-values.
        """
        temp_file = self.config_file.with_suffix(".tmp")
        try:
            with open(temp_file, "w") as f:
                json.dump(config_data, f, indent=4)
            
            secure_permissions(temp_file)
            
            shutil.move(str(temp_file), str(self.config_file))
        except Exception as e:
            if temp_file.exists():
                temp_file.unlink()
            raise SessionError(f"Failed to save configuration: {str(e)}")

    def load_config(self) -> Dict[str, Any]:
        """
        Loads configuration from config.json.

        Returns:
            Dictionary containing the configuration.

        Raises:
            SessionError: If the config file is missing or corrupted.
        """
        if not self.config_file.exists():
            return {}

        try:
            with open(self.config_file, "r") as f:
                data = json.load(f)
                if not isinstance(data, dict):
                    raise ValueError("Config content is not a JSON object")
                return data
        except (json.JSONDecodeError, ValueError) as e:
            raise SessionError(f"Configuration file is corrupted: {str(e)}")
        except Exception as e:
            raise SessionError(f"Failed to load configuration: {str(e)}")

    def get_api_credentials(self) -> Tuple[Optional[int], Optional[str]]:
        """
        Retrieves API ID and Hash from config.

        Returns:
            A tuple of (api_id, api_hash).
        """
        config = self.load_config()
        return config.get("api_id"), config.get("api_hash")

    def save_api_credentials(self, api_id: int, api_hash: str) -> None:
        """Saves API credentials to the config."""
        config = self.load_config()
        config["api_id"] = api_id
        config["api_hash"] = api_hash
        self.save_config(config)

    def is_developer_mode(self) -> bool:
        """Checks if developer mode is enabled."""
        config = self.load_config()
        features = config.get("features", {})
        return features.get("developer_mode", config.get("developer_mode", False))

    def set_developer_mode(self, enabled: bool) -> None:
        """Enables or disables developer mode."""
        self.update_feature_flag("developer_mode", enabled)

    def update_feature_flag(self, flag_name: str, enabled: bool) -> None:
        """Updates a specific feature flag in the config."""
        config = self.load_config()
        if "features" not in config:
            config["features"] = {}
        config["features"][flag_name] = enabled
        
        if flag_name == "developer_mode":
            config["developer_mode"] = enabled
            
        self.save_config(config)

    def get_feature_flags(self) -> Dict[str, bool]:
        """Returns all feature flags."""
        config = self.load_config()
        return config.get("features", {})

    def get_salt(self) -> Optional[str]:
        """Retrieves the master salt (hex string) from config."""
        config = self.load_config()
        return config.get("master_salt")

    def save_salt(self, salt_hex: str) -> None:
        """Saves the master salt to the config."""
        config = self.load_config()
        config["master_salt"] = salt_hex
        self.save_config(config)

    def verify_password(self, password: str) -> bool:
        """
        Validates the master password against the stored verification blob.
        Returns True if correct, False otherwise.
        """
        from core.crypto import derive_key, decrypt, CryptoError
        config = self.load_config()
        salt_hex = config.get("master_salt")
        blob_hex = config.get("password_verification")
        
        if not salt_hex or not blob_hex:
            return False

        try:
            salt = bytes.fromhex(salt_hex)
            payload = bytes.fromhex(blob_hex)
            
            nonce = payload[:12]
            ciphertext = payload[12:]
            
            key = derive_key(password, salt)
            plaintext = decrypt(nonce, ciphertext, key)
            
            return plaintext == b"tdrive-verified"
        except (CryptoError, ValueError, Exception):
            return False

    def setup_password_verification(self, password: str) -> None:
        """
        Creates a verification blob for the given master password.
        Used during 'tdrive init'.
        """
        from core.crypto import derive_key, encrypt
        config = self.load_config()
        salt_hex = config.get("master_salt")
        if not salt_hex:
             raise SessionError("Salt not found. Run init first.")
        
        salt = bytes.fromhex(salt_hex)
        key = derive_key(password, salt)
        nonce, ciphertext = encrypt(b"tdrive-verified", key)
        
        verification_blob = (nonce + ciphertext).hex()
        config["password_verification"] = verification_blob
        self.save_config(config)
