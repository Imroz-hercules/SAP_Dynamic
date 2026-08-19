"""
System Mode Routes
==================
API endpoints for managing demo/production mode and system settings.
"""

from flask import Blueprint, request, jsonify
from sqlalchemy import text
import logging

log = logging.getLogger("system_mode_routes")

system_mode_bp = Blueprint("system_mode", __name__, url_prefix="/api/system")


# =============================================================================
# System Mode Status
# =============================================================================

@system_mode_bp.route("/mode", methods=["GET"])
def get_system_mode():
    """Get current system mode and status."""
    try:
        from models.system_settings import (
            is_demo_mode_enabled, 
            is_mock_sap_enabled,
            is_emulator_auto_start,
            get_all_settings,
        )
        from services.embedded_emulator import get_emulator
        
        emulator = get_emulator()
        emulator_status = emulator.get_status()
        
        return jsonify({
            "demo_mode": is_demo_mode_enabled(),
            "mock_sap": is_mock_sap_enabled(),
            "emulator_auto_start": is_emulator_auto_start(),
            "emulator_running": emulator_status.get("running", False),
            "emulator_active_scales": emulator_status.get("active_scales", 0),
            "emulator_last_update": emulator_status.get("last_update"),
            "settings": get_all_settings(),
        })
    except Exception as e:
        log.error(f"Error getting system mode: {e}")
        return jsonify({"error": str(e)}), 500


@system_mode_bp.route("/mode", methods=["PUT"])
def set_system_mode():
    """Update system mode settings."""
    try:
        from models.system_settings import set_setting, get_setting
        from services.embedded_emulator import get_emulator
        
        data = request.get_json() or {}
        
        # Update settings
        if "demo_mode" in data:
            set_setting("demo_mode_enabled", data["demo_mode"], "boolean")
            
            # Auto-start/stop emulator based on mode
            emulator = get_emulator()
            if data["demo_mode"]:
                if get_setting("emulator_auto_start", True):
                    emulator.start()
                    log.info("🚀 Emulator auto-started (demo mode enabled)")
            else:
                if emulator.running:
                    emulator.stop()
                    log.info("⏹️ Emulator stopped (demo mode disabled)")
        
        if "mock_sap" in data:
            set_setting("mock_sap_enabled", data["mock_sap"], "boolean")
        
        if "emulator_auto_start" in data:
            set_setting("emulator_auto_start", data["emulator_auto_start"], "boolean")
        
        # Emulator config
        emulator = get_emulator()
        if "emulator_interval" in data:
            set_setting("emulator_interval", data["emulator_interval"], "float")
            emulator.set_config(interval=float(data["emulator_interval"]))
        
        if "emulator_step_min" in data:
            set_setting("emulator_step_min", data["emulator_step_min"], "float")
            emulator.set_config(step_min=float(data["emulator_step_min"]))
        
        if "emulator_step_max" in data:
            set_setting("emulator_step_max", data["emulator_step_max"], "float")
            emulator.set_config(step_max=float(data["emulator_step_max"]))
        
        return jsonify({"status": "ok", "message": "Settings updated"})
    except Exception as e:
        log.error(f"Error setting system mode: {e}")
        return jsonify({"error": str(e)}), 500


# =============================================================================
# Database Reset Functions (Demo Tables Only)
# =============================================================================

@system_mode_bp.route("/reset/kpi-tracking", methods=["POST"])
def reset_kpi_tracking():
    """Reset kpi_send_tracking table (clear all baseline records)."""
    try:
        from database import PostgresSessionLocal
        
        with PostgresSessionLocal() as db:
            result = db.execute(text("DELETE FROM kpi_send_tracking"))
            deleted = result.rowcount
            db.commit()
        
        log.info(f"🗑️ Cleared {deleted} records from kpi_send_tracking")
        return jsonify({
            "status": "ok",
            "message": f"Cleared {deleted} records from kpi_send_tracking",
            "deleted_count": deleted
        })
    except Exception as e:
        log.error(f"Error resetting kpi_send_tracking: {e}")
        return jsonify({"error": str(e)}), 500


@system_mode_bp.route("/reset/scada-aggregate", methods=["POST"])
def reset_scada_aggregate():
    """Reset scada_aggregate_values table."""
    try:
        from database import PostgresSessionLocal
        
        with PostgresSessionLocal() as db:
            result = db.execute(text("DELETE FROM scada_aggregate_values"))
            deleted = result.rowcount
            db.commit()
        
        log.info(f"🗑️ Cleared {deleted} records from scada_aggregate_values")
        return jsonify({
            "status": "ok",
            "message": f"Cleared {deleted} records from scada_aggregate_values",
            "deleted_count": deleted
        })
    except Exception as e:
        log.error(f"Error resetting scada_aggregate_values: {e}")
        return jsonify({"error": str(e)}), 500


@system_mode_bp.route("/reset/kpi-snapshots", methods=["POST"])
def reset_kpi_snapshots():
    """Reset both milling and packing KPI snapshot tables."""
    try:
        from database import PostgresSessionLocal
        
        deleted_milling = 0
        deleted_packing = 0
        
        with PostgresSessionLocal() as db:
            result = db.execute(text("DELETE FROM milling_kpi_snapshots"))
            deleted_milling = result.rowcount
            
            result = db.execute(text("DELETE FROM packing_kpi_snapshots"))
            deleted_packing = result.rowcount
            
            db.commit()
        
        log.info(f"🗑️ Cleared {deleted_milling} milling + {deleted_packing} packing snapshots")
        return jsonify({
            "status": "ok",
            "message": f"Cleared {deleted_milling} milling and {deleted_packing} packing snapshots",
            "deleted_milling": deleted_milling,
            "deleted_packing": deleted_packing,
        })
    except Exception as e:
        log.error(f"Error resetting KPI snapshots: {e}")
        return jsonify({"error": str(e)}), 500


@system_mode_bp.route("/reset/all-demo-data", methods=["POST"])
def reset_all_demo_data():
    """Reset all demo-related data (KPI tracking, SCADA aggregates, snapshots)."""
    try:
        from database import PostgresSessionLocal
        from services.embedded_emulator import get_emulator
        
        totals = {
            "kpi_tracking": 0,
            "scada_aggregate": 0,
            "milling_snapshots": 0,
            "packing_snapshots": 0,
        }
        
        with PostgresSessionLocal() as db:
            # KPI tracking
            result = db.execute(text("DELETE FROM kpi_send_tracking"))
            totals["kpi_tracking"] = result.rowcount
            
            # SCADA aggregate
            result = db.execute(text("DELETE FROM scada_aggregate_values"))
            totals["scada_aggregate"] = result.rowcount
            
            # KPI snapshots
            result = db.execute(text("DELETE FROM milling_kpi_snapshots"))
            totals["milling_snapshots"] = result.rowcount
            
            result = db.execute(text("DELETE FROM packing_kpi_snapshots"))
            totals["packing_snapshots"] = result.rowcount
            
            db.commit()
        
        # Also reset emulator values
        emulator = get_emulator()
        emulator.reset_to_realistic()
        
        total_deleted = sum(totals.values())
        log.info(f"🗑️ Cleared all demo data: {total_deleted} total records")
        
        return jsonify({
            "status": "ok",
            "message": f"Cleared {total_deleted} total records and reset emulator",
            "deleted": totals,
            "emulator_reset": True,
        })
    except Exception as e:
        log.error(f"Error resetting all demo data: {e}")
        return jsonify({"error": str(e)}), 500


# =============================================================================
# Connection Test Endpoints
# =============================================================================

@system_mode_bp.route("/test/postgres", methods=["GET"])
def test_postgres():
    """Test PostgreSQL connection."""
    try:
        from database import postgres_engine
        
        with postgres_engine.connect() as conn:
            result = conn.execute(text("SELECT version()"))
            version = result.scalar()
        
        return jsonify({
            "status": "connected",
            "version": version[:100] if version else "Unknown"
        })
    except Exception as e:
        log.error(f"PostgreSQL connection error: {e}")
        return jsonify({"status": "error", "error": str(e)}), 500


@system_mode_bp.route("/test/mssql", methods=["GET"])
def test_mssql():
    """Test MSSQL connection."""
    try:
        from database import engine as mssql_engine
        
        with mssql_engine.connect() as conn:
            result = conn.execute(text("SELECT @@VERSION"))
            version = result.scalar()
        
        return jsonify({
            "status": "connected",
            "version": version[:100] if version else "Unknown"
        })
    except Exception as e:
        log.error(f"MSSQL connection error: {e}")
        return jsonify({"status": "error", "error": str(e)}), 500


@system_mode_bp.route("/test/emulator", methods=["GET"])
def test_emulator():
    """Test embedded emulator connectivity."""
    try:
        from services.embedded_emulator import get_emulator
        
        emulator = get_emulator()
        data = emulator.get_latest()
        
        return jsonify({
            "status": "ok",
            "running": emulator.running,
            "has_data": bool(data.get("scales")),
            "scale_count": len(data.get("scales", {})),
        })
    except Exception as e:
        log.error(f"Emulator test error: {e}")
        return jsonify({"status": "error", "error": str(e)}), 500


@system_mode_bp.route("/test/external-emulator", methods=["GET"])
def test_external_emulator():
    """Test external SCADA emulator at localhost:7000."""
    try:
        import requests
        
        response = requests.get("http://localhost:7000/scada/latest", timeout=5)
        
        if response.status_code == 200:
            data = response.json()
            return jsonify({
                "status": "connected",
                "has_data": bool(data),
                "sample": list(data.keys())[:5] if isinstance(data, dict) else []
            })
        else:
            return jsonify({
                "status": "error",
                "error": f"HTTP {response.status_code}"
            }), response.status_code
            
    except requests.exceptions.ConnectionError:
        return jsonify({
            "status": "not_running",
            "error": "External emulator not running at localhost:7000"
        }), 503
    except Exception as e:
        return jsonify({
            "status": "error",
            "error": str(e)
        }), 500


@system_mode_bp.route("/test/mock-sap", methods=["GET"])
def test_mock_sap():
    """Test mock SAP server at localhost:6000."""
    try:
        import requests
        
        # Try connecting to mock SAP health endpoint
        response = requests.get("http://localhost:6000/health", timeout=5)
        
        return jsonify({
            "status": "connected" if response.status_code == 200 else "error",
            "http_status": response.status_code
        })
    except requests.exceptions.ConnectionError:
        return jsonify({
            "status": "not_running",
            "error": "Mock SAP server not running at localhost:6000"
        }), 503
    except Exception as e:
        return jsonify({
            "status": "error",
            "error": str(e)
        }), 500


# =============================================================================
# Statistics
# =============================================================================

@system_mode_bp.route("/stats", methods=["GET"])
def get_system_stats():
    """Get system statistics (table counts, etc.)."""
    try:
        from database import PostgresSessionLocal
        
        stats = {}
        
        with PostgresSessionLocal() as db:
            # Count records in key tables
            tables = [
                "kpi_send_tracking",
                "scada_aggregate_values",
                "milling_kpi_snapshots",
                "packing_kpi_snapshots",
                "shift_master",
            ]
            
            for table in tables:
                try:
                    result = db.execute(text(f"SELECT COUNT(*) FROM {table}"))
                    stats[table] = result.scalar()
                except:
                    stats[table] = -1  # Table doesn't exist
        
        return jsonify(stats)
    except Exception as e:
        log.error(f"Error getting system stats: {e}")
        return jsonify({"error": str(e)}), 500
