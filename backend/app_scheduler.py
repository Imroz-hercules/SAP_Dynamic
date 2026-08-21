# import os
# import logging
# import signal
# import atexit
# import requests
# from datetime import datetime, timezone
# from apscheduler.schedulers.background import BackgroundScheduler
# from apscheduler.triggers.interval import IntervalTrigger
# from sqlalchemy import text

# # Import services
# from services.process_order_pull import pull_from_sap_once
# from services.scada_persist import persist_scada_latest
# from services.kpi_store_flat import store_split_tables
# from services.accumulator_service import OrderAccumulator
# from services.shift_auto_confirm import auto_push_shift_confirmation
# # from services.auto_validator import auto_validator  # Import inside function to avoid circular imports

# # Import database engines
# from database import engine as mssql_engine, postgres_engine

# log = logging.getLogger("scheduler")

# # Configuration constants
# SCADA_KEYS = [
#     "WG101","WG201","WG202","WG301","WG302","WG501","WG502","WG503",
#     "DM101","DM102","DM201","DM202","DM203",
#     "SL601_COUNTER"
# ]
# SOURCE_TABLE = "[HerculesV2].[dbo].[ASMArchive_DB5]"
# SCADA_INTERVAL_SECONDS = int(os.getenv("SCADA_POLL_INTERVAL_SEC", "60"))
# PO_PULL_INTERVAL_HOURS = float(os.getenv("PO_PULL_INTERVAL_HOURS", "3"))
# ACCUMULATOR_INTERVAL_SECONDS = int(os.getenv("ACCUMULATOR_INTERVAL_SEC", "5"))  # default 5s

# # --------------------------------------------------
# # Job functions
# # --------------------------------------------------
# def poll_and_store_latest_scada():
#     """Read newest row from SQL Server and write SCADA-style values into Postgres."""
#     from services.system_logger import log_scada_event
    
#     if postgres_engine is None:
#         log.warning("PostgreSQL engine not configured; skipping SCADA insert.")
#         return
#     try:
#         latest_sql = text(f"SELECT TOP 1 * FROM {SOURCE_TABLE} ORDER BY [CreatedOn] DESC")
#         with mssql_engine.connect() as conn:
#             row = conn.execute(latest_sql).mappings().first()
#             if not row:
#                 log.info("No MSSQL rows found yet; skipping.")
#                 return

#         aggregated = {}
#         for k in SCADA_KEYS:
#             v = row.get(k)
#             try:
#                 aggregated[k] = float(v) if v is not None else 0.0
#             except Exception:
#                 aggregated[k] = 0.0

#         persist_scada_latest(aggregated)
        
#         # Log successful SCADA data sync
#         log_scada_event(
#             action="SCADA Data Sync Completed",
#             status="Success",
#             details=f"Successfully synced SCADA data with {len(aggregated)} values",
#             metadata={
#                 "scada_keys_count": len(aggregated),
#                 "triggered_by": "scheduler",
#                 "source_table": SOURCE_TABLE
#             }
#         )
        
#         log.info("SCADA data stored successfully")
#     except Exception as e:
#         # Log SCADA sync failure
#         log_scada_event(
#             action="SCADA Data Sync Failed",
#             status="Error",
#             details=f"SCADA data sync failed: {str(e)}",
#             error_code="SCADA_SYNC_ERROR",
#             metadata={
#                 "triggered_by": "scheduler",
#                 "source_table": SOURCE_TABLE,
#                 "error": str(e)
#             }
#         )
#         log.exception("SCADA poll/store failed: %s", e)


# def poll_and_store_kpi_data():
#     """Fetch KPI data from API and store in separate milling/packing tables."""
#     if postgres_engine is None:
#         log.warning("PostgreSQL engine not configured; skipping KPI insert.")
#         return
#     try:
#         response = requests.get("http://localhost:5000/api/kpi", timeout=10)
#         response.raise_for_status()
#         kpi_data = response.json()
#         store_split_tables(kpi_data, mode="latest")
#         log.info("KPI data stored successfully in milling/packing tables")
#     except requests.RequestException as e:
#         log.error("Failed to fetch KPI data from API: %s", e)
#     except Exception as e:
#         log.exception("KPI poll/store failed: %s", e)


# def pull_process_orders_from_sap():
#     """Pull process orders from SAP."""
#     from services.system_logger import log_sap_event
    
#     try:
#         # Log scheduled sync start
#         log_sap_event(
#             action="Scheduled Order Sync Started",
#             status="InProgress",
#             details="Automatic scheduled sync of process orders from SAP"
#         )
        
#         n = pull_from_sap_once()
        
#         # Log successful sync
#         log_sap_event(
#             action="Scheduled Order Sync Completed",
#             status="Success",
#             details=f"Successfully pulled {n} orders from SAP",
#             metadata={"orders_pulled": n, "triggered_by": "scheduler"}
#         )
        
#         log.info("[PO-PULL] %s pulled %d orders",
#                  datetime.now(timezone.utc).isoformat(), n)
#     except Exception as e:
#         # Log sync failure
#         log_sap_event(
#             action="Scheduled Order Sync Failed",
#             status="Error",
#             details=f"Scheduled order sync failed: {str(e)}",
#             error_code="SCHEDULED_SYNC_ERROR",
#             metadata={"triggered_by": "scheduler", "error": str(e)}
#         )
#         log.exception("[PO-PULL] failed")

# # --------------------------------------------------
# # Scheduler setup
# # --------------------------------------------------
# def start_scheduler():
#     """Start the main scheduler with all configured jobs."""
#     sched = BackgroundScheduler(timezone=timezone.utc, daemon=True)

#     # --- Core jobs ---
#     sched.add_job(
#         poll_and_store_latest_scada,
#         "interval",
#         seconds=SCADA_INTERVAL_SECONDS,
#         id="scada_poll_job",
#         replace_existing=True
#     )

#     sched.add_job(
#         poll_and_store_kpi_data,
#         "interval",
#         seconds=SCADA_INTERVAL_SECONDS,
#         id="kpi_poll_job",
#         replace_existing=True
#     )

#     sched.add_job(
#         pull_process_orders_from_sap,
#         IntervalTrigger(hours=PO_PULL_INTERVAL_HOURS),
#         id="po_pull_job",
#         replace_existing=True
#     )

#     # --- Accumulator job (order validation/confirmation) ---
#     # ⭐ DISABLED: OrderAccumulator is a legacy system that conflicts with the new auto-validation worker
#     # The new auto-validation worker in order_validation.py handles all validation properly:
#     # - Uses proper classification (MILLING vs PACKING)
#     # - Tracks multiple equipment streams (WG202, WG501, WG502, WG503 for milling)
#     # - Sends 10 TON chunk confirmations to SAP
#     # - Uses correct status values (Validated, Rejected)
#     # - Has proper baseline capture per equipment
#     # 
#     # OrderAccumulator issues:
#     # - Only checks WG202 (single scale) - doesn't account for multiple equipment streams
#     # - Uses old status values ("Open", "Planned") - not used in new system
#     # - Sets status to "Confirmed" instead of "Validated"
#     # - No classification support (MILLING vs PACKING)
#     # - No 10 TON chunking - confirms entire order at once
#     # - May conflict with auto-validation worker (race conditions)
#     #
#     # acc = OrderAccumulator(poll_interval=5, tolerance_pct=0.5)
#     # sched.add_job(
#     #     acc.tick,
#     #     "interval",
#     #     seconds=ACCUMULATOR_INTERVAL_SECONDS,
#     #     id="order_accumulator_job",
#     #     replace_existing=True
#     # )
#     log.info("OrderAccumulator scheduler job disabled - using new auto-validation worker instead")

#     # --- Auto Validator job (MANUAL START ONLY) ---
#     # ⭐ REMOVED: Automatic startup every 30 seconds
#     # Auto-validator now only starts when explicitly triggered by frontend button
#     # This prevents the "already running" issue and gives users full control
    
#     log.info("Auto-validator scheduler job removed - manual start only")

#     # ⭐⭐⭐ NEW: Auto Shift-End SAP Confirmation ⭐⭐⭐
#     sched.add_job(
#         auto_push_shift_confirmation,
#         IntervalTrigger(minutes=1),  # check every 1 minute
#         id="auto_shift_confirm_job",
#         replace_existing=True
#     )
#     log.info("Auto Shift-End Confirmation job enabled (runs every 1 minute)")

#     # Start the scheduler
#     sched.start()
    
#     # ⭐ REMOVED: Immediate AutoValidator startup
#     # Auto-validator now only starts when explicitly triggered by frontend button

#     # Register shutdown handlers
#     def shutdown_scheduler(*_args):
#         if sched.running:
#             sched.shutdown(wait=False)

#     atexit.register(shutdown_scheduler)
#     signal.signal(signal.SIGTERM, shutdown_scheduler)

#     log.info("Scheduler started with jobs:")
#     log.info(f"  - SCADA polling every {SCADA_INTERVAL_SECONDS}s")
#     log.info(f"  - KPI polling every {SCADA_INTERVAL_SECONDS}s")
#     log.info(f"  - SAP order pull every {PO_PULL_INTERVAL_HOURS}h")
#     log.info(f"  - Auto Shift-End confirmation every 1 minute")
#     log.info("  - Auto-validator: MANUAL ONLY")

#     return sched
import os
import logging
import signal
import atexit
import requests
from datetime import datetime, timezone
from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.triggers.interval import IntervalTrigger
from sqlalchemy import text

# -------------------------------------------------------------------
# Import services
# -------------------------------------------------------------------
from services.process_order_pull import pull_from_sap_once
from services.scada_persist import persist_scada_latest
from services.kpi_store_flat import store_split_tables
from services.shift_auto_confirm import auto_push_shift_confirmation

# ⭐ NEW — LIVE SHIFT PRODUCTION CALCULATION
from services.shift_live_update import update_live_shift_production

# ⭐ NEW — AUTO KPI SYNC ON SHIFT END
from services.kpi_shift_auto_sync import auto_send_kpis_on_shift_end

# Import database engines
from database import engine as mssql_engine, postgres_engine

log = logging.getLogger("scheduler")

# -------------------------------------------------------------------
# Configuration
# -------------------------------------------------------------------
SCADA_KEYS = [
    "WG101", "WG201", "WG202", "WG301", "WG302", "WG501", "WG502", "WG503",
    "DM101", "DM102", "DM201", "DM202", "DM203",
    "SL601_COUNTER",
]

# Workstream B: replace with active+pollable tags from scada_tags when available.
try:
    from services.scada_tag_registry import poll_keys, refresh_consumer_lists
    _reg_keys = poll_keys()
    if _reg_keys:
        SCADA_KEYS = list(_reg_keys)
    refresh_consumer_lists()
except Exception as _reg_exc:
    log.debug("SCADA registry not applied at scheduler import: %s", _reg_exc)

SOURCE_TABLE = os.getenv(
    "SCADA_SOURCE_TABLE",
    "[HerculesV2].[dbo].[ASMArchive_DB5]",
)

SCADA_INTERVAL_SECONDS = int(os.getenv("SCADA_POLL_INTERVAL_SEC", "60"))
PO_PULL_INTERVAL_HOURS = float(os.getenv("PO_PULL_INTERVAL_HOURS", "3"))
ACCUMULATOR_INTERVAL_SECONDS = int(os.getenv("ACCUMULATOR_INTERVAL_SEC", "5"))


# -------------------------------------------------------------------
# SCADA Poll Job
# -------------------------------------------------------------------
def poll_and_store_latest_scada():
    """Read SCADA data from MSSQL or embedded emulator and write into Postgres."""
    from services.system_logger import log_scada_event
    from database import get_demo_mode
    
    if postgres_engine is None:
        log.warning("PostgreSQL engine not configured; skipping SCADA insert.")
        return

    try:
        aggregated = {}
        
        # ✅ CHECK DEMO MODE - Use embedded emulator directly
        if get_demo_mode():
            try:
                from services.embedded_emulator import get_emulator
                emulator = get_emulator()
                data = emulator.get_latest()
                
                # Get raw scales (HI/LO separate)
                raw_scales = data.get("raw_scales", {})
                
                # Extract values for SCADA_KEYS from embedded emulator
                for k in SCADA_KEYS:
                    v = raw_scales.get(k)
                    try:
                        aggregated[k] = float(v) if v is not None else 0.0
                    except (ValueError, TypeError):
                        aggregated[k] = 0.0
                
                log.info(f"✅ Fetched SCADA data from embedded emulator: {len(aggregated)} values")
            except Exception as e:
                log.error(f"Failed to fetch from embedded emulator: {e}")
                return
        else:
            # Fetch from MSSQL database (production mode)
            latest_sql = text(f"SELECT TOP 1 * FROM {SOURCE_TABLE} ORDER BY [CreatedOn] DESC")
            with mssql_engine.connect() as conn:
                row = conn.execute(latest_sql).mappings().first()
                if not row:
                    log.info("No MSSQL rows found yet; skipping.")
                    return

            for k in SCADA_KEYS:
                v = row.get(k)
                try:
                    aggregated[k] = float(v) if v is not None else 0.0
                except Exception:
                    aggregated[k] = 0.0

        # Store aggregated data
        persist_scada_latest(aggregated)

        log_scada_event(
            action="SCADA Data Sync Completed",
            status="Success",
            details=f"Successfully synced SCADA data with {len(aggregated)} values",
            metadata={
                "scada_keys_count": len(aggregated),
                "source": "emulator" if get_demo_mode() else "mssql"
            }
        )

        log.info("SCADA data stored successfully")

    except Exception as e:
        log_scada_event(
            action="SCADA Data Sync Failed",
            status="Error",
            details=f"SCADA sync failed: {str(e)}",
            error_code="SCADA_SYNC_ERROR"
        )
        log.exception("SCADA poll/store failed: %s", e)


# -------------------------------------------------------------------
# KPI Poll Job
# -------------------------------------------------------------------
def poll_and_store_kpi_data():
    """Fetch KPI data from API and store in separate milling/packing tables."""
    if postgres_engine is None:
        log.warning("PostgreSQL engine not configured; skipping KPI insert.")
        return
    try:
        response = requests.get("http://localhost:5000/api/kpi", timeout=10)
        response.raise_for_status()
        kpi_data = response.json()
        store_split_tables(kpi_data, mode="latest")
        log.info("KPI data stored successfully")

    except requests.RequestException as e:
        log.error("Failed to fetch KPI data: %s", e)
    except Exception as e:
        log.exception("KPI poll/store failed: %s", e)


# -------------------------------------------------------------------
# SAP Order Pull Job
# -------------------------------------------------------------------
def pull_process_orders_from_sap():
    """Pull process orders from SAP."""
    from services.system_logger import log_sap_event

    try:
        log_sap_event(
            action="Scheduled Order Sync Started",
            status="InProgress",
            details="Automatic scheduled sync"
        )

        count = pull_from_sap_once()

        log_sap_event(
            action="Scheduled Order Sync Completed",
            status="Success",
            details=f"Pulled {count} orders"
        )

        log.info("[PO-PULL] Pulled %d orders", count)

    except Exception as e:
        log_sap_event(
            action="Scheduled Order Sync Failed",
            status="Error",
            details=str(e),
            error_code="SCHEDULED_SYNC_ERROR"
        )
        log.exception("PO pull failed")


# -------------------------------------------------------------------
# Scheduler Setup
# -------------------------------------------------------------------
def start_scheduler():
    """Start the main scheduler with all configured jobs."""
    sched = BackgroundScheduler(timezone=timezone.utc, daemon=True)

    # --------------------------------------------------------
    # 1) SCADA live poll
    # --------------------------------------------------------
    sched.add_job(
        poll_and_store_latest_scada,
        "interval",
        seconds=SCADA_INTERVAL_SECONDS,
        id="scada_poll_job",
        replace_existing=True
    )

    # --------------------------------------------------------
    # ⭐ 2) LIVE SHIFT PRODUCTION CALCULATION (NEW)
    # --------------------------------------------------------
    sched.add_job(
        update_live_shift_production,
        "interval",
        seconds=SCADA_INTERVAL_SECONDS,
        id="live_shift_update_job",
        replace_existing=True
    )
    log.info("Live Shift Production Updater enabled every %s seconds", SCADA_INTERVAL_SECONDS)

    # --------------------------------------------------------
    # 3) KPI Poll
    # --------------------------------------------------------
    sched.add_job(
        poll_and_store_kpi_data,
        "interval",
        seconds=SCADA_INTERVAL_SECONDS,
        id="kpi_poll_job",
        replace_existing=True
    )

    # --------------------------------------------------------
    # 4) SAP Order Pull (Every X Hours)
    # --------------------------------------------------------
    sched.add_job(
        pull_process_orders_from_sap,
        IntervalTrigger(hours=PO_PULL_INTERVAL_HOURS),
        id="po_pull_job",
        replace_existing=True
    )

    # --------------------------------------------------------
    # 5) Shift-End Auto SAP Confirmation
    # --------------------------------------------------------
    sched.add_job(
        auto_push_shift_confirmation,
        IntervalTrigger(minutes=1),
        id="auto_shift_confirm_job",
        replace_existing=True
    )
    log.info("Auto Shift-End Confirmation enabled (every 1 minute)")

    # --------------------------------------------------------
    # 6) Auto KPI Sync on Shift End
    # --------------------------------------------------------
    sched.add_job(
        auto_send_kpis_on_shift_end,
        IntervalTrigger(minutes=1),
        id="auto_kpi_shift_sync_job",
        replace_existing=True
    )
    log.info("Auto KPI Shift-End Sync enabled (every 1 minute)")

    # --------------------------------------------------------
    # Start Scheduler
    # --------------------------------------------------------
    sched.start()

    def shutdown_scheduler(*_args):
        if sched.running:
            sched.shutdown(wait=False)

    atexit.register(shutdown_scheduler)
    signal.signal(signal.SIGTERM, shutdown_scheduler)

    # --------------------------------------------------------
    # Logs
    # --------------------------------------------------------
    log.info("Scheduler started with jobs:")
    log.info("  - SCADA polling: %s sec", SCADA_INTERVAL_SECONDS)
    log.info("  - KPI polling: %s sec", SCADA_INTERVAL_SECONDS)
    log.info("  - Live Shift Weight Update: %s sec", SCADA_INTERVAL_SECONDS)
    log.info("  - SAP order pull every %s hours", PO_PULL_INTERVAL_HOURS)
    log.info("  - Auto Shift-End Confirmation: every 1 minute")
    log.info("  - Auto KPI Shift-End Sync: every 1 minute")

    return sched
