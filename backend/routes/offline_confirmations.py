from flask import Blueprint, jsonify, request
from sqlalchemy import func, text
from database import PostgresSessionLocal
from models.offline_confirmation import OfflineConfirmation
from services.sap_confirmation import sap_confirmation_service
from utils.vpn_check import check_vpn_connection
import logging
import json
from datetime import datetime

print("=" * 60)
print("🔥🔥🔥 OFFLINE_CONFIRMATIONS.PY LOADED 🔥🔥🔥")
print("=" * 60)

offline_bp = Blueprint("offline", __name__, url_prefix="/api")
logger = logging.getLogger(__name__)

@offline_bp.route("/offline-confirmations", methods=["GET"])
def list_offline_confirmations():
    """List pending offline confirmations. Optional order_type=MILLING|PACKING to filter by material."""
    status_filter = request.args.get('status', 'pending')
    order_type = request.args.get('order_type', '').strip()
    
    try:
        with PostgresSessionLocal() as db:
            query = db.query(OfflineConfirmation)
            
            if status_filter:
                query = query.filter(OfflineConfirmation.status == status_filter)
            if order_type and order_type.upper() in ('MILLING', 'PACKING'):
                prefix = '13' if order_type.upper() == 'MILLING' else '14'
                query = query.filter(text("ltrim(COALESCE(material, ''), '0') LIKE :prefix")).params(prefix=f"{prefix}%")
                
            confirmations = query.order_by(OfflineConfirmation.created_at.desc()).all()
            
            return jsonify({
                "success": True,
                "offline_confirmations": [c.to_dict() for c in confirmations],
                "count": len(confirmations)
            }), 200
    except Exception as e:
        logger.error(f"Error listing offline confirmations: {e}")
        return jsonify({"success": False, "error": str(e)}), 500

@offline_bp.route("/offline-confirmations/count", methods=["GET"])
def count_offline_confirmations():
    """Get count of pending offline orders. Optional order_type=MILLING|PACKING to filter by material."""
    order_type = request.args.get('order_type', '').strip()
    
    try:
        with PostgresSessionLocal() as db:
            query = db.query(func.count(OfflineConfirmation.id)).filter(
                OfflineConfirmation.status == 'pending'
            )
            if order_type and order_type.upper() in ('MILLING', 'PACKING'):
                prefix = '13' if order_type.upper() == 'MILLING' else '14'
                query = query.filter(text("ltrim(COALESCE(material, ''), '0') LIKE :prefix")).params(prefix=f"{prefix}%")
            count = query.scalar()
            return jsonify({"count": count or 0}), 200
    except Exception as e:
        logger.error(f"Error counting offline confirmations: {e}")
        return jsonify({"count": 0, "error": str(e)}), 500

@offline_bp.route("/offline-confirmations/<int:id>", methods=["PUT"])
def update_offline_confirmation(id):
    """Update scrap and confirmed_text for an offline order."""
    data = request.get_json()
    
    try:
        with PostgresSessionLocal() as db:
            record = db.query(OfflineConfirmation).filter(OfflineConfirmation.id == id).first()
            
            if not record:
                return jsonify({"success": False, "error": "Order not found"}), 404
                
            if 'scrap' in data:
                record.scrap = float(data['scrap'])
                # Update payload if present - use LOWERCASE keys (internal format)
                # The SAP service expects lowercase keys and converts them
                if record.sap_payload:
                    if isinstance(record.sap_payload, list) and len(record.sap_payload) > 0:
                        record.sap_payload[0]['scrap'] = record.scrap
                    elif isinstance(record.sap_payload, dict):
                        record.sap_payload['scrap'] = record.scrap
            
            if 'confirmed_text' in data:
                record.confirmed_text = data['confirmed_text']
                # Update payload if present - use LOWERCASE keys (internal format)
                if record.sap_payload:
                    if isinstance(record.sap_payload, list) and len(record.sap_payload) > 0:
                        record.sap_payload[0]['confirmed_text'] = record.confirmed_text
                    elif isinstance(record.sap_payload, dict):
                        record.sap_payload['confirmed_text'] = record.confirmed_text
            
            db.commit()
            return jsonify({"success": True, "message": "Order updated successfully"}), 200
            
    except Exception as e:
        logger.error(f"Error updating offline confirmation: {e}")
        return jsonify({"success": False, "error": str(e)}), 500

@offline_bp.route("/offline-confirmations/send", methods=["POST"])
def send_offline_confirmations():
    """Send offline confirmations to SAP (bulk or individual)."""
    print("🚀🚀🚀 [OFFLINE SEND] Route called! 🚀🚀🚀")
    data = request.get_json()
    print(f"🚀 [OFFLINE SEND] Request data: {data}")
    order_ids = data.get('order_ids', [])
    print(f"🚀 [OFFLINE SEND] Order IDs to send: {order_ids}")
    
    if not order_ids:
        return jsonify({"success": False, "error": "No order IDs provided"}), 400
        
    # Check VPN status first (skip if mock mode)
    # ✅ Read mock mode from database settings (not environment variable)
    try:
        from models.system_settings import is_mock_sap_enabled
        mock_mode = is_mock_sap_enabled()
    except Exception:
        mock_mode = True  # Default to mock mode for safety
    
    if mock_mode:
        # Mock mode: Skip VPN check, always send to demo server
        vpn_status = {"connected": True, "message": "Mock mode - using demo server"}
    else:
        # Real SAP mode: Check VPN connection
        vpn_status = check_vpn_connection()
    
    if not vpn_status["connected"]:
        return jsonify({
            "success": False, 
            "error": "VPN disconnected. Cannot send orders to SAP.",
            "vpn_status": vpn_status
        }), 503
        
    results = {
        "success": [],
        "failed": []
    }
    
    try:
        with PostgresSessionLocal() as db:
            # Process each order
            for order_id in order_ids:
                record = db.query(OfflineConfirmation).filter(OfflineConfirmation.id == order_id).first()
                
                if not record:
                    results["failed"].append({"id": order_id, "error": "Record not found"})
                    continue
                    
                if record.status == 'sent':
                    results["success"].append({"id": order_id, "message": "Already sent"})
                    continue
                
                # Get payload
                payload = record.sap_payload
                if not payload:
                    results["failed"].append({"id": order_id, "error": "No SAP payload found"})
                    continue
                
                # Parse JSON string if needed (PostgreSQL JSON column might return string)
                if isinstance(payload, str):
                    try:
                        payload = json.loads(payload)
                    except json.JSONDecodeError as e:
                        results["failed"].append({"id": order_id, "error": f"Invalid JSON in payload: {str(e)}"})
                        continue
                
                # Ensure payload is a list for push_confirmation
                if isinstance(payload, dict):
                    payload_list = [payload]
                elif isinstance(payload, list):
                    payload_list = payload
                else:
                    results["failed"].append({"id": order_id, "error": f"Invalid payload type: {type(payload)}"})
                    continue
                
                # Update payload with latest scrap/text values - use LOWERCASE keys (internal format)
                # The SAP service expects lowercase keys and converts them to SAP format
                for item in payload_list:
                    if not isinstance(item, dict):
                        results["failed"].append({"id": order_id, "error": f"Payload item is not a dict: {type(item)}"})
                        continue
                    item['scrap'] = float(record.scrap or 0)  # lowercase, as number (handle None)
                    item['confirmed_text'] = record.confirmed_text or ""  # lowercase
                
                # Send to SAP
                try:
                    # ✅ Use 'offline' confirmation type to ensure SCRAP and CONFIRMED_TEXT
                    # are included in the SAP request (the SAP service only adds them for 'offline' type)
                    logger.info(f"🔍 Sending offline confirmation for PO {record.order_id} - Mock mode: {sap_confirmation_service.mock_mode}")
                    logger.info(f"🔍 Payload structure: {len(payload_list)} item(s), first item keys: {list(payload_list[0].keys()) if payload_list and isinstance(payload_list[0], dict) else 'N/A'}")
                    logger.info(f"🔍 First item sample: {str(payload_list[0])[:200] if payload_list else 'N/A'}")
                    result = sap_confirmation_service.push_confirmation(payload_list, confirmation_type='offline')
                    logger.info(f"📤 Offline confirmation result: success={result.get('success')}, ok={result.get('ok')}, error={result.get('error')}")
                    
                    if result.get('success') or result.get('ok'):
                        record.status = 'sent'
                        record.sent_at = datetime.now()
                        record.retry_count = (record.retry_count or 0) + 1
                        results["success"].append({"id": order_id, "po": record.order_id})
                        
                        # ✅ NOTE: Confirmation values (confirmed_shift_X, last_confirmed_qty) are 
                        # already updated when the order was stored offline - no need to update again.
                        # This only marks the offline record as 'sent' to SAP.
                        logger.info(f"✅ Offline order {record.order_id} synced to SAP successfully")
                    else:
                        record.retry_count = (record.retry_count or 0) + 1
                        results["failed"].append({
                            "id": order_id, 
                            "po": record.order_id, 
                            "error": result.get('message') or result.get('error')
                        })
                        
                except Exception as e:
                    record.retry_count = (record.retry_count or 0) + 1
                    results["failed"].append({"id": order_id, "error": str(e)})
            
            db.commit()
            
        return jsonify({
            "success": True,
            "results": results,
            "message": f"Processed {len(order_ids)} orders: {len(results['success'])} sent, {len(results['failed'])} failed"
        }), 200
        
    except Exception as e:
        logger.error(f"Error sending offline confirmations: {e}")
        return jsonify({"success": False, "error": str(e)}), 500

@offline_bp.route("/vpn/status", methods=["GET"])
def get_vpn_status():
    """Check VPN connection status to SAP."""
    # Use SAPConfirmationService to get mock mode status (consistent detection)
    from services.sap_confirmation import SAPConfirmationService
    sap_service_check = SAPConfirmationService()
    
    if sap_service_check.mock_mode:
        # Mock mode: Return mock status
        status = {"connected": True, "message": "Mock mode - using demo server", "mock_mode": True}
    else:
        # Real SAP mode: Check VPN connection
        status = check_vpn_connection()
        status["mock_mode"] = False
    
    return jsonify(status), 200

