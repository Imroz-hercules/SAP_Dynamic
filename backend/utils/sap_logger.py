from models.sap_log import SapLog
from database import PostgresSessionLocal
from datetime import datetime
import json
import os
from threading import Lock

# ============================================================================
# JSON FILE LOGGING - Added for debugging SAP confirmations
# ============================================================================

print("=" * 60)
print("*** SAP_LOGGER.PY LOADED ***")
print("=" * 60)

# JSON file path for SAP confirmation logs
SAP_LOG_JSON_FILE = os.path.join(
    os.path.dirname(os.path.dirname(__file__)),  # backend folder
    "logs",
    "sap_confirmations.json"
)

# Thread-safe file writing lock
_file_lock = Lock()

# In-memory cache of log entries (for updating responses)
_pending_logs = {}


def _convert_to_sap_format(payload: dict) -> dict:
    """
    Convert internal payload format to SAP format (uppercase keys, string values).
    This ensures JSON logs show the exact SAP payload format.
    """
    if not payload or not isinstance(payload, dict):
        return payload
    
    # If already in SAP format (has uppercase keys like PROCESS_ORDER), return as-is
    if "PROCESS_ORDER" in payload:
        return payload
    
    # Format date as YYYYMMDD
    created_at = payload.get('created_at', '')
    if created_at:
        try:
            if hasattr(created_at, 'strftime'):
                created_on = created_at.strftime('%Y%m%d')
                confirmed_at = created_at.strftime('%H%M%S')
            else:
                # Parse string datetime
                from dateutil import parser
                dt = parser.parse(str(created_at))
                created_on = dt.strftime('%Y%m%d')
                confirmed_at = dt.strftime('%H%M%S')
        except:
            created_on = ""
            confirmed_at = ""
    else:
        created_on = ""
        confirmed_at = ""
    
    # Format PO number with leading zeros
    po_number = str(payload.get('po_number', '')).zfill(12)
    
    # Format material with leading zeros
    material = str(payload.get('material', '')).zfill(18)
    
    # Determine final confirmation
    is_final = payload.get('is_final_confirmation', False)
    final_conf = "X" if is_final else ""
    
    # Convert to SAP format
    sap_payload = {
        "PROCESS_ORDER": po_number,
        "MATERIAL": material,
        "VERSION": payload.get('version', ''),
        "MATERIAL_DESC": payload.get('material_desc', ''),
        "TOTAL_QTY": f"{float(payload.get('total_qty', 0)):.3f}",
        "CONFIRMED_WEIGHT": str(int(float(payload.get('confirmed_weight', 0)))),
        "UOM": payload.get('uom', payload.get('unit', 'KG')),
        "PLANT": payload.get('plant', ''),
        "CREATED_ON": created_on,
        "CONFIRMED_AT": confirmed_at,
        "BATCH": payload.get('batch', ''),
        "STATUS": "Confirmed",
        "FINAL_CONFIRMATION": final_conf,
        "SHIFT": payload.get('shift', ''),
        "SCALE1": payload.get('scale1', ''),
        "SCALE1_QTY": str(payload.get('scale1_qty', 0.0)),
        "SCALE2": payload.get('scale2', ''),
        "SCALE2_QTY": str(payload.get('scale2_qty', 0.0)),
        "SCALE3": payload.get('scale3', ''),
        "SCALE3_QTY": str(payload.get('scale3_qty', 0.0)),
        "CONFIRMED_TEXT": payload.get('confirmed_text', ''),
        "SCRAP": str(int(float(payload.get('scrap', 0))))
    }
    
    return sap_payload


def _ensure_log_directory():
    """Ensure the logs directory exists."""
    log_dir = os.path.dirname(SAP_LOG_JSON_FILE)
    if not os.path.exists(log_dir):
        os.makedirs(log_dir)


def _write_to_json_file(log_entry: dict):
    """
    Write a log entry to the JSON file.
    Thread-safe and keeps last 500 entries to prevent file from growing too large.
    """
    _ensure_log_directory()
    
    with _file_lock:
        logs = []
        if os.path.exists(SAP_LOG_JSON_FILE):
            try:
                with open(SAP_LOG_JSON_FILE, 'r', encoding='utf-8') as f:
                    content = f.read().strip()
                    if content:
                        logs = json.loads(content)
            except (json.JSONDecodeError, FileNotFoundError, IOError) as e:
                print(f"⚠️ [SAP_LOGGER] Could not read existing SAP log file: {e}")
                logs = []
        
        # Append new entry
        logs.append(log_entry)
        
        # Keep only last 500 entries to prevent file from growing too large
        if len(logs) > 500:
            logs = logs[-500:]
        
        # Write back to file
        try:
            with open(SAP_LOG_JSON_FILE, 'w', encoding='utf-8') as f:
                json.dump(logs, f, indent=2, default=str, ensure_ascii=False)
        except IOError as e:
            print(f"❌ [SAP_LOGGER] Could not write SAP log file: {e}")


def _update_json_log_response(timestamp: str, response_payload, status_code, error_message=None, duration_ms=None):
    """
    Update the response fields in the JSON log file for a specific request.
    Finds the log entry by timestamp and updates it with response data.
    """
    _ensure_log_directory()
    
    with _file_lock:
        if not os.path.exists(SAP_LOG_JSON_FILE):
            return
        
        try:
            with open(SAP_LOG_JSON_FILE, 'r', encoding='utf-8') as f:
                content = f.read().strip()
                if not content:
                    return
                logs = json.loads(content)
        except (json.JSONDecodeError, FileNotFoundError, IOError):
            return
        
        # Extract simplified SAP response message
        sap_message = None
        if response_payload:
            if isinstance(response_payload, dict):
                # Try to get the message or sap_response field
                sap_message = response_payload.get('message') or response_payload.get('sap_response') or response_payload.get('text')
            elif isinstance(response_payload, str):
                sap_message = response_payload
        
        # Determine status
        is_success = status_code and 200 <= status_code < 300 and not error_message
        status = "SUCCESS" if is_success else f"FAILED ({error_message or 'Error'})"
        
        # Find and update the matching entry (search from end since it's likely recent)
        for i in range(len(logs) - 1, -1, -1):
            if logs[i].get('timestamp') == timestamp:
                logs[i]['status'] = status
                logs[i]['sap_response'] = sap_message
                break
        
        # Write back
        try:
            with open(SAP_LOG_JSON_FILE, 'w', encoding='utf-8') as f:
                json.dump(logs, f, indent=2, default=str, ensure_ascii=False)
        except IOError as e:
            print(f"Warning: Could not update SAP log file: {e}")


# ============================================================================
# ORIGINAL DATABASE LOGGING FUNCTIONS (unchanged logic)
# ============================================================================

def log_sap_request(endpoint, method, payload, po_number=None, log_type=None):
    """Log SAP request before sending - to BOTH database AND JSON file"""
    print(f"🚀 [SAP_LOGGER] log_sap_request CALLED: po={po_number}, type={log_type}")
    
    timestamp = datetime.now()
    timestamp_iso = timestamp.isoformat()
    
    # Determine source label for simplified display
    source_labels = {
        "manual_confirmation": "MANUAL",
        "auto_confirmation": "AUTO (Shift-End)",
        "auto_shift_end_confirmation": "AUTO (Shift-End)",
        "offline_confirmation": "OFFLINE",
        "online_confirmation": "ONLINE",
        "mid_shift_confirmation": "MID-SHIFT",
        "push_confirmation": "AUTO/MID-SHIFT",
        "manual_confirmation_offline": "MANUAL (Offline)",
        "offline_storage_vpn_down": "OFFLINE (VPN Down)",
        "sap_failure_offline_fallback": "OFFLINE (SAP Failed)",
        "sap_partial_failure_offline": "OFFLINE (Partial Fail)",
    }
    source = source_labels.get(log_type, log_type or "UNKNOWN")
    
    # ✅ Convert payload to SAP format (uppercase keys, string values)
    if isinstance(payload, dict):
        sap_formatted_payload = _convert_to_sap_format(payload)
    elif isinstance(payload, list):
        # Handle batch confirmations (list of orders)
        sap_formatted_payload = [_convert_to_sap_format(p) if isinstance(p, dict) else p for p in payload]
    else:
        sap_formatted_payload = payload
    
    # ✅ STEP 1: Write SIMPLIFIED JSON entry (only essential fields)
    json_entry = {
        "timestamp": timestamp_iso,
        "source": source,
        "po_number": po_number,
        "payload": sap_formatted_payload,
        "status": "PENDING",
        "sap_response": None
    }
    
    try:
        _write_to_json_file(json_entry)
        # Store timestamp for later response update
        _pending_logs[id(payload) if payload else timestamp_iso] = timestamp_iso
        print(f"✅ [SAP_LOGGER] JSON file write completed for {po_number}")
    except Exception as e:
        print(f"❌ [SAP_LOGGER] Failed to write SAP request to JSON file: {e}")
        import traceback
        traceback.print_exc()
    
    # ✅ STEP 2: Write to database (original logic - unchanged)
    try:
        with PostgresSessionLocal() as db:
            log = SapLog(
                direction='sent',
                endpoint=endpoint,
                method=method,
                request_payload=payload,
                po_number=po_number,
                log_type=log_type,
                created_at=timestamp
            )
            db.add(log)
            db.commit()
            db.refresh(log)
            
            # Store the mapping from DB log ID to JSON timestamp
            _pending_logs[log.id] = timestamp_iso
            
            return log.id
    except Exception as e:
        print(f"Failed to log SAP request: {e}")
        return None


def log_sap_response(log_id, response_payload, status_code, error_message=None, duration_ms=None):
    """Log SAP response after receiving - to BOTH database AND JSON file"""
    if not log_id:
        return
    
    # ✅ STEP 1: Update JSON file (for debugging)
    try:
        # Get the timestamp from pending logs
        timestamp_iso = _pending_logs.pop(log_id, None)
        if timestamp_iso:
            _update_json_log_response(
                timestamp=timestamp_iso,
                response_payload=response_payload,
                status_code=status_code,
                error_message=error_message,
                duration_ms=duration_ms
            )
    except Exception as e:
        print(f"Warning: Failed to update SAP response in JSON file: {e}")
    
    # ✅ STEP 2: Update database (original logic - unchanged)
    try:
        with PostgresSessionLocal() as db:
            log = db.query(SapLog).filter(SapLog.id == log_id).first()
            if log:
                log.response_payload = response_payload
                log.status_code = status_code
                log.error_message = error_message
                log.duration_ms = duration_ms
                db.commit()
    except Exception as e:
        print(f"Failed to log SAP response: {e}")


# ============================================================================
# UTILITY FUNCTIONS FOR READING JSON LOGS
# ============================================================================

def get_json_logs(limit: int = 100, log_type: str = None, po_number: str = None) -> list:
    """
    Retrieve SAP logs from JSON file with optional filtering.
    
    Args:
        limit: Maximum number of logs to return (default 100)
        log_type: Filter by log type (e.g., 'online_confirmation', 'offline_confirmation')
        po_number: Filter by PO number (partial match)
    
    Returns:
        List of log entries, most recent first
    """
    if not os.path.exists(SAP_LOG_JSON_FILE):
        return []
    
    with _file_lock:
        try:
            with open(SAP_LOG_JSON_FILE, 'r', encoding='utf-8') as f:
                content = f.read().strip()
                if not content:
                    return []
                logs = json.loads(content)
        except (json.JSONDecodeError, FileNotFoundError, IOError):
            return []
    
    # Apply filters
    if log_type:
        logs = [l for l in logs if l.get('log_type') == log_type]
    
    if po_number:
        logs = [l for l in logs if po_number in str(l.get('po_number', ''))]
    
    # Return most recent first, limited
    return logs[-limit:][::-1]


def clear_json_logs():
    """Clear all JSON logs (useful for testing/maintenance)."""
    _ensure_log_directory()
    
    with _file_lock:
        try:
            with open(SAP_LOG_JSON_FILE, 'w', encoding='utf-8') as f:
                json.dump([], f)
            return True
        except IOError as e:
            print(f"Failed to clear SAP log file: {e}")
            return False
