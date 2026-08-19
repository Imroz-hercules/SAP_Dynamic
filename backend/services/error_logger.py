# backend/services/error_logger.py
import json
import logging
from datetime import datetime
from database import PostgresSessionLocal
from models.error_log import ErrorLog

log = logging.getLogger(__name__)

def log_order_error(po_number: str, error_type: str, error_message: str, payload=None, source="unknown"):
    """
    Insert an error entry into error_log table.
    This DOES NOT break or modify existing logic.
    """

    try:
        # Convert payload to JSON format and handle datetime serialization
        if isinstance(payload, str):
            try:
                payload = json.loads(payload)
            except:
                payload = {"raw": payload}
        
        # Serialize any non-serializable objects (like datetime) in payload
        if isinstance(payload, dict):
            def json_serial(obj):
                """JSON serializer for objects not serializable by default json code"""
                if isinstance(obj, datetime):
                    return obj.isoformat()
                return str(obj)
            
            # Re-serialize/deserialize to handle all nested objects
            try:
                payload = json.loads(json.dumps(payload, default=json_serial))
            except Exception as json_err:
                log.warning(f"Error serializing payload: {json_err}")
                payload = {"error": "Payload serialization failed", "raw": str(payload)}

        if payload is None:
            payload = {}

        with PostgresSessionLocal() as db:
            entry = ErrorLog(
                po_number=po_number,
                error_type=error_type,
                error_message=error_message,
                payload=payload,
                source=source,
                status="Open"
            )
            db.add(entry)
            db.commit()
            db.refresh(entry)
            log.info(f"📌 Error logged for PO {po_number} (log_id={entry.id})")
            return entry.id

    except Exception as e:
        log.exception(f"❌ Failed to log error: {e}")
        return None
