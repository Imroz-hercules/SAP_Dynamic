from flask import Blueprint, jsonify, request
from sqlalchemy import text
from database import PostgresSessionLocal
from services.sap_confirmation import SAPConfirmationService
from services.error_logger import log_order_error
import json
from datetime import datetime

error_log_bp = Blueprint("error_log", __name__, url_prefix="/api/error-log")

@error_log_bp.get("/")
def get_error_logs():
    with PostgresSessionLocal() as db:
        rows = db.execute(text("SELECT * FROM error_log ORDER BY created_at DESC")).mappings().all()
        result = []
        for r in rows:
            row_dict = dict(r)
            # Ensure datetime fields are properly serialized to ISO format
            if row_dict.get('created_at') and hasattr(row_dict['created_at'], 'isoformat'):
                row_dict['created_at'] = row_dict['created_at'].isoformat()
            if row_dict.get('resolved_at') and hasattr(row_dict['resolved_at'], 'isoformat'):
                row_dict['resolved_at'] = row_dict['resolved_at'].isoformat()
            result.append(row_dict)
        return jsonify(result), 200

@error_log_bp.get("/count")
def get_error_log_count():
    with PostgresSessionLocal() as db:
        count = db.execute(text("SELECT COUNT(*) FROM error_log WHERE status != 'Resolved'")).scalar()
        return jsonify({"count": count}), 200

@error_log_bp.post("/<int:log_id>/resend")
def resend_sap(log_id):
    """
    Resend a VPN-failed confirmation to SAP with user-provided scrap and confirmed_text.
    
    This endpoint handles:
    1. VPN network errors (partial confirmations during auto shift-end)
    2. Deduplication: Check if already confirmed before resending (can be bypassed with force_resend)
    3. Use exact payload that failed but with new scrap/confirmed_text values
    """
    data = request.get_json() or {}
    scrap = float(data.get('scrap', 0.0))
    confirmed_text = data.get('confirmed_text', '')
    force_resend = data.get('force_resend', False)  # Bypass local deduplication check
    
    with PostgresSessionLocal() as db:
        row = db.execute(text("SELECT * FROM error_log WHERE id=:id"), {"id": log_id}).mappings().first()
        if not row:
            return jsonify({"ok": False, "message": "Entry not found"}), 404

        original = row["payload"]
        po_number = row["po_number"]
        error_type = row["error_type"]
        
        # ✅ Parse payload if it's a string
        if isinstance(original, str):
            try:
                original = json.loads(original)
            except:
                return jsonify({"ok": False, "message": "Invalid payload format"}), 400
        
        # The logged payload already contains sent_payload
        payload = original.get("sent_payload")
        if not payload:
            return jsonify({"ok": False, "message": "No payload stored to resend"}), 400

        if isinstance(payload, dict):
            payload_list = [payload]
        else:
            payload_list = payload
        
        # ✅ Update payload with user-provided scrap and confirmed_text
        for p in payload_list:
            p['scrap'] = scrap
            p['confirmed_text'] = confirmed_text
        
        # ✅ CRITICAL: Check for deduplication before resending (skip if force_resend=True)
        # For partial confirmations, check if already confirmed to SAP
        if force_resend:
            print(f"⚠️ [Resend] Force resend enabled for log_id={log_id}, PO={po_number} - bypassing local deduplication check")
        else:
            try:
                for p in payload_list:
                    po = p.get('po_number')
                    shift = p.get('shift', '').upper()
                    confirmed_weight = p.get('confirmed_weight', 0)
                    
                    if po and shift in ('A', 'B', 'C'):
                        # Check if this shift was already confirmed
                        shift_col = f"confirmed_shift_{shift.lower()}"
                        order_row = db.execute(text(f"""
                            SELECT {shift_col}, weight_shift_{shift.lower()}, order_id 
                            FROM process_orders 
                            WHERE order_id = :po
                        """), {"po": po}).mappings().first()
                        
                        if order_row:
                            already_confirmed = float(order_row.get(shift_col, 0) or 0)
                            shift_weight = float(order_row.get(f"weight_shift_{shift.lower()}", 0) or 0)
                            
                            print(f"📊 [Resend] Deduplication check for PO {po} - Shift {shift}:")
                            print(f"   Attempting to resend: {confirmed_weight:.2f}")
                            print(f"   Already confirmed to SAP: {already_confirmed:.2f}")
                            print(f"   Shift weight: {shift_weight:.2f}")
                            
                            # If already confirmed, skip this payload
                            if already_confirmed >= confirmed_weight:
                                return jsonify({
                                    "ok": False, 
                                    "error": "duplicate",
                                    "message": f"Order {po} Shift {shift} already confirmed ({already_confirmed:.2f} >= {confirmed_weight:.2f}). Not resending to prevent duplication. Use 'Force Resend' to override."
                                }), 400
            except Exception as dedup_err:
                print(f"❌ Deduplication check failed: {dedup_err}")
                # Continue anyway, let SAP handle it

    # Check VPN before sending
    sap_service = SAPConfirmationService()
    if sap_service.mock_mode:
        vpn_status = {"connected": True, "message": "Mock mode - using demo server"}
    else:
        from utils.vpn_check import check_vpn_connection
        vpn_status = check_vpn_connection()
    
    if not vpn_status.get("connected"):
        return jsonify({
            "ok": False,
            "error": "vpn_disconnected",
            "message": "VPN is still disconnected. Cannot resend to SAP.",
            "vpn_status": vpn_status
        }), 503

    # ✅ VPN is connected - send to SAP
    # For partial confirmations (shift auto confirm), use confirm_offline endpoint
    if error_type == "sap_network_error" and original.get("confirmation_type") == "partial_shift_end":
        result = sap_service.confirm_offline(payload_list)
    else:
        result = sap_service.confirm_online(payload_list)

    if result.get("ok") or result.get("success"):
        with PostgresSessionLocal() as db:
            db.execute(text("UPDATE error_log SET status='Resolved', resolved_at=NOW() WHERE id=:id"), {"id": log_id})
            db.commit()
        
        return jsonify({"ok": True, "success": True, "message": "Confirmation resent successfully to SAP"})
    else:
        return jsonify({
            "ok": False,
            "error": result.get("error") or result.get("message"),
            "message": f"Failed to resend: {result.get('error') or result.get('message')}"
        }), 500

@error_log_bp.post("/<int:log_id>/reprocess")
def reprocess_error_order(log_id):
    """
    Reprocess an order from error log with new scrap/confirmed_text.
    
    Per Dec_13_changes.md fallback strategy:
    1. Check VPN before reprocessing
    2. If VPN disconnected → store in offline_confirmations
    3. If VPN connected → send to SAP
    4. If SAP succeeds → mark error_log as "Resolved"
    5. If SAP fails again → update error_log with new error
    """
    data = request.get_json() or {}
    scrap = float(data.get('scrap', 0.0))
    confirmed_text = data.get('confirmed_text', '')
    retry_vpn_check = data.get('retry_vpn_check', True)  # Default to checking VPN
    
    with PostgresSessionLocal() as db:
        row = db.execute(text("SELECT * FROM error_log WHERE id=:id"), {"id": log_id}).mappings().first()
        if not row:
            return jsonify({"ok": False, "message": "Entry not found"}), 404

        original = row["payload"]
        if not original:
            return jsonify({"ok": False, "message": "No payload stored"}), 400
            
    # Get sent_payload
    payload = original.get("sent_payload")
    if not payload:
        return jsonify({"ok": False, "message": "No sent_payload found"}), 400

    # Update payload with new values
    if isinstance(payload, dict):
        payload['scrap'] = scrap
        payload['confirmed_text'] = confirmed_text
        payload_list = [payload]
    else:
        # Assuming list
        for p in payload:
            p['scrap'] = scrap
            p['confirmed_text'] = confirmed_text
        payload_list = payload

    sap_service = SAPConfirmationService()
    
    # ✅ CRITICAL: Check VPN before reprocessing (per Dec_13_changes.md fallback strategy)
    # Skip VPN check if using mock mode (demo server)
    if sap_service.mock_mode:
        vpn_status = {"connected": True, "message": "Mock mode - using demo server"}
    else:
        from utils.vpn_check import check_vpn_connection
        vpn_status = check_vpn_connection()
    
    if not vpn_status.get("connected"):
        # ✅ VPN DISCONNECTED: Store in offline_confirmations and mark error_log as Resolved
        from models.offline_confirmation import OfflineConfirmation
        
        stored_count = 0
        try:
            with PostgresSessionLocal() as offline_db:
                for p in payload_list:
                    po_number = p.get('po_number')
                    if not po_number:
                        continue
                    
                    # Check for duplicates
                    po_num_stripped = str(po_number).lstrip('0')
                    existing = offline_db.query(OfflineConfirmation).filter(
                        OfflineConfirmation.status == 'pending'
                    ).all()
                    
                    is_duplicate = any(
                        str(e.order_id).lstrip('0') == po_num_stripped 
                        for e in existing if e.order_id
                    )
                    
                    if is_duplicate:
                        continue
                    
                    offline_record = OfflineConfirmation(
                        order_id=str(po_number),
                        process_order_id=p.get('process_order_id'),
                        material=p.get('material'),
                        version=p.get('version'),
                        confirmed_weight=float(p.get('confirmed_weight', 0)),
                        total_qty=float(p.get('total_qty', 0)),
                        uom=p.get('uom', 'KG'),
                        plant=p.get('plant'),
                        batch=p.get('batch', ''),
                        shift=p.get('shift'),
                        scrap=scrap,
                        confirmed_text=confirmed_text or f"Reprocess from error_log: VPN down",
                        sap_payload=json.loads(json.dumps(p, default=str)),
                        validation_method='Reprocess',
                        status='pending',
                        retry_count=0
                    )
                    offline_db.add(offline_record)
                    stored_count += 1
                
                if stored_count > 0:
                    offline_db.commit()
                    
                    # Mark error_log as Resolved (moved to offline)
                    offline_db.execute(text(
                        "UPDATE error_log SET status='Resolved', resolved_at=NOW() WHERE id=:id"
                    ), {"id": log_id})
                    offline_db.commit()
                    
                    return jsonify({
                        "success": True,
                        "offline_mode": True,
                        "message": f"VPN disconnected - {stored_count} order(s) stored for offline confirmation",
                        "stored_count": stored_count,
                        "vpn_status": vpn_status
                    }), 200
                else:
                    return jsonify({
                        "success": False,
                        "offline_mode": True,
                        "message": "VPN disconnected but no orders stored (possible duplicates)",
                        "vpn_status": vpn_status
                    }), 200
        except Exception as offline_err:
            return jsonify({
                "success": False,
                "message": f"Failed to store offline: {str(offline_err)}",
                "vpn_status": vpn_status
            }), 500
    
    # ✅ VPN CONNECTED: Try to send to SAP
    result = sap_service.confirm_online(payload_list)

    with PostgresSessionLocal() as db:
        if result.get("ok"):
            # Mark resolved
            db.execute(text("UPDATE error_log SET status='Resolved', resolved_at=NOW() WHERE id=:id"), {"id": log_id})
            db.commit()
            return jsonify({"success": True, "message": "Order reprocessed successfully"})
        else:
            # Update error log with new error (keep status Open for retry)
            new_payload = original.copy()
            new_payload['sent_payload'] = payload_list  # Updated with new values
            new_payload['last_error'] = result.get('error')
            new_payload['last_reprocess_attempt'] = datetime.now().isoformat()
            new_payload['vpn_connected'] = True  # VPN was connected, SAP rejected
            
            # Using raw SQL with json.dumps
            db.execute(text("UPDATE error_log SET payload=:p, error_message=:e, updated_at=NOW() WHERE id=:id"), {
                "id": log_id,
                "p": json.dumps(new_payload),
                "e": result.get('error', 'Reprocess failed')
            })
            db.commit()
            return jsonify({"success": False, "error": result.get('error')}), 500

@error_log_bp.post("/<int:log_id>/revalidate")
def revalidate_from_log(log_id):
    print(f"🔄 Revalidate request received for log_id={log_id}")
    try:
        with PostgresSessionLocal() as db:
            row = db.execute(text("SELECT * FROM error_log WHERE id=:id"), {"id": log_id}).mappings().first()
            if not row:
                print(f"❌ Error log entry {log_id} not found in database")
                return jsonify({"ok": False, "message": f"Error log entry {log_id} not found"}), 404
            
            print(f"✅ Found error log entry: id={log_id}, po_number={row.get('po_number')}, error_type={row.get('error_type')}")

            po = row["po_number"]
            # Also check payload for original PO number (might have leading zeros)
            payload = row.get("payload") or {}
            if isinstance(payload, str):
                try:
                    import json
                    payload = json.loads(payload)
                except:
                    payload = {}
            
            # Get PO from payload if available (might have leading zeros)
            po_from_payload = payload.get("po_number") or payload.get("order_id")
            if po_from_payload:
                po = str(po_from_payload)
            
            if not po:
                return jsonify({"ok": False, "message": "PO number not found in error log entry"}), 400

            # Normalize PO number (remove leading zeros for matching)
            po_clean = str(po).lstrip("0") if po else ""
            if not po_clean:
                return jsonify({"ok": False, "message": "Invalid PO number in error log entry"}), 400
            
            print(f"🔍 Using PO: original={po}, cleaned={po_clean}")

            # Reset order status - try both with and without leading zeros
            # First try with the exact PO from error_log
            result = db.execute(
                text("UPDATE process_orders SET status='Pending' WHERE order_id=:po OR order_id=:po_clean"),
                {"po": po, "po_clean": po_clean}
            )
            db.commit()
            
            if result.rowcount == 0:
                return jsonify({"ok": False, "message": f"Order {po} not found in process_orders table"}), 404

        # restart validator worker
        try:
            # Import necessary functions from order_validation
            from routes.order_validation import init_and_start_order_worker, classify_order
            from models.process_order_pg import ProcessOrderPG as ProcessOrder
            from database import PostgresSessionLocal as db_session
            
            with db_session() as db:
                # Try to find order with both PO formats
                order = db.query(ProcessOrder).filter(
                    (ProcessOrder.order_id == po) | (ProcessOrder.order_id == po_clean)
                ).first()
                
                if not order:
                    return jsonify({"ok": False, "message": f"Order {po} not found in database"}), 404
                
                classification = classify_order(order)
                if classification.get("error"):
                    return jsonify({"ok": False, "message": f"Classification failed: {classification['error']}"}), 400
                
                init_and_start_order_worker(db, order, classification)
        except ImportError as e:
            import traceback
            traceback.print_exc()
            return jsonify({"ok": False, "message": f"Import error: {str(e)}"}), 500
        except Exception as e:
            import traceback
            traceback.print_exc()
            return jsonify({"ok": False, "message": f"Failed to restart validation: {str(e)}"}), 500

        # mark resolved
        with PostgresSessionLocal() as db:
            db.execute(text("UPDATE error_log SET status='Resolved', resolved_at=NOW() WHERE id=:id"), {"id": log_id})
            db.commit()

        return jsonify({"ok": True, "message": f"Revalidation started for {po_clean}"})
    except Exception as e:
        import traceback
        traceback.print_exc()
        return jsonify({"ok": False, "message": f"Unexpected error: {str(e)}"}), 500
