"""
System Settings Model
=====================
Stores system-wide configuration including demo mode settings.
"""

from sqlalchemy import Column, Integer, String, Boolean, DateTime, Text
from sqlalchemy.sql import func
from database import PostgresBase, PostgresSessionLocal
import logging

log = logging.getLogger("system_settings")


class SystemSettings(PostgresBase):
    """
    System-wide settings stored in PostgreSQL.
    Uses key-value pairs for flexibility.
    """
    __tablename__ = "system_settings"
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    key = Column(String(100), unique=True, nullable=False, index=True)
    value = Column(Text, nullable=True)
    value_type = Column(String(20), default="string")  # string, boolean, integer, float, json
    description = Column(Text, nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())


# =============================================================================
# Default Settings
# =============================================================================

DEFAULT_SETTINGS = {
    # Demo Mode Settings
    "demo_mode_enabled": {
        "value": "true",
        "value_type": "boolean",
        "description": "Enable demo mode (uses embedded SCADA emulator instead of real MSSQL)"
    },
    "mock_sap_enabled": {
        "value": "true",
        "value_type": "boolean",
        "description": "Enable mock SAP mode (sends to localhost:6000 instead of real SAP)"
    },
    "emulator_auto_start": {
        "value": "true",
        "value_type": "boolean",
        "description": "Automatically start embedded emulator when demo mode is enabled"
    },
    
    # Emulator Configuration
    "emulator_interval": {
        "value": "10",
        "value_type": "float",
        "description": "Seconds between emulator data updates"
    },
    "emulator_step_min": {
        "value": "1",
        "value_type": "float",
        "description": "Minimum increment per emulator tick"
    },
    "emulator_step_max": {
        "value": "10",
        "value_type": "float",
        "description": "Maximum increment per emulator tick"
    },
    # Scale Configuration (JSON string of active scales)
    "emulator_active_scales": {
        "value": "[]",
        "value_type": "json",
        "description": "List of active SCADA tags in emulator"
    },

    # Order Routing (A1)
    "default_plant": {
        "value": "3130",
        "value_type": "string",
        "description": "Plant code assumed for orders that arrive from SAP without one. "
                       "Used to pick shift rows out of shift_master."
    },

    # Validator Tuning (A5)
    "auto_validator_interval_seconds": {
        "value": "1",
        "value_type": "float",
        "description": "Seconds the auto-validation worker sleeps between cycles. "
                       "Read once per cycle, so a change applies without a restart. "
                       "Clamped to 0.1-60."
    },

    # Mill nameplate (B4)
    "mill_nameplate_tph": {
        "value": "25",
        "value_type": "float",
        "description": "Mill nameplate capacity in tons/hour"
    },
}


# =============================================================================
# Helper Functions
# =============================================================================

def get_setting(key: str, default=None):
    """Get a setting value by key."""
    try:
        with PostgresSessionLocal() as db:
            setting = db.query(SystemSettings).filter(SystemSettings.key == key).first()
            if not setting:
                return default
            
            # Convert based on type
            if setting.value_type == "boolean":
                return setting.value.lower() in ("true", "1", "yes", "on")
            elif setting.value_type == "integer":
                return int(setting.value) if setting.value else default
            elif setting.value_type == "float":
                return float(setting.value) if setting.value else default
            else:
                return setting.value
    except Exception as e:
        log.error(f"Error getting setting {key}: {e}")
        return default


def set_setting(key: str, value, value_type: str = None, description: str = None):
    """Set a setting value."""
    try:
        with PostgresSessionLocal() as db:
            setting = db.query(SystemSettings).filter(SystemSettings.key == key).first()
            
            # Convert value to string for storage
            str_value = str(value).lower() if isinstance(value, bool) else str(value)
            
            if setting:
                setting.value = str_value
                if value_type:
                    setting.value_type = value_type
                if description:
                    setting.description = description
            else:
                setting = SystemSettings(
                    key=key,
                    value=str_value,
                    value_type=value_type or "string",
                    description=description
                )
                db.add(setting)
            
            db.commit()
            return True
    except Exception as e:
        log.error(f"Error setting {key}: {e}")
        return False


def get_all_settings() -> dict:
    """Get all settings as a dictionary."""
    try:
        with PostgresSessionLocal() as db:
            settings = db.query(SystemSettings).all()
            result = {}
            for s in settings:
                if s.value_type == "boolean":
                    result[s.key] = s.value.lower() in ("true", "1", "yes", "on")
                elif s.value_type == "integer":
                    result[s.key] = int(s.value) if s.value else 0
                elif s.value_type == "float":
                    result[s.key] = float(s.value) if s.value else 0.0
                else:
                    result[s.key] = s.value
            return result
    except Exception as e:
        log.error(f"Error getting all settings: {e}")
        return {}


def init_default_settings():
    """Initialize default settings if they don't exist."""
    try:
        with PostgresSessionLocal() as db:
            for key, config in DEFAULT_SETTINGS.items():
                existing = db.query(SystemSettings).filter(SystemSettings.key == key).first()
                if not existing:
                    setting = SystemSettings(
                        key=key,
                        value=config["value"],
                        value_type=config["value_type"],
                        description=config["description"]
                    )
                    db.add(setting)
                    log.info(f"✅ Created default setting: {key}")
            
            db.commit()
            log.info("✅ Default system settings initialized")
    except Exception as e:
        log.error(f"Error initializing default settings: {e}")


def is_demo_mode_enabled() -> bool:
    """Quick check if demo mode is enabled."""
    return get_setting("demo_mode_enabled", True)


def is_mock_sap_enabled() -> bool:
    """Quick check if mock SAP mode is enabled."""
    return get_setting("mock_sap_enabled", True)


def is_emulator_auto_start() -> bool:
    """Check if emulator should auto-start."""
    return get_setting("emulator_auto_start", True)
