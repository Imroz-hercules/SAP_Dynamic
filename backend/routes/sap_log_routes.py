from flask import Blueprint, jsonify, request
from sqlalchemy import text
from database import PostgresSessionLocal
from models.sap_log import SapLog
import logging
import json
import os

sap_log_bp = Blueprint("sap_log", __name__, url_prefix="/api")
logger = logging.getLogger(__name__)

# Path to SAP confirmation JSON logs
SAP_LOG_JSON_FILE = os.path.join(
    os.path.dirname(os.path.dirname(__file__)),
    "logs",
    "sap_confirmations.json"
)

@sap_log_bp.route("/sap-logs", methods=["GET"])
def get_sap_logs():
    """Get SAP logs with pagination and filtering"""
    page = request.args.get('page', 1, type=int)
    limit = request.args.get('limit', 50, type=int)
    direction = request.args.get('direction')
    log_type = request.args.get('log_type')
    po_number = request.args.get('po_number')
    
    try:
        with PostgresSessionLocal() as db:
            query = db.query(SapLog)
            
            if direction:
                query = query.filter(SapLog.direction == direction)
            if log_type:
                query = query.filter(SapLog.log_type == log_type)
            if po_number:
                query = query.filter(SapLog.po_number.ilike(f"%{po_number}%"))
                
            total = query.count()
            
            logs = query.order_by(SapLog.created_at.desc()).offset((page - 1) * limit).limit(limit).all()
            
            return jsonify({
                "success": True,
                "logs": [{
                    "id": log.id,
                    "direction": log.direction,
                    "endpoint": log.endpoint,
                    "method": log.method,
                    "status_code": log.status_code,
                    "po_number": log.po_number,
                    "log_type": log.log_type,
                    "created_at": log.created_at.isoformat() if log.created_at else None,
                    "duration_ms": log.duration_ms,
                    "error_message": log.error_message
                } for log in logs],
                "total": total,
                "page": page,
                "pages": (total + limit - 1) // limit
            }), 200
            
    except Exception as e:
        logger.error(f"Error fetching SAP logs: {e}")
        return jsonify({"success": False, "error": str(e)}), 500

@sap_log_bp.route("/sap-logs/<int:log_id>", methods=["GET"])
def get_sap_log_detail(log_id):
    """Get detailed view of a single SAP log entry"""
    try:
        with PostgresSessionLocal() as db:
            log = db.query(SapLog).filter(SapLog.id == log_id).first()
            
            if not log:
                return jsonify({"success": False, "error": "Log not found"}), 404
                
            return jsonify({
                "success": True,
                "log": {
                    "id": log.id,
                    "direction": log.direction,
                    "endpoint": log.endpoint,
                    "method": log.method,
                    "status_code": log.status_code,
                    "po_number": log.po_number,
                    "log_type": log.log_type,
                    "created_at": log.created_at.isoformat() if log.created_at else None,
                    "duration_ms": log.duration_ms,
                    "error_message": log.error_message,
                    "request_payload": log.request_payload,
                    "response_payload": log.response_payload
                }
            }), 200
            
    except Exception as e:
        logger.error(f"Error fetching SAP log detail: {e}")
        return jsonify({"success": False, "error": str(e)}), 500


@sap_log_bp.route("/sap-logs/confirmations", methods=["GET"])
def get_sap_confirmation_logs():
    """
    Get SAP confirmation logs from JSON file.
    These logs track all confirmations sent to SAP (manual and automatic).
    ✅ UPDATED (Feb 4, 2026): Flatten batch confirmations so each order appears as separate row
    """
    limit = request.args.get('limit', 100, type=int)
    
    # Debug logging
    print(f"📋 [SAP-LOGS] Fetching confirmation logs...")
    print(f"📋 [SAP-LOGS] File path: {SAP_LOG_JSON_FILE}")
    print(f"📋 [SAP-LOGS] File exists: {os.path.exists(SAP_LOG_JSON_FILE)}")
    
    try:
        if os.path.exists(SAP_LOG_JSON_FILE):
            file_size = os.path.getsize(SAP_LOG_JSON_FILE)
            print(f"📋 [SAP-LOGS] File size: {file_size} bytes")
            
            with open(SAP_LOG_JSON_FILE, 'r', encoding='utf-8') as f:
                logs = json.load(f)
            
            print(f"📋 [SAP-LOGS] Loaded {len(logs)} raw log entries")
            
            # ✅ FLATTEN: Expand batch confirmations into individual order entries
            flattened_logs = []
            for log_entry in logs:
                payload = log_entry.get('payload', [])
                timestamp = log_entry.get('timestamp')
                source = log_entry.get('source', 'UNKNOWN')
                status = log_entry.get('status', 'UNKNOWN')
                sap_response = log_entry.get('sap_response', '')
                
                # Parse SAP response to get per-order status
                order_statuses = {}
                if sap_response:
                    try:
                        response_data = json.loads(sap_response) if isinstance(sap_response, str) else sap_response
                        if isinstance(response_data, list):
                            for resp in response_data:
                                po = resp.get('PROCESS_ORDER', '')
                                order_statuses[po] = {
                                    'status': resp.get('STATUS', status),
                                    'message': resp.get('MESSAGE', '')
                                }
                    except:
                        pass
                
                # If payload is a list of orders, create one entry per order
                if isinstance(payload, list) and len(payload) > 0:
                    for order in payload:
                        po_number = order.get('PROCESS_ORDER', order.get('po_number', ''))
                        order_resp = order_statuses.get(po_number, {})
                        
                        flattened_logs.append({
                            'timestamp': timestamp,
                            'source': source,
                            'po_number': po_number,
                            'material': order.get('MATERIAL', order.get('material', '')),
                            'qty': order.get('CONFIRMED_WEIGHT', order.get('confirmed_weight', 0)),
                            'uom': order.get('UOM', order.get('uom', 'KG')),
                            'final': order.get('FINAL_CONFIRMATION', ''),
                            'shift': order.get('SHIFT', order.get('shift', '')),
                            'status': order_resp.get('status', status),
                            'message': order_resp.get('message', ''),
                            'payload': order  # Individual order payload
                        })
                else:
                    # Single order or non-array payload
                    flattened_logs.append({
                        'timestamp': timestamp,
                        'source': source,
                        'po_number': log_entry.get('po_number', ''),
                        'material': payload.get('MATERIAL', '') if isinstance(payload, dict) else '',
                        'qty': payload.get('CONFIRMED_WEIGHT', 0) if isinstance(payload, dict) else 0,
                        'status': status,
                        'payload': payload
                    })
            
            print(f"📋 [SAP-LOGS] Flattened to {len(flattened_logs)} individual order entries")
            
            # Return most recent first (reverse order), limited
            recent_logs = flattened_logs[-limit:][::-1]
            
            # Add index ID for display
            for i, log in enumerate(recent_logs):
                log['id'] = len(flattened_logs) - i
            
            print(f"📋 [SAP-LOGS] Returning {len(recent_logs)} entries (total: {len(flattened_logs)})")
            
            return jsonify({
                "success": True,
                "logs": recent_logs,
                "total": len(flattened_logs)
            }), 200
        else:
            print(f"⚠️ [SAP-LOGS] File NOT found at: {SAP_LOG_JSON_FILE}")
            return jsonify({
                "success": True, 
                "logs": [],
                "total": 0,
                "message": f"No log file found at {SAP_LOG_JSON_FILE}"
            }), 200
            
    except json.JSONDecodeError as e:
        logger.error(f"Error parsing SAP confirmation JSON: {e}")
        return jsonify({
            "success": False, 
            "error": "Invalid JSON format in log file"
        }), 500
    except Exception as e:
        logger.error(f"Error fetching SAP confirmation logs: {e}")
        return jsonify({"success": False, "error": str(e)}), 500


@sap_log_bp.route("/sap-logs/confirmations/clear", methods=["POST"])
def clear_sap_confirmation_logs():
    """Clear all SAP confirmation logs from JSON file"""
    try:
        if os.path.exists(SAP_LOG_JSON_FILE):
            with open(SAP_LOG_JSON_FILE, 'w', encoding='utf-8') as f:
                json.dump([], f)
            return jsonify({
                "success": True,
                "message": "Confirmation logs cleared"
            }), 200
        else:
            return jsonify({
                "success": True,
                "message": "No log file to clear"
            }), 200
            
    except Exception as e:
        logger.error(f"Error clearing SAP confirmation logs: {e}")
        return jsonify({"success": False, "error": str(e)}), 500
