"""
TDrive Integrity Guard.

Deterministic security layer to detect unauthorized environment changes.
Blocks destructive actions via a strict State Machine.
"""

import hashlib
import os
import uuid
import platform
import logging
from pathlib import Path
from typing import Dict, Any, Optional
from core.session import SessionManager
from core.utils import secure_permissions

logger = logging.getLogger(__name__)

class IntegrityState:
    INIT = "INIT"
    LOCKED = "LOCKED"
    SAFE_MODE = "SAFE_MODE"
    VERIFIED = "VERIFIED"
    FULL_ACCESS = "FULL_ACCESS"

class IntegrityGuard:
    """
    Manages the integrity state of the TDrive instance.
    Ensures that write operations are only performed in authorized environments.
    """

    def __init__(self, sm: Optional[SessionManager] = None):
        self.sm = sm or SessionManager()
        self.lock_file = self.sm.config_dir / "instance.lock"

    def get_machine_id(self) -> str:
        """Generates a stable identifier for the current hardware."""
        node = uuid.getnode()
        plat = f"{platform.system()}-{platform.machine()}-{platform.node()}"
        raw = f"{node}:{plat}"
        return hashlib.sha256(raw.encode()).hexdigest()

    def generate_fingerprint(self) -> Optional[str]:
        """Creates a unique fingerprint for this TDrive instance."""
        config = self.sm.load_config()
        if not config:
            return None
        
        salt = config.get("master_salt", "")
        channel_id = str(config.get("channel_id", ""))
        machine_id = self.get_machine_id()
        
        # Identity = Salt + Channel + Hardware
        raw = f"{salt}:{channel_id}:{machine_id}"
        return hashlib.sha256(raw.encode()).hexdigest()

    def is_ci_environment(self) -> bool:
        """Detects common CI/CD environments."""
        ci_triggers = ["GITHUB_ACTIONS", "CI", "VERCEL", "NETLIFY", "TRAVIS"]
        return any(os.environ.get(env) for env in ci_triggers)

    def get_integrity_status(self) -> Dict[str, Any]:
        """
        Determines the current integrity state and allowed operations.
        """
        # 1. CI Detection (Temporary Read-Only Override)
        if self.is_ci_environment():
            return {
                "state": IntegrityState.SAFE_MODE,
                "safe_mode": True,
                "read_only": True,
                "message": "CI Environment detected. Destructive actions blocked."
            }

        config = self.sm.load_config()
        if not config:
            return {
                "state": IntegrityState.INIT,
                "safe_mode": False,
                "read_only": False,
                "message": "System not initialized."
            }

        # 2. Lock File Presence
        if not self.lock_file.exists():
            return {
                "state": IntegrityState.LOCKED,
                "safe_mode": True,
                "read_only": True,
                "message": "Environment not authorized. Run: tdrive verify-instance"
            }

        # 3. Fingerprint Match
        current_fp = self.generate_fingerprint()
        try:
            stored_fp = self.lock_file.read_text().strip()
        except Exception:
            stored_fp = ""

        if current_fp != stored_fp:
            return {
                "state": IntegrityState.SAFE_MODE,
                "safe_mode": True,
                "read_only": True,
                "message": "Fingerprint mismatch. Environment moved. Run: tdrive verify-instance"
            }

        # 4. Authorized Access
        return {
            "state": IntegrityState.FULL_ACCESS,
            "safe_mode": False,
            "read_only": False,
            "message": "Environment verified. Full access granted."
        }

    def verify_instance(self, password: str, reset: bool = False) -> bool:
        """
        Explicitly authorizes the current environment.
        Requires master password confirmation.
        """
        if not self.sm.verify_password(password):
            logger.error("Integrity verification failed: Invalid Master Password.")
            return False

        if not reset and self.lock_file.exists():
            # Check if it already matches to avoid unnecessary writes
            if self.generate_fingerprint() == self.lock_file.read_text().strip():
                return True

        fp = self.generate_fingerprint()
        if not fp:
            return False
        
        try:
            self.lock_file.write_text(fp)
            secure_permissions(self.lock_file)
            logger.info(f"Instance fingerprint locked successfully.")
            return True
        except Exception as e:
            logger.error(f"Failed to write instance lock: {e}")
            return False
