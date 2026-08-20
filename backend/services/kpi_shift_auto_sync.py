"""
Auto KPI Sync Service - Automatically sends KPIs to SAP at shift end
- Milling: 3 shifts (A, B, C)
- Packing: 2 shifts (A, B)
- Raw data: Manual sync only (not included in shift-end sync)
"""
import logging
from datetime import datetime, timedelta
from sqlalchemy import text
from database import PostgresSessionLocal, postgres_engine
from models.shift_master import ShiftMaster
from utils.shifts import get_current_shift
import requests
from requests.auth import HTTPBasicAuth
import urllib3
import os

# ✅ Import sum_dm_readings for correct DM water calculation
try:
    from services.scale_service import sum_dm_readings
except ImportError:
    def sum_dm_readings(dm_tag: str, start_time, end_time=None) -> float:
        """Fallback if import fails"""
        return 0.0

urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

log = logging.getLogger("kpi_shift_auto_sync")

# SAP Configuration
# ✅ Read mock mode from database settings (not environment variable)
# A8: these were module-level os.getenv() calls with the production host and
# credentials as their literal defaults, evaluated once at import - so nothing
# short of a restart could change them. They now resolve per read through
# services/runtime_config (database -> .env -> documented default).
from services import runtime_config as _rc


def _sap_mock_base_url():
    return _rc.sap_mock_url()


def _sap_production_base_url():
    return _rc.sap_production_url()


def _sap_username():
    return _rc.sap_username()


def _sap_password():
    return _rc.sap_password()

def get_mock_sap_mode() -> bool:
    """Get mock SAP mode from database settings."""
    try:
        from models.system_settings import is_mock_sap_enabled
        return is_mock_sap_enabled()
    except Exception as e:
        log.warning(f"Could not read mock SAP mode from database: {e}, defaulting to True")
        return True  # Default to mock mode for safety

# Track last sent shift per department to avoid duplicates
_last_sent_shift = {
    "MILLING": {"shift_code": None, "end_time": None},
    "PACKING": {"shift_code": None, "end_time": None}
}


def _parse_time(time_val):
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


def get_sap_url(endpoint: str, client: str = "200") -> str:
    """Get the full SAP URL for an endpoint."""
    if get_mock_sap_mode():
        return f"{_sap_mock_base_url()}{endpoint}"
    else:
        return f"{_sap_production_base_url()}{endpoint}?sap-client={client}"


def send_milling_kpis_to_sap_internal(shift_code: str = None):
    """
    Internal function to send incremental milling KPIs to SAP.
    Only sends new data since last send.
    """
    from services.kpi_incremental import get_incremental_kpis, save_sent_baseline, get_current_scada_values
    from routes.kpi_routes import safe
    
    try:
        # Get incremental KPIs (only new data since last send)
        kpi_result, current_scada, baseline = get_incremental_kpis("MILLING", shift_code)
        
        if not kpi_result:
            log.info("No new milling KPIs to send (no delta since last send)")
            return False, "No new data to send"
        
        # Extract milling KPIs from delta
        milling_kpis = kpi_result.get("milling_kpis", {})
        
        # Get SCADA water data (delta)
        scada_water_data = {
            "totalPreCleaningWater": 0.0,
            "waterCleanWheat": 0.0,
            "totalWaterUsed": 0.0
        }
        
        if current_scada and baseline:
            # ✅ FIX: DM water meters are 30-sec averages, need SUM not delta
            # Get baseline time from tracking record
            baseline_time = baseline.get("last_sent_at")
            if baseline_time and isinstance(baseline_time, str):
                try:
                    from dateutil import parser as dtparser
                    baseline_time = dtparser.parse(baseline_time)
                except:
                    baseline_time = datetime.now() - timedelta(hours=8)
            elif not baseline_time:
                baseline_time = datetime.now() - timedelta(hours=8)
            
            # Sum DM readings from baseline time to now
            dm101_sum = sum_dm_readings("DM101", baseline_time)
            dm102_sum = sum_dm_readings("DM102", baseline_time)
            dm201_sum = sum_dm_readings("DM201", baseline_time)
            dm202_sum = sum_dm_readings("DM202", baseline_time)
            dm203_sum = sum_dm_readings("DM203", baseline_time)
            
            scada_water_data = {
                "totalPreCleaningWater": dm101_sum + dm102_sum,
                "waterCleanWheat": dm201_sum + dm202_sum + dm203_sum,
                "totalWaterUsed": dm101_sum + dm102_sum + dm201_sum + dm202_sum + dm203_sum
            }
            
            log.info(f"💧 Water SUM from {baseline_time}: DM101={dm101_sum:.2f}, DM102={dm102_sum:.2f}, DM201={dm201_sum:.2f}, DM202={dm202_sum:.2f}, DM203={dm203_sum:.2f}")
        elif current_scada:
            # First send, use current values
            scada_water_data = {
                "totalPreCleaningWater": safe(current_scada.get("DM101", 0.0)) + safe(current_scada.get("DM102", 0.0)),
                "waterCleanWheat": safe(current_scada.get("DM201", 0.0)) + safe(current_scada.get("DM202", 0.0)) + safe(current_scada.get("DM203", 0.0)),
                "totalWaterUsed": (safe(current_scada.get("DM101", 0.0)) + safe(current_scada.get("DM102", 0.0)) + 
                                 safe(current_scada.get("DM201", 0.0)) + safe(current_scada.get("DM202", 0.0)) + safe(current_scada.get("DM203", 0.0)))
            }

        # Prepare SAP payload (include SHIFT so auto path matches manual sync)
        sap_milling_payload = {
            "MILL_THROUGHPUT": str(milling_kpis.get("Mill Throughput (%)", 0.0)),
            "MILL_TIME_EFFICIENCY": str(milling_kpis.get("Mill Time Efficiency (%)", 0.0)),
            "TOTAL_UTILIZATION": str(milling_kpis.get("Total Utilization (%)", 0.0)),
            "MAX_UTILIZATION": str(milling_kpis.get("Max Utilization of Milling Capacity (%)", 0.0)),
            "MILLING_GAIN": str(milling_kpis.get("Milling Gain", 0.0)),
            "PRE_CLEAN_SCREENING": str(milling_kpis.get("Pre Cleaning Screening (%)", 0.0)),
            "MILLING_SCREENING": str(milling_kpis.get("Milling Screening (%)", 0.0)),
            "PRE_CLEAN_WATER": str(scada_water_data.get("totalPreCleaningWater", 0.0)),
            "CLEANING_WATER": str(scada_water_data.get("waterCleanWheat", 0.0)),
            "NET_HOURS": str(milling_kpis.get("Net Hours (hrs)", 0.0)),
            "MILLING_DOWN_TIME": str(milling_kpis.get("Downtime (hrs)", 0.0)),
            "BREAK_CAPACITY": str(milling_kpis.get("1st Break Capacity per Hour (t/h)", 0.0)),
            "FLOUR_EXTRACTION": str(milling_kpis.get("Flour Extraction (%)", 0.0)),
            "BRAN_EXTRACTION": str(milling_kpis.get("Bran Extraction (%)", 0.0)),
            "MILLING_LOSS": str(milling_kpis.get("Milling Loss (%)", 0.0)),
            "TOTAL_WATER": str(scada_water_data.get("totalWaterUsed", 0.0)),
            "SHIFT": shift_code or ""
        }

        SAP_URL = get_sap_url("/zmi_kpi_mill/MKPI", client="200")
        
        # MOCK MODE
        if get_mock_sap_mode():
            post_response = requests.post(SAP_URL, json=sap_milling_payload, timeout=30)
            if post_response.status_code in [200, 201]:
                # ✅ Save baseline in MOCK MODE too (for auditing)
                if current_scada:
                    save_sent_baseline("MILLING", current_scada, "auto_shift_end", shift_code, 
                                     f"Auto shift-end sync for shift {shift_code} (mock mode)",
                                     kpi_payload=sap_milling_payload)
                return True, "Milling KPIs sent successfully (mock mode)"
            return False, f"Failed to send milling KPIs: {post_response.status_code}"
        
        # PRODUCTION MODE - CSRF token flow
        get_headers = {
            "x-csrf-token": "fetch",
            "Accept": "application/json",
            "User-Agent": "Python-Requests/2.31.0",
            "Connection": "keep-alive"
        }
        
        token_response = requests.get(
            SAP_URL,
            headers=get_headers,
            auth=HTTPBasicAuth(_sap_username(), _sap_password()),
            timeout=30,
            verify=False
        )
        
        if token_response.status_code not in [200, 201]:
            return False, f"Failed to fetch CSRF token: {token_response.status_code}"
        
        csrf_token = (
            token_response.headers.get("x-csrf-token") or 
            token_response.headers.get("X-CSRF-Token") or
            token_response.headers.get("X-Csrf-Token")
        )
        
        if not csrf_token:
            return False, "CSRF token not found in response"
        
        cookies = token_response.cookies
        
        post_headers = {
            "x-csrf-token": csrf_token,
            "Content-Type": "application/json",
            "Accept": "application/json",
            "User-Agent": "Python-Requests/2.31.0",
            "Connection": "keep-alive"
        }
        
        post_response = requests.post(
            SAP_URL,
            json=sap_milling_payload,
            headers=post_headers,
            cookies=cookies,
            auth=HTTPBasicAuth(_sap_username(), _sap_password()),
            timeout=30,
            verify=False
        )
        
        if post_response.status_code in [200, 201]:
            # ✅ CRITICAL: Save baseline after successful send
            if current_scada:
                save_sent_baseline("MILLING", current_scada, "auto_shift_end", shift_code, 
                                 f"Auto shift-end sync for shift {shift_code}",
                                 kpi_payload=sap_milling_payload)  # Store payload for auditing
            return True, "Milling KPIs sent successfully (incremental)"
        return False, f"Failed to send milling KPIs: {post_response.status_code}"
        
    except Exception as e:
        log.exception(f"Error sending milling KPIs: {e}")
        return False, f"Error: {str(e)}"


def send_packing_kpis_to_sap_internal(shift_code: str = None):
    """
    Internal function to send incremental packing KPIs to SAP.
    Only sends new data since last send.
    """
    from services.kpi_incremental import get_incremental_kpis, save_sent_baseline
    
    try:
        # Get incremental KPIs (only new data since last send)
        kpi_result, current_scada, baseline = get_incremental_kpis("PACKING", shift_code)
        
        if not kpi_result:
            log.info("No new packing KPIs to send (no delta since last send)")
            return False, "No new data to send"
        
        # Extract packing KPIs from delta
        packing_kpis = kpi_result.get("packing_kpis", {})
        
        # Prepare SAP payload (include SHIFT so auto path matches manual sync)
        sap_packing_payload = {
            "PACKING_CAPACITY_BAG": str(packing_kpis.get("Packing Line Capacity (bags/hr)", 0.0)),
            "PACKING_CAPACITY_TON": str(packing_kpis.get("Packing Line Capacity (tons/hr)", 0.0)),
            "PACKING_BAG": str(packing_kpis.get("Daily Packing Output (bags)", 0.0)),
            "PACKING_HOURS": str(packing_kpis.get("Net Hours (hrs)", 0.0)),
            "PACKING_TOTAL_DOWNTIME": str(packing_kpis.get("Downtime (hrs)", 0.0)),
            "PACKING_MACHINE_UTILIZ": str(packing_kpis.get("Machine Utilization (%)", 0.0)),
            "SHIFT": shift_code or ""
        }

        SAP_URL = get_sap_url("/zmi_kpi_pack/PKPI", client="200")
        
        # MOCK MODE
        if get_mock_sap_mode():
            post_response = requests.post(SAP_URL, json=sap_packing_payload, timeout=30)
            if post_response.status_code in [200, 201]:
                # ✅ Save baseline in MOCK MODE too (for auditing)
                if current_scada:
                    save_sent_baseline("PACKING", current_scada, "auto_shift_end", shift_code,
                                     f"Auto shift-end sync for shift {shift_code} (mock mode)",
                                     kpi_payload=sap_packing_payload)
                return True, "Packing KPIs sent successfully (mock mode)"
            return False, f"Failed to send packing KPIs: {post_response.status_code}"
        
        # PRODUCTION MODE - CSRF token flow
        get_headers = {
            "x-csrf-token": "fetch",
            "Accept": "application/json",
            "User-Agent": "Python-Requests/2.31.0",
            "Connection": "keep-alive"
        }
        
        token_response = requests.get(
            SAP_URL,
            headers=get_headers,
            auth=HTTPBasicAuth(_sap_username(), _sap_password()),
            timeout=30,
            verify=False
        )
        
        if token_response.status_code not in [200, 201]:
            return False, f"Failed to fetch CSRF token: {token_response.status_code}"
        
        csrf_token = (
            token_response.headers.get("x-csrf-token") or 
            token_response.headers.get("X-CSRF-Token") or
            token_response.headers.get("X-Csrf-Token")
        )
        
        if not csrf_token:
            return False, "CSRF token not found in response"
        
        cookies = token_response.cookies
        
        post_headers = {
            "x-csrf-token": csrf_token,
            "Content-Type": "application/json",
            "Accept": "application/json",
            "User-Agent": "Python-Requests/2.31.0",
            "Connection": "keep-alive"
        }
        
        post_response = requests.post(
            SAP_URL,
            json=sap_packing_payload,
            headers=post_headers,
            cookies=cookies,
            auth=HTTPBasicAuth(_sap_username(), _sap_password()),
            timeout=30,
            verify=False
        )
        
        if post_response.status_code in [200, 201]:
            # ✅ CRITICAL: Save baseline after successful send
            if current_scada:
                save_sent_baseline("PACKING", current_scada, "auto_shift_end", shift_code,
                                 f"Auto shift-end sync for shift {shift_code}",
                                 kpi_payload=sap_packing_payload)  # Store payload for auditing
            return True, "Packing KPIs sent successfully (incremental)"
        return False, f"Failed to send packing KPIs: {post_response.status_code}"
        
    except Exception as e:
        log.exception(f"Error sending packing KPIs: {e}")
        return False, f"Error: {str(e)}"


def detect_shift_end(department: str, plant: str = None):
    """
    Detect if a shift has just ended for the given department.
    For MILLING: checks all plants (KPIs are plant-agnostic, so we send once per shift)
    For PACKING: checks all shifts (no plant filter)
    Returns (has_ended, shift_code, shift_end_time) or (False, None, None)
    """
    global _last_sent_shift
    
    try:
        with PostgresSessionLocal() as db:
            # Get all shifts for this department
            if department.upper() == "PACKING":
                # PACKING: no plant filter
                shifts = db.query(ShiftMaster).filter(
                    ShiftMaster.department == "PACKING"
                ).order_by(ShiftMaster.sort_order.asc()).all()
            else:
                # MILLING: Get shifts from all plants (KPIs are plant-agnostic)
                # We'll group by shift_code to avoid duplicates
                all_milling_shifts = db.query(ShiftMaster).filter(
                    ShiftMaster.department == "MILLING"
                ).order_by(ShiftMaster.sort_order.asc()).all()
                
                # Group by shift_code and take the first one (they should have same times)
                shifts_dict = {}
                for shift in all_milling_shifts:
                    if shift.shift_code not in shifts_dict:
                        shifts_dict[shift.shift_code] = shift
                shifts = list(shifts_dict.values())
                # Sort by sort_order
                shifts.sort(key=lambda x: x.sort_order)
            
            if not shifts:
                log.warning(f"No shifts found for department: {department}")
                return False, None, None
            
            now = datetime.now()
            current_time = now.time()
            
            # Check each shift to see if it just ended
            for shift in shifts:
                # ✅ CRITICAL FIX: Parse time values that might be strings
                shift_end_time = _parse_time(shift.end_time)
                shift_start_time = _parse_time(shift.start_time)
                
                if not shift_end_time or not shift_start_time:
                    log.warning(f"⚠️ Could not parse shift times for {shift.shift_code}: start={shift.start_time}, end={shift.end_time}")
                    continue
                
                # Calculate if shift has ended
                # For same-day shifts (start < end)
                if shift_start_time < shift_end_time:
                    # Shift ended if current time >= end time
                    if current_time >= shift_end_time:
                        # Check if we already sent for this shift
                        last_sent = _last_sent_shift.get(department.upper(), {})
                        if (last_sent.get("shift_code") == shift.shift_code and 
                            last_sent.get("end_time") == shift_end_time):
                            # Already sent for this shift
                            continue
                        
                        # Shift just ended - check if within last 5 minutes to avoid duplicates
                        # Calculate end datetime for today
                        shift_end_datetime = datetime.combine(now.date(), shift_end_time)
                        time_since_end = (now - shift_end_datetime).total_seconds()
                        
                        # Only trigger if shift ended within last 5 minutes (300 seconds)
                        if 0 <= time_since_end <= 300:
                            return True, shift.shift_code, shift_end_time
                
                # For overnight shifts (start > end, e.g., 23:00 - 07:00)
                else:
                    # Shift ended if current time >= end time (and we're past midnight)
                    if current_time >= shift_end_time:
                        # Calculate end datetime (it's today if we're past midnight)
                        shift_end_datetime = datetime.combine(now.date(), shift_end_time)
                        time_since_end = (now - shift_end_datetime).total_seconds()
                        
                        # Check if we already sent for this shift
                        last_sent = _last_sent_shift.get(department.upper(), {})
                        if (last_sent.get("shift_code") == shift.shift_code and 
                            last_sent.get("end_time") == shift_end_time):
                            continue
                        
                        # Only trigger if shift ended within last 5 minutes
                        if 0 <= time_since_end <= 300:
                            return True, shift.shift_code, shift_end_time
            
            return False, None, None
            
    except Exception as e:
        log.exception(f"Error detecting shift end for {department}: {e}")
        return False, None, None


def auto_send_kpis_on_shift_end():
    """
    Main function to automatically send KPIs to SAP at shift end.
    - Checks for MILLING shift end (3 shifts: A, B, C)
    - Checks for PACKING shift end (2 shifts: A, B)
    - Sends KPIs to SAP when a shift ends
    - Raw data is NOT sent (manual sync only)
    """
    global _last_sent_shift
    
    log.info("=" * 60)
    log.info("🔄 Auto KPI Shift-End Sync: Starting scan")
    log.info(f"⏱️ Timestamp: {datetime.now().isoformat()}")
    
    try:
        # Check MILLING shifts
        log.info("🔍 Checking MILLING shifts...")
        has_ended, shift_code, shift_end_time = detect_shift_end("MILLING")
        
        if has_ended:
            log.info(f"✅ MILLING shift {shift_code} ended at {shift_end_time} - Sending incremental KPIs to SAP...")
            success, message = send_milling_kpis_to_sap_internal(shift_code)
            
            if success:
                log.info(f"✅ MILLING KPIs sent successfully: {message}")
                # Update tracking
                _last_sent_shift["MILLING"] = {
                    "shift_code": shift_code,
                    "end_time": shift_end_time
                }
            else:
                log.error(f"❌ Failed to send MILLING KPIs: {message}")
        else:
            log.debug("No MILLING shift end detected")
        
        # Check PACKING shifts
        log.info("🔍 Checking PACKING shifts...")
        has_ended, shift_code, shift_end_time = detect_shift_end("PACKING")
        
        if has_ended:
            log.info(f"✅ PACKING shift {shift_code} ended at {shift_end_time} - Sending incremental KPIs to SAP...")
            success, message = send_packing_kpis_to_sap_internal(shift_code)
            
            if success:
                log.info(f"✅ PACKING KPIs sent successfully: {message}")
                # Update tracking
                _last_sent_shift["PACKING"] = {
                    "shift_code": shift_code,
                    "end_time": shift_end_time
                }
            else:
                log.error(f"❌ Failed to send PACKING KPIs: {message}")
        else:
            log.debug("No PACKING shift end detected")
        
        log.info("=" * 60)
        
    except Exception as e:
        log.exception(f"❌ Error in auto KPI shift-end sync: {e}")
        from services.system_logger import log_hercules_event
        log_hercules_event(
            action="Auto KPI Shift-End Sync",
            status="Error",
            details=f"Error: {str(e)}",
            metadata={"error": str(e)}
        )

