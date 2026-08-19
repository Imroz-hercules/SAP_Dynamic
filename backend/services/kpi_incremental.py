"""
Incremental KPI Calculation Service
Calculates KPIs only for new data since last send (delta)
"""
import logging
from datetime import datetime, timedelta, timezone
from sqlalchemy import text
from database import PostgresSessionLocal, postgres_engine
from models.kpi_send_tracking import KpiSendTracking
from routes.kpi_routes import (
    engine, fetch_existing_columns, build_latest_sql, 
    calc_kpis_from_row, OPTIONAL_TIME_COLS, safe
)

log = logging.getLogger("kpi_incremental")


def get_last_sent_baseline(department: str, shift_code: str = None, exclude_recent_seconds: int = 10):
    """
    Get the last sent SCADA baseline for a department.
    exclude_recent_seconds: If provided, exclude baselines created within this many seconds (to skip recently reserved ones).
    Returns dict of baseline values or None if no previous send.
    For manual sends, we don't filter by shift_code (get most recent regardless of shift).
    """
    try:
        with PostgresSessionLocal() as db:
            query = db.query(KpiSendTracking).filter(
                KpiSendTracking.department == department.upper()
            )
            
            # Only filter by shift_code for auto shift-end sends
            # For manual sends, get the most recent regardless of shift
            if shift_code:
                query = query.filter(KpiSendTracking.shift_code == shift_code.upper())
            
            # If excluding recent baselines, filter them out
            if exclude_recent_seconds > 0:
                cutoff_time = datetime.now(timezone.utc) - timedelta(seconds=exclude_recent_seconds)
                query = query.filter(KpiSendTracking.last_sent_at < cutoff_time)
            
            # Get most recent (order by last_sent_at descending)
            last_tracking = query.order_by(KpiSendTracking.last_sent_at.desc()).first()
            
            if not last_tracking:
                log.info(f"No previous baseline found for {department}")
                return None
            
            # ✅ CRITICAL: Check if last send was very recent (within last 5 seconds)
            # This prevents duplicate sends from rapid button clicks
            # Handle timezone-aware datetime comparison
            now_aware = datetime.now(timezone.utc)
            last_sent = last_tracking.last_sent_at
            if last_sent.tzinfo is None:
                last_sent = last_sent.replace(tzinfo=timezone.utc)
            time_since_last_send = (now_aware - last_sent).total_seconds()
            if time_since_last_send < 5.0:
                log.warning(f"⚠️ Last send was only {time_since_last_send:.1f} seconds ago - preventing duplicate send")
                return {
                    "id": last_tracking.id,
                    "last_sent_at": last_tracking.last_sent_at,
                    "WG101": last_tracking.baseline_WG101 or 0.0,
                    "WG201": last_tracking.baseline_WG201 or 0.0,
                    "WG202": last_tracking.baseline_WG202 or 0.0,
                    "WG301": last_tracking.baseline_WG301 or 0.0,
                    "WG302": last_tracking.baseline_WG302 or 0.0,
                    "WG501": last_tracking.baseline_WG501 or 0.0,
                    "WG502": last_tracking.baseline_WG502 or 0.0,
                    "WG503": last_tracking.baseline_WG503 or 0.0,
                    "DM101": last_tracking.baseline_DM101 or 0.0,
                    "DM102": last_tracking.baseline_DM102 or 0.0,
                    "DM201": last_tracking.baseline_DM201 or 0.0,
                    "DM202": last_tracking.baseline_DM202 or 0.0,
                    "DM203": last_tracking.baseline_DM203 or 0.0,
                    "PL601_TOT": last_tracking.baseline_PL601_TOT or 0.0,
                    "PL602_TOT": last_tracking.baseline_PL602_TOT or 0.0,
                    "PL603_TOT": last_tracking.baseline_PL603_TOT or 0.0,
                    "_recent_send": True  # Flag to indicate this is a very recent send
                }
            
            log.info(f"Found baseline for {department}: last_sent_at={last_tracking.last_sent_at}, shift={last_tracking.shift_code}, type={last_tracking.send_type}")
            
            # Return baseline values
            baseline = {
                "id": last_tracking.id,
                "last_sent_at": last_tracking.last_sent_at,
                "WG101": last_tracking.baseline_WG101 or 0.0,
                "WG201": last_tracking.baseline_WG201 or 0.0,
                "WG202": last_tracking.baseline_WG202 or 0.0,
                "WG301": last_tracking.baseline_WG301 or 0.0,
                "WG302": last_tracking.baseline_WG302 or 0.0,
                "WG501": last_tracking.baseline_WG501 or 0.0,
                "WG502": last_tracking.baseline_WG502 or 0.0,
                "WG503": last_tracking.baseline_WG503 or 0.0,
                "DM101": last_tracking.baseline_DM101 or 0.0,
                "DM102": last_tracking.baseline_DM102 or 0.0,
                "DM201": last_tracking.baseline_DM201 or 0.0,
                "DM202": last_tracking.baseline_DM202 or 0.0,
                "DM203": last_tracking.baseline_DM203 or 0.0,
                "PL601_TOT": last_tracking.baseline_PL601_TOT or 0.0,
                "PL602_TOT": last_tracking.baseline_PL602_TOT or 0.0,
                "PL603_TOT": last_tracking.baseline_PL603_TOT or 0.0,
            }
            
            log.debug(f"Baseline values: WG202={baseline['WG202']:.2f}, WG501={baseline['WG501']:.2f}, WG502={baseline['WG502']:.2f}")
            return baseline
    except Exception as e:
        log.exception(f"Error getting last sent baseline: {e}")
        return None


def get_current_scada_values():
    """
    Get current SCADA values from database or emulator.
    
    ✅ FIXED (Jan 28, 2026): Now uses get_demo_mode() to check if demo mode is enabled.
    In demo mode: Fetches from embedded emulator
    In production mode: Fetches from MSSQL database
    """
    try:
        # ✅ CHECK DEMO MODE FIRST - Use embedded emulator
        from database import get_demo_mode
        
        if get_demo_mode():
            log.info("📊 [DEMO MODE] get_current_scada_values() fetching from embedded emulator...")
            try:
                from services.embedded_emulator import get_emulator
                emulator = get_emulator()
                scales = emulator.get_all_scales()
                
                if not scales:
                    log.warning("⚠️ [DEMO MODE] Emulator returned no data")
                    return None
                
                # Build current values dict from emulator data
                current = {}
                
                # Map emulator fields to expected SCADA fields
                # WG scales - combine HI and LO values for totals
                for wg in ["WG101", "WG201", "WG202", "WG301", "WG302", "WG501", "WG502", "WG503"]:
                    hi_val = safe(scales.get(f"{wg}_HI", 0.0))
                    lo_val = safe(scales.get(f"{wg}_LO", 0.0))
                    # If HI/LO exist, combine them; otherwise use direct value
                    if f"{wg}_HI" in scales or f"{wg}_LO" in scales:
                        current[wg] = hi_val + lo_val
                    else:
                        current[wg] = safe(scales.get(wg, 0.0))
                
                # DM scales - direct values
                for dm in ["DM101", "DM102", "DM201", "DM202", "DM203"]:
                    current[dm] = safe(scales.get(dm, 0.0))
                
                # PL scales - direct values
                for pl in ["PL601_TOT", "PL602_TOT", "PL603_TOT"]:
                    current[pl] = safe(scales.get(pl, 0.0))
                
                # Ensure all fields exist
                for k in ["WG101", "WG201", "WG202", "WG301", "WG302", "WG501", "WG502", "WG503",
                          "DM101", "DM102", "DM201", "DM202", "DM203",
                          "PL601_TOT", "PL602_TOT", "PL603_TOT"]:
                    current.setdefault(k, 0.0)
                
                log.info(f"✅ [DEMO MODE] Emulator SCADA values: WG202={current.get('WG202', 0):.2f}, WG501={current.get('WG501', 0):.2f}, PL601_TOT={current.get('PL601_TOT', 0):.2f}")
                return current
                
            except Exception as emulator_err:
                log.exception(f"⚠️ [DEMO MODE] Error fetching from emulator: {emulator_err}")
                return None
        
        # ✅ PRODUCTION MODE - Use MSSQL database
        log.info("📊 [PRODUCTION MODE] get_current_scada_values() fetching from MSSQL...")
        with engine.connect() as conn:
            existing = fetch_existing_columns(conn)
            row = conn.execute(build_latest_sql()).mappings().first()
            if not row:
                return None
            
            current = dict(row)
            # Ensure all fields exist
            for k in ["WG101", "WG201", "WG202", "WG301", "WG302", "WG501", "WG502", "WG503",
                      "DM101", "DM102", "DM201", "DM202", "DM203",
                      "PL601_TOT", "PL602_TOT", "PL603_TOT"]:
                current.setdefault(k, 0.0)
            
            return current
    except Exception as e:
        log.exception(f"Error getting current SCADA values: {e}")
        return None


def calculate_delta_scada(current, baseline):
    """
    Calculate delta SCADA values (current - baseline).
    Returns dict with delta values.
    
    - First send (no baseline): Returns full current values
    - Subsequent sends (baseline exists): Returns incremental (current - baseline)
    """
    if not baseline:
        # No baseline = first send, use current values as delta (FULL DATA)
        log.info("📊 FIRST SEND: No baseline exists - sending FULL current SCADA values")
        if current:
            log.info(f"   Full values: WG202={current.get('WG202', 0):.2f}, WG501={current.get('WG501', 0):.2f}, WG502={current.get('WG502', 0):.2f}")
        return current.copy() if current else {}
    
    # Baseline exists = subsequent send, calculate INCREMENTAL (current - baseline)
    log.info("📊 INCREMENTAL SEND: Baseline exists - calculating delta (current - baseline)")
    delta = {}
    scada_fields = [
        "WG101", "WG201", "WG202", "WG301", "WG302", "WG501", "WG502", "WG503",
        "DM101", "DM102", "DM201", "DM202", "DM203",
        "PL601_TOT", "PL602_TOT", "PL603_TOT"
    ]
    
    for field in scada_fields:
        current_val = safe(current.get(field, 0.0)) if current else 0.0
        baseline_val = safe(baseline.get(field, 0.0))
        delta[field] = max(0.0, current_val - baseline_val)  # Ensure non-negative
    
    # Log key delta values for verification
    if "WG202" in delta or "WG501" in delta or "WG502" in delta:
        log.info(f"   Delta calculated: WG202={delta.get('WG202', 0):.2f} (current={current.get('WG202', 0):.2f} - baseline={baseline.get('WG202', 0):.2f}), "
                f"WG501={delta.get('WG501', 0):.2f} (current={current.get('WG501', 0):.2f} - baseline={baseline.get('WG501', 0):.2f}), "
                f"WG502={delta.get('WG502', 0):.2f} (current={current.get('WG502', 0):.2f} - baseline={baseline.get('WG502', 0):.2f})")
    
    return delta


def check_duplicate_send(department: str, current_scada: dict, time_window_seconds: int = 60, exclude_tracking_id: int = None):
    """
    Check if the exact same SCADA values were sent recently (within time_window_seconds).
    exclude_tracking_id: If provided, exclude this tracking ID from the check (useful when checking after reserving).
    Returns True if duplicate found, False otherwise.
    Uses comprehensive field comparison to catch all duplicates.
    """
    try:
        with PostgresSessionLocal() as db:
            # Get recent sends for this department (extended window to catch all duplicates)
            # Use timezone-aware datetime for comparison
            cutoff_time = datetime.now(timezone.utc) - timedelta(seconds=time_window_seconds)
            query = db.query(KpiSendTracking).filter(
                KpiSendTracking.department == department.upper(),
                KpiSendTracking.last_sent_at >= cutoff_time
            )
            
            # Exclude the tracking ID we just reserved (if provided)
            if exclude_tracking_id is not None:
                query = query.filter(KpiSendTracking.id != exclude_tracking_id)
            
            recent_sends = query.order_by(KpiSendTracking.last_sent_at.desc()).all()
            
            if not recent_sends:
                return False
            
            # ✅ SMART CHECK: Compare key production fields that indicate actual production change
            # For MILLING: WG202 (total running time), WG501, WG502 (flour production) are key indicators
            # For PACKING: PL601_TOT is the key indicator
            if department.upper() == "MILLING":
                scada_fields = ["WG202", "WG501", "WG502"]  # Key production indicators
            elif department.upper() == "PACKING":
                scada_fields = ["PL601_TOT"]  # Key production indicator
            else:
                # Fallback: compare all fields for unknown departments
                scada_fields = [
                    "WG101", "WG201", "WG202", "WG301", "WG302", "WG501", "WG502", "WG503",
                    "DM101", "DM102", "DM201", "DM202", "DM203",
                    "PL601_TOT", "PL602_TOT", "PL603_TOT"
                ]
            
            # Get current time as timezone-aware datetime
            now_aware = datetime.now(timezone.utc)
            
            for recent in recent_sends:
                # Check if ALL fields match (within tolerance)
                all_match = True
                mismatched_fields = []
                for field in scada_fields:
                    current_val = safe(current_scada.get(field, 0.0))
                    # Map field name to database column
                    baseline_field = f"baseline_{field}"
                    recent_val = safe(getattr(recent, baseline_field, 0.0) or 0.0)
                    
                    # Use 0.01 tolerance for floating point comparison
                    diff = abs(current_val - recent_val)
                    if diff > 0.01:
                        all_match = False
                        mismatched_fields.append(f"{field}: current={current_val:.2f} vs baseline={recent_val:.2f} (diff={diff:.2f})")
                        # Don't break immediately - collect all mismatches for logging
                
                if all_match:
                    # Handle timezone-aware datetime comparison
                    last_sent = recent.last_sent_at
                    if last_sent.tzinfo is None:
                        # If naive, assume UTC
                        last_sent = last_sent.replace(tzinfo=timezone.utc)
                    time_diff = (now_aware - last_sent).total_seconds()
                    log.warning(f"⚠️ DUPLICATE DETECTED: All SCADA values match - sent {time_diff:.1f} seconds ago (ID: {recent.id}, type: {recent.send_type})")
                    log.info(f"   Current SCADA: WG202={current_scada.get('WG202', 0):.2f}, WG501={current_scada.get('WG501', 0):.2f}, WG502={current_scada.get('WG502', 0):.2f}")
                    log.info(f"   Baseline SCADA: WG202={getattr(recent, 'baseline_WG202', 0):.2f}, WG501={getattr(recent, 'baseline_WG501', 0):.2f}, WG502={getattr(recent, 'baseline_WG502', 0):.2f}")
                    return True
                else:
                    # Log mismatches for debugging
                    if mismatched_fields:
                        log.info(f"✅ NOT A DUPLICATE: Values differ from baseline ID {recent.id}. Mismatches: {', '.join(mismatched_fields[:3])}")  # Show first 3 mismatches
            
            return False
    except Exception as e:
        log.exception(f"Error checking duplicate send: {e}")
        return False  # On error, allow send (fail open)


def reserve_baseline_slot(department: str, current_scada: dict, send_type: str, shift_code: str = None, notes: str = None, kpi_payload: dict = None):
    """
    Reserve a baseline slot BEFORE sending to SAP.
    Uses PostgreSQL advisory locks + row-level locking to prevent race conditions.
    Returns (tracking_id, success) tuple.
    
    Args:
        department: MILLING or PACKING
        current_scada: Current SCADA values
        send_type: 'manual' or 'auto_shift_end'
        shift_code: Shift code (A, B, C) - now tracked for manual sends too
        notes: Optional notes
        kpi_payload: The KPI payload being sent to SAP (for auditing)
    """
    # Use department-specific advisory lock key (MILLING=1, PACKING=2)
    lock_key = 1 if department.upper() == "MILLING" else 2
    
    try:
        with PostgresSessionLocal() as db:
            # ✅ STEP 1: Acquire advisory lock (prevents concurrent sends for same department)
            try:
                lock_result = db.execute(text("SELECT pg_try_advisory_xact_lock(:lock_key)"), {"lock_key": lock_key}).scalar()
                if not lock_result:
                    log.warning(f"⚠️ Advisory lock already held - another send in progress for {department}")
                    return None, False
            except Exception as lock_err:
                log.warning(f"⚠️ Failed to acquire advisory lock: {lock_err}")
                return None, False
            
            # ✅ STEP 2: Quick pre-check (now we have the lock, so this is safe)
            if check_duplicate_send(department, current_scada, time_window_seconds=60):
                log.warning(f"⚠️ Duplicate detected in pre-check - blocking")
                return None, False
            
            # ✅ STEP 3: Lock recent rows and check for duplicates atomically
            cutoff_time = datetime.now(timezone.utc) - timedelta(seconds=60)
            
            try:
                # Get all recent sends and lock them (use mappings() for dict access)
                # Note: PostgreSQL requires quoted identifiers for mixed-case column names
                recent_sends = db.execute(
                    text("""
                        SELECT id, "baseline_WG101", "baseline_WG201", "baseline_WG202", "baseline_WG301", "baseline_WG302",
                               "baseline_WG501", "baseline_WG502", "baseline_WG503",
                               "baseline_DM101", "baseline_DM102", "baseline_DM201", "baseline_DM202", "baseline_DM203",
                               "baseline_PL601_TOT", "baseline_PL602_TOT", "baseline_PL603_TOT"
                        FROM kpi_send_tracking
                        WHERE department = :dept
                          AND last_sent_at >= :cutoff
                        ORDER BY last_sent_at DESC
                        FOR UPDATE NOWAIT
                    """),
                    {
                        "dept": department.upper(),
                        "cutoff": cutoff_time
                    }
                ).mappings().fetchall()
                
                # Check if any recent send matches KEY production SCADA values
                # Use same logic as check_duplicate_send - only compare key production indicators
                if department.upper() == "MILLING":
                    scada_fields = [
                        ("WG202", "baseline_WG202"),
                        ("WG501", "baseline_WG501"),
                        ("WG502", "baseline_WG502")
                    ]
                elif department.upper() == "PACKING":
                    scada_fields = [
                        ("PL601_TOT", "baseline_PL601_TOT")
                    ]
                else:
                    # Fallback: compare all fields
                    scada_fields = [
                        ("WG101", "baseline_WG101"), ("WG201", "baseline_WG201"), ("WG202", "baseline_WG202"),
                        ("WG301", "baseline_WG301"), ("WG302", "baseline_WG302"),
                        ("WG501", "baseline_WG501"), ("WG502", "baseline_WG502"), ("WG503", "baseline_WG503"),
                        ("DM101", "baseline_DM101"), ("DM102", "baseline_DM102"),
                        ("DM201", "baseline_DM201"), ("DM202", "baseline_DM202"), ("DM203", "baseline_DM203"),
                        ("PL601_TOT", "baseline_PL601_TOT"), ("PL602_TOT", "baseline_PL602_TOT"), ("PL603_TOT", "baseline_PL603_TOT")
                    ]
                
                for recent in recent_sends:
                    all_match = True
                    for scada_field, db_field in scada_fields:
                        current_val = safe(current_scada.get(scada_field, 0.0))
                        recent_val = safe(recent.get(db_field, 0.0) or 0.0)
                        if abs(current_val - recent_val) > 0.01:
                            all_match = False
                            break
                    
                    if all_match:
                        recent_id = recent.get("id")
                        log.warning(f"⚠️ Duplicate detected in reserve_baseline_slot (locked row ID: {recent_id}) - blocking")
                        db.rollback()
                        return None, False
                        
            except Exception as lock_error:
                # Handle lock timeout (another request is checking)
                if "could not obtain lock" in str(lock_error).lower() or "lock_not_available" in str(lock_error).lower():
                    log.warning(f"⚠️ Database lock timeout - another request is processing. Blocking duplicate.")
                    db.rollback()
                    return None, False
                raise  # Re-raise if it's a different error
            
            # No duplicate found, create new tracking record
            tracking = KpiSendTracking(
                department=department.upper(),
                shift_code=shift_code.upper() if shift_code else None,
                last_sent_at=datetime.now(timezone.utc),
                baseline_WG101=safe(current_scada.get("WG101", 0.0)),
                baseline_WG201=safe(current_scada.get("WG201", 0.0)),
                baseline_WG202=safe(current_scada.get("WG202", 0.0)),
                baseline_WG301=safe(current_scada.get("WG301", 0.0)),
                baseline_WG302=safe(current_scada.get("WG302", 0.0)),
                baseline_WG501=safe(current_scada.get("WG501", 0.0)),
                baseline_WG502=safe(current_scada.get("WG502", 0.0)),
                baseline_WG503=safe(current_scada.get("WG503", 0.0)),
                baseline_DM101=safe(current_scada.get("DM101", 0.0)),
                baseline_DM102=safe(current_scada.get("DM102", 0.0)),
                baseline_DM201=safe(current_scada.get("DM201", 0.0)),
                baseline_DM202=safe(current_scada.get("DM202", 0.0)),
                baseline_DM203=safe(current_scada.get("DM203", 0.0)),
                baseline_PL601_TOT=safe(current_scada.get("PL601_TOT", 0.0)),
                baseline_PL602_TOT=safe(current_scada.get("PL602_TOT", 0.0)),
                baseline_PL603_TOT=safe(current_scada.get("PL603_TOT", 0.0)),
                send_type=send_type,
                notes=notes or f"Reserved at {datetime.now(timezone.utc).isoformat()}",
                kpi_payload_sent=kpi_payload  # Store the SAP payload for auditing
            )
            db.add(tracking)
            db.commit()
            log.info(f"✅ Reserved baseline slot for {department} (type: {send_type}, shift: {shift_code}, ID: {tracking.id})")
            return tracking.id, True
    except Exception as e:
        # Handle lock timeout (another request is checking)
        if "could not obtain lock" in str(e).lower() or "lock_not_available" in str(e).lower():
            log.warning(f"⚠️ Database lock timeout - another request is processing. Blocking duplicate.")
            db.rollback()
            return None, False
        log.exception(f"Error reserving baseline slot: {e}")
        if 'db' in locals():
            db.rollback()
        return None, False


def save_sent_baseline(department: str, current_scada: dict, send_type: str, shift_code: str = None, notes: str = None, kpi_payload: dict = None):
    """
    Save the current SCADA values as the new baseline after successful send.
    Uses database transaction to ensure atomicity.
    
    Args:
        department: MILLING or PACKING
        current_scada: Current SCADA values
        send_type: 'manual' or 'auto_shift_end'
        shift_code: Shift code (A, B, C)
        notes: Optional notes
        kpi_payload: The KPI payload sent to SAP (for auditing)
    """
    try:
        with PostgresSessionLocal() as db:
            tracking = KpiSendTracking(
                department=department.upper(),
                shift_code=shift_code.upper() if shift_code else None,
                last_sent_at=datetime.now(timezone.utc),
                baseline_WG101=safe(current_scada.get("WG101", 0.0)),
                baseline_WG201=safe(current_scada.get("WG201", 0.0)),
                baseline_WG202=safe(current_scada.get("WG202", 0.0)),
                baseline_WG301=safe(current_scada.get("WG301", 0.0)),
                baseline_WG302=safe(current_scada.get("WG302", 0.0)),
                baseline_WG501=safe(current_scada.get("WG501", 0.0)),
                baseline_WG502=safe(current_scada.get("WG502", 0.0)),
                baseline_WG503=safe(current_scada.get("WG503", 0.0)),
                baseline_DM101=safe(current_scada.get("DM101", 0.0)),
                baseline_DM102=safe(current_scada.get("DM102", 0.0)),
                baseline_DM201=safe(current_scada.get("DM201", 0.0)),
                baseline_DM202=safe(current_scada.get("DM202", 0.0)),
                baseline_DM203=safe(current_scada.get("DM203", 0.0)),
                baseline_PL601_TOT=safe(current_scada.get("PL601_TOT", 0.0)),
                baseline_PL602_TOT=safe(current_scada.get("PL602_TOT", 0.0)),
                baseline_PL603_TOT=safe(current_scada.get("PL603_TOT", 0.0)),
                send_type=send_type,
                notes=notes,
                kpi_payload_sent=kpi_payload  # Store the SAP payload for auditing
            )
            db.add(tracking)
            db.commit()
            log.info(f"✅ Saved baseline for {department} (type: {send_type}, shift: {shift_code}, ID: {tracking.id})")
            return True
    except Exception as e:
        log.exception(f"Error saving baseline: {e}")
        db.rollback()
        return False


def update_tracking_payload(tracking_id: int, kpi_payload: dict, shift_code: str = None):
    """
    Update an existing tracking record with the KPI payload and optionally the shift code.
    This is called after reserve_baseline_slot when the payload is built later.
    
    Args:
        tracking_id: The ID of the tracking record to update
        kpi_payload: The KPI payload sent to SAP
        shift_code: Shift code (A, B, C) if not already set
    """
    try:
        with PostgresSessionLocal() as db:
            tracking = db.query(KpiSendTracking).filter(KpiSendTracking.id == tracking_id).first()
            if tracking:
                tracking.kpi_payload_sent = kpi_payload
                if shift_code and not tracking.shift_code:
                    tracking.shift_code = shift_code.upper()
                db.commit()
                log.info(f"✅ Updated tracking {tracking_id} with payload and shift_code={shift_code}")
                return True
            else:
                log.warning(f"⚠️ Tracking record {tracking_id} not found for update")
                return False
    except Exception as e:
        log.exception(f"Error updating tracking payload: {e}")
        return False


def get_incremental_kpis(department: str, shift_code: str = None, exclude_recent_seconds: int = 10):
    """
    Get incremental KPIs (only new data since last send).
    exclude_recent_seconds: Exclude baselines created within this many seconds (to skip recently reserved ones).
    Returns (kpi_result, current_scada, baseline) tuple.
    """
    # Get current SCADA values FIRST (before checking baseline)
    current_scada = get_current_scada_values()
    if not current_scada:
        log.warning("No current SCADA data available")
        return None, None, None
    
    # ✅ CRITICAL: Check for duplicate sends with exact same SCADA values (within last 30 seconds)
    if check_duplicate_send(department, current_scada, time_window_seconds=30):
        log.warning(f"⚠️ DUPLICATE PREVENTED: Same SCADA values were sent recently for {department}")
        return None, current_scada, None
    
    # Get last sent baseline, excluding recently reserved ones
    baseline = get_last_sent_baseline(department, shift_code, exclude_recent_seconds=exclude_recent_seconds)
    
    # ✅ CRITICAL: Check if this is a very recent send (within 5 seconds)
    if baseline and baseline.get("_recent_send"):
        log.warning(f"⚠️ Preventing duplicate send for {department} - last send was less than 5 seconds ago")
        return None, current_scada, baseline
    
    # ✅ CRITICAL: Check if current SCADA is exactly the same as baseline (no new data)
    # Only compare KEY production fields, not all fields
    if baseline:
        if department.upper() == "MILLING":
            key_fields = ["WG202", "WG501", "WG502"]  # Key production indicators
        elif department.upper() == "PACKING":
            key_fields = ["PL601_TOT"]  # Key production indicator
        else:
            # Fallback: compare all fields
            key_fields = [
                "WG101", "WG201", "WG202", "WG301", "WG302", "WG501", "WG502", "WG503",
                "DM101", "DM102", "DM201", "DM202", "DM203",
                "PL601_TOT", "PL602_TOT", "PL603_TOT"
            ]
        
        # Check if all KEY fields are the same (within small tolerance for floating point)
        all_same = True
        for field in key_fields:
            current_val = safe(current_scada.get(field, 0.0))
            baseline_val = safe(baseline.get(field, 0.0))
            # Use small tolerance (0.01) for floating point comparison
            if abs(current_val - baseline_val) > 0.01:
                all_same = False
                log.info(f"✅ New data detected: {field} changed from {baseline_val:.2f} to {current_val:.2f}")
                break
        
        if all_same:
            log.info(f"⚠️ No new data for {department} - key production values are identical to last sent baseline")
            log.info(f"   Last sent at: {baseline.get('last_sent_at')}")
            log.info(f"   Key fields: {', '.join([f'{f}={current_scada.get(f, 0):.2f}' for f in key_fields])}")
            return None, current_scada, baseline
    
    # Calculate delta
    delta_scada = calculate_delta_scada(current_scada, baseline)
    
    if not delta_scada:
        log.warning("No delta SCADA data to calculate KPIs")
        return None, current_scada, baseline
    
    # Check if there's any meaningful delta
    has_delta = any(v > 0.001 for v in delta_scada.values())
    if not has_delta:
        log.info("No meaningful delta (all values are zero or very small)")
        return None, current_scada, baseline
    
    # Add time fields for KPI calculation (use defaults for delta)
    for k in OPTIONAL_TIME_COLS:
        delta_scada.setdefault(k, 0.0)
    
    # Calculate KPIs from delta
    try:
        kpi_result = calc_kpis_from_row(delta_scada)
        
        # Determine if this is first send (full) or incremental send
        send_type = "FULL DATA (first send)" if not baseline else "INCREMENTAL (delta since last send)"
        log.info(f"✅ Calculated KPIs for {department} - {send_type}")
        log.info(f"   Delta summary: WG202={delta_scada.get('WG202', 0):.2f}, WG501={delta_scada.get('WG501', 0):.2f}, WG502={delta_scada.get('WG502', 0):.2f}")
        if baseline:
            log.info(f"   Baseline was: WG202={baseline.get('WG202', 0):.2f}, WG501={baseline.get('WG501', 0):.2f}, WG502={baseline.get('WG502', 0):.2f} (sent at {baseline.get('last_sent_at')})")
            log.info(f"   Current is: WG202={current_scada.get('WG202', 0):.2f}, WG501={current_scada.get('WG501', 0):.2f}, WG502={current_scada.get('WG502', 0):.2f}")
            log.info(f"   → Sending INCREMENTAL: {delta_scada.get('WG202', 0):.2f} = {current_scada.get('WG202', 0):.2f} - {baseline.get('WG202', 0):.2f}")
        else:
            log.info(f"   → Sending FULL DATA: All current values (no previous baseline)")
        
        return kpi_result, current_scada, baseline
    except Exception as e:
        log.exception(f"Error calculating incremental KPIs: {e}")
        return None, current_scada, baseline

