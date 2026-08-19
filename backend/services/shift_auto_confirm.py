# # services/shift_auto_confirm.py
# import logging
# from datetime import datetime
# from sqlalchemy import text

# from database import postgres_engine
# from services.sap_confirmation import SAPConfirmationService, confirm_orders_batch
# from services.system_logger import log_hercules_event

# log = logging.getLogger("shift_auto_confirm")


# def auto_push_shift_confirmation():
#     """
#     AUTO SHIFT END CONFIRMATION JOB
#     - Runs every 1 minute from scheduler
#     - Detects which shifts have ended
#     - Sends SAP confirmation for completed shifts
#     - Prevents duplicates via shift_x_confirmed flags
#     """

#     log.info("=" * 60)
#     log.info("⏱️ Auto Shift-End Confirmation: Scan started")
#     log.info(f"⏱️ Timestamp: {datetime.now().isoformat()}")

#     try:
#         with postgres_engine.connect() as conn:
#             log.debug("✅ Database connection established")

#             # ----------------------------------------------------
#             # FETCH orders that are Validated or InProgress
#             # ----------------------------------------------------
#             rows = conn.execute(text("""
#                 SELECT
#                     id AS process_order_id,
#                     order_id AS po_number,
#                     material,
#                     version,
#                     material_desc,
#                     quantity AS total_qty,
#                     confirmed_qty,
#                     unit AS uom,
#                     plant,
#                     batch,
#                     created_at,
#                     updated_at AS confirmed_at,

#                     current_shift,
#                     weight_shift_a, weight_shift_b, weight_shift_c,
#                     confirmed_shift_a, confirmed_shift_b, confirmed_shift_c,

#                     -- IMPORTANT: use exact column names & alias for map
#                     shift_a_confirmed AS shift_a_flag,
#                     shift_b_confirmed AS shift_b_flag,
#                     shift_c_confirmed AS shift_c_flag,

#                     last_confirmed_qty,
#                     is_final_sent

#                 FROM process_orders
#                 WHERE status IN ('Validated', 'InProgress')
#                 ORDER BY id
#             """)).mappings().all()

#             log.info(f"📊 Found {len(rows)} active orders (Validated/InProgress)")

#             if not rows:
#                 log.info("No active orders found — nothing to confirm.")
#                 return

#             per_shift_orders = []
#             now = datetime.now()
#             log.debug(f"🔍 Scanning shifts for orders...")

#             # ----------------------------------------------------
#             # SHIFT DETECTION LOGIC
#             # ----------------------------------------------------
#             for r in rows:

#                 current_shift = (r.current_shift or "").upper().strip()

#                 shift_info = [
#                     ("A", r.weight_shift_a, r.confirmed_shift_a, bool(r.shift_a_flag)),
#                     ("B", r.weight_shift_b, r.confirmed_shift_b, bool(r.shift_b_flag)),
#                     ("C", r.weight_shift_c, r.confirmed_shift_c, bool(r.shift_c_flag)),
#                 ]

#                 for letter, weight_val, confirmed_val, flag in shift_info:

#                     # Skip NOT completed shift (we NEVER send mid-shift)
#                     if letter == current_shift:
#                         continue

#                     # Skip empty shift
#                     try:
#                         w = float(weight_val or 0)
#                     except:
#                         w = 0

#                     if w <= 0:
#                         continue

#                     # Skip already confirmed shifts
#                     try:
#                         c = float(confirmed_val or 0)
#                     except:
#                         c = 0

#                     if flag or c > 0:
#                         log.debug(f"⏭️ Skipping shift {letter} for PO {r.po_number}: already confirmed (flag={flag}, confirmed={c})")
#                         continue

#                     # ----------------------------------------------------
#                     # Build per-shift order payload
#                     # ----------------------------------------------------
#                     log.info(f"✅ Found unconfirmed shift {letter} for PO {r.po_number}: weight={w} kg")
#                     per_shift_orders.append({
#                         "process_order_id": r.process_order_id,
#                         "po_number": r.po_number,
#                         "material": r.material,
#                         "version": r.version or "",
#                         "material_desc": r.material_desc or "",
#                         "total_qty": float(r.total_qty or 0),
#                         "confirmed_weight": float(w),
#                         "uom": r.uom or "KG",
#                         "plant": r.plant,
#                         "batch": r.batch or "",
#                         "created_at": r.created_at,
#                         "confirmed_at": r.confirmed_at,
#                         "shift": letter,
#                         "shift_column": f"weight_shift_{letter.lower()}",
#                         "confirmed_shift_column": f"confirmed_shift_{letter.lower()}",
#                         "shift_flag_column": f"shift_{letter.lower()}_confirmed",
#                         "last_confirmed_qty": float(r.last_confirmed_qty or 0),
#                         "is_final_sent": bool(r.is_final_sent)
#                     })

#             log.info(f"📋 Total shifts to confirm: {len(per_shift_orders)}")

#             if not per_shift_orders:
#                 log.info("No completed shifts pending SAP confirmation.")
#                 return

#             # ----------------------------------------------------
#             # SEND TO SAP (online)
#             # ----------------------------------------------------
#             sap_service = SAPConfirmationService()
#             log.info(f"🚀 Sending {len(per_shift_orders)} shift confirmations to SAP (AUTO MODE)")
#             log.info(f"📦 Shift details: {[(item['po_number'], item['shift'], item['confirmed_weight']) for item in per_shift_orders]}")

#             sap_result = confirm_orders_batch(per_shift_orders, "auto")
#             log.info(f"📥 SAP response: ok={sap_result.get('ok', False)}, successful={len(sap_result.get('successful_orders', []))}, failed={len(sap_result.get('failed_orders', []))}")

#             # Normalize PO keys
#             po_map = {}
#             for item in per_shift_orders:
#                 key = str(item["po_number"]).lstrip("0")
#                 po_map.setdefault(key, []).append(item)

#             successful = set()
#             failed = []
#             log.debug(f"📊 Processing SAP results...")

#             if sap_result.get("ok", False):
#                 successful_sap_pos = set(str(po).lstrip("0") for po in sap_result.get("successful_orders", []))

#                 for norm, items in po_map.items():
#                     if norm in successful_sap_pos:
#                         for it in items:
#                             successful.add((it["po_number"], it["shift"]))
#                     else:
#                         for it in items:
#                             failed.append((it["po_number"], it["shift"]))
#             else:
#                 # Complete SAP failure → mark all failed
#                 for it in per_shift_orders:
#                     failed.append((it["po_number"], it["shift"]))

#             # ----------------------------------------------------
#             # UPDATE DATABASE
#             # ----------------------------------------------------
#             log.info(f"💾 Updating database: {len(successful)} successful confirmations")
            
#             if successful:
#                 with postgres_engine.connect() as conn2:
#                     for po, shift in list(successful):
#                         log.debug(f"💾 Updating PO {po}, shift {shift}")
#                         items = po_map.get(str(po).lstrip("0"), [])
#                         item = next((x for x in items if x["shift"] == shift), None)
#                         if not item:
#                             continue

#                         confirmed_col = item["confirmed_shift_column"]
#                         flag_col = item["shift_flag_column"]
#                         weight_val = float(item["confirmed_weight"])

#                         new_last = item["last_confirmed_qty"] + weight_val
#                         is_final = new_last >= float(item["total_qty"])

#                         conn2.execute(text(f"""
#                             UPDATE process_orders
#                             SET {confirmed_col} = :val,
#                                 {flag_col} = TRUE,
#                                 last_confirmed_qty = :new_last,
#                                 is_final_sent = :final,
#                                 status = :status,
#                                 updated_at = NOW()
#                             WHERE order_id = :po
#                         """), {
#                             "val": weight_val,
#                             "new_last": new_last,
#                             "final": is_final,
#                             "status": "Confirmed" if is_final else "InProgress",
#                             "po": po
#                         })

#                     conn2.commit()

#             # ----------------------------------------------------
#             # LOGGING
#             # ----------------------------------------------------
#             log_hercules_event(
#                 action="Auto Shift-End Confirmation",
#                 status="Success" if len(failed) == 0 else "PartialSuccess",
#                 details=f"AUTO SAP confirmation → {len(successful)} OK, {len(failed)} failed",
#                 metadata={
#                     "attempted": len(per_shift_orders),
#                     "successful": len(successful),
#                     "failed": len(failed),
#                 }
#             )

#             log.info(f"✅ Auto shift confirmation complete: {len(successful)} ok, {len(failed)} failed")
#             log.info("=" * 60)

#     except Exception as e:
#         log.exception("❌ Auto shift confirmation failed: %s", e)
#         log.error(f"❌ Error details: {type(e).__name__}: {str(e)}")
#         log_hercules_event(
#             action="Auto Shift-End Confirmation",
#             status="Error",
#             details="Auto shift confirmation failed",
#             metadata={"error": str(e)}
#         )
import logging
import json
import os
from datetime import datetime
from sqlalchemy import text

from database import postgres_engine
from services.sap_confirmation import SAPConfirmationService, confirm_orders_batch
from services.system_logger import log_hercules_event
from models.shift_master import ShiftMaster
from models.offline_confirmation import OfflineConfirmation
from database import PostgresSessionLocal
from utils.vpn_check import check_vpn_connection
# ✅ REMOVED: log_sap_request import (Feb 4, 2026) - logging now handled by confirm_orders_batch

log = logging.getLogger("shift_auto_confirm")


def _parse_time(time_val) -> 'datetime.time':
    """
    Parse a time value that might be a string or datetime.time object.
    Returns a datetime.time object.
    """
    from datetime import time as dt_time
    
    if time_val is None:
        return None
    
    # Already a time object
    if isinstance(time_val, dt_time):
        return time_val
    
    # String format like "07:00:00" or "15:00:00"
    if isinstance(time_val, str):
        try:
            parts = time_val.split(":")
            hour = int(parts[0])
            minute = int(parts[1]) if len(parts) > 1 else 0
            second = int(parts[2]) if len(parts) > 2 else 0
            return dt_time(hour, minute, second)
        except (ValueError, IndexError) as e:
            log.warning(f"Failed to parse time string '{time_val}': {e}")
            return None
    
    log.warning(f"Unknown time format: {type(time_val)} - {time_val}")
    return None


def _get_shift_timing(shift_code: str, plant: str, department: str):
    """
    Get detailed timing information for a shift.
    Returns a dict with:
      - found: bool
      - start_time: time
      - end_time: time
      - seconds_remaining: float (positive = future, negative = past)
      - is_ending_soon: bool (within 5 mins before end)
      - has_ended: bool (past end time)
      - has_ended_with_buffer: bool (past end time + 2 min buffer)
    """
    from datetime import timedelta
    
    result = {
        "found": False,
        "seconds_remaining": 0,
        "is_ending_soon": False,
        "has_ended": False,
        "has_ended_with_buffer": False
    }

    try:
        with PostgresSessionLocal() as db:
            # Get shift from database
            if department.upper() == "PACKING":
                shift = db.query(ShiftMaster).filter(
                    ShiftMaster.department == "PACKING",
                    ShiftMaster.shift_code == shift_code
                ).first()
            else:
                # MILLING: Get shift for specific plant
                shift = db.query(ShiftMaster).filter(
                    ShiftMaster.plant == plant,
                    ShiftMaster.department == "MILLING",
                    ShiftMaster.shift_code == shift_code
                ).first()
            
            if not shift:
                log.warning(f"⚠️ Shift {shift_code} not found in database (plant={plant}, department={department})")
                return result
            
            result["found"] = True
            now = datetime.now()
            current_time = now.time()
            
            shift_end_time = _parse_time(shift.end_time)
            shift_start_time = _parse_time(shift.start_time)
            
            if not shift_end_time or not shift_start_time:
                log.warning(f"⚠️ Could not parse shift times for {shift_code}")
                return result

            # Determine Shift End Datetime
            # For same-day shifts (start < end, e.g., 07:00 - 15:00)
            if shift_start_time < shift_end_time:
                shift_end_datetime = datetime.combine(now.date(), shift_end_time)
            else:
                # Overnight shift (start > end, e.g., 23:00 - 07:00)
                shift_end_datetime = datetime.combine(now.date(), shift_end_time)
                # If current time is BEFORE end time (e.g. 05:00 < 07:00), it ends TODAY.
                # If current time is AFTER end time (e.g. 23:30 > 07:00), it ends TOMORROW.
                # But wait, if we are at 23:30, the shift STARTED today at 23:00 and ends TOMORROW at 07:00.
                if current_time > shift_start_time:
                     # e.g. 23:30 > 23:00. Ends tomorrow.
                     shift_end_datetime = datetime.combine((now + timedelta(days=1)).date(), shift_end_time)
                elif current_time < shift_end_time:
                     # e.g. 05:00 < 07:00. Ends today.
                     pass
                else:
                     # We are between end and start (e.g. 12:00).
                     # The "current" instance of this shift code hasn't started yet?
                     # Or we are looking at the PAST shift?
                     # This function checks if "A shift" (generic) is ending soon relative to NOW.
                     # If it's 12:00, and shift is 23:00-07:00. It is NOT ending soon.
                     # It starts in 11 hours.
                     # We need to target the *nearest* occurrence?
                     # Actually, for "ending soon", we care about the one ending soon.
                     shift_end_datetime = datetime.combine(now.date(), shift_end_time)
                     if current_time > shift_end_time:
                         # Shift end passed today. The next one ends tomorrow.
                         # But we might want to check if the *previous* one just ended?
                         # Let's rely on seconds_remaining.
                         pass

            # Recalculate robustly:
            # We want the shift end that is closest to NOW.
            
            # Simple approach: Construct the end time for Today and Tomorrow and Yesterday, pick closest?
            # Or just assume standard flow.
            
            # Let's stick to the previous logic but refined:
            # If same day:
            is_active = False
            if shift_start_time < shift_end_time:
                shift_end_dt = datetime.combine(now.date(), shift_end_time)
                is_active = shift_start_time <= current_time < shift_end_time
            else:
                # Overnight
                # If now is 23:30 (start 23:00, end 07:00). End is T+1 07:00.
                # If now is 06:30. End is T 07:00.
                if current_time >= shift_start_time:
                    shift_end_dt = datetime.combine((now + timedelta(days=1)).date(), shift_end_time)
                    is_active = True
                elif current_time < shift_end_time:
                    shift_end_dt = datetime.combine(now.date(), shift_end_time)
                    is_active = True
                else:
                    # Time is between End and Start (e.g. 12:00).
                    # The shift ended earlier today.
                    shift_end_dt = datetime.combine(now.date(), shift_end_time)
                    is_active = False

            seconds_remaining = (shift_end_dt - now).total_seconds()
            minutes_remaining = seconds_remaining / 60.0 if seconds_remaining > 0 else 0
            
            # Ending Soon: 0 < remaining <= 5 mins (300s) before end
            # Triggers when there's between 1 second and 5 minutes remaining
            is_ending_soon = 0 < seconds_remaining <= 300
            
            # Has Ended: remaining <= 0
            has_ended = seconds_remaining <= 0
            
            # Has Ended with Buffer: Trigger in a TIME WINDOW (2 min before to 10 min after shift end)
            # ✅ CRITICAL FIX (Dec 16, 2025): Use a window, not a single threshold
            # seconds_remaining = 120 means "2 min until shift end" (BEFORE)
            # seconds_remaining = -600 means "10 min past shift end" (AFTER) - widened so InProgress/Pending with confirm weight are not missed
            has_ended_with_buffer = -600 <= seconds_remaining <= 120
            
            result.update({
                "seconds_remaining": seconds_remaining,
                "is_ending_soon": is_ending_soon,
                "has_ended": has_ended,
                "has_ended_with_buffer": has_ended_with_buffer,
                "is_active": is_active
            })
            
            # ✅ ENHANCED LOGGING (Dec 16, 2025): ALWAYS log when close to shift end (within 5 minutes)
            # This helps diagnose timing issues with shift-end confirmations
            if abs(seconds_remaining) <= 300:  # Within 5 minutes (before or after)
                log.info(f"🕒 Shift {shift_code} Timing (plant={plant}, dept={department}): "
                         f"now={current_time.strftime('%H:%M:%S')}, "
                         f"end={shift_end_time.strftime('%H:%M:%S') if hasattr(shift_end_time, 'strftime') else str(shift_end_time)}, "
                         f"seconds_remaining={seconds_remaining:.0f}, "
                         f"minutes={seconds_remaining/60:.1f}min, "
                         f"is_active={is_active}, "
                         f"has_ended={has_ended}, "
                         f"has_ended_with_buffer={has_ended_with_buffer}")
            else:
                log.debug(f"🕒 Shift {shift_code} Timing: now={current_time}, end={shift_end_time}, rem={seconds_remaining:.1f}s, ended_buf={has_ended_with_buffer}")
            
    except Exception as e:
        log.error(f"Error checking shift timing for {shift_code}: {e}")
        
    return result


def _is_shift_ending_soon(shift_code: str, plant: str, department: str, minutes_before: int = 5) -> bool:
    """Wrapper using new unified timing function"""
    timing = _get_shift_timing(shift_code, plant, department)
    return timing["is_ending_soon"]


def _has_shift_ended(shift_code: str, plant: str, department: str) -> bool:
    """Wrapper using new unified timing function"""
    timing = _get_shift_timing(shift_code, plant, department)
    return timing["has_ended_with_buffer"]



def auto_push_shift_confirmation():
    """
    AUTO SHIFT END CONFIRMATION JOB
    - Runs every 1 minute from scheduler
    - Detects finished shifts
    - Sends SAP confirmation for completed shifts
    - Updates DB correctly (final shift → status = Validated)
    """
    # ✅ FIX (Jan 29, 2026): Add print statements for debugging
    print("=" * 60)
    print("⏱️⏱️⏱️ AUTO SHIFT-END CONFIRMATION: SCAN STARTED ⏱️⏱️⏱️")
    print(f"⏱️ Timestamp: {datetime.now().isoformat()}")
    print(f"⏱️ Current time: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    
    log.info("=" * 60)
    log.info("⏱️⏱️⏱️ AUTO SHIFT-END CONFIRMATION: SCAN STARTED ⏱️⏱️⏱️")
    log.info(f"⏱️ Timestamp: {datetime.now().isoformat()}")
    log.info(f"⏱️ Current time: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")

    try:
        # ✅ CRITICAL FIX (Dec 15, 2025): Use PostgresSessionLocal for consistent database access
        # The raw postgres_engine.connect() was sometimes returning stale/empty results
        # due to connection pooling or isolation level differences
        with PostgresSessionLocal() as db:
            
            # ✅ DEBUG: First check what statuses exist in the database
            debug_statuses = db.execute(text("""
                SELECT status, COUNT(*) as cnt 
                FROM process_orders 
                GROUP BY status
            """)).mappings().all()
            print(f"🔍 DEBUG: Status distribution in database: {[dict(s) for s in debug_statuses]}")
            log.info(f"🔍 DEBUG: Status distribution in database: {[dict(s) for s in debug_statuses]}")
            
            # ✅ DEBUG: Check for orders that SHOULD match our query
            debug_matching = db.execute(text("""
                SELECT order_id, status, UPPER(status) as upper_status
                FROM process_orders 
                WHERE UPPER(status) IN ('VALIDATED', 'COMPLETED', 'INPROGRESS', 'CONFIRMED', 'PENDING')
                  AND (UPPER(TRIM(status)) != 'CNF')
                  AND (UPPER(TRIM(status)) != 'COMP')
                LIMIT 10
            """)).mappings().all()
            log.info(f"🔍 DEBUG: Sample orders matching query: {[dict(m) for m in debug_matching]}")

            # ----------------------------------------------------
            # FETCH orders that are Validated (final shift still needs SAP)
            # or InProgress (normal shift cycle)
            # ✅ Use UPPER() for case-insensitive matching
            # ----------------------------------------------------
            rows = db.execute(text("""
                SELECT
                    id AS process_order_id,
                    order_id AS po_number,
                    material,
                    version,
                    material_desc,
                    quantity AS total_qty,
                    confirmed_qty,
                    unit AS uom,
                    plant,
                    batch,
                    created_at,
                    updated_at AS confirmed_at,

                    current_shift,
                    shift_end_time,
                    weight_shift_a, weight_shift_b, weight_shift_c,
                    confirmed_shift_a, confirmed_shift_b, confirmed_shift_c,

                    shift_a_confirmed AS shift_a_flag,
                    shift_b_confirmed AS shift_b_flag,
                    shift_c_confirmed AS shift_c_flag,

                    last_confirmed_qty,
                    is_final_sent,
                    status,
                    order_type,
                    
                    -- ✅ Add scale columns for PACKING orders
                    scale1,
                    scale1_qty,
                    scale2,
                    scale2_qty,
                    scale3,
                    scale3_qty,
                    scrap

                FROM process_orders
                WHERE UPPER(status) IN ('VALIDATED', 'COMPLETED', 'INPROGRESS', 'CONFIRMED', 'PENDING')
                  AND (UPPER(TRIM(status)) != 'CNF')
                  AND (UPPER(TRIM(status)) != 'COMP')
                ORDER BY id
            """)).mappings().all()

            log.info(f"📊 Found {len(rows)} active orders")
            
            # ✅ DEBUG: Log details of found orders
            if rows:
                for idx, r in enumerate(rows[:5]):  # Log first 5 orders
                    log.info(f"🔍 Order {idx+1}: PO={r.po_number}, Status={r.status}, Plant={r.plant}, OrderType={r.order_type}")
            else:
                log.warning(f"⚠️ Query returned 0 rows. This might indicate:")
                log.warning(f"   1. No orders exist with status 'Validated', 'Completed', 'InProgress', 'Confirmed', or 'Pending'")
                log.warning(f"   2. Database connection/session issue")
                log.warning(f"   3. Status values in DB don't match expected values")

            if not rows:
                log.info("No active orders — nothing to confirm.")
                return

            per_shift_orders = []
            
            # ✅ Log summary of orders being checked
            log.info(f"🔍 Checking {len(rows)} orders for completed shifts...")

            # ----------------------------------------------------
            # CHECK EACH SHIFT
            # ----------------------------------------------------
            validated_orders_count = sum(1 for r in rows if (r.status or "").upper() in ("VALIDATED", "COMPLETED", "CONFIRMED"))
            log.info(f"📊 Total orders to check: {len(rows)} (Validated/Completed: {validated_orders_count}, InProgress: {len(rows) - validated_orders_count})")
            
            for r in rows:

                current_shift = (r.current_shift or "").upper().strip()
                order_status = (r.status or "").upper()
                # ✅ Feb 5, 2026: Treat both "Validated" and "Completed" as validated orders
                is_validated_order = (order_status in ("VALIDATED", "COMPLETED"))
                
                log.info(f"🔍 Checking PO {r.po_number} (status={order_status}, current_shift={current_shift}, shift_end_time={r.shift_end_time})")
                log.info(f"   Shift weights: A={r.weight_shift_a or 0}, B={r.weight_shift_b or 0}, C={r.weight_shift_c or 0}")
                log.info(f"   Confirmed: A={r.confirmed_shift_a or 0}, B={r.confirmed_shift_b or 0}, C={r.confirmed_shift_c or 0}")
                log.info(f"   Flags: A={bool(r.shift_a_flag)}, B={bool(r.shift_b_flag)}, C={bool(r.shift_c_flag)}")

                shift_info = [
                    ("A", r.weight_shift_a, r.confirmed_shift_a, bool(r.shift_a_flag)),
                    ("B", r.weight_shift_b, r.confirmed_shift_b, bool(r.shift_b_flag)),
                    ("C", r.weight_shift_c, r.confirmed_shift_c, bool(r.shift_c_flag)),
                ]

                # ✅ For validated orders: Track if we've already added a shift for this order
                # Only process ONE shift per validated order per run to prevent multiple confirmations
                validated_order_shift_added = False
                
                # ✅ SIMPLIFIED (Dec 15, 2025): Find which shift has ENDED for this department
                # Both validated and partial orders trigger ONLY when shift has ended
                # Determine department first
                # ✅ CRITICAL FIX (Jan 28, 2026): Use order_type column to determine department, NOT plant
                # Previously: department = "MILLING" if "3130" in plant_str else "PACKING"
                # This was incorrect because PACKING orders can have plant 3130 but should use PACKING shift times
                plant_str = str(r.plant or "3130")
                order_type_str = (r.order_type or "").upper()
                # Use order_type to determine department - order_type accurately reflects MILLING vs PACKING
                department = order_type_str if order_type_str in ("MILLING", "PACKING") else ("MILLING" if "3130" in plant_str else "PACKING")
                
                # ✅ For validated orders: Check shifts for this department to find which one has ENDED
                # PACKING has only 2 shifts (A, B), MILLING has 3 shifts (A, B, C)
                shift_ended_for_department = None
                if is_validated_order:
                    # Determine which shifts to check based on department
                    shifts_to_check = ["A", "B"] if department == "PACKING" else ["A", "B", "C"]
                    
                    # Check shifts for this department to find which one has ENDED (with buffer)
                    for shift_letter in shifts_to_check:
                        timing = _get_shift_timing(shift_letter, plant_str, department)
                        if timing["has_ended_with_buffer"]:
                            shift_ended_for_department = shift_letter
                            seconds_rem = timing.get("seconds_remaining", 0)
                            minutes_rem = abs(seconds_rem) / 60.0
                            log.info(f"🎯 Validated {department} order PO {r.po_number}: Shift {shift_letter} for {department} has ENDED ({minutes_rem:.1f} min ago)")
                            break
                
                # ✅ CRITICAL: For validated orders, determine which shift has the most production
                # This ensures we confirm the correct shift (the one with actual production)
                # instead of an old shift that might have ended
                if is_validated_order:
                    # Find the shift with the most unconfirmed production
                    # PACKING orders only have shifts A and B, skip shift C for PACKING
                    max_production_shift = None
                    max_production = 0
                    for shift_letter, shift_weight, shift_confirmed, shift_flag in shift_info:
                        # Skip shift C for PACKING orders
                        if department == "PACKING" and shift_letter == "C":
                            continue
                        if not shift_flag:  # Not already confirmed
                            try:
                                w_val = float(shift_weight or 0)
                                c_val = float(shift_confirmed or 0)
                                remaining = w_val - c_val
                                if remaining > max_production:
                                    max_production = remaining
                                    max_production_shift = shift_letter
                            except:
                                pass
                    
                    # ✅ If a shift for this department has ended, prioritize it over max production shift
                    if shift_ended_for_department:
                        max_production_shift = shift_ended_for_department
                        log.info(f"🎯 Validated {department} order PO {r.po_number}: Prioritizing shift {shift_ended_for_department} (has ENDED for {department}) over production-based shift")
                    elif max_production_shift:
                        log.info(f"🎯 Validated {department} order PO {r.po_number}: Shift with most production is {max_production_shift} (remaining={max_production:.2f})")
                    else:
                        # No production found, will use remaining_to_target logic
                        log.info(f"🎯 Validated {department} order PO {r.po_number}: No unconfirmed production found, will use remaining_to_target")
                else:
                    max_production_shift = None

                for letter, weight_val, confirmed_val, flag in shift_info:

                    # ✅ CRITICAL: PACKING orders only have shifts A and B, skip shift C for PACKING
                    if department == "PACKING" and letter == "C":
                        log.info(f"⏭️ PO {r.po_number} - Shift {letter}: Skipping (PACKING orders only have shifts A and B, not C)")
                        continue

                    # ✅ CRITICAL FIX (Dec 15, 2025): For VALIDATED orders, don't skip based on flag alone
                    # A partial/mid-shift confirmation may have set the flag, but the order was later validated
                    # and still needs the final confirmation sent at shift end.
                    # For VALIDATED orders: Check if there's remaining production to confirm
                    # For InProgress orders: Skip if flag is set (already confirmed)
                    is_validated_order_early_check = (r.status or "").upper() in ("VALIDATED", "CONFIRMED", "COMPLETED")
                    
                    if flag:
                        if is_validated_order_early_check:
                            # ✅ For VALIDATED orders: Check if there's remaining production DESPITE flag
                            # This handles the case where partial confirmation set the flag, but order was later validated
                            try:
                                w = float(weight_val or 0)
                                c = float(confirmed_val or 0)
                                remaining_in_shift = w - c
                                
                                # Also check remaining_to_target for validated orders
                                total_qty = float(r.total_qty or 0)
                                total_confirmed = float(r.confirmed_shift_a or 0) + float(r.confirmed_shift_b or 0) + float(r.confirmed_shift_c or 0)
                                remaining_to_target = max(0, total_qty - total_confirmed)
                                
                                if remaining_in_shift > 0 or remaining_to_target > 0:
                                    # ✅ There's remaining production - DON'T skip, let it process
                                    log.info(f"✅ PO {r.po_number} - Shift {letter}: VALIDATED order with flag=True BUT has remaining production (shift_remaining={remaining_in_shift:.2f}, target_remaining={remaining_to_target:.2f}) - PROCESSING instead of skipping")
                                    # ✅ FIX (Jan 29, 2026): Don't continue here - let it fall through to timing check
                                    pass  # Continue processing below
                                else:
                                    # No remaining production - safe to skip
                                    log.info(f"⏭️ PO {r.po_number} - Shift {letter}: Skipping VALIDATED order (flag=True and no remaining: shift_remaining={remaining_in_shift:.2f}, target_remaining={remaining_to_target:.2f})")
                                    continue
                            except Exception as e:
                                log.warning(f"⚠️ PO {r.po_number} - Shift {letter}: Error checking remaining production: {e} - skipping")
                                continue
                        else:
                            # ✅ For InProgress/Pending: Allow second (incremental) confirmation when shift has more production
                            # Same as VALIDATED: if remaining_in_shift > 0, do not skip so remaining_for_shift can be sent
                            try:
                                w = float(weight_val or 0)
                                c = float(confirmed_val or 0)
                                remaining_in_shift = w - c
                                total_qty = float(r.total_qty or 0)
                                total_confirmed = float(r.confirmed_shift_a or 0) + float(r.confirmed_shift_b or 0) + float(r.confirmed_shift_c or 0)
                                remaining_to_target = max(0, total_qty - total_confirmed)
                                if remaining_in_shift > 0 or remaining_to_target > 0:
                                    log.info(f"✅ PO {r.po_number} - Shift {letter}: InProgress order with flag=True BUT has remaining (shift_remaining={remaining_in_shift:.2f}, target_remaining={remaining_to_target:.2f}) - PROCESSING for incremental confirm")
                                    pass  # Continue processing below
                                else:
                                    log.info(f"⏭️ PO {r.po_number} - Shift {letter}: Skipping InProgress order (flag=True and no remaining: shift_remaining={remaining_in_shift:.2f}, target_remaining={remaining_to_target:.2f})")
                                    continue
                            except Exception as e:
                                log.warning(f"⚠️ PO {r.po_number} - Shift {letter}: Error checking remaining for InProgress: {e} - skipping")
                                continue

                    # ✅ CRITICAL: Auto-trigger ONLY works at actual shift end, not mid-shift
                    # For ALL orders: Check if shift has actually ended based on schedule
                    # ✅ CRITICAL FIX (Jan 28, 2026): Use order_type column to determine department, NOT plant
                    plant_str = str(r.plant or "3130")
                    order_type_for_timing = (r.order_type or "").upper()
                    department = order_type_for_timing if order_type_for_timing in ("MILLING", "PACKING") else ("MILLING" if "3130" in plant_str else "PACKING")
                    
                    # ✅ ALWAYS check if shift has actually ended (regardless of order status)
                    log.info(f"🔍 PO {r.po_number} - Shift {letter}: Checking timing (plant={plant_str}, order_type={order_type_for_timing}, department={department})")
                    
                    # Use new unified timing function
                    timing_info = _get_shift_timing(letter, plant_str, department)
                    # ✅ FIX (Jan 29, 2026): Both VALIDATED and InProgress use the SAME timing
                    # - has_ended_with_buffer: True only within 2min before to 30sec after shift end
                    # This prevents validated orders from triggering immediately when a past shift ended
                    shift_has_ended_any = timing_info.get("has_ended", False)  # For logging only
                    shift_has_ended_buffer = timing_info["has_ended_with_buffer"]  # For BOTH order types
                    is_ending_soon = timing_info["is_ending_soon"]
                    is_active = timing_info.get("is_active", False)
                    seconds_remaining = timing_info.get("seconds_remaining", 0)
                    minutes_remaining = seconds_remaining / 60.0 if seconds_remaining > 0 else 0
                    
                    # ✅ Enhanced logging for timing checks
                    log.info(f"🕒 PO {r.po_number} - Shift {letter}: Timing check - is_active={is_active}, is_ending_soon={is_ending_soon}, has_ended={shift_has_ended_any}, has_ended_buffer={shift_has_ended_buffer}, seconds_remaining={seconds_remaining:.0f}, minutes_remaining={minutes_remaining:.1f}")
                    
                    # Check if this is the current shift based on DB or timing
                    # Note: DB might be lagging if worker hasn't updated current_shift yet
                    # So we use timing as the source of truth for "Active" vs "Ended"
                    
                    # ✅ Check order status early to determine confirmation rules
                    is_validated_order = (r.status or "").upper() in ("VALIDATED", "CONFIRMED", "COMPLETED")
                    # ✅ FIX (Jan 30, 2026): Include PENDING orders with InProgress
                    # PENDING orders with produced weight should also be sent at shift end
                    is_inprogress_order = (r.status or "").upper() in ("INPROGRESS", "PENDING")
                    
                    # ✅ UPDATED RULES (Jan 30, 2026): 
                    # - VALIDATED orders: Confirm when shift has ENDED (any time - no narrow window)
                    #   These are finalized orders that MUST be confirmed to SAP
                    # - INPROGRESS/PENDING orders: Confirm only within narrow window (has_ended_with_buffer)
                    #   This prevents duplicate confirmations for ongoing orders
                    
                    should_process = False
                    
                    if is_validated_order:
                        # ✅ FIX (Jan 29, 2026): VALIDATED orders use SAME timing as InProgress
                        # Both order types should only trigger within the narrow window at shift end
                        # This prevents validated orders from triggering immediately when a past shift ended
                        if shift_has_ended_buffer:
                            seconds_rem = timing_info.get("seconds_remaining", 0)
                            minutes_rem = abs(seconds_rem) / 60.0
                            log.info(f"✅✅ PO {r.po_number} - Shift {letter}: VALIDATED order - shift has ENDED ({minutes_rem:.1f} min ago) - WILL PROCESS")
                            should_process = True
                        else:
                            log.info(f"⏭️ PO {r.po_number} - Shift {letter}: Skipping VALIDATED order (shift not ended yet - {minutes_remaining:.1f} min remaining)")
                            should_process = False
                    
                    elif is_inprogress_order:
                        # ✅ InProgress/Pending orders: Confirm ONLY within narrow window (prevents duplicates)
                        if shift_has_ended_buffer:
                            seconds_rem = timing_info.get("seconds_remaining", 0)
                            minutes_rem = abs(seconds_rem) / 60.0
                            log.info(f"✅ PO {r.po_number} - Shift {letter}: {order_status} order - shift has ENDED ({minutes_rem:.1f} min ago) - processing")
                            should_process = True
                        else:
                            log.info(f"⏭️ PO {r.po_number} - Shift {letter}: Skipping {order_status} order (shift not ended yet - {minutes_remaining:.1f} min remaining)")
                            should_process = False
                            
                    if not should_process:
                        continue

                    # ✅ CRITICAL: Calculate values first
                    try:
                        w = float(weight_val or 0)
                    except:
                        w = 0

                    try:
                        c = float(confirmed_val or 0)
                    except:
                        c = 0
                    
                    # Calculate remaining production
                    remaining_production = w - c
                    
                    # ✅ For VALIDATED orders: Calculate remaining to TARGET early
                    # This allows us to process validated orders even if shift weight is 0
                    if is_validated_order:
                        total_qty = float(r.total_qty or 0)
                        total_confirmed = float(r.confirmed_shift_a or 0) + float(r.confirmed_shift_b or 0) + float(r.confirmed_shift_c or 0)
                        remaining_to_target = max(0, total_qty - total_confirmed)
                        
                        # ✅ CRITICAL FIX (Jan 24, 2026): Calculate total remaining production across ALL shifts
                        # This is used to cap the confirmation amount to prevent sending more than actual production
                        total_weight_all_shifts = float(r.weight_shift_a or 0) + float(r.weight_shift_b or 0) + float(r.weight_shift_c or 0)
                        total_remaining_production = max(0, total_weight_all_shifts - total_confirmed)
                        
                        log.info(f"🔍 Validated PO {r.po_number}: total_weight={total_weight_all_shifts:.2f}, total_confirmed={total_confirmed:.2f}, remaining_production={total_remaining_production:.2f}, remaining_to_target={remaining_to_target:.2f}")
                        
                        # ✅ CRITICAL: For validated orders, only process if there's production in this shift
                        # This prevents confirming empty shifts that ended long ago
                        # Only allow remaining_to_target if this shift has some production
                        if w <= 0 and remaining_to_target <= 0:
                            log.info(f"⏭️ PO {r.po_number} - Shift {letter}: Skipping (VALIDATED order, no production={w:.2f} in this shift and no remaining_to_target={remaining_to_target:.2f} - nothing to confirm)")
                            continue
                    else:
                        remaining_to_target = 0
                        total_remaining_production = 0
                    
                    log.info(f"🔍 PO {r.po_number} - Shift {letter}: weight={w:.2f}, confirmed={c:.2f}, remaining={remaining_production:.2f}, flag={flag}, status={r.status}, remaining_to_target={remaining_to_target:.2f}")
                    
                    # ✅ For InProgress orders: Skip if zero production or already confirmed
                    if is_inprogress_order:
                        if w <= 0:
                            log.info(f"⏭️ PO {r.po_number} - Shift {letter}: Skipping (zero production: weight={w:.2f})")
                            continue
                        
                        # Flag already checked at top, but double-check confirmed value
                        if c >= w and w > 0:
                            log.info(f"⏭️ PO {r.po_number} - Shift {letter}: Skipping (already fully confirmed: confirmed={c:.2f} >= weight={w:.2f})")
                            continue
                    
                    # ✅ For Validated orders: Different rules
                    # Allow processing if there's production OR remaining_to_target
                    # Flag already checked at top, so we can proceed
                    if is_validated_order:
                        # ✅ For validated orders: Process if there's production in this shift OR remaining_to_target
                        # This allows confirming validated orders even if shift weight is 0, as long as there's remaining_to_target
                        if w <= 0:
                            # No production in this shift - only process if there's remaining_to_target
                            if remaining_to_target <= 0:
                                log.info(f"⏭️ Validated order PO {r.po_number} - Shift {letter}: Skipping (no production={w:.2f} in this shift and no remaining_to_target={remaining_to_target:.2f} - nothing to confirm)")
                                continue
                            else:
                                # There's remaining_to_target but no production in this shift
                                # This is okay for validated orders - they need to complete the order
                                log.info(f"✅ Validated order PO {r.po_number} - Shift {letter}: Processing (no production in shift but remaining_to_target={remaining_to_target:.2f} - will confirm remaining)")
                        
                        # Skip if remaining_production is negative (confirmed > weight - already over-confirmed)
                        # BUT only if there's no remaining_to_target
                        if remaining_production < 0 and remaining_to_target <= 0:
                            log.info(f"⏭️ Validated order PO {r.po_number} - Shift {letter}: Skipping (over-confirmed: confirmed={c:.2f} > weight={w:.2f}, remaining={remaining_production:.2f}, no remaining_to_target)")
                            continue
                    
                    # ✅ Determine confirmation weight based on order status
                    confirm_weight = 0
                    
                    if is_validated_order:
                        # For VALIDATED orders: Calculate remaining to TARGET (not just shift production)
                        # This ensures we send the correct amount to complete the order
                        # ✅ CRITICAL FIX (Jan 24, 2026): For validated orders, send the FULL remaining_to_target
                        # This handles cases where:
                        # 1. Production continued in a previous shift after mid-shift confirmation
                        # 2. Multiple shifts have unconfirmed production
                        # Example: Target=300, Shift B confirmed=165, Shift B actual=211 (46 unconfirmed)
                        #          Shift C=90 → remaining_to_target=135 (not just 90!)
                        # We should NOT limit to current shift's remaining_production
                        if remaining_to_target > 0:
                            # ✅ FIX: Send the FULL remaining_to_target to complete the order
                            # This includes unconfirmed production from ALL shifts, not just current shift
                            # BUT cap it at total_remaining_production to never send more than actual production
                            confirm_weight = min(remaining_to_target, total_remaining_production)
                            
                            if confirm_weight < remaining_to_target:
                                log.warning(f"⚠️ Validated PO {r.po_number}: Capping confirm_weight from {remaining_to_target:.2f} to {confirm_weight:.2f} (can't exceed actual production)")
                            
                            log.info(f"✅ Validated order PO {r.po_number} - Shift {letter}: Sending {confirm_weight:.2f} to complete order (remaining_to_target={remaining_to_target:.2f}, total_remaining_production={total_remaining_production:.2f}, total={total_qty:.2f}, confirmed={total_confirmed:.2f})")
                        else:
                            # Order already fully confirmed, skip
                            log.info(f"⏭️ Validated order PO {r.po_number} - Shift {letter}: Already fully confirmed (total={total_qty:.2f}, confirmed={total_confirmed:.2f})")
                            continue
                    elif is_inprogress_order:
    # ✅ CRITICAL: For InProgress orders, check if there is remaining production
                        # DO NOT skip just because flag is True - mid-shift confirmation might have set it
                        # Only skip if fully confirmed (confirmed >= weight)
                        if c >= w and w > 0:
                            log.debug(f"⏭️ InProgress order PO {r.po_number} - Shift {letter}: Skipping (fully confirmed: confirmed={c:.2f} >= weight={w:.2f})")
                            continue
                        
                        # Calculate remaining production for this shift
                        remaining_for_shift = w - c
                        if remaining_for_shift <= 0:
                            # No remaining production to confirm
                            log.debug(f"⏭️ InProgress order PO {r.po_number} - Shift {letter}: Skipping (no remaining: weight={w:.2f}, confirmed={c:.2f}, remaining={remaining_for_shift:.2f})")
                            continue
                        
                        # ✅ Use remaining production (incremental), not full weight
                        confirm_weight = remaining_for_shift
                        log.info(f"✅ InProgress order PO {r.po_number} - Shift {letter}: Ready to confirm {confirm_weight:.2f} INCREMENTAL (weight={w:.2f}, already_confirmed={c:.2f}, remaining={remaining_for_shift:.2f})")
                    else:
                        # Unknown status, skip
                        log.info(f"⏭️ PO {r.po_number} - Shift {letter}: Skipping (unknown status '{r.status}')")
                        continue
                    
                    # Final check: must have weight to confirm
                    if confirm_weight <= 0:
                        log.info(f"⏭️ PO {r.po_number} - Shift {letter}: Skipping (no weight to confirm: confirm_weight={confirm_weight:.2f})")
                        continue

                    # ✅ CRITICAL: For validated orders, only process ONE shift per order per run
                    # Prioritize: 1) Shift ending soon for department, 2) Shift with most production
                    # IMPORTANT: This check is per-order, so multiple orders can each have their shift processed
                    if is_validated_order:
                        if validated_order_shift_added:
                            log.info(f"⏭️ PO {r.po_number} - Shift {letter}: Skipping (VALIDATED order already has a shift queued for this run - preventing multiple confirmations per order)")
                            continue
                        
                        # ✅ FIX (Jan 29, 2026): Use shift_has_ended_buffer for validated orders too
                        # Both order types should only trigger within the narrow window at shift end
                        if not shift_has_ended_buffer:
                            log.warning(f"⚠️ PO {r.po_number} - Shift {letter}: INCONSISTENCY - should_process=True but shift_has_ended_buffer={shift_has_ended_buffer} - skipping")
                            continue
                        
                        log.info(f"✅✅ PO {r.po_number} - Shift {letter}: VALIDATED order PASSED all checks - shift_has_ended_buffer=True - PROCEEDING")
                        
                        if max_production_shift and letter != max_production_shift:
                            # max_production_shift is set and different from current shift
                            log.info(f"✅ PO {r.po_number} - Shift {letter}: Processing (VALIDATED order, shift {letter} has ended, even though max_production_shift={max_production_shift})")
                        elif max_production_shift and letter == max_production_shift:
                            # This is the max_production_shift and it has ended - process it
                            log.info(f"✅ PO {r.po_number} - Shift {letter}: Processing (VALIDATED order, this is the max_production_shift and it has ended)")
                        else:
                            # No max_production_shift set, but this shift has ended - process it
                            log.info(f"✅ PO {r.po_number} - Shift {letter}: Processing (VALIDATED order, shift {letter} has ended, no max_production_shift)")

                    # ----------------------------------------------------
                    # BUILD CONFIRMATION PAYLOAD
                    # ✅ Add final_confirmation flag based on order status
                    # ----------------------------------------------------
                    # Rule: If status is Validated → final_confirmation = "X"
                    #       If status is InProgress → final_confirmation = "" (empty)
                    new_last = float(r.last_confirmed_qty or 0) + confirm_weight
                    is_final = is_validated_order  # ✅ Only validated orders get final flag
                    
                    # ✅ Enhanced logging for validated orders with final flag
                    if is_validated_order:
                        log.info(f"🎯 VALIDATED ORDER - PO {r.po_number} - Shift {letter}: Sending {confirm_weight:.2f} with FINAL flag (weight={w:.2f}, confirmed={c:.2f}, total={float(r.total_qty or 0):.2f}, is_final={is_final})")
                        validated_order_shift_added = True  # Mark that we've added a shift for this validated order
                    else:
                        log.info(f"✅ Found shift {letter} for PO {r.po_number}: weight={w:.2f}, confirmed={c:.2f}, remaining={confirm_weight:.2f}, status={r.status}, is_final={is_final}")
                    
                    # ✅ CRITICAL: Ensure shift is always a valid string (A, B, or C)
                    # ✅ CRITICAL: Use the ENDED shift (letter) in confirmation, NOT the next shift
                    # The 'letter' variable represents the shift that just ended (e.g., Shift C)
                    # This ensures we send confirmation with the correct ended shift, not the new/next shift
                    shift_letter = str(letter).strip().upper()
                    if shift_letter not in ("A", "B", "C"):
                        log.error(f"❌ PO {r.po_number} - Invalid shift letter '{letter}', defaulting to current shift lookup")
                        # Fallback: use current shift from database
                        # ✅ CRITICAL FIX (Jan 28, 2026): Use order_type for department, not plant
                        plant_str = str(r.plant or "3130")
                        fallback_order_type = (r.order_type or "").upper()
                        department = fallback_order_type if fallback_order_type in ("MILLING", "PACKING") else ("MILLING" if "3130" in plant_str else "PACKING")
                        from utils.shifts import get_current_shift
                        with PostgresSessionLocal() as db:
                            shift_row = get_current_shift(plant_str, department, db)
                            if shift_row:
                                shift_letter = shift_row.shift_code
                            else:
                                shift_letter = "A"  # Final fallback
                        log.warning(f"⚠️ PO {r.po_number} - Using fallback shift: {shift_letter}")
                    
                    log.info(f"📋 PO {r.po_number} - Building confirmation payload: shift={shift_letter} (ENDED shift), weight={confirm_weight:.2f}, production_shift={letter}")
                    log.info(f"✅✅ ADDING TO CONFIRMATION LIST: PO {r.po_number} - Shift {shift_letter}, Weight={confirm_weight:.2f}, Status={r.status}, is_final={is_final}")
                    
                    per_shift_orders.append({
                        "process_order_id": r.process_order_id,
                        "po_number": r.po_number,
                        "material": r.material,
                        "version": r.version or "",
                        "material_desc": r.material_desc or "",
                        "total_qty": float(r.total_qty or 0),
                        "confirmed_weight": confirm_weight,  # ✅ Use remaining production for validated orders
                        "uom": r.uom or "KG",
                        "plant": r.plant,
                        "batch": r.batch or "",
                        "created_at": r.created_at,
                        "confirmed_at": r.confirmed_at,
                        "shift": shift_letter,  # ✅ Use ENDED shift (letter), NOT the next shift
                        "shift_column": f"weight_shift_{letter.lower()}",
                        "confirmed_shift_column": f"confirmed_shift_{letter.lower()}",
                        "shift_flag_column": f"shift_{letter.lower()}_confirmed",
                        "last_confirmed_qty": float(r.last_confirmed_qty or 0),
                        "is_final_sent": bool(r.is_final_sent),
                        "order_status": r.status,
                        "is_final_confirmation": is_final,  # ✅ Flag for final confirmation
                        # ✅ Add scale columns for PACKING orders (same as manual push)
                        "scale1": r.scale1 or "" if hasattr(r, 'scale1') else "",
                        "scale1_qty": float(r.scale1_qty or 0) if hasattr(r, 'scale1_qty') else 0.0,
                        "scale2": r.scale2 or "" if hasattr(r, 'scale2') else "",
                        "scale2_qty": float(r.scale2_qty or 0) if hasattr(r, 'scale2_qty') else 0.0,
                        "scale3": r.scale3 or "" if hasattr(r, 'scale3') else "",
                        "scale3_qty": float(r.scale3_qty or 0) if hasattr(r, 'scale3_qty') else 0.0,
                        "scrap": float(r.scrap or 0) if hasattr(r, 'scrap') else 0.0
                    })

            log.info(f"📦 Shifts pending SAP confirmation: {len(per_shift_orders)}")
            
            if len(per_shift_orders) > 0:
                # ✅ Build shift details list (avoiding f-string backslash issue)
                shift_details = []
                for item in per_shift_orders:
                    weight_str = f"{item['confirmed_weight']:.2f}"
                    shift_details.append(f"PO {item['po_number']} - Shift {item['shift']}: {weight_str} {item['uom']}")
                log.info(f"📋 Shifts to confirm: {', '.join(shift_details)}")

            if not per_shift_orders:
                log.info("ℹ️ No shifts found ready for auto-confirmation (all shifts are either active, already confirmed, or have zero production)")
                log.info("💡 Tip: Check logs above to see why each shift was skipped")
                return

            # ----------------------------------------------------
            # ✅ CHECK VPN CONNECTION BEFORE SAP CALL
            # For validated orders ending soon (5 min before shift end), check VPN and send immediately
            # Skip VPN check if using mock mode (demo server)
            # ----------------------------------------------------
            # Use SAPConfirmationService to get mock mode status (consistent detection)
            sap_service_check = SAPConfirmationService()
            
            if sap_service_check.mock_mode:
                # Mock mode: Skip VPN check, always send to demo server
                log.info("🔧 MOCK MODE ENABLED - Will send confirmations to DEMO SERVER")
                log.info(f"🔧 Mock mode detection: MOCK_SAP_MODE env={os.getenv('MOCK_SAP_MODE', 'not set')}, mock_mode={sap_service_check.mock_mode}")
                vpn_status = {"connected": True, "message": "Mock mode - using demo server"}
            else:
                # Real SAP mode: Check VPN connection
                log.info("🔧 PRODUCTION MODE - Checking VPN connection to real SAP...")
                vpn_status = check_vpn_connection()
            
            # ✅ Store both validated and partial confirmation orders offline when VPN is down
            validated_orders = [item for item in per_shift_orders if (item.get('order_status') or "").upper() in ("VALIDATED", "CONFIRMED", "COMPLETED")]
            non_validated_orders = [item for item in per_shift_orders if (item.get('order_status') or "").upper() not in ("VALIDATED", "CONFIRMED", "COMPLETED")]
            
            log.info(f"🔍 Orders to process: {len(validated_orders)} validated, {len(non_validated_orders)} partial")
            log.info(f"🔍 VPN/Connection Status: connected={vpn_status.get('connected', False)}, message={vpn_status.get('message', 'N/A')}")
            
            if vpn_status.get("connected"):
                if sap_service_check.mock_mode:
                    log.info(f"📤 Will send {len(validated_orders + non_validated_orders)} orders to DEMO SERVER")
                else:
                    log.info(f"📤 Will send {len(validated_orders + non_validated_orders)} orders to REAL SAP SERVER")
            else:
                log.info(f"📦 Will store {len(validated_orders + non_validated_orders)} orders OFFLINE (VPN disconnected)")
            
            if not vpn_status.get("connected"):
                # VPN is disconnected - store ALL orders (validated + partial) for offline confirmation
                # ✅ UPDATED: Now storing both validated and partial confirmations offline (allows duplicates for partials)
                # ✅ CRITICAL FIX (Dec 15, 2025): DO NOT log to error_log - VPN disconnected is NOT an error
                # The error_log should ONLY contain actual SAP communication errors
                log.info(f"📦 VPN disconnected during auto shift confirmation - storing {len(per_shift_orders)} orders (validated + partial) offline")
                
                stored_count = 0
                stored_orders = []
                
                # ✅ Handle non-validated orders (partial confirmations) - just log to console, NOT error_log
                for item in non_validated_orders:
                    try:
                        po_number = item.get('po_number')
                        shift = item.get('shift')
                        confirmed_weight = item.get('confirmed_weight', 0)
                        log.info(f"📌 Partial confirmation stored offline: PO {po_number} - Shift {shift}: {confirmed_weight:.2f} {item.get('uom', 'KG')}")
                    except Exception as log_err:
                        log.error(f"❌ Failed to log partial confirmation for {item.get('po_number')}: {log_err}")

                
                try:
                    from sqlalchemy import func
                    with PostgresSessionLocal() as offline_db:
                        processed_po_numbers = set()  # Track PO numbers processed in this batch
                        # ✅ Process ALL orders for offline storage (validated + partial confirmations)
                        for item in per_shift_orders:
                            try:
                                po_number = item.get('po_number')
                                
                                # ✅ REMOVED JSON LOGGING FOR OFFLINE STORAGE (Feb 4, 2026)
                                # Offline orders are stored in DB and will be logged to JSON
                                # when actually sent to SAP later (avoids PENDING entries that never update)
                                
                                if not po_number:
                                    log.error(f"❌ No PO number found, skipping")
                                    continue
                                
                                po_num_stripped = str(po_number).lstrip('0')
                                if not po_num_stripped or po_num_stripped == '':
                                    po_num_stripped = str(po_number)
                                
                                log.info(f"🔍 [ShiftAuto] Checking duplicate for PO: original={po_number}, stripped={po_num_stripped}")
                                
                                # Get order status first to determine duplicate handling
                                order_status_row = offline_db.execute(text("""
                                    SELECT status FROM process_orders 
                                    WHERE LTRIM(order_id, '0') = LTRIM(:po, '0')
                                    LIMIT 1
                                """), {"po": str(po_number)}).fetchone()
                                
                                order_status = (order_status_row[0] or "").upper() if order_status_row else ""
                                
                                # First check: Is this PO already processed in this batch?
                                if po_num_stripped in processed_po_numbers:
                                    log.warning(f"⏭️ [ShiftAuto] DUPLICATE IN BATCH: Order {po_number} (stripped: '{po_num_stripped}') already processed - skipping")
                                    continue
                                
                                # Second check: Database duplicate check using database-level LTRIM with row-level locking
                                # ✅ CRITICAL FIX (Dec 16, 2025): Use row-level locking to prevent race conditions
                                # This ensures only one process can update the record at a time
                                from sqlalchemy import func
                                log.info(f"🔍 [ShiftAuto] Looking for existing offline record for PO: {po_number} (stripped: '{po_num_stripped}')")
                                
                                # ✅ Use with_for_update() for row-level locking (SELECT FOR UPDATE)
                                # This prevents concurrent updates to the same record
                                existing = offline_db.query(OfflineConfirmation).filter(
                                    func.ltrim(OfflineConfirmation.order_id, '0') == po_num_stripped,
                                        OfflineConfirmation.status == 'pending'
                                ).with_for_update().first()
                                
                                if existing:
                                    log.info(f"🔄 [ShiftAuto] ✅ MATCH FOUND! {order_status} order {po_number} (stripped: '{po_num_stripped}') matches existing ID {existing.id} - will UPDATE with ROW LOCK")
                                    log.info(f"🔄 [ShiftAuto] FOUND existing offline record: ID={existing.id}, order_id={existing.order_id}, current_weight={existing.confirmed_weight:.2f}")
                                else:
                                    log.info(f"🆕 [ShiftAuto] NO existing record found for PO {po_number} (stripped: '{po_num_stripped}') - will CREATE new")
                                
                                if existing:
                                    # ✅ UPDATE existing record - accumulate values (for both VALIDATED and partial orders)
                                    try:
                                        import json
                                        new_weight = float(item.get('confirmed_weight', 0))
                                        old_weight = existing.confirmed_weight or 0
                                        accumulated_weight = old_weight + new_weight
                                        
                                        log.info(f"📝 [ShiftAuto] BEFORE UPDATE: ID={existing.id}, order_id={existing.order_id}, weight={old_weight:.2f}")
                                        
                                        existing.confirmed_weight = accumulated_weight
                                        new_scrap = float(item.get('scrap', 0))
                                        old_scrap = existing.scrap or 0
                                        existing.scrap = old_scrap + new_scrap
                                        sap_payload_serialized = json.loads(json.dumps(item, default=str))
                                        sap_payload_serialized['confirmed_weight'] = accumulated_weight
                                        sap_payload_serialized['scrap'] = existing.scrap
                                        existing.sap_payload = sap_payload_serialized
                                        
                                        # ✅ Keep existing confirmed_text - don't overwrite user's manual notes
                                        # existing.confirmed_text is preserved as-is
                                        
                                        # ✅ CRITICAL (Dec 16, 2025): Explicitly add to session and flush
                                        # This ensures the update is written immediately to the database
                                        offline_db.add(existing)
                                        offline_db.flush()
                                        
                                        # ✅ VERIFICATION: Re-query to confirm the update was persisted
                                        offline_db.expire(existing)  # Clear session cache
                                        offline_db.refresh(existing)  # Reload from database
                                        verified_weight = existing.confirmed_weight or 0
                                        
                                        if abs(verified_weight - accumulated_weight) < 0.01:
                                            log.info(f"✅ [ShiftAuto] VERIFIED UPDATE: Database shows weight={verified_weight:.2f} (expected {accumulated_weight:.2f}) ✓")
                                        else:
                                            log.error(f"❌ [ShiftAuto] UPDATE VERIFICATION FAILED! Database shows weight={verified_weight:.2f} but expected {accumulated_weight:.2f}")
                                            # Try to recover by re-updating
                                            existing.confirmed_weight = accumulated_weight
                                            offline_db.flush()
                                            log.info(f"🔄 [ShiftAuto] Attempted recovery flush")
                                        
                                        log.info(f"✅ [ShiftAuto] AFTER UPDATE: ID={existing.id}, order_id={existing.order_id}, weight={accumulated_weight:.2f} (was {old_weight:.2f}, added {new_weight:.2f}), scrap={existing.scrap:.2f} (was {old_scrap:.2f}, added {new_scrap:.2f})")
                                        log.info(f"✅ [ShiftAuto] UPDATED and FLUSHED offline {order_status} order {po_number}: {old_weight:.2f} + {new_weight:.2f} = {accumulated_weight:.2f}")
                                        
                                        processed_po_numbers.add(po_num_stripped)
                                        stored_count += 1
                                        stored_orders.append(po_number)
                                        continue  # Skip creating new record
                                    except Exception as update_err:
                                        log.error(f"❌ [ShiftAuto] EXCEPTION during offline update for PO {po_number}: {update_err}")
                                        import traceback
                                        log.error(traceback.format_exc())
                                        # Fall through to create new record as fallback
                                        log.warning(f"⚠️ [ShiftAuto] Update failed - will try to create new record instead")
                                
                                # ✅ No existing record found - create new offline record
                                log.info(f"✅ [ShiftAuto] Processing NEW order {po_number} for offline storage (status: {order_status})")
                                
                                # Mark this PO as processed in this batch
                                processed_po_numbers.add(po_num_stripped)
                                
                                log.info(f"✅ [ShiftAuto] NEW ORDER: PO {po_number} (stripped: {po_num_stripped}) - storing...")
                                
                                # ✅ Serialize sap_payload to handle datetime objects (JSON serialization)
                                import json
                                sap_payload_serialized = json.loads(json.dumps(item, default=str))
                                
                                offline_record = OfflineConfirmation(
                                    order_id=po_number,
                                    process_order_id=item.get('process_order_id'),
                                    material=item.get('material'),
                                    version=item.get('version', ''),
                                    confirmed_weight=float(item.get('confirmed_weight', 0)),
                                    total_qty=float(item.get('total_qty', 0)),
                                    uom=item.get('uom', 'KG'),
                                    plant=item.get('plant'),
                                    batch=item.get('batch', ''),
                                    shift=item.get('shift'),
                                    scrap=float(item.get('scrap', 0)),
                                    confirmed_text="",  # Leave empty for user to fill manually
                                    sap_payload=sap_payload_serialized,
                                    validation_method='ShiftAuto',
                                    status='pending'
                                )
                                offline_db.add(offline_record)
                                offline_db.flush()  # Flush so subsequent duplicate checks can see this record
                                stored_count += 1
                                stored_orders.append(po_number)
                                log.info(f"✅ [ShiftAuto] Stored offline: PO {po_number} - Shift {item.get('shift')}: {item.get('confirmed_weight', 0):.2f} {item.get('uom', 'KG')} (flushed to session)")
                            except Exception as item_err:
                                log.error(f"❌ Failed to store offline order {item.get('po_number')}: {item_err}")
                        
                        offline_db.commit()
                        log.info(f"✅ Stored {stored_count} orders (validated + partial confirmations) in offline_confirmations table")
                        
                        # ✅ Update process_orders - treat offline as confirmed
                        # Update confirmation values so the system knows this has been confirmed
                        # ✅ STEP 1: Update validated orders that were stored offline
                        if stored_count > 0:
                            try:
                                for item in validated_orders:
                                    # Only update if this order was actually stored
                                    if item.get('po_number') not in stored_orders:
                                        continue
                                    po_num = item.get('po_number')
                                    shift = (item.get('shift') or '').upper()
                                    confirmed_weight = float(item.get('confirmed_weight', 0))
                                    is_final = item.get('is_final', False)
                                    
                                    if po_num and shift in ('A', 'B', 'C'):
                                        shift_col = f"confirmed_shift_{shift.lower()}"
                                        
                                        if shift == 'A':
                                            last_calc = f"(COALESCE(confirmed_shift_a, 0) + :w) + COALESCE(confirmed_shift_b, 0) + COALESCE(confirmed_shift_c, 0)"
                                        elif shift == 'B':
                                            last_calc = f"COALESCE(confirmed_shift_a, 0) + (COALESCE(confirmed_shift_b, 0) + :w) + COALESCE(confirmed_shift_c, 0)"
                                        else:
                                            last_calc = f"COALESCE(confirmed_shift_a, 0) + COALESCE(confirmed_shift_b, 0) + (COALESCE(confirmed_shift_c, 0) + :w)"
                                        
                                        offline_db.execute(text(f"""
                                            UPDATE process_orders
                                            SET {shift_col} = COALESCE({shift_col}, 0) + :w,
                                                last_confirmed_qty = {last_calc},
                                                is_final_sent = CASE WHEN :is_final THEN TRUE ELSE is_final_sent END,
                                                status = CASE WHEN :is_final THEN 'Validated' ELSE status END,
                                                updated_at = NOW()
                                            WHERE order_id = :po
                                        """), {"w": confirmed_weight, "is_final": is_final, "po": po_num})
                                offline_db.commit()
                                log.info(f"✅ Updated confirmation values for {len(stored_orders)} validated orders (offline)")
                            except Exception as update_err:
                                log.error(f"Failed to update process_orders confirmation values: {update_err}")
                        
                        # ✅ STEP 2: Update non-validated orders (partial confirmations)
                        # Treat as confirmed locally even though not sent to SAP
                        if len(non_validated_orders) > 0:
                            try:
                                for item in non_validated_orders:
                                    po_num = item.get('po_number')
                                    shift = (item.get('shift') or '').upper()
                                    confirmed_weight = float(item.get('confirmed_weight', 0))
                                    
                                    if po_num and shift in ('A', 'B', 'C'):
                                        shift_col = f"confirmed_shift_{shift.lower()}"
                                        shift_flag = f"shift_{shift.lower()}_confirmed"
                                        
                                        # Calculate last_confirmed_qty
                                        if shift == 'A':
                                            last_calc = f"(COALESCE(confirmed_shift_a, 0) + :w) + COALESCE(confirmed_shift_b, 0) + COALESCE(confirmed_shift_c, 0)"
                                        elif shift == 'B':
                                            last_calc = f"COALESCE(confirmed_shift_a, 0) + (COALESCE(confirmed_shift_b, 0) + :w) + COALESCE(confirmed_shift_c, 0)"
                                        else:
                                            last_calc = f"COALESCE(confirmed_shift_a, 0) + COALESCE(confirmed_shift_b, 0) + (COALESCE(confirmed_shift_c, 0) + :w)"
                                        
                                        offline_db.execute(text(f"""
                                            UPDATE process_orders
                                            SET {shift_col} = COALESCE({shift_col}, 0) + :w,
                                                last_confirmed_qty = {last_calc},
                                                {shift_flag} = TRUE,
                                                updated_at = NOW()
                                            WHERE order_id = :po
                                        """), {"w": confirmed_weight, "po": po_num})
                                        log.info(f"✅ Marked partial confirmation as locally confirmed: PO {po_num} - Shift {shift}: {confirmed_weight:.2f}")
                                
                                offline_db.commit()
                                log.info(f"✅ Updated confirmation values for {len(non_validated_orders)} partial confirmations (locally confirmed)")
                            except Exception as update_err:
                                log.error(f"Failed to update process_orders confirmation values for partial confirmations: {update_err}")
                except Exception as offline_err:
                    log.error(f"❌ Failed to store offline confirmations: {offline_err}")
                    import traceback
                    log.debug(traceback.format_exc())
                
                # Log the event
                log_hercules_event(
                    action="Auto Shift-End Confirmation",
                    status="Success (Offline)",
                    details=f"VPN disconnected - {stored_count} validated orders stored offline, {len(non_validated_orders)} partial confirmations marked as locally confirmed",
                    metadata={
                        "validated_stored_count": stored_count,
                        "validated_orders": stored_orders,
                        "partial_confirmations_count": len(non_validated_orders),
                        "partial_confirmations": [item.get('po_number') for item in non_validated_orders],
                        "vpn_status": vpn_status,
                        "timestamp": datetime.now().isoformat()
                    }
                )
                log.info(f"✅ Auto shift confirmation completed (VPN disconnected): {stored_count} validated orders stored offline, {len(non_validated_orders)} partial confirmations locally confirmed")
                return

            # ----------------------------------------------------
            # SEND TO SAP ONLINE (VPN is connected)
            # ✅ Send validated orders immediately if VPN is up (5 min before shift end)
            # ✅ Also send non-validated orders if VPN is up (for ended shifts)
            # ----------------------------------------------------
            sap_service = SAPConfirmationService()
            
            # ✅ Combine validated and non-validated orders for sending
            orders_to_send = validated_orders + non_validated_orders
            
            if validated_orders:
                log.info(f"✅ VPN is connected - sending {len(validated_orders)} VALIDATED orders to SAP/Demo")
                for v_order in validated_orders:
                    log.info(f"   📤 Validated: PO={v_order.get('po_number')}, Shift={v_order.get('shift')}, Weight={v_order.get('confirmed_weight', 0):.2f}")
            
            if non_validated_orders:
                log.info(f"✅ VPN is connected - also sending {len(non_validated_orders)} partial orders to SAP/Demo")
                for p_order in non_validated_orders:
                    log.info(f"   📤 Partial: PO={p_order.get('po_number')}, Shift={p_order.get('shift')}, Weight={p_order.get('confirmed_weight', 0):.2f}")
            
            log.info(f"📡 Calling confirm_orders_batch with {len(orders_to_send)} orders (type='auto')...")
            
            # ✅ REMOVED DUPLICATE LOGGING (Feb 4, 2026)
            # confirm_orders_batch already logs to JSON with source "ONLINE"
            # No need to log here as "AUTO (Shift-End)" - it creates duplicates
            
            sap_result = confirm_orders_batch(orders_to_send, "auto")

            log.info(f"📡 SAP response: {sap_result}")

            # ----------------------------------------------------
            # INTERPRET SAP RESULTS
            # ----------------------------------------------------
            po_map = {}
            for item in orders_to_send:
                key = str(item["po_number"]).lstrip("0")
                po_map.setdefault(key, []).append(item)

            successful = set()
            failed = []

            if sap_result.get("ok", False):
                success_list = {str(po).lstrip("0") for po in sap_result.get("successful_orders", [])}
                log.info(f"✅ SAP returned OK=True, successful_orders: {success_list}")
                
                failed_items_for_offline = []  # Track items that failed for offline storage

                for norm, items in po_map.items():
                    if norm in success_list:
                        for it in items:
                            successful.add((it["po_number"], it["shift"]))
                            log.info(f"✅ SUCCESS: PO {it['po_number']} Shift {it['shift']} sent successfully")
                    else:
                        # Entire PO failed - collect for offline storage
                        for it in items:
                            failed.append((it["po_number"], it["shift"]))
                            failed_items_for_offline.append(it)
                            log.warning(f"❌ FAILED: PO {it['po_number']} Shift {it['shift']} - not in success list")
                
                # ✅ CRITICAL FIX (Jan 30, 2026): Store partially failed orders OFFLINE
                # When SAP returns OK but some orders are not in success list
                if failed_items_for_offline:
                    partial_error = f"SAP partial success - {len(failed_items_for_offline)} orders rejected"
                    log.info(f"📦 Storing {len(failed_items_for_offline)} partially failed orders OFFLINE")
                    
                    try:
                        from sqlalchemy import func as sql_func
                        with PostgresSessionLocal() as partial_db:
                            partial_stored_count = 0
                            for item in failed_items_for_offline:
                                try:
                                    po_number = item.get('po_number')
                                    
                                    # ✅ REMOVED JSON LOGGING FOR PARTIAL FAILURES (Feb 4, 2026)
                                    # These orders are stored in offline table and will be logged
                                    # when actually sent to SAP later (avoids PENDING entries)
                                    
                                    if not po_number:
                                        continue
                                    
                                    po_num_stripped = str(po_number).lstrip('0') or str(po_number)
                                    
                                    # Check for existing offline record
                                    existing = partial_db.query(OfflineConfirmation).filter(
                                        sql_func.ltrim(OfflineConfirmation.order_id, '0') == po_num_stripped,
                                        OfflineConfirmation.status == 'pending'
                                    ).first()
                                    
                                    if existing:
                                        old_weight = existing.confirmed_weight or 0
                                        new_weight = float(item.get('confirmed_weight', 0))
                                        existing.confirmed_weight = old_weight + new_weight
                                        existing.scrap = (existing.scrap or 0) + float(item.get('scrap', 0))
                                        existing.error_message = partial_error
                                        partial_db.add(existing)
                                    else:
                                        import json
                                        sap_payload_serialized = json.loads(json.dumps(item, default=str))
                                        
                                        offline_record = OfflineConfirmation(
                                            order_id=po_number,
                                            process_order_id=item.get('process_order_id'),
                                            material=item.get('material'),
                                            version=item.get('version', ''),
                                            confirmed_weight=float(item.get('confirmed_weight', 0)),
                                            total_qty=float(item.get('total_qty', 0)),
                                            uom=item.get('uom', 'KG'),
                                            plant=item.get('plant', ''),
                                            batch=item.get('batch', ''),
                                            shift=item.get('shift', ''),
                                            scrap=float(item.get('scrap', 0)),
                                            confirmed_text=f"Partial failure: {partial_error}",
                                            sap_payload=sap_payload_serialized,
                                            validation_method='ShiftAuto_Partial_Fallback',
                                            status='pending',
                                            error_message=partial_error
                                        )
                                        partial_db.add(offline_record)
                                    
                                    partial_stored_count += 1
                                except Exception as item_err:
                                    log.error(f"❌ Failed to store partial failure for PO {item.get('po_number')}: {item_err}")
                            
                            partial_db.commit()
                            log.info(f"✅ Partial failure fallback: Stored {partial_stored_count} orders offline")
                    except Exception as partial_err:
                        log.error(f"❌ Failed to store partial failure fallback: {partial_err}")
                        
            else:
                # complete SAP failure
                sap_error_message = sap_result.get('error', 'Unknown SAP error')
                log.error(f"❌ SAP returned OK=False - ALL orders failed. Error: {sap_error_message}")
                for it in orders_to_send:
                    failed.append((it["po_number"], it["shift"]))
                    log.error(f"❌ FAILED: PO {it['po_number']} Shift {it['shift']}")
                
                # ✅ CRITICAL FIX (Jan 30, 2026): Store failed orders OFFLINE when real SAP fails
                # This ensures orders are not lost when SAP is unreachable or rejects the request
                log.info(f"📦 SAP call failed - storing {len(orders_to_send)} orders OFFLINE as fallback")
                
                try:
                    from sqlalchemy import func as sql_func
                    with PostgresSessionLocal() as fallback_db:
                        fallback_stored_count = 0
                        for item in orders_to_send:
                            try:
                                po_number = item.get('po_number')
                                
                                # ✅ REMOVED JSON LOGGING FOR SAP FAILURES (Feb 4, 2026)
                                # These orders are stored in offline table and will be logged
                                # when actually sent to SAP later (avoids PENDING entries)
                                
                                if not po_number:
                                    continue
                                
                                po_num_stripped = str(po_number).lstrip('0') or str(po_number)
                                
                                # Check for existing offline record
                                existing = fallback_db.query(OfflineConfirmation).filter(
                                    sql_func.ltrim(OfflineConfirmation.order_id, '0') == po_num_stripped,
                                    OfflineConfirmation.status == 'pending'
                                ).first()
                                
                                if existing:
                                    # Update existing record
                                    old_weight = existing.confirmed_weight or 0
                                    new_weight = float(item.get('confirmed_weight', 0))
                                    existing.confirmed_weight = old_weight + new_weight
                                    existing.scrap = (existing.scrap or 0) + float(item.get('scrap', 0))
                                    existing.error_message = f"SAP Failed: {sap_error_message}"
                                    fallback_db.add(existing)
                                    log.info(f"✅ Updated offline record for PO {po_number}: {old_weight:.2f} + {new_weight:.2f} = {existing.confirmed_weight:.2f}")
                                else:
                                    # Create new offline record
                                    import json
                                    sap_payload_serialized = json.loads(json.dumps(item, default=str))
                                    
                                    offline_record = OfflineConfirmation(
                                        order_id=po_number,
                                        process_order_id=item.get('process_order_id'),
                                        material=item.get('material'),
                                        version=item.get('version', ''),
                                        confirmed_weight=float(item.get('confirmed_weight', 0)),
                                        total_qty=float(item.get('total_qty', 0)),
                                        uom=item.get('uom', 'KG'),
                                        plant=item.get('plant', ''),
                                        batch=item.get('batch', ''),
                                        shift=item.get('shift', ''),
                                        scrap=float(item.get('scrap', 0)),
                                        confirmed_text=f"SAP Failed: {sap_error_message}",
                                        sap_payload=sap_payload_serialized,
                                        validation_method='ShiftAuto_SAP_Fallback',
                                        status='pending',
                                        error_message=sap_error_message
                                    )
                                    fallback_db.add(offline_record)
                                    log.info(f"✅ Created offline record for PO {po_number}: {item.get('confirmed_weight', 0):.2f} {item.get('uom', 'KG')}")
                                
                                fallback_stored_count += 1
                            except Exception as item_err:
                                log.error(f"❌ Failed to store offline fallback for PO {item.get('po_number')}: {item_err}")
                        
                        fallback_db.commit()
                        log.info(f"✅ SAP failure fallback: Stored {fallback_stored_count} orders offline")
                        
                        # Log to Hercules event
                        log_hercules_event(
                            action="Auto Shift-End SAP Failure Fallback",
                            status="StoredOffline",
                            details=f"SAP call failed - stored {fallback_stored_count} orders offline. Error: {sap_error_message}",
                            metadata={
                                "fallback_stored_count": fallback_stored_count,
                                "sap_error": sap_error_message,
                                "orders": [item.get('po_number') for item in orders_to_send],
                                "timestamp": datetime.now().isoformat()
                            }
                        )
                except Exception as fallback_err:
                    log.error(f"❌ CRITICAL: Failed to store offline fallback: {fallback_err}")
                    import traceback
                    log.error(traceback.format_exc())

            # ----------------------------------------------------
            # UPDATE DATABASE FOR SUCCESSFUL SHIFTS
            # ----------------------------------------------------
            if successful:
                # Use begin() to ensure explicit transaction handling
                with postgres_engine.begin() as tx:
                    for po, shift in list(successful):

                        items = po_map.get(str(po).lstrip("0"), [])
                        item = next((x for x in items if x["shift"] == shift), None)

                        if not item:
                            continue

                        confirmed_col = item["confirmed_shift_column"]
                        flag_col = item["shift_flag_column"]

                        weight_val = float(item["confirmed_weight"])
                        # ✅ For validated orders, add to existing confirmed value (not replace)
                        # Get current confirmed value first
                        current_confirmed_result = tx.execute(text(f"""
                            SELECT {confirmed_col} FROM process_orders WHERE order_id = :po
                        """), {"po": po}).fetchone()
                        
                        current_confirmed = float(current_confirmed_result[0] or 0) if current_confirmed_result else 0
                        # Add the new confirmation to existing
                        new_confirmed = current_confirmed + weight_val
                        
                        new_last = item["last_confirmed_qty"] + weight_val

                        # ✔ Final if >= total quantity or order is validated
                        is_validated = (item.get("order_status") or "").upper() in ("VALIDATED", "CONFIRMED", "COMPLETED")
                        is_final = new_last >= float(item["total_qty"]) or is_validated

                        # ✅ Feb 5, 2026: Set 'Validated' only after successful SAP confirmation
                        # Don't change status if already Validated
                        current_status_result = tx.execute(text(f"""
                            SELECT status FROM process_orders WHERE order_id = :po
                        """), {"po": po}).fetchone()
                        current_status = current_status_result[0] if current_status_result else "InProgress"
                        
                        # Set to 'Validated' on final SAP confirmation (successful push to SAP)
                        # Keep existing status otherwise
                        if is_final and current_status != "Validated":
                            new_status = "Validated"
                        else:
                            new_status = current_status

                        tx.execute(text(f"""
                            UPDATE process_orders
                            SET {confirmed_col} = :val,
                                {flag_col} = TRUE,
                                last_confirmed_qty = :new_last,
                                is_final_sent = :final,
                                status = :status,
                                updated_at = NOW()
                            WHERE order_id = :po
                        """), {
                            "val": new_confirmed,  # ✅ Use accumulated confirmed value
                            "new_last": new_last,
                            "final": is_final,
                            "status": new_status,
                            "po": po
                        })

            # ----------------------------------------------------
            # LOGGING
            # ----------------------------------------------------
            # ✅ Log detailed notification for successful confirmations
            if successful:
                if sap_service_check.mock_mode:
                    log.info(f"🎉 Successfully sent {len(successful)} confirmations to DEMO SERVER:")
                else:
                    log.info(f"🎉 Successfully sent {len(successful)} confirmations to REAL SAP:")
            
            successful_details = []
            for po, shift in list(successful):
                items = po_map.get(str(po).lstrip("0"), [])
                item = next((x for x in items if x["shift"] == shift), None)
                if item:
                    is_final = item.get("is_final_confirmation", False)
                    final_flag = " (FINAL)" if is_final else ""
                    successful_details.append(f"PO {po} - Shift {shift}{final_flag}: {item['confirmed_weight']:.2f} {item['uom']}")
                    log.info(f"   ✅ PO {po} - Shift {shift}{final_flag}: {item['confirmed_weight']:.2f} {item['uom']}")
            
            # Log failed orders
            if failed:
                log.error(f"❌ Failed to send {len(failed)} confirmations:")
                for po, shift in failed:
                    items = po_map.get(str(po).lstrip("0"), [])
                    item = next((x for x in items if x["shift"] == shift), None)
                    if item:
                        log.error(f"   ❌ PO {po} - Shift {shift}: {item['confirmed_weight']:.2f} {item['uom']}")
            
            log_hercules_event(
                action="Auto Shift-End Confirmation",
                status="Success" if not failed else "PartialSuccess",
                details=f"Shift confirmations: OK={len(successful)}, Failed={len(failed)}",
                metadata={
                    "successful": len(successful),
                    "failed": len(failed),
                    "successful_details": successful_details,  # ✅ Add detailed info for notifications
                    "timestamp": datetime.now().isoformat()
                }
            )

            log.info("✔ Auto shift confirmation complete.")

    except Exception as e:
        log.exception("❌❌❌ Auto shift confirmation failed with exception")
        log.error(f"❌ Error type: {type(e).__name__}")
        log.error(f"❌ Error message: {str(e)}")
        import traceback
        log.error(f"❌ Full traceback:\n{traceback.format_exc()}")
        log_hercules_event(
            action="Auto Shift-End Confirmation",
            status="Error",
            details=f"Execution failure: {str(e)}",
            metadata={"error": str(e), "error_type": type(e).__name__}
        )
