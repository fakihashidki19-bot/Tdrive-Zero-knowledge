"""
TDrive Feature Registry Engine.

Centralizes all system features and their operational status.
Provides a runtime Single Source of Truth (SSOT) for feature toggles.
"""

import logging
from typing import Dict, Any, List, Optional
from core.session import SessionManager

logger = logging.getLogger(__name__)

class FeatureID:
    # CORE (Immutable)
    AES_ENCRYPTION = "F-CORE-01"
    STREAMING_CHUNKS = "F-CORE-02"
    STATELESS_METADATA = "F-CORE-03"
    MTPROTO_BRIDGE = "F-CORE-04"
    
    # SECURITY
    ZERO_KNOWLEDGE_AUTH = "F-SEC-01"
    INTEGRITY_GUARD = "F-SEC-02"
    SAFE_MODE_CI = "F-SEC-03"
    DUAL_TOKEN_SECURITY = "F-SEC-04"
    RATE_LIMITING = "F-SEC-05"
    
    # UI / UX
    RESPONSIVE_GRID = "F-UI-01"
    DENSITY_ENGINE = "F-UI-02"
    RICH_PREVIEW = "F-UI-03"
    BULK_ACTIONS = "F-UI-04"
    CLI_TOOLSET = "F-UI-05"
    
    # OPTIONAL / EXPERIMENTAL
    BACKGROUND_MATERIALIZATION = "F-OPT-01"
    AUTO_TRASH_PURGE = "F-OPT-02"
    DEVELOPER_CONSOLE = "F-OPT-03"
    BOT_INTERFACE = "F-OPT-04"

class FeatureRegistry:
    """
    Manages the feature map and resolves toggles against user configuration.
    """

    def __init__(self, sm: Optional[SessionManager] = None):
        self.sm = sm or SessionManager()
        self._feature_map = self._initialize_map()

    def _get_default_flags(self) -> Dict[str, bool]:
        """Default values for togglable features."""
        return {
            "developer_mode": True,
            "bulk_actions": True,
            "rich_preview": True,
            "integrity_guard": True,
            "auto_materialization": True,
            "trash_system": True,
            "bot_interface": False,
            "bot_write_access": False,
            "ci_readonly": True
        }

    def _initialize_map(self) -> Dict[str, Any]:
        """Maps canonical features to categories and default states."""
        return {
            "core": {
                FeatureID.AES_ENCRYPTION: {"name": "AES-256-GCM Encryption", "immutable": True},
                FeatureID.STREAMING_CHUNKS: {"name": "Streaming Chunk Pipeline", "immutable": True},
                FeatureID.STATELESS_METADATA: {"name": "Stateless Metadata Backbone", "immutable": True},
                FeatureID.MTPROTO_BRIDGE: {"name": "Resilient MTProto Bridge", "immutable": True},
            },
            "security": {
                FeatureID.ZERO_KNOWLEDGE_AUTH: {"name": "Zero-Knowledge Auth", "immutable": True},
                FeatureID.INTEGRITY_GUARD: {"name": "Repository Integrity Guard", "flag": "integrity_guard"},
                FeatureID.SAFE_MODE_CI: {"name": "Safe Mode & CI Detection", "immutable": True},
                FeatureID.DUAL_TOKEN_SECURITY: {"name": "Dual-Token CSRF/Session", "immutable": True},
                FeatureID.RATE_LIMITING: {"name": "Global Rate Limiting", "immutable": True},
            },
            "ui": {
                FeatureID.RESPONSIVE_GRID: {"name": "Responsive Grid System", "immutable": True},
                FeatureID.DENSITY_ENGINE: {"name": "Layout Density Engine", "immutable": True},
                FeatureID.RICH_PREVIEW: {"name": "Rich Preview Engine", "flag": "rich_preview"},
                FeatureID.BULK_ACTIONS: {"name": "Multi-Select Bulk Actions", "flag": "bulk_actions"},
                FeatureID.CLI_TOOLSET: {"name": "CLI Administrative Tools", "immutable": True},
            },
            "optional": {
                FeatureID.BACKGROUND_MATERIALIZATION: {"name": "Auto Materialization", "flag": "auto_materialization"},
                FeatureID.AUTO_TRASH_PURGE: {"name": "Automated Trash Purge", "flag": "trash_system"},
                FeatureID.DEVELOPER_CONSOLE: {"name": "Developer Console", "flag": "developer_mode"},
                FeatureID.BOT_INTERFACE: {"name": "Telegram Bot Interface", "flag": "bot_interface"},
            }
        }

    def get_feature_flags(self) -> Dict[str, bool]:
        """Resolves current feature flags from config.json."""
        config = self.sm.load_config() or {}
        user_flags = config.get("features", {})
        
        flags = self._get_default_flags()
        flags.update(user_flags)
        return flags

    def is_enabled(self, feature_id: str) -> bool:
        """Checks if a specific feature is currently enabled."""
        # 1. Find feature in map
        feature_data = None
        for group in self._feature_map.values():
            if feature_id in group:
                feature_data = group[feature_id]
                break
        
        if not feature_data:
            logger.warning(f"Feature Registry: Unknown feature ID {feature_id}")
            return False

        # 2. Check immutability
        if feature_data.get("immutable"):
            return True

        # 3. Resolve flag
        flag_name = feature_data.get("flag")
        if not flag_name:
            return True
            
        flags = self.get_feature_flags()
        return flags.get(flag_name, False)

    def get_runtime_map(self) -> Dict[str, List[Dict[str, Any]]]:
        """Returns the full feature map with current enablement status."""
        flags = self.get_feature_flags()
        runtime_map = {
            "core": [],
            "security": [],
            "ui": [],
            "optional": []
        }

        for group_name, features in self._feature_map.items():
            for fid, data in features.items():
                is_enabled = True
                if not data.get("immutable"):
                    flag_name = data.get("flag")
                    is_enabled = flags.get(flag_name, False) if flag_name else True

                runtime_map[group_name].append({
                    "id": fid,
                    "name": data["name"],
                    "enabled": is_enabled,
                    "immutable": data.get("immutable", False)
                })

        return runtime_map
