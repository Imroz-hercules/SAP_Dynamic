# database.py
import os
import logging
from pathlib import Path
from dotenv import load_dotenv
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, declarative_base

# Load backend/.env so scripts and Flask both pick up DB URLs
load_dotenv(Path(__file__).resolve().parent / ".env")

log = logging.getLogger("database")

# =============================================================================
# SCADA EMULATOR & DEMO MODE CONFIGURATION
# =============================================================================
# These are default fallback values. Runtime values are read from system_settings
# table via get_demo_mode() and get_emulator_url() functions.
#
# DEMO MODE: Uses embedded emulator for SCADA data
# PRODUCTION MODE: Uses real MSSQL for SCADA data
# =============================================================================

# Legacy flags (kept for backward compatibility)
USE_SCADA_EMULATOR = True
SCADA_EMULATOR_URL = "http://localhost:7000"

# Embedded emulator URL (used when demo mode is enabled)
EMBEDDED_EMULATOR_URL = "/api/emulator/latest"

# =============================================================================

# SQL Server (SCADA read-only). Override with MSSQL_URL in backend/.env
mssql_connection_string = os.getenv(
    "MSSQL_URL",
    "mssql+pyodbc://Hercules:nl6oUpr@localhost/HerculesV2"
    "?driver=ODBC+Driver+17+for+SQL+Server&TrustServerCertificate=yes",
)
engine = create_engine(mssql_connection_string)  # <-- MSSQL engine (kept for routes)
SessionLocal = sessionmaker(bind=engine, autocommit=False, autoflush=False)

# PostgreSQL (app CRUD). Override with POSTGRES_URL in backend/.env
postgres_url = os.getenv(
    "POSTGRES_URL",
    "postgresql+psycopg2://postgres:Hercules@localhost:5432/sap",
)
postgres_engine = create_engine(postgres_url)
PostgresSessionLocal = sessionmaker(bind=postgres_engine, autocommit=False, autoflush=False)

# Base for PostgreSQL models
PostgresBase = declarative_base()

# Base for MSSQL models (existing)
Base = declarative_base()


# =============================================================================
# Dynamic Mode Functions
# =============================================================================

def get_demo_mode() -> bool:
    """
    Get current demo mode status from database settings.
    Falls back to USE_SCADA_EMULATOR if settings table not available.
    """
    try:
        from models.system_settings import is_demo_mode_enabled
        return is_demo_mode_enabled()
    except Exception as e:
        log.debug(f"Could not read demo mode from DB, using default: {e}")
        return USE_SCADA_EMULATOR


def get_mock_sap_mode() -> bool:
    """
    Get current mock SAP mode status from database settings.
    """
    try:
        from models.system_settings import is_mock_sap_enabled
        return is_mock_sap_enabled()
    except Exception as e:
        log.debug(f"Could not read mock SAP mode from DB: {e}")
        return True  # Default to mock mode for safety


def get_emulator_url() -> str:
    """
    Get the URL for SCADA data based on current mode.
    - Demo mode: Uses embedded emulator
    - Production mode: Uses real MSSQL (returns None)
    """
    if get_demo_mode():
        return EMBEDDED_EMULATOR_URL
    return None


def get_scada_source() -> str:
    """
    Get a human-readable description of the current SCADA data source.
    """
    if get_demo_mode():
        return "Embedded SCADA Emulator (Demo Mode)"
    return "MSSQL Database (Production Mode)"

