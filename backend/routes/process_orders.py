# # # routes/process_orders.py
# # from __future__ import annotations

# # from typing import List, Dict, Any, Optional, Tuple
# # from flask import Blueprint, jsonify, request, abort
# # from sqlalchemy import text
# # from datetime import datetime, timedelta

# # from database import postgres_engine, PostgresSessionLocal
# # from services.process_order_sync import sync_process_orders           # legacy/internal sync (optional)
# # from services.process_order_pull import pull_from_sap_once, test_sap_connection
# # from utils.shifts import get_current_shift
# # import json  # shared SAP -> Hercules pull
# # from models.manual_confirmation import ManualConfirmation


# # process_orders_bp = Blueprint("process_orders", __name__, url_prefix="/api")

# # # -------------------------------------------------------------------
# # # Helpers
# # # -------------------------------------------------------------------

# # def _row_to_api(row) -> dict:
# #     """Map DB row -> API shape (doc-aligned)."""
# #     return {
# #         "id": row.id,
# #         "po_number": row.order_id,  # order_id is the PO number from SAP
# #         "material": row.material,
# #         "version": row.version,
# #         "batch": row.batch,
# #         "quantity": float(row.quantity) if row.quantity is not None else None,
# #         "unit": row.unit,
# #         "status": row.status,
# #         "priority": row.priority,
# #         "plant": getattr(row, 'plant', None),
# #         "confirmed_qty": float(row.confirmed_qty) if hasattr(row, 'confirmed_qty') and row.confirmed_qty is not None else None,
# #         "material_desc": getattr(row, 'material_desc', None),
# #         "expected_weight": float(row.expected_weight) if hasattr(row, 'expected_weight') and row.expected_weight is not None else None,
# #         "created_at": row.created_at.isoformat() if row.created_at else None,
# #         "order_type": getattr(row, 'order_type', None),  # Add order_type field
# #     }

# # def _queue_where_clause(statuses: Optional[List[str]] = None) -> Tuple[str, Dict[str, Any]]:
# #     """
# #     Build WHERE for queue. By default we queue only 'Open' or 'Pending'.
# #     """
# #     params: Dict[str, Any] = {}
# #     if not statuses:
# #         statuses = ["Open", "Pending"]
# #     placeholders = ", ".join([f":s{i}" for i, _ in enumerate(statuses)])
# #     for i, s in enumerate(statuses):
# #         params[f"s{i}"] = s
# #     where_sql = f" WHERE status IN ({placeholders})"
# #     return where_sql, params

# # def _queue_order_by_clause() -> str:
# #     """
# #     Priority first (ascending: smaller number = higher priority),
# #     then FIFO by created_at (oldest first), finally by id to break ties.
# #     """
# #     return " ORDER BY priority ASC, created_at ASC NULLS LAST, id ASC "


# # def _ensure_order_from_po(conn, po_row_id: int) -> dict | None:
# #     """
# #     Create (or ensure) an 'orders' row from a claimed process_orders row.
# #     Returns the upserted order as a mapping (dict-like).
# #     """
# #     # 1) fetch the claimed process order row
# #     po = conn.execute(text("""
# #         SELECT order_id, material, version, batch, quantity, unit, plant, confirmed_qty, material_desc
# #         FROM process_orders
# #         WHERE id = :id
# #     """), {"id": po_row_id}).mappings().first()
# #     if not po:
# #         return None

# #     # 2) UPSERT into orders using po_number as unique key
# #     conn.execute(text("""
# #         INSERT INTO orders (po_number, material, version, batch, quantity, unit, plant, confirmed_qty, material_desc, status, created_at, updated_at)
# #         VALUES (:po_number, :material, :version, :batch, :quantity, :unit, :plant, :confirmed_qty, :material_desc, 'Pending', NOW(), NOW())
# #         ON CONFLICT (po_number) DO UPDATE
# #         SET material      = EXCLUDED.material,
# #             version       = EXCLUDED.version,
# #             batch         = EXCLUDED.batch,
# #             quantity      = EXCLUDED.quantity,
# #             unit          = EXCLUDED.unit,
# #             plant         = EXCLUDED.plant,
# #             confirmed_qty = EXCLUDED.confirmed_qty,
# #             material_desc = EXCLUDED.material_desc,
# #             updated_at    = NOW()
# #     """), {
# #         "po_number": po.order_id,
# #         "material":  po.material,
# #         "version":   po.version,
# #         "batch":     po.batch,
# #         "quantity":  po.quantity,
# #         "unit":      po.unit or "KG",
# #         "plant":     po.plant,
# #         "confirmed_qty": po.confirmed_qty,
# #         "material_desc": po.material_desc,
# #     })

# #     # 3) return the orders row
# #     order = conn.execute(text("""
# #         SELECT id, po_number, material, version, batch, quantity, unit, plant, confirmed_qty, material_desc, status, created_at, updated_at
# #         FROM orders
# #         WHERE po_number = :po
# #     """), {"po": po.order_id}).mappings().first()
# #     return order

# # # -------------------------------------------------------------------
# # # Routes
# # # -------------------------------------------------------------------

# # @process_orders_bp.get("/process_orders")
# # def list_process_orders():
# #     """
# #     List process orders (doc-aligned fields only).

# #     Query params:
# #       - status: filter by status (e.g., Open, Pending, Validated, Rejected)
# #       - limit: page size (default 50)
# #       - offset: page offset (default 0)
# #     """
# #     status = request.args.get("status")
# #     try:
# #         limit = int(request.args.get("limit", 50))
# #         offset = int(request.args.get("offset", 0))
# #     except ValueError:
# #         limit, offset = 50, 0

# #     base_sql = """
# #       SELECT
# #         id,
# #         order_id,
# #         material,
# #         version,
# #         batch,
# #         quantity,
# #         unit,
# #         status,
# #         priority,
# #         plant,
# #         confirmed_qty,
# #         material_desc,
# #         expected_weight,
# #         created_at,
# #         order_type
# #       FROM process_orders
# #     """

# #     params = {"limit": limit, "offset": offset}
# #     where_sql = ""
# #     if status and status != "All":
# #         where_sql = " WHERE status = :status"
# #         params["status"] = status

# #     sql = (
# #         base_sql
# #         + where_sql
# #         + " ORDER BY created_at DESC NULLS LAST LIMIT :limit OFFSET :offset"
# #     )

# #     try:
# #         with postgres_engine.connect() as conn:
# #             rows = conn.execute(text(sql), params).mappings().all()
# #         return jsonify([_row_to_api(r) for r in rows]), 200
# #     except Exception as e:
# #         # Dev-only fallback; remove in production
# #         print(f"[process_orders] list error: {e}")
# #         sample = [{
# #             "id": 1,
# #             "po_number": "PO-001",
# #             "material": "1300005",
# #             "version": "BKF1",
# #             "batch": "BATCH-001",
# #             "quantity": 1000.0,
# #             "unit": "KG",
# #             "status": "Open",
# #             "priority": 1,
# #             "created_at": (datetime.now() - timedelta(days=1)).isoformat(),
# #         }]
# #         return jsonify(sample), 200


# # @process_orders_bp.post("/process_orders/pull")
# # def pull_process_orders_from_sap():
# #     """
# #     Manual 'Pull New Orders' (SAP -> Hercules):
# #     - Fetch open POs from SAP using the shared service
# #     - Upsert by order_id (po_number)
# #     """
# #     try:
# #         count = pull_from_sap_once()
# #         return jsonify({"message": f"Pulled {count} orders from SAP"}), 200
# #     except Exception as e:
# #         return jsonify({"error": f"Pull failed: {str(e)}"}), 500


# # @process_orders_bp.post("/process_orders/sync")
# # def sync_process_orders_endpoint():
# #     """
# #     Optional legacy/internal sync (e.g., SQL Server -> Postgres).
# #     Keep if still in use alongside SAP Pull; otherwise safe to remove later.
# #     """
# #     try:
# #         success = sync_process_orders()
# #         if success:
# #             return jsonify({"message": "Process orders synced successfully"}), 200
# #         return jsonify({"error": "Failed to sync process orders"}), 500
# #     except Exception as e:
# #         return jsonify({"error": f"Sync failed: {str(e)}"}), 500


# # # -------------------------------
# # # FIFO queue (priority → FIFO)
# # # -------------------------------

# # @process_orders_bp.get("/process_orders/queue")
# # def list_process_orders_queue():
# #     """
# #     Returns the execution queue already sorted:
# #     - priority ASC
# #     - created_at ASC (FIFO)
# #     - id ASC (tie-breaker)

# #     Query params:
# #       - limit (default 50)
# #       - statuses CSV (default: Open,Pending) e.g. ?statuses=Open,Pending,Validated
# #     """
# #     try:
# #         limit = int(request.args.get("limit", 50))
# #     except ValueError:
# #         limit = 50

# #     statuses_param = request.args.get("statuses")
# #     statuses = [s.strip() for s in statuses_param.split(",")] if statuses_param else None

# #     base_sql = """
# #       SELECT
# #         id,
# #         order_id,
# #         material,
# #         version,
# #         batch,
# #         quantity,
# #         unit,
# #         status,
# #         priority,
# #         plant,
# #         confirmed_qty,
# #         material_desc,
# #         expected_weight,
# #         created_at
# #       FROM process_orders
# #     """

# #     where_sql, params = _queue_where_clause(statuses)
# #     sql = base_sql + where_sql + _queue_order_by_clause() + " LIMIT :limit"
# #     params["limit"] = limit

# #     with postgres_engine.connect() as conn:
# #         rows = conn.execute(text(sql), params).mappings().all()
# #     return jsonify([_row_to_api(r) for r in rows]), 200


# # @process_orders_bp.post("/process_orders/next")
# # def claim_next_process_order():
# #     """
# #     Returns the 'next' order by (priority → FIFO). If claim=true:
# #       1) atomically set process_orders.status='InProgress'
# #       2) upsert into orders (po_number unique) with status 'Pending'
# #       3) return both the claimed process order and the execution order
# #     Body (optional):
# #       { "claim": true }
# #     """
# #     payload = request.get_json(silent=True) or {}
# #     claim = bool(payload.get("claim", False))

# #     select_sql = """
# #       SELECT id, order_id, material, version, batch, quantity, unit, status, priority, plant, confirmed_qty, material_desc, created_at
# #       FROM process_orders
# #       WHERE status IN ('Open', 'Pending')
# #     """ + _queue_order_by_clause() + " LIMIT 1"

# #     with postgres_engine.connect() as conn:
# #         row = conn.execute(text(select_sql)).mappings().first()
# #         if not row:
# #             return jsonify({"message": "No eligible orders found"}), 200

# #         if not claim:
# #             return jsonify(_row_to_api(row)), 200

# #         # 1) claim the process order (atomic)
# #         claimed = conn.execute(text("""
# #             UPDATE process_orders
# #             SET status = 'InProgress', updated_at = NOW()
# #             WHERE id = :id AND status IN ('Open','Pending')
# #             RETURNING id, order_id, material, version, batch, quantity, unit, status, priority, plant, confirmed_qty, material_desc, created_at
# #         """), {"id": row.id}).mappings().first()
# #         if not claimed:
# #             conn.rollback()
# #             abort(409, description="Order already claimed by another worker")

# #         # 2) ensure an execution order exists (orders table)
# #         order_row = _ensure_order_from_po(conn, claimed.id)

# #         conn.commit()

# #         return jsonify({
# #             "claimed_process_order": _row_to_api(claimed),
# #             "execution_order": {
# #                 "id": order_row["id"],
# #                 "po_number": order_row["po_number"],
# #                 "material": order_row["material"],
# #                 "version": order_row["version"],
# #                 "batch": order_row["batch"],
# #                 "quantity": float(order_row["quantity"]) if order_row["quantity"] is not None else None,
# #                 "unit": order_row["unit"],
# #                 "plant": order_row["plant"],
# #                 "confirmed_qty": float(order_row["confirmed_qty"]) if order_row["confirmed_qty"] is not None else None,
# #                 "material_desc": order_row["material_desc"],
# #                 "status": order_row["status"],
# #                 "created_at": order_row["created_at"].isoformat() if order_row["created_at"] else None,
# #             }
# #         }), 200


# # @process_orders_bp.get("/process_orders/test-sap")
# # def test_sap_connection_endpoint():
# #     """
# #     Test SAP API connection.
# #     Returns connection status and basic info.
# #     """
# #     try:
# #         is_connected = test_sap_connection()
# #         return jsonify({
# #             "connected": is_connected,
# #             "message": "SAP connection test completed",
# #             "timestamp": datetime.now().isoformat()
# #         }), 200
# #     except Exception as e:
# #         return jsonify({
# #             "connected": False,
# #             "error": str(e),
# #             "message": "SAP connection test failed",
# #             "timestamp": datetime.now().isoformat()
# #         }), 500


# # # (Optional) claim a specific process order by id (supervisor override)
# # @process_orders_bp.post("/process_orders/<int:po_id>/claim")
# # def claim_specific_process_order(po_id: int):
# #     """
# #     Claim a specific process order by id, then ensure an 'orders' row exists.
# #     Returns both records.
# #     """
# #     with postgres_engine.connect() as conn:
# #         claimed = conn.execute(text("""
# #             UPDATE process_orders
# #             SET status = 'InProgress', updated_at = NOW()
# #             WHERE id = :id AND status IN ('Open','Pending')
# #             RETURNING id, order_id, material, version, batch, quantity, unit, status, priority, plant, confirmed_qty, material_desc, created_at
# #         """), {"id": po_id}).mappings().first()

# #         if not claimed:
# #             conn.rollback()
# #             return jsonify({"error": "Order not claimable (not found or already in progress)"}), 409

# #         order_row = _ensure_order_from_po(conn, claimed.id)

# #         conn.commit()

# #         return jsonify({
# #             "claimed_process_order": _row_to_api(claimed),
# #             "execution_order": {
# #                 "id": order_row["id"],
# #                 "po_number": order_row["po_number"],
# #                 "material": order_row["material"],
# #                 "version": order_row["version"],
# #                 "batch": order_row["batch"],
# #                 "quantity": float(order_row["quantity"]) if order_row["quantity"] is not None else None,
# #                 "unit": order_row["unit"],
# #                 "plant": order_row["plant"],
# #                 "confirmed_qty": float(order_row["confirmed_qty"]) if order_row["confirmed_qty"] is not None else None,
# #                 "material_desc": order_row["material_desc"],
# #                 "status": order_row["status"],
# #                 "created_at": order_row["created_at"].isoformat() if order_row["created_at"] else None,
# #             }
# #         }), 200


# # @process_orders_bp.post("/process_orders/<int:po_id>/validate")
# # def validate_process_order(po_id: int):
# #     """
# #     Validate a process order and store the result in the orders table.
# #     Body:
# #       { 
# #         "status": "Validated" | "Rejected", 
# #         "remarks": "validation notes",
# #         "confirmed_text": "confirmation text",
# #         "scrap": "scrap quantity",
# #         "confirmed_qty": "confirmed quantity (allows partial confirmation)"
# #       }
# #     """
# #     payload = request.get_json(silent=True) or {}
# #     status = payload.get("status")
# #     remarks = payload.get("remarks", "")
# #     confirmed_text = payload.get("confirmed_text")
# #     scrap = payload.get("scrap")
# #     confirmed_qty = payload.get("confirmed_qty")  # Allow partial confirmation
    
# #     if status not in ["Validated", "Rejected"]:
# #         return jsonify({"error": "Status must be 'Validated' or 'Rejected'"}), 400
    
# #     try:
# #         with postgres_engine.connect() as conn:
# #             # 1) Update the process_orders status
# #             # If confirmed_qty is provided, use it; otherwise keep the existing confirmed_qty
# #             update_query = """
# #                 UPDATE process_orders
# #                 SET status = :status, updated_at = NOW(), validation_method = :validation_method, 
# #                     confirmed_text = :confirmed_text, scrap = :scrap
# #             """
# #             params = {
# #                 "id": po_id, 
# #                 "status": status, 
# #                 "validation_method": "Manual",
# #                 "confirmed_text": confirmed_text,
# #                 "scrap": scrap
# #             }
            
# #             # Add confirmed_qty update if provided (allows partial confirmation)
# #             if confirmed_qty is not None:
# #                 update_query += ", confirmed_qty = :confirmed_qty"
# #                 params["confirmed_qty"] = confirmed_qty
            
# #             update_query += """
# #                 WHERE id = :id
# #                 RETURNING id, order_id, material, version, batch, quantity, unit, status, priority, plant, confirmed_qty, material_desc, created_at
# #             """
            
# #             updated_po = conn.execute(text(update_query), params).mappings().first()
            
# #             if not updated_po:
# #                 return jsonify({"error": "Process order not found"}), 404
            
# #             # 2) Store the validation result in orders table
# #             # Use the provided confirmed_qty if available, otherwise use the updated_po.confirmed_qty
# #             final_confirmed_qty = confirmed_qty if confirmed_qty is not None else updated_po.confirmed_qty
            
# #             conn.execute(text("""
# #                 INSERT INTO orders (po_number, material, version, batch, quantity, unit, plant, confirmed_qty, material_desc, status, confirmed_text, scrap, created_at, updated_at)
# #                 VALUES (:po_number, :material, :version, :batch, :quantity, :unit, :plant, :confirmed_qty, :material_desc, :status, :confirmed_text, :scrap, NOW(), NOW())
# #                 ON CONFLICT (po_number) DO UPDATE
# #                 SET material = EXCLUDED.material,
# #                     version = EXCLUDED.version,
# #                     batch = EXCLUDED.batch,
# #                     quantity = EXCLUDED.quantity,
# #                     unit = EXCLUDED.unit,
# #                     plant = EXCLUDED.plant,
# #                     confirmed_qty = EXCLUDED.confirmed_qty,
# #                     material_desc = EXCLUDED.material_desc,
# #                     status = EXCLUDED.status,
# #                     confirmed_text = EXCLUDED.confirmed_text,
# #                     scrap = EXCLUDED.scrap,
# #                     updated_at = NOW()
# #             """), {
# #                 "po_number": updated_po.order_id,
# #                 "material": updated_po.material,
# #                 "version": updated_po.version,
# #                 "batch": updated_po.batch,
# #                 "quantity": updated_po.quantity,
# #                 "unit": updated_po.unit,
# #                 "plant": updated_po.plant,
# #                 "confirmed_qty": final_confirmed_qty,
# #                 "material_desc": updated_po.material_desc,
# #                 "status": status,
# #                 "confirmed_text": confirmed_text,
# #                 "scrap": scrap
# #             })
            
# #             conn.commit()
            
# #             # Check if this is a partial confirmation
# #             is_partial = confirmed_qty is not None and confirmed_qty != updated_po.quantity
# #             partial_info = ""
# #             if is_partial:
# #                 partial_info = f" (Partial: {final_confirmed_qty}/{updated_po.quantity} {updated_po.unit})"
            
# #             return jsonify({
# #                 "message": f"Order {updated_po.order_id} {status.lower()} successfully{partial_info}",
# #                 "process_order": _row_to_api(updated_po),
# #                 "status": status,
# #                 "remarks": remarks,
# #                 "confirmed_text": confirmed_text,
# #                 "scrap": scrap,
# #                 "is_partial_confirmation": is_partial,
# #                 "partial_info": {
# #                     "confirmed_qty": final_confirmed_qty,
# #                     "total_qty": updated_po.quantity,
# #                     "unit": updated_po.unit,
# #                     "completion_percentage": round((final_confirmed_qty / updated_po.quantity) * 100, 2) if updated_po.quantity > 0 else 0
# #                 } if is_partial else None
# #             }), 200
            
# #     except Exception as e:
# #         return jsonify({"error": f"Validation failed: {str(e)}"}), 500

# # def get_shift_manual_used(conn, process_order_id, shift_letter):
# #     """
# #     Returns total manually confirmed weight for a specific order + shift.
# #     """
# #     rows = conn.execute(text("""
# #         SELECT COALESCE(SUM(confirmed_weight), 0) AS total
# #         FROM manual_confirmations
# #         WHERE process_order_id = :oid
# #           AND shift_code = :shift
# #           AND synced_to_sap = TRUE
# #     """), {
# #         "oid": process_order_id,
# #         "shift": shift_letter.upper()
# #     }).mappings().first()

# #     return float(rows.total or 0)
# # # @process_orders_bp.post("/process_orders/push-confirmation")
# # # def push_confirmation():
# # #     """
# # #     Clean + correct mid-shift manual + shift-end confirmation.
# # #     Fixes:
# # #       ✔ Correct WHERE clause (uses po.id instead of po.order_id)
# # #       ✔ Never duplicates manual confirmations
# # #       ✔ Prevents double-shift confirmation
# # #       ✔ Sends manual + shift-end in one single batch
# # #       ✔ Marks manual confirmations as synced safely
# # #       ✔ Updates shift flags, confirmed_shift_X, last_confirmed_qty
# # #     """
# # #     from services.system_logger import log_hercules_event
# # #     from services.sap_confirmation import confirm_orders_batch, SAPConfirmationService
# # #     import json

# # #     payload = request.get_json(silent=True) or {}
# # #     order_ids = payload.get("order_ids", [])
# # #     operator = payload.get("operator", "manual")

# # #     # Log start
# # #     try:
# # #         log_hercules_event(
# # #             action="Push Confirmation Started",
# # #             status="InProgress",
# # #             details=f"Pushing confirmations for {order_ids}",
# # #             operator=operator
# # #         )
# # #     except:
# # #         pass

# # #     try:
# # #         with postgres_engine.connect() as conn:

# # #             #---------------------------------------------------------
# # #             # 1) Load UNSYNCED manual confirmations
# # #             #---------------------------------------------------------
# # #             manual_rows = conn.execute(text("""
# # #                 SELECT mc.id manual_id,
# # #                        mc.process_order_id,
# # #                        po.order_id AS po_number,
# # #                        mc.shift_code,
# # #                        mc.confirmed_weight,
# # #                        po.material,
# # #                        po.version,
# # #                        po.material_desc,
# # #                        po.quantity as total_qty,
# # #                        po.unit as uom,
# # #                        po.plant,
# # #                        po.batch,
# # #                        po.created_at
# # #                 FROM manual_confirmations mc
# # #                 JOIN process_orders po ON po.id = mc.process_order_id
# # #                 WHERE mc.synced_to_sap = FALSE
# # #                 ORDER BY mc.id
# # #             """)).mappings().all()

# # #             manual_payloads = []
# # #             unsynced_sum = {}

# # #             for m in manual_rows:
# # #                 key = (m.process_order_id, m.shift_code.upper())
# # #                 unsynced_sum[key] = unsynced_sum.get(key, 0) + float(m.confirmed_weight)

# # #                 manual_payloads.append({
# # #                     "type": "manual",
# # #                     "manual_id": m.manual_id,
# # #                     "process_order_id": m.process_order_id,
# # #                     "po_number": m.po_number,
# # #                     "material": m.material,
# # #                     "version": m.version,
# # #                     "material_desc": m.material_desc,
# # #                     "total_qty": float(m.total_qty or 0),
# # #                     "confirmed_weight": float(m.confirmed_weight or 0),
# # #                     "uom": m.uom or "KG",
# # #                     "plant": m.plant,
# # #                     "batch": m.batch,
# # #                     "shift": m.shift_code.upper(),
# # #                     "confirmed_text": "MID-SHIFT MANUAL",
# # #                     "scrap": 0
# # #                 })

# # #             #---------------------------------------------------------
# # #             # 2) Load PROCESS ORDERS requested by frontend
# # #             #---------------------------------------------------------
# # #             if not order_ids:
# # #                 return jsonify({
# # #                     "message": "No orders selected",
# # #                     "successful_count": 0,
# # #                     "failed_count": 0,
# # #                     "results": []
# # #                 }), 200

# # #             placeholders = ", ".join([f":id{i}" for i in range(len(order_ids))])
# # #             params = {f"id{i}": int(oid) for i, oid in enumerate(order_ids)}

# # #             auto_rows = conn.execute(text(f"""
# # #                 SELECT  po.id AS pid,
# # #                         po.order_id AS po_number,
# # #                         po.material,
# # #                         po.version,
# # #                         po.material_desc,
# # #                         po.quantity AS total_qty,
# # #                         po.unit AS uom,
# # #                         po.plant,
# # #                         po.batch,
# # #                         po.created_at,
# # #                         po.last_confirmed_qty,
# # #                         po.current_shift,
# # #                         po.weight_shift_a,
# # #                         po.weight_shift_b,
# # #                         po.weight_shift_c,
# # #                         po.confirmed_shift_a,
# # #                         po.confirmed_shift_b,
# # #                         po.confirmed_shift_c,
# # #                         po.is_final_sent
# # #                 FROM process_orders po
# # #                 WHERE po.id IN ({placeholders})
# # #                   AND po.status IN ('Validated','InProgress')
# # #             """), params).mappings().all()

# # #             #---------------------------------------------------------
# # #             # 3) Prepare SHIFT-END payloads (skip active shift)
# # #             #---------------------------------------------------------
# # #             shift_payloads = []

# # #             # Preload already-synced manual confirmations
# # #             synced_rows = conn.execute(text("""
# # #                 SELECT process_order_id, shift_code, SUM(confirmed_weight) total
# # #                 FROM manual_confirmations
# # #                 WHERE synced_to_sap = TRUE
# # #                 GROUP BY process_order_id, shift_code
# # #             """)).mappings().all()

# # #             synced_sum = {
# # #                 (r.process_order_id, r.shift_code.upper()): float(r.total or 0)
# # #                 for r in synced_rows
# # #             }

# # #             for r in auto_rows:

# # #                 if r.is_final_sent:
# # #                     continue

# # #                 shifts = [
# # #                     ("A", r.weight_shift_a, r.confirmed_shift_a),
# # #                     ("B", r.weight_shift_b, r.confirmed_shift_b),
# # #                     ("C", r.weight_shift_c, r.confirmed_shift_c),
# # #                 ]

# # #                 current_shift = (r.current_shift or "").upper()

# # #                 for letter, raw_weight, confirmed_flag in shifts:

# # #                     if letter == current_shift:
# # #                         continue  # never confirm active shift

# # #                     raw_weight = float(raw_weight or 0)
# # #                     if raw_weight <= 0:
# # #                         continue

# # #                     confirmed_flag = float(confirmed_flag or 0)
# # #                     if confirmed_flag > 0:
# # #                         continue  # already confirmed earlier

# # #                     key = (r.pid, letter)
# # #                     used_manual = synced_sum.get(key, 0) + unsynced_sum.get(key, 0)
# # #                     remaining = raw_weight - used_manual

# # #                     if remaining <= 0:
# # #                         continue

# # #                     shift_payloads.append({
# # #                         "type": "shift",
# # #                         "process_order_id": r.pid,
# # #                         "po_number": r.po_number,
# # #                         "material": r.material,
# # #                         "version": r.version,
# # #                         "material_desc": r.material_desc,
# # #                         "total_qty": float(r.total_qty),
# # #                         "confirmed_weight": float(remaining),
# # #                         "uom": r.uom,
# # #                         "plant": r.plant,
# # #                         "batch": r.batch,
# # #                         "shift": letter,
# # #                         "last_confirmed_qty": float(r.last_confirmed_qty),
# # #                     })

# # #             #---------------------------------------------------------
# # #             # NO DATA?
# # #             #---------------------------------------------------------
# # #             if not manual_payloads and not shift_payloads:
# # #                 return jsonify({
# # #                     "message": "Nothing to confirm",
# # #                     "successful_count": 0,
# # #                     "failed_count": 0,
# # #                     "results": []
# # #                 }), 200

# # #             batch_payload = manual_payloads + shift_payloads

# # #             #---------------------------------------------------------
# # #             # 4) SEND TO SAP
# # #             #---------------------------------------------------------
# # #             try:
# # #                 result = confirm_orders_batch(batch_payload, "online")
# # #             except:
# # #                 sap = SAPConfirmationService()
# # #                 result = sap.confirm_orders_batch(batch_payload, "online")

# # #             success_ids = {str(x).lstrip("0") for x in result.get("successful_orders", [])}

# # #             results = []
# # #             failed = []

# # #             #---------------------------------------------------------
# # #             # 5) MARK manual confirmations as synced
# # #             #---------------------------------------------------------
# # #             with postgres_engine.begin() as tx:

# # #                 for m in manual_payloads:
# # #                     po_norm = str(m["po_number"]).lstrip("0")

# # #                     if po_norm in success_ids:
# # #                         tx.execute(text("""
# # #                             UPDATE manual_confirmations
# # #                             SET synced_to_sap = TRUE,
# # #                                 sap_response = :resp,
# # #                                 updated_at = NOW()
# # #                             WHERE id = :mid
# # #                         """), {"mid": m["manual_id"], "resp": json.dumps({"status": "confirmed"})})

# # #                         results.append({"process_order": m["po_number"], "status": "Manual Confirmed"})
# # #                     else:
# # #                         failed.append(m["po_number"])
# # #                         results.append({"process_order": m["po_number"], "status": "Manual Failed"})

# # #                 #-----------------------------------------------------
# # #                 # 6) APPLY shift-end confirmations to DB
# # #                 #-----------------------------------------------------
# # #                 for s in shift_payloads:
# # #                     po_norm = str(s["po_number"]).lstrip("0")

# # #                     if po_norm not in success_ids:
# # #                         failed.append(s["po_number"])
# # #                         results.append({"process_order": s["po_number"], "status": "Shift Failed"})
# # #                         continue

# # #                     new_last = s["last_confirmed_qty"] + s["confirmed_weight"]
# # #                     is_final = new_last >= s["total_qty"]

# # #                     letter = s["shift"].lower()

# # #                     tx.execute(text(f"""
# # #                         UPDATE process_orders
# # #                         SET confirmed_shift_{letter} = :w,
# # #                             last_confirmed_qty = :lc,
# # #                             is_final_sent = :final,
# # #                             updated_at = NOW(),
# # #                             status = CASE WHEN :final THEN 'Confirmed' ELSE 'InProgress' END
# # #                         WHERE order_id = :po
# # #                     """), {
# # #                         "w": s["confirmed_weight"],
# # #                         "lc": new_last,
# # #                         "final": is_final,
# # #                         "po": s["po_number"]
# # #                     })

# # #                     results.append({
# # #                         "process_order": s["po_number"],
# # #                         "status": "Shift Confirmed",
# # #                         "final": is_final
# # #                     })

# # #             return jsonify({
# # #                 "message": "Push confirmation complete",
# # #                 "successful_count": len(success_ids),
# # #                 "failed_count": len(failed),
# # #                 "results": results
# # #             }), 200

# # #     except Exception as e:
# # #         return jsonify({"error": str(e)}), 500
# # @process_orders_bp.post("/process_orders/push-confirmation")
# # def push_confirmation():
# #     """
# #     ✅ FIXED: Mid-shift + shift-end confirmation with proper deduplication.
    
# #     Features:
# #       - Mid-shift: User clicks button → sends current shift production
# #       - Shift-end: Auto-scheduler → sends remaining production only
# #       - Deduplication: weight_shift_X - confirmed_shift_X = remaining
# #       - Accumulates confirmed_shift_X properly (no double-counting)
# #     """
# #     from services.system_logger import log_hercules_event
# #     from services.sap_confirmation import SAPConfirmationService
# #     import json

# #     payload = request.get_json(silent=True) or {}
# #     order_ids = payload.get("order_ids", [])
# #     operator = payload.get("operator", "manual")
# #     confirm_current_shift = payload.get("confirm_current_shift", False)  # Mid-shift flag

# #     # Log start
# #     try:
# #         log_hercules_event(
# #             action="Push Confirmation Started",
# #             status="InProgress",
# #             details=f"Pushing confirmations for {order_ids} (mid_shift={confirm_current_shift})",
# #             operator=operator
# #         )
# #     except:
# #         pass

# #     try:
# #         with postgres_engine.connect() as conn:

# #             #---------------------------------------------------------
# #             # 1) Load PROCESS ORDERS
# #             #---------------------------------------------------------
# #             if not order_ids:
# #                 return jsonify({
# #                     "message": "No orders selected",
# #                     "successful_count": 0,
# #                     "failed_count": 0,
# #                     "results": []
# #                 }), 200

# #             placeholders = ", ".join([f":id{i}" for i in range(len(order_ids))])
# #             params = {f"id{i}": int(oid) for i, oid in enumerate(order_ids)}

# #             rows = conn.execute(text(f"""
# #                 SELECT  
# #                     po.id AS pid,
# #                     po.order_id AS po_number,
# #                     po.material,
# #                     po.version,
# #                     po.material_desc,
# #                     po.quantity AS total_qty,
# #                     po.unit AS uom,
# #                     po.plant,
# #                     po.batch,
# #                     po.created_at,
# #                     po.last_confirmed_qty,
# #                     po.current_shift,
# #                     po.weight_shift_a,
# #                     po.weight_shift_b,
# #                     po.weight_shift_c,
# #                     po.confirmed_shift_a,
# #                     po.confirmed_shift_b,
# #                     po.confirmed_shift_c,
# #                     po.is_final_sent,
# #                     po.priority,
# #                     po.scale1,
# #                     po.scale1_qty,
# #                     po.scale2,
# #                     po.scale2_qty,
# #                     po.scale3,
# #                     po.scale3_qty,
# #                     po.scrap
# #                 FROM process_orders po
# #                 WHERE po.id IN ({placeholders})
# #                   AND po.status IN ('Validated','InProgress')
# #             """), params).mappings().all()

# #             #---------------------------------------------------------
# #             # 2) ✅ Build SAP payloads with proper remaining calculation
# #             #---------------------------------------------------------
# #             sap_payloads = []

# #             for r in rows:

# #                 if r.is_final_sent:
# #                     continue

# #                 shifts = [
# #                     ("A", r.weight_shift_a, r.confirmed_shift_a),
# #                     ("B", r.weight_shift_b, r.confirmed_shift_b),
# #                     ("C", r.weight_shift_c, r.confirmed_shift_c),
# #                 ]

# #                 order_current_shift = (r.current_shift or "").upper()

# #                 for shift_letter, weight_produced, weight_confirmed in shifts:

# #                     # ✅ Skip active shift UNLESS mid-shift confirmation requested
# #                     if shift_letter == order_current_shift and not confirm_current_shift:
# #                         continue

# #                     # ✅ Calculate REMAINING production for this shift
# #                     # Formula: total_produced - already_sent_to_SAP = remaining
# #                     total_produced = float(weight_produced or 0)
# #                     already_sent = float(weight_confirmed or 0)
# #                     remaining = total_produced - already_sent

# #                     if remaining <= 0:
# #                         continue  # Nothing new to confirm for this shift

# #                     # ✅ Build payload (send only REMAINING production)
# #                     # ✅ CRITICAL: Always include byproduct scales (even if order not validated)
# #                     sap_payloads.append({
# #                         "po_number": r.po_number,
# #                         "process_order_id": r.pid,
# #                         "material": r.material,
# #                         "version": r.version or "",
# #                         "material_desc": r.material_desc or "",
# #                         "total_qty": float(r.total_qty),
# #                         "confirmed_weight": float(remaining),  # ✅ Only send remaining
# #                         "uom": r.uom or "KG",
# #                         "plant": r.plant,
# #                         "created_at": r.created_at,
# #                         "batch": r.batch or "",
# #                         "shift": shift_letter,
# #                         "priority": r.priority or 1,
# #                         "last_confirmed_qty": float(r.last_confirmed_qty or 0),
# #                         "is_final_sent": False,
# #                         "order_current_shift": order_current_shift,
# #                         # ✅ CRITICAL: Always include byproduct scales (scale1, scale2, scale3 and their quantities)
# #                         # This ensures they appear in SAP payload for mid-shift and end-shift confirmations
# #                         "scale1": r.scale1 or "",
# #                         "scale1_qty": float(r.scale1_qty or 0),
# #                         "scale2": r.scale2 or "",
# #                         "scale2_qty": float(r.scale2_qty or 0),
# #                         "scale3": r.scale3 or "",
# #                         "scale3_qty": float(r.scale3_qty or 0),
# #                         "scrap": float(r.scrap or 0),
# #                     })

# #             #---------------------------------------------------------
# #             # NO DATA?
# #             #---------------------------------------------------------
# #             if not sap_payloads:
# #                 return jsonify({
# #                     "message": "Nothing to confirm",
# #                     "successful_count": 0,
# #                     "failed_count": 0,
# #                     "results": []
# #                 }), 200

# #             #---------------------------------------------------------
# #             # 3) ✅ SEND TO SAP
# #             #---------------------------------------------------------
# #             sap_service = SAPConfirmationService()
# #             result = sap_service.confirm_orders_batch(sap_payloads, "auto")

# #             success_ids = {str(x).lstrip("0") for x in result.get("successful_orders", [])}
# #             results = []
# #             failed = []

# #             #---------------------------------------------------------
# #             # 4) ✅ FIXED: Update database after SAP success
# #             #---------------------------------------------------------
# #             with postgres_engine.begin() as tx:

# #                 for payload in sap_payloads:
# #                     po_norm = str(payload["po_number"]).lstrip("0")

# #                     if po_norm not in success_ids:
# #                         failed.append(payload["po_number"])
# #                         results.append({
# #                             "process_order": payload["po_number"],
# #                             "status": "Failed",
# #                             "shift": payload["shift"]
# #                         })
# #                         continue

# #                     confirmed_weight = payload["confirmed_weight"]
# #                     shift_letter = payload["shift"].lower()

# #                     # ✅ CRITICAL FIX: ADD to confirmed_shift_X (accumulate, don't replace)
# #                     # This tracks cumulative confirmed weight for deduplication
# #                     tx.execute(text(f"""
# #                         UPDATE process_orders
# #                         SET confirmed_shift_{shift_letter} = COALESCE(confirmed_shift_{shift_letter}, 0) + :w,
# #                             updated_at = NOW()
# #                         WHERE id = :pid
# #                     """), {
# #                         "w": confirmed_weight,  # ✅ Add only what was just confirmed
# #                         "pid": payload["process_order_id"]
# #                     })

# #                     conf_type = "Mid-Shift Confirmed" if payload["shift"] == payload["order_current_shift"] else "Shift-End Confirmed"
                    
# #                     results.append({
# #                         "process_order": payload["po_number"],
# #                         "status": conf_type,
# #                         "confirmed_weight": confirmed_weight,
# #                         "shift": payload["shift"],
# #                     })

# #             return jsonify({
# #                 "message": "Push confirmation complete",
# #                 "successful_count": len(success_ids),
# #                 "failed_count": len(failed),
# #                 "results": results
# #             }), 200

# #     except Exception as e:
# #         return jsonify({"error": str(e)}), 500


# # @process_orders_bp.post("/process_orders/test-confirmation")
# # def test_confirmation():
# #     """
# #     Temporary API for testing:
# #     - Builds SAP payload using existing SAPConfirmationService
# #     - Does NOT send to SAP
# #     - Stores payload in sap_confirmation_test table
# #     - Returns the generated payloads for debugging
# #     """
# #     from services.sap_confirmation import SAPConfirmationService

# #     try:
# #         with postgres_engine.connect() as conn:

# #             # ----------------------------------------------------
# #             # 🔥 DEBUG INFORMATION (to verify DB connection)
# #             # ----------------------------------------------------
# #             db_info = conn.execute(text("SELECT current_database()")).scalar()
# #             print("🔍 Connected DB:", db_info)

# #             count = conn.execute(text("SELECT COUNT(*) FROM process_orders")).scalar()
# #             print("🔍 process_orders count:", count)

# #             statuses = conn.execute(text("SELECT DISTINCT status FROM process_orders")).fetchall()
# #             print("🔍 statuses:", statuses)

# #             # ----------------------------------------------------
# #             # 1) Fetch orders that are Validated or InProgress
# #             # ----------------------------------------------------
# #             rows = conn.execute(text("""
# #                 SELECT 
# #                     order_id as po_number,
# #                     material,
# #                     version,
# #                     material_desc,
# #                     quantity as total_qty,
# #                     confirmed_qty,
# #                     unit as uom,
# #                     plant,
# #                     created_at,
# #                     updated_at as confirmed_at,
# #                     batch,
# #                     priority as shift,
# #                     confirmed_text,
# #                     scrap,
# #                     scale1,
# #                     scale1_qty,
# #                     scale2,
# #                     scale2_qty,
# #                     scale3,
# #                     scale3_qty
# #                 FROM process_orders
# #                 WHERE status IN ('Validated', 'InProgress')
# #                 ORDER BY id
# #             """)).mappings().all()

# #             print("🔍 rows fetched:", len(rows))

# #             if not rows:
# #                 return jsonify({
# #                     "message": "No validated or in-progress orders found",
# #                     "debug": {
# #                         "connected_db": db_info,
# #                         "process_orders_count": count,
# #                         "statuses": [s[0] for s in statuses]
# #                     }
# #                 }), 200

# #             # ----------------------------------------------------
# #             # 2) Convert DB rows → SAP service payload structure
# #             # ----------------------------------------------------
# #             orders = []
# #             for r in rows:
# #                 orders.append({
# #                     "po_number": r.po_number,
# #                     "material": r.material,
# #                     "version": r.version or "",
# #                     "material_desc": r.material_desc or "",
# #                     "total_qty": float(r.total_qty or 0),
# #                     "confirmed_weight": float(r.confirmed_qty or 0),
# #                     "uom": r.uom or "KG",
# #                     "plant": r.plant,
# #                     "created_at": r.created_at,
# #                     "confirmed_at": r.confirmed_at,
# #                     "batch": r.batch or "",
# #                     "shift": "A",  # simple for testing
# #                     "confirmed_text": r.confirmed_text or "",
# #                     "scrap": float(r.scrap or 0),
# #                     "scale1": r.scale1 or "",
# #                     "scale1_qty": float(r.scale1_qty or 0),
# #                     "scale2": r.scale2 or "",
# #                     "scale2_qty": float(r.scale2_qty or 0),
# #                     "scale3": r.scale3 or "",
# #                     "scale3_qty": float(r.scale3_qty or 0),
# #                 })

# #             print("🔍 Converted orders:", len(orders))

# #             # ----------------------------------------------------
# #             # 3) Build SAP JSON payloads
# #             # ----------------------------------------------------
# #             sap = SAPConfirmationService()
# #             payloads = sap._convert_to_json_format(orders, "online")

# #             print("🔍 Payloads generated:", len(payloads))

# #             # ----------------------------------------------------
# #             # 4) Store payloads into sap_confirmation_test table
# #             # ----------------------------------------------------
# #             for p in payloads:
# #                 conn.execute(text("""
# #                     INSERT INTO sap_confirmation_test (po_number, payload, confirmation_type)
# #                     VALUES (:po, :payload, 'online')
# #                 """), {
# #                     "po": p.get("PROCESS_ORDER"),
# #                     "payload": json.dumps(p)
# #                 })

# #             conn.commit()

# #             # ----------------------------------------------------
# #             # 5) Final response
# #             # ----------------------------------------------------
# #             return jsonify({
# #                 "message": "Test payloads generated (not sent to SAP)",
# #                 "count": len(payloads),
# #                 "payloads": payloads,
# #                 "debug": {
# #                     "connected_db": db_info,
# #                     "process_orders_count": count,
# #                     "statuses": [s[0] for s in statuses]
# #                 }
# #             }), 200

# #     except Exception as e:
# #         print("❌ ERROR:", e)
# #         return jsonify({"error": f"Failed: {str(e)}"}), 500

# # @process_orders_bp.post("/process_orders/manual-confirm")
# # def manual_confirm():
# #     from database import PostgresSessionLocal
# #     from models.process_order_pg import ProcessOrderPG
# #     from models.manual_confirmation import ManualConfirmation  # create this model

# #     data = request.get_json(silent=True) or {}
# #     po_number = data.get("po_number")
# #     shift = data.get("shift")
# #     weight = data.get("weight")
# #     operator = data.get("operator", "manual")

# #     if not po_number or not shift or weight is None:
# #         return jsonify({"error": "po_number, shift, and weight are required"}), 400

# #     db = PostgresSessionLocal()

# #     try:
# #         order = db.query(ProcessOrderPG).filter(
# #             ProcessOrderPG.order_id == po_number
# #         ).first()

# #         if not order:
# #             return jsonify({"error": f"Order {po_number} not found"}), 404

# #         entry = ManualConfirmation(
# #             process_order_id=order.id,
# #             shift_code=shift.upper(),
# #             confirmed_weight=float(weight),
# #             synced_to_sap=False,
# #             created_by=operator
# #         )

# #         db.add(entry)
# #         db.commit()
# #         db.refresh(entry)

# #         return jsonify({
# #             "success": True,
# #             "message": "Manual confirmation stored",
# #             "id": entry.id
# #         })

# #     except Exception as e:
# #         db.rollback()
# #         return jsonify({"error": str(e)}), 500
# #     finally:
# #         db.close()

# # # backend/routes/process_orders.py
# # # backend/routes/process_orders.py (around line 1200-1260)
# # # Line 1201 - FIXED
# # # backend/routes/process_orders.py
# # # backend/routes/process_orders.py
# # # backend/routes/process_orders.py


# # @process_orders_bp.route("/process_orders/<string:orderid>/offline-confirm", methods=["POST", "OPTIONS"])
# # def offline_manual_confirmation(orderid: str):
# #     if request.method == "OPTIONS":
# #         return jsonify(ok=True), 200

# #     from services.sap_confirmation import SAPConfirmationService

# #     data = request.get_json() or {}
# #     scrap = float(data.get("scrap", 0.0))
# #     confirmed_text = data.get("confirmed_text", "")

# #     try:
# #         with PostgresSessionLocal() as db:
# #             order_result = db.execute(
# #                 text("SELECT * FROM process_orders WHERE order_id = :orderid"), 
# #                 {"orderid": orderid}
# #             ).mappings().first()

# #             if order_result is None:
# #                 return jsonify(error=f"Order {orderid} not found"), 404

# #             # ✅ CRITICAL: Convert Row to dict for easier access
# #             # Using .mappings() returns a dict-like Row object
# #             order = dict(order_result)
            
# #             # ✅ CRITICAL: Get current confirmed_qty from database
# #             confirmed_qty = float(order.get('confirmed_qty') or order.get('confirmedqty') or 0)
            
# #             # ✅ CRITICAL: If confirmed_qty is 0 but there's production (delta showing 200kg),
# #             # we need to calculate it from shift weights or current production
# #             # Check if order has shift weights that indicate production
# #             weight_shift_a = float(order.get('weight_shift_a') or 0)
# #             weight_shift_b = float(order.get('weight_shift_b') or 0)
# #             weight_shift_c = float(order.get('weight_shift_c') or 0)
# #             shift_weights_sum = weight_shift_a + weight_shift_b + weight_shift_c
            
# #             # ✅ CRITICAL: If confirmed_qty is 0 but shift weights show production, use shift weights
# #             if confirmed_qty == 0.0 and shift_weights_sum > 0.0:
# #                 confirmed_qty = shift_weights_sum
# #                 print(f"📊 [ManualConfirm-{orderid}] confirmed_qty was 0, but shift weights show {shift_weights_sum:.2f} - using shift weights")
            
# #             # ✅ CRITICAL: Also check if there's a current_shift weight that should be used
# #             current_shift = (order.get('current_shift') or 'A').upper()
# #             current_shift_weight_field = f"weight_shift_{current_shift.lower()}"
# #             current_shift_weight = float(order.get(current_shift_weight_field) or 0)
            
# #             # ✅ CRITICAL: If confirmed_qty is still 0 but current shift has weight, use it
# #             if confirmed_qty == 0.0 and current_shift_weight > 0.0:
# #                 confirmed_qty = current_shift_weight
# #                 print(f"📊 [ManualConfirm-{orderid}] confirmed_qty was 0, but current shift ({current_shift}) weight shows {current_shift_weight:.2f} - using current shift weight")

# #             # Build SAP payload in the format expected by confirm_offline
# #             # The method expects lowercase field names that match the order structure
# #             sappayload = {
# #                 "po_number": order.get('order_id') or order.get('orderid'),
# #                 "material": order.get('material'),
# #                 "version": order.get('version') or '',
# #                 "material_desc": order.get('material_desc') or '',
# #                 "total_qty": float(order.get('quantity') or 0),
# #                 "confirmed_weight": confirmed_qty,  # Full confirmed qty, no minus scrap
# #                 "uom": order.get('unit') or order.get('uom') or 'KG',
# #                 "plant": order.get('plant') or '',
# #                 "batch": order.get('batch') or '',
# #                 "created_at": order.get('created_at') or datetime.now(),
# #                 "confirmed_text": confirmed_text,  # For offline confirmation
# #                 "scrap": scrap,  # For offline confirmation
# #                 "scale1": order.get('scale1') or '',
# #                 "scale1_qty": float(order.get('scale1_qty') or 0),
# #                 "scale2": order.get('scale2') or '',
# #                 "scale2_qty": float(order.get('scale2_qty') or 0),
# #                 "scale3": order.get('scale3') or '',
# #                 "scale3_qty": float(order.get('scale3_qty') or 0),
# #                 "last_confirmed_qty": float(order.get('last_confirmed_qty') or 0),
# #                 "is_final_sent": bool(order.get('is_final_sent') or False),
# #             }

# #             sapservice = SAPConfirmationService()
# #             sapresult = sapservice.confirm_offline([sappayload])

# #             # ✅ CRITICAL: Update order with scrap, confirmed_text, validation method, AND confirmed_qty
# #             # ⚠️ IMPORTANT: Do NOT change status - just send confirmation to SAP, keep order as InProgress
# #             # This ensures confirmed_qty is preserved even if it was calculated from shift weights
# #             update_sql = text("""
# #                 UPDATE process_orders
# #                 SET scrap = :scrap,
# #                     confirmed_text = :confirmed_text,
# #                     validation_method = 'Manual Offline',
# #                     confirmed_qty = :confirmed_qty,
# #                     updated_at = NOW()
# #                 WHERE order_id = :orderid
# #             """)
# #             db.execute(update_sql, {
# #                 "scrap": scrap,
# #                 "confirmed_text": confirmed_text,
# #                 "confirmed_qty": confirmed_qty,
# #                 "orderid": orderid
# #             })
# #             db.commit()

# #             return jsonify(
# #                 success=True,
# #                 message=sapresult.get("message", "Offline confirmation sent to SAP successfully."),
# #                 orderid=orderid,
# #                 confirmedqty=confirmed_qty,
# #                 scrap=scrap,
# #                 confirmed_text=confirmed_text
# #             ), 200

# #     except Exception as ex:
# #         import traceback
# #         error_trace = traceback.format_exc()
# #         print(f"❌ [ManualConfirm-{orderid}] Error: {str(ex)}")
# #         print(f"❌ [ManualConfirm-{orderid}] Traceback: {error_trace}")
# #         return jsonify(error=f"Internal server error: {str(ex)}"), 500
# # routes/process_orders.py
# from __future__ import annotations

# from typing import List, Dict, Any, Optional, Tuple
# from flask import Blueprint, jsonify, request, abort
# from sqlalchemy import text
# from datetime import datetime, timedelta

# from database import postgres_engine, PostgresSessionLocal
# from services.process_order_sync import sync_process_orders           # legacy/internal sync (optional)
# from services.process_order_pull import pull_from_sap_once, test_sap_connection
# from utils.shifts import get_current_shift
# import json  # shared SAP -> Hercules pull
# from models.manual_confirmation import ManualConfirmation


# process_orders_bp = Blueprint("process_orders", __name__, url_prefix="/api")

# # -------------------------------------------------------------------
# # Helpers
# # -------------------------------------------------------------------

# def _row_to_api(row) -> dict:
#     """Map DB row -> API shape (doc-aligned)."""
#     return {
#         "id": row.id,
#         "po_number": row.order_id,  # order_id is the PO number from SAP
#         "material": row.material,
#         "version": row.version,
#         "batch": row.batch,
#         "quantity": float(row.quantity) if row.quantity is not None else None,
#         "unit": row.unit,
#         "status": row.status,
#         "priority": row.priority,
#         "plant": getattr(row, 'plant', None),
#         "confirmed_qty": float(row.confirmed_qty) if hasattr(row, 'confirmed_qty') and row.confirmed_qty is not None else None,
#         "last_confirmed_qty": float(row.last_confirmed_qty) if hasattr(row, 'last_confirmed_qty') and row.last_confirmed_qty is not None else 0.0,
#         "material_desc": getattr(row, 'material_desc', None),
#         "expected_weight": float(row.expected_weight) if hasattr(row, 'expected_weight') and row.expected_weight is not None else None,
#         "created_at": row.created_at.isoformat() if row.created_at else None,
#         "order_type": getattr(row, 'order_type', None),  # Add order_type field
#     }

# def _queue_where_clause(statuses: Optional[List[str]] = None) -> Tuple[str, Dict[str, Any]]:
#     """
#     Build WHERE for queue. By default we queue only 'Open' or 'Pending'.
#     """
#     params: Dict[str, Any] = {}
#     if not statuses:
#         statuses = ["Open", "Pending"]
#     placeholders = ", ".join([f":s{i}" for i, _ in enumerate(statuses)])
#     for i, s in enumerate(statuses):
#         params[f"s{i}"] = s
#     where_sql = f" WHERE status IN ({placeholders})"
#     return where_sql, params

# def _queue_order_by_clause() -> str:
#     """
#     Priority first (ascending: smaller number = higher priority),
#     then FIFO by created_at (oldest first), finally by id to break ties.
#     """
#     return " ORDER BY priority ASC, created_at ASC NULLS LAST, id ASC "


# def _ensure_order_from_po(conn, po_row_id: int) -> dict | None:
#     """
#     Create (or ensure) an 'orders' row from a claimed process_orders row.
#     Returns the upserted order as a mapping (dict-like).
#     """
#     # 1) fetch the claimed process order row
#     po = conn.execute(text("""
#         SELECT order_id, material, version, batch, quantity, unit, plant, confirmed_qty, material_desc
#         FROM process_orders
#         WHERE id = :id
#     """), {"id": po_row_id}).mappings().first()
#     if not po:
#         return None

#     # 2) UPSERT into orders using po_number as unique key
#     conn.execute(text("""
#         INSERT INTO orders (po_number, material, version, batch, quantity, unit, plant, confirmed_qty, material_desc, status, created_at, updated_at)
#         VALUES (:po_number, :material, :version, :batch, :quantity, :unit, :plant, :confirmed_qty, :material_desc, 'Pending', NOW(), NOW())
#         ON CONFLICT (po_number) DO UPDATE
#         SET material      = EXCLUDED.material,
#             version       = EXCLUDED.version,
#             batch         = EXCLUDED.batch,
#             quantity      = EXCLUDED.quantity,
#             unit          = EXCLUDED.unit,
#             plant         = EXCLUDED.plant,
#             confirmed_qty = EXCLUDED.confirmed_qty,
#             material_desc = EXCLUDED.material_desc,
#             updated_at    = NOW()
#     """), {
#         "po_number": po.order_id,
#         "material":  po.material,
#         "version":   po.version,
#         "batch":     po.batch,
#         "quantity":  po.quantity,
#         "unit":      po.unit or "KG",
#         "plant":     po.plant,
#         "confirmed_qty": po.confirmed_qty,
#         "material_desc": po.material_desc,
#     })

#     # 3) return the orders row
#     order = conn.execute(text("""
#         SELECT id, po_number, material, version, batch, quantity, unit, plant, confirmed_qty, material_desc, status, created_at, updated_at
#         FROM orders
#         WHERE po_number = :po
#     """), {"po": po.order_id}).mappings().first()
#     return order

# # -------------------------------------------------------------------
# # Routes
# # -------------------------------------------------------------------

# @process_orders_bp.get("/process_orders")
# def list_process_orders():
#     """
#     List process orders (doc-aligned fields only).

#     Query params:
#       - status: filter by status (e.g., Open, Pending, Validated, Rejected)
#       - limit: page size (default 50)
#       - offset: page offset (default 0)
#     """
#     status = request.args.get("status")
#     try:
#         limit = int(request.args.get("limit", 50))
#         offset = int(request.args.get("offset", 0))
#     except ValueError:
#         limit, offset = 50, 0

#     base_sql = """
#       SELECT
#         id,
#         order_id,
#         material,
#         version,
#         batch,
#         quantity,
#         unit,
#         status,
#         priority,
#         plant,
#         confirmed_qty,
#         material_desc,
#         expected_weight,
#         created_at,
#         order_type
#       FROM process_orders
#     """

#     params = {"limit": limit, "offset": offset}
#     where_sql = ""
#     if status and status != "All":
#         where_sql = " WHERE status = :status"
#         params["status"] = status

#     sql = (
#         base_sql
#         + where_sql
#         + " ORDER BY created_at DESC NULLS LAST LIMIT :limit OFFSET :offset"
#     )

#     try:
#         with postgres_engine.connect() as conn:
#             rows = conn.execute(text(sql), params).mappings().all()
#         return jsonify([_row_to_api(r) for r in rows]), 200
#     except Exception as e:
#         # Dev-only fallback; remove in production
#         print(f"[process_orders] list error: {e}")
#         sample = [{
#             "id": 1,
#             "po_number": "PO-001",
#             "material": "1300005",
#             "version": "BKF1",
#             "batch": "BATCH-001",
#             "quantity": 1000.0,
#             "unit": "KG",
#             "status": "Open",
#             "priority": 1,
#             "created_at": (datetime.now() - timedelta(days=1)).isoformat(),
#         }]
#         return jsonify(sample), 200


# @process_orders_bp.post("/process_orders/pull")
# def pull_process_orders_from_sap():
#     """
#     Manual 'Pull New Orders' (SAP -> Hercules):
#     - Fetch open POs from SAP using the shared service
#     - Upsert by order_id (po_number)
#     """
#     try:
#         count = pull_from_sap_once()
#         return jsonify({"message": f"Pulled {count} orders from SAP"}), 200
#     except Exception as e:
#         return jsonify({"error": f"Pull failed: {str(e)}"}), 500


# @process_orders_bp.post("/process_orders/sync")
# def sync_process_orders_endpoint():
#     """
#     Optional legacy/internal sync (e.g., SQL Server -> Postgres).
#     Keep if still in use alongside SAP Pull; otherwise safe to remove later.
#     """
#     try:
#         success = sync_process_orders()
#         if success:
#             return jsonify({"message": "Process orders synced successfully"}), 200
#         return jsonify({"error": "Failed to sync process orders"}), 500
#     except Exception as e:
#         return jsonify({"error": f"Sync failed: {str(e)}"}), 500


# # -------------------------------
# # FIFO queue (priority → FIFO)
# # -------------------------------

# @process_orders_bp.get("/process_orders/queue")
# def list_process_orders_queue():
#     """
#     Returns the execution queue already sorted:
#     - priority ASC
#     - created_at ASC (FIFO)
#     - id ASC (tie-breaker)

#     Query params:
#       - limit (default 50)
#       - statuses CSV (default: Open,Pending) e.g. ?statuses=Open,Pending,Validated
#     """
#     try:
#         limit = int(request.args.get("limit", 50))
#     except ValueError:
#         limit = 50

#     statuses_param = request.args.get("statuses")
#     statuses = [s.strip() for s in statuses_param.split(",")] if statuses_param else None

#     base_sql = """
#       SELECT
#         id,
#         order_id,
#         material,
#         version,
#         batch,
#         quantity,
#         unit,
#         status,
#         priority,
#         plant,
#         confirmed_qty,
#         material_desc,
#         expected_weight,
#         created_at
#       FROM process_orders
#     """

#     where_sql, params = _queue_where_clause(statuses)
#     sql = base_sql + where_sql + _queue_order_by_clause() + " LIMIT :limit"
#     params["limit"] = limit

#     with postgres_engine.connect() as conn:
#         rows = conn.execute(text(sql), params).mappings().all()
#     return jsonify([_row_to_api(r) for r in rows]), 200


# @process_orders_bp.post("/process_orders/next")
# def claim_next_process_order():
#     """
#     Returns the 'next' order by (priority → FIFO). If claim=true:
#       1) atomically set process_orders.status='InProgress'
#       2) upsert into orders (po_number unique) with status 'Pending'
#       3) return both the claimed process order and the execution order
#     Body (optional):
#       { "claim": true }
#     """
#     payload = request.get_json(silent=True) or {}
#     claim = bool(payload.get("claim", False))

#     select_sql = """
#       SELECT id, order_id, material, version, batch, quantity, unit, status, priority, plant, confirmed_qty, material_desc, created_at
#       FROM process_orders
#       WHERE status IN ('Open', 'Pending')
#     """ + _queue_order_by_clause() + " LIMIT 1"

#     with postgres_engine.connect() as conn:
#         row = conn.execute(text(select_sql)).mappings().first()
#         if not row:
#             return jsonify({"message": "No eligible orders found"}), 200

#         if not claim:
#             return jsonify(_row_to_api(row)), 200

#         # 1) claim the process order (atomic)
#         claimed = conn.execute(text("""
#             UPDATE process_orders
#             SET status = 'InProgress', updated_at = NOW()
#             WHERE id = :id AND status IN ('Open','Pending')
#             RETURNING id, order_id, material, version, batch, quantity, unit, status, priority, plant, confirmed_qty, material_desc, created_at
#         """), {"id": row.id}).mappings().first()
#         if not claimed:
#             conn.rollback()
#             abort(409, description="Order already claimed by another worker")

#         # 2) ensure an execution order exists (orders table)
#         order_row = _ensure_order_from_po(conn, claimed.id)

#         conn.commit()

#         return jsonify({
#             "claimed_process_order": _row_to_api(claimed),
#             "execution_order": {
#                 "id": order_row["id"],
#                 "po_number": order_row["po_number"],
#                 "material": order_row["material"],
#                 "version": order_row["version"],
#                 "batch": order_row["batch"],
#                 "quantity": float(order_row["quantity"]) if order_row["quantity"] is not None else None,
#                 "unit": order_row["unit"],
#                 "plant": order_row["plant"],
#                 "confirmed_qty": float(order_row["confirmed_qty"]) if order_row["confirmed_qty"] is not None else None,
#                 "material_desc": order_row["material_desc"],
#                 "status": order_row["status"],
#                 "created_at": order_row["created_at"].isoformat() if order_row["created_at"] else None,
#             }
#         }), 200


# @process_orders_bp.get("/process_orders/test-sap")
# def test_sap_connection_endpoint():
#     """
#     Test SAP API connection.
#     Returns connection status and basic info.
#     """
#     try:
#         is_connected = test_sap_connection()
#         return jsonify({
#             "connected": is_connected,
#             "message": "SAP connection test completed",
#             "timestamp": datetime.now().isoformat()
#         }), 200
#     except Exception as e:
#         return jsonify({
#             "connected": False,
#             "error": str(e),
#             "message": "SAP connection test failed",
#             "timestamp": datetime.now().isoformat()
#         }), 500


# # (Optional) claim a specific process order by id (supervisor override)
# @process_orders_bp.post("/process_orders/<int:po_id>/claim")
# def claim_specific_process_order(po_id: int):
#     """
#     Claim a specific process order by id, then ensure an 'orders' row exists.
#     Returns both records.
#     """
#     with postgres_engine.connect() as conn:
#         claimed = conn.execute(text("""
#             UPDATE process_orders
#             SET status = 'InProgress', updated_at = NOW()
#             WHERE id = :id AND status IN ('Open','Pending')
#             RETURNING id, order_id, material, version, batch, quantity, unit, status, priority, plant, confirmed_qty, material_desc, created_at
#         """), {"id": po_id}).mappings().first()

#         if not claimed:
#             conn.rollback()
#             return jsonify({"error": "Order not claimable (not found or already in progress)"}), 409

#         order_row = _ensure_order_from_po(conn, claimed.id)

#         conn.commit()

#         return jsonify({
#             "claimed_process_order": _row_to_api(claimed),
#             "execution_order": {
#                 "id": order_row["id"],
#                 "po_number": order_row["po_number"],
#                 "material": order_row["material"],
#                 "version": order_row["version"],
#                 "batch": order_row["batch"],
#                 "quantity": float(order_row["quantity"]) if order_row["quantity"] is not None else None,
#                 "unit": order_row["unit"],
#                 "plant": order_row["plant"],
#                 "confirmed_qty": float(order_row["confirmed_qty"]) if order_row["confirmed_qty"] is not None else None,
#                 "material_desc": order_row["material_desc"],
#                 "status": order_row["status"],
#                 "created_at": order_row["created_at"].isoformat() if order_row["created_at"] else None,
#             }
#         }), 200


# @process_orders_bp.post("/process_orders/<int:po_id>/validate")
# def validate_process_order(po_id: int):
#     """
#     Validate a process order and store the result in the orders table.
#     Body:
#       { 
#         "status": "Validated" | "Rejected", 
#         "remarks": "validation notes",
#         "confirmed_text": "confirmation text",
#         "scrap": "scrap quantity",
#         "confirmed_qty": "confirmed quantity (allows partial confirmation)"
#       }
#     """
#     payload = request.get_json(silent=True) or {}
#     status = payload.get("status")
#     remarks = payload.get("remarks", "")
#     confirmed_text = payload.get("confirmed_text")
#     scrap = payload.get("scrap")
#     confirmed_qty = payload.get("confirmed_qty")  # Allow partial confirmation
    
#     if status not in ["Validated", "Rejected"]:
#         return jsonify({"error": "Status must be 'Validated' or 'Rejected'"}), 400
    
#     try:
#         with postgres_engine.connect() as conn:
#             # 1) Update the process_orders status
#             # If confirmed_qty is provided, use it; otherwise keep the existing confirmed_qty
#             update_query = """
#                 UPDATE process_orders
#                 SET status = :status, updated_at = NOW(), validation_method = :validation_method, 
#                     confirmed_text = :confirmed_text, scrap = :scrap
#             """
#             params = {
#                 "id": po_id, 
#                 "status": status, 
#                 "validation_method": "Manual",
#                 "confirmed_text": confirmed_text,
#                 "scrap": scrap
#             }
            
#             # Add confirmed_qty update if provided (allows partial confirmation)
#             if confirmed_qty is not None:
#                 update_query += ", confirmed_qty = :confirmed_qty"
#                 params["confirmed_qty"] = confirmed_qty
            
#             update_query += """
#                 WHERE id = :id
#                 RETURNING id, order_id, material, version, batch, quantity, unit, status, priority, plant, confirmed_qty, material_desc, created_at
#             """
            
#             updated_po = conn.execute(text(update_query), params).mappings().first()
            
#             if not updated_po:
#                 return jsonify({"error": "Process order not found"}), 404
            
#             # 2) Store the validation result in orders table
#             # Use the provided confirmed_qty if available, otherwise use the updated_po.confirmed_qty
#             final_confirmed_qty = confirmed_qty if confirmed_qty is not None else updated_po.confirmed_qty
            
#             conn.execute(text("""
#                 INSERT INTO orders (po_number, material, version, batch, quantity, unit, plant, confirmed_qty, material_desc, status, confirmed_text, scrap, created_at, updated_at)
#                 VALUES (:po_number, :material, :version, :batch, :quantity, :unit, :plant, :confirmed_qty, :material_desc, :status, :confirmed_text, :scrap, NOW(), NOW())
#                 ON CONFLICT (po_number) DO UPDATE
#                 SET material = EXCLUDED.material,
#                     version = EXCLUDED.version,
#                     batch = EXCLUDED.batch,
#                     quantity = EXCLUDED.quantity,
#                     unit = EXCLUDED.unit,
#                     plant = EXCLUDED.plant,
#                     confirmed_qty = EXCLUDED.confirmed_qty,
#                     material_desc = EXCLUDED.material_desc,
#                     status = EXCLUDED.status,
#                     confirmed_text = EXCLUDED.confirmed_text,
#                     scrap = EXCLUDED.scrap,
#                     updated_at = NOW()
#             """), {
#                 "po_number": updated_po.order_id,
#                 "material": updated_po.material,
#                 "version": updated_po.version,
#                 "batch": updated_po.batch,
#                 "quantity": updated_po.quantity,
#                 "unit": updated_po.unit,
#                 "plant": updated_po.plant,
#                 "confirmed_qty": final_confirmed_qty,
#                 "material_desc": updated_po.material_desc,
#                 "status": status,
#                 "confirmed_text": confirmed_text,
#                 "scrap": scrap
#             })
            
#             conn.commit()
            
#             # Check if this is a partial confirmation
#             is_partial = confirmed_qty is not None and confirmed_qty != updated_po.quantity
#             partial_info = ""
#             if is_partial:
#                 partial_info = f" (Partial: {final_confirmed_qty}/{updated_po.quantity} {updated_po.unit})"
            
#             return jsonify({
#                 "message": f"Order {updated_po.order_id} {status.lower()} successfully{partial_info}",
#                 "process_order": _row_to_api(updated_po),
#                 "status": status,
#                 "remarks": remarks,
#                 "confirmed_text": confirmed_text,
#                 "scrap": scrap,
#                 "is_partial_confirmation": is_partial,
#                 "partial_info": {
#                     "confirmed_qty": final_confirmed_qty,
#                     "total_qty": updated_po.quantity,
#                     "unit": updated_po.unit,
#                     "completion_percentage": round((final_confirmed_qty / updated_po.quantity) * 100, 2) if updated_po.quantity > 0 else 0
#                 } if is_partial else None
#             }), 200
            
#     except Exception as e:
#         return jsonify({"error": f"Validation failed: {str(e)}"}), 500

# def get_shift_manual_used(conn, process_order_id, shift_letter):
#     """
#     Returns total manually confirmed weight for a specific order + shift.
#     """
#     rows = conn.execute(text("""
#         SELECT COALESCE(SUM(confirmed_weight), 0) AS total
#         FROM manual_confirmations
#         WHERE process_order_id = :oid
#           AND shift_code = :shift
#           AND synced_to_sap = TRUE
#     """), {
#         "oid": process_order_id,
#         "shift": shift_letter.upper()
#     }).mappings().first()

#     return float(rows.total or 0)
# # @process_orders_bp.post("/process_orders/push-confirmation")
# # def push_confirmation():
# #     """
# #     Clean + correct mid-shift manual + shift-end confirmation.
# #     Fixes:
# #       ✔ Correct WHERE clause (uses po.id instead of po.order_id)
# #       ✔ Never duplicates manual confirmations
# #       ✔ Prevents double-shift confirmation
# #       ✔ Sends manual + shift-end in one single batch
# #       ✔ Marks manual confirmations as synced safely
# #       ✔ Updates shift flags, confirmed_shift_X, last_confirmed_qty
# #     """
# #     from services.system_logger import log_hercules_event
# #     from services.sap_confirmation import confirm_orders_batch, SAPConfirmationService
# #     import json

# #     payload = request.get_json(silent=True) or {}
# #     order_ids = payload.get("order_ids", [])
# #     operator = payload.get("operator", "manual")

# #     # Log start
# #     try:
# #         log_hercules_event(
# #             action="Push Confirmation Started",
# #             status="InProgress",
# #             details=f"Pushing confirmations for {order_ids}",
# #             operator=operator
# #         )
# #     except:
# #         pass

# #     try:
# #         with postgres_engine.connect() as conn:

# #             #---------------------------------------------------------
# #             # 1) Load UNSYNCED manual confirmations
# #             #---------------------------------------------------------
# #             manual_rows = conn.execute(text("""
# #                 SELECT mc.id manual_id,
# #                        mc.process_order_id,
# #                        po.order_id AS po_number,
# #                        mc.shift_code,
# #                        mc.confirmed_weight,
# #                        po.material,
# #                        po.version,
# #                        po.material_desc,
# #                        po.quantity as total_qty,
# #                        po.unit as uom,
# #                        po.plant,
# #                        po.batch,
# #                        po.created_at
# #                 FROM manual_confirmations mc
# #                 JOIN process_orders po ON po.id = mc.process_order_id
# #                 WHERE mc.synced_to_sap = FALSE
# #                 ORDER BY mc.id
# #             """)).mappings().all()

# #             manual_payloads = []
# #             unsynced_sum = {}

# #             for m in manual_rows:
# #                 key = (m.process_order_id, m.shift_code.upper())
# #                 unsynced_sum[key] = unsynced_sum.get(key, 0) + float(m.confirmed_weight)

# #                 manual_payloads.append({
# #                     "type": "manual",
# #                     "manual_id": m.manual_id,
# #                     "process_order_id": m.process_order_id,
# #                     "po_number": m.po_number,
# #                     "material": m.material,
# #                     "version": m.version,
# #                     "material_desc": m.material_desc,
# #                     "total_qty": float(m.total_qty or 0),
# #                     "confirmed_weight": float(m.confirmed_weight or 0),
# #                     "uom": m.uom or "KG",
# #                     "plant": m.plant,
# #                     "batch": m.batch,
# #                     "shift": m.shift_code.upper(),
# #                     "confirmed_text": "MID-SHIFT MANUAL",
# #                     "scrap": 0
# #                 })

# #             #---------------------------------------------------------
# #             # 2) Load PROCESS ORDERS requested by frontend
# #             #---------------------------------------------------------
# #             if not order_ids:
# #                 return jsonify({
# #                     "message": "No orders selected",
# #                     "successful_count": 0,
# #                     "failed_count": 0,
# #                     "results": []
# #                 }), 200

# #             placeholders = ", ".join([f":id{i}" for i in range(len(order_ids))])
# #             params = {f"id{i}": int(oid) for i, oid in enumerate(order_ids)}

# #             auto_rows = conn.execute(text(f"""
# #                 SELECT  po.id AS pid,
# #                         po.order_id AS po_number,
# #                         po.material,
# #                         po.version,
# #                         po.material_desc,
# #                         po.quantity AS total_qty,
# #                         po.unit AS uom,
# #                         po.plant,
# #                         po.batch,
# #                         po.created_at,
# #                         po.last_confirmed_qty,
# #                         po.current_shift,
# #                         po.weight_shift_a,
# #                         po.weight_shift_b,
# #                         po.weight_shift_c,
# #                         po.confirmed_shift_a,
# #                         po.confirmed_shift_b,
# #                         po.confirmed_shift_c,
# #                         po.is_final_sent
# #                 FROM process_orders po
# #                 WHERE po.id IN ({placeholders})
# #                   AND po.status IN ('Validated','InProgress')
# #             """), params).mappings().all()

# #             #---------------------------------------------------------
# #             # 3) Prepare SHIFT-END payloads (skip active shift)
# #             #---------------------------------------------------------
# #             shift_payloads = []

# #             # Preload already-synced manual confirmations
# #             synced_rows = conn.execute(text("""
# #                 SELECT process_order_id, shift_code, SUM(confirmed_weight) total
# #                 FROM manual_confirmations
# #                 WHERE synced_to_sap = TRUE
# #                 GROUP BY process_order_id, shift_code
# #             """)).mappings().all()

# #             synced_sum = {
# #                 (r.process_order_id, r.shift_code.upper()): float(r.total or 0)
# #                 for r in synced_rows
# #             }

# #             for r in auto_rows:

# #                 if r.is_final_sent:
# #                     continue

# #                 shifts = [
# #                     ("A", r.weight_shift_a, r.confirmed_shift_a),
# #                     ("B", r.weight_shift_b, r.confirmed_shift_b),
# #                     ("C", r.weight_shift_c, r.confirmed_shift_c),
# #                 ]

# #                 current_shift = (r.current_shift or "").upper()

# #                 for letter, raw_weight, confirmed_flag in shifts:

# #                     if letter == current_shift:
# #                         continue  # never confirm active shift

# #                     raw_weight = float(raw_weight or 0)
# #                     if raw_weight <= 0:
# #                         continue

# #                     confirmed_flag = float(confirmed_flag or 0)
# #                     if confirmed_flag > 0:
# #                         continue  # already confirmed earlier

# #                     key = (r.pid, letter)
# #                     used_manual = synced_sum.get(key, 0) + unsynced_sum.get(key, 0)
# #                     remaining = raw_weight - used_manual

# #                     if remaining <= 0:
# #                         continue

# #                     shift_payloads.append({
# #                         "type": "shift",
# #                         "process_order_id": r.pid,
# #                         "po_number": r.po_number,
# #                         "material": r.material,
# #                         "version": r.version,
# #                         "material_desc": r.material_desc,
# #                         "total_qty": float(r.total_qty),
# #                         "confirmed_weight": float(remaining),
# #                         "uom": r.uom,
# #                         "plant": r.plant,
# #                         "batch": r.batch,
# #                         "shift": letter,
# #                         "last_confirmed_qty": float(r.last_confirmed_qty),
# #                     })

# #             #---------------------------------------------------------
# #             # NO DATA?
# #             #---------------------------------------------------------
# #             if not manual_payloads and not shift_payloads:
# #                 return jsonify({
# #                     "message": "Nothing to confirm",
# #                     "successful_count": 0,
# #                     "failed_count": 0,
# #                     "results": []
# #                 }), 200

# #             batch_payload = manual_payloads + shift_payloads

# #             #---------------------------------------------------------
# #             # 4) SEND TO SAP
# #             #---------------------------------------------------------
# #             try:
# #                 result = confirm_orders_batch(batch_payload, "online")
# #             except:
# #                 sap = SAPConfirmationService()
# #                 result = sap.confirm_orders_batch(batch_payload, "online")

# #             success_ids = {str(x).lstrip("0") for x in result.get("successful_orders", [])}

# #             results = []
# #             failed = []

# #             #---------------------------------------------------------
# #             # 5) MARK manual confirmations as synced
# #             #---------------------------------------------------------
# #             with postgres_engine.begin() as tx:

# #                 for m in manual_payloads:
# #                     po_norm = str(m["po_number"]).lstrip("0")

# #                     if po_norm in success_ids:
# #                         tx.execute(text("""
# #                             UPDATE manual_confirmations
# #                             SET synced_to_sap = TRUE,
# #                                 sap_response = :resp,
# #                                 updated_at = NOW()
# #                             WHERE id = :mid
# #                         """), {"mid": m["manual_id"], "resp": json.dumps({"status": "confirmed"})})

# #                         results.append({"process_order": m["po_number"], "status": "Manual Confirmed"})
# #                     else:
# #                         failed.append(m["po_number"])
# #                         results.append({"process_order": m["po_number"], "status": "Manual Failed"})

# #                 #-----------------------------------------------------
# #                 # 6) APPLY shift-end confirmations to DB
# #                 #-----------------------------------------------------
# #                 for s in shift_payloads:
# #                     po_norm = str(s["po_number"]).lstrip("0")

# #                     if po_norm not in success_ids:
# #                         failed.append(s["po_number"])
# #                         results.append({"process_order": s["po_number"], "status": "Shift Failed"})
# #                         continue

# #                     new_last = s["last_confirmed_qty"] + s["confirmed_weight"]
# #                     is_final = new_last >= s["total_qty"]

# #                     letter = s["shift"].lower()

# #                     tx.execute(text(f"""
# #                         UPDATE process_orders
# #                         SET confirmed_shift_{letter} = :w,
# #                             last_confirmed_qty = :lc,
# #                             is_final_sent = :final,
# #                             updated_at = NOW(),
# #                             status = CASE WHEN :final THEN 'Confirmed' ELSE 'InProgress' END
# #                         WHERE order_id = :po
# #                     """), {
# #                         "w": s["confirmed_weight"],
# #                         "lc": new_last,
# #                         "final": is_final,
# #                         "po": s["po_number"]
# #                     })

# #                     results.append({
# #                         "process_order": s["po_number"],
# #                         "status": "Shift Confirmed",
# #                         "final": is_final
# #                     })

# #             return jsonify({
# #                 "message": "Push confirmation complete",
# #                 "successful_count": len(success_ids),
# #                 "failed_count": len(failed),
# #                 "results": results
# #             }), 200

# #     except Exception as e:
# #         return jsonify({"error": str(e)}), 500
# @process_orders_bp.post("/process_orders/push-confirmation")
# def push_confirmation():
#     """
#     ✅ FIXED: Mid-shift + shift-end confirmation with proper deduplication.
    
#     Features:
#       - Mid-shift: User clicks button → sends current shift production
#       - Shift-end: Auto-scheduler → sends remaining production only
#       - Deduplication: weight_shift_X - confirmed_shift_X = remaining
#       - Accumulates confirmed_shift_X properly (no double-counting)
#     """
#     from services.system_logger import log_hercules_event
#     from services.sap_confirmation import SAPConfirmationService
#     import json

#     payload = request.get_json(silent=True) or {}
#     order_ids = payload.get("order_ids", [])
#     operator = payload.get("operator", "manual")
#     confirm_current_shift = payload.get("confirm_current_shift", False)  # Mid-shift flag

#     # Log start
#     try:
#         log_hercules_event(
#             action="Push Confirmation Started",
#             status="InProgress",
#             details=f"Pushing confirmations for {order_ids} (mid_shift={confirm_current_shift})",
#             operator=operator
#         )
#     except:
#         pass

#     try:
#         with postgres_engine.connect() as conn:

#             #---------------------------------------------------------
#             # 1) Load PROCESS ORDERS
#             #---------------------------------------------------------
#             if not order_ids:
#                 return jsonify({
#                     "message": "No orders selected",
#                     "successful_count": 0,
#                     "failed_count": 0,
#                     "results": []
#                 }), 200

#             placeholders = ", ".join([f":id{i}" for i in range(len(order_ids))])
#             params = {f"id{i}": int(oid) for i, oid in enumerate(order_ids)}

#             rows = conn.execute(text(f"""
#                 SELECT  
#                     po.id AS pid,
#                     po.order_id AS po_number,
#                     po.material,
#                     po.version,
#                     po.material_desc,
#                     po.quantity AS total_qty,
#                     po.unit AS uom,
#                     po.plant,
#                     po.batch,
#                     po.created_at,
#                     po.last_confirmed_qty,
#                     po.current_shift,
#                     po.weight_shift_a,
#                     po.weight_shift_b,
#                     po.weight_shift_c,
#                     po.confirmed_shift_a,
#                     po.confirmed_shift_b,
#                     po.confirmed_shift_c,
#                     po.is_final_sent,
#                     po.priority,
#                     po.scale1,
#                     po.scale1_qty,
#                     po.scale2,
#                     po.scale2_qty,
#                     po.scale3,
#                     po.scale3_qty,
#                     po.scrap
#                 FROM process_orders po
#                 WHERE po.id IN ({placeholders})
#                   AND po.status IN ('Validated','InProgress')
#             """), params).mappings().all()

#             #---------------------------------------------------------
#             # 2) ✅ Build SAP payloads with proper remaining calculation
#             #---------------------------------------------------------
#             sap_payloads = []

#             for r in rows:

#                 if r.is_final_sent:
#                     continue

#                 shifts = [
#                     ("A", r.weight_shift_a, r.confirmed_shift_a),
#                     ("B", r.weight_shift_b, r.confirmed_shift_b),
#                     ("C", r.weight_shift_c, r.confirmed_shift_c),
#                 ]

#                 order_current_shift = (r.current_shift or "").upper()

#                 for shift_letter, weight_produced, weight_confirmed in shifts:

#                     # ✅ Skip active shift UNLESS mid-shift confirmation requested
#                     if shift_letter == order_current_shift and not confirm_current_shift:
#                         continue

#                     # ✅ Calculate REMAINING production for this shift
#                     # Formula: total_produced - already_sent_to_SAP = remaining
#                     total_produced = float(weight_produced or 0)
#                     already_sent = float(weight_confirmed or 0)
#                     remaining = total_produced - already_sent

#                     if remaining <= 0:
#                         continue  # Nothing new to confirm for this shift

#                     # ✅ Build payload (send only REMAINING production)
#                     # ✅ CRITICAL: Always include byproduct scales (even if order not validated)
#                     sap_payloads.append({
#                         "po_number": r.po_number,
#                         "process_order_id": r.pid,
#                         "material": r.material,
#                         "version": r.version or "",
#                         "material_desc": r.material_desc or "",
#                         "total_qty": float(r.total_qty),
#                         "confirmed_weight": float(remaining),  # ✅ Only send remaining
#                         "uom": r.uom or "KG",
#                         "plant": r.plant,
#                         "created_at": r.created_at,
#                         "batch": r.batch or "",
#                         "shift": shift_letter,
#                         "priority": r.priority or 1,
#                         "last_confirmed_qty": float(r.last_confirmed_qty or 0),
#                         "is_final_sent": False,
#                         "order_current_shift": order_current_shift,
#                         # ✅ CRITICAL: Always include byproduct scales (scale1, scale2, scale3 and their quantities)
#                         # This ensures they appear in SAP payload for mid-shift and end-shift confirmations
#                         "scale1": r.scale1 or "",
#                         "scale1_qty": float(r.scale1_qty or 0),
#                         "scale2": r.scale2 or "",
#                         "scale2_qty": float(r.scale2_qty or 0),
#                         "scale3": r.scale3 or "",
#                         "scale3_qty": float(r.scale3_qty or 0),
#                         "scrap": float(r.scrap or 0),
#                     })

#             #---------------------------------------------------------
#             # NO DATA?
#             #---------------------------------------------------------
#             if not sap_payloads:
#                 return jsonify({
#                     "message": "Nothing to confirm",
#                     "successful_count": 0,
#                     "failed_count": 0,
#                     "results": []
#                 }), 200

#             #---------------------------------------------------------
#             # 3) ✅ SEND TO SAP
#             #---------------------------------------------------------
#             sap_service = SAPConfirmationService()
#             result = sap_service.confirm_orders_batch(sap_payloads, "auto")

#             success_ids = {str(x).lstrip("0") for x in result.get("successful_orders", [])}
#             results = []
#             failed = []

#             #---------------------------------------------------------
#             # 4) ✅ FIXED: Update database after SAP success
#             #---------------------------------------------------------
#             with postgres_engine.begin() as tx:

#                 for payload in sap_payloads:
#                     po_norm = str(payload["po_number"]).lstrip("0")

#                     if po_norm not in success_ids:
#                         failed.append(payload["po_number"])
#                         results.append({
#                             "process_order": payload["po_number"],
#                             "status": "Failed",
#                             "shift": payload["shift"]
#                         })
#                         continue

#                     confirmed_weight = payload["confirmed_weight"]
#                     shift_letter = payload["shift"].lower()

#                     # ✅ CRITICAL FIX: ADD to confirmed_shift_X (accumulate, don't replace)
#                     # This tracks cumulative confirmed weight for deduplication
#                     # ✅ Update last_confirmed_qty with sum of all shift confirmations (using NEW value for updated shift)
#                     # Calculate last_confirmed_qty using the NEW value for the shift being updated
#                     if shift_letter == 'a':
#                         # For shift A: use NEW value (old + :w) for A, old values for B and C
#                         last_confirmed_calc = "(COALESCE(confirmed_shift_a, 0) + :w) + COALESCE(confirmed_shift_b, 0) + COALESCE(confirmed_shift_c, 0)"
#                     elif shift_letter == 'b':
#                         # For shift B: use old value for A, NEW value (old + :w) for B, old value for C
#                         last_confirmed_calc = "COALESCE(confirmed_shift_a, 0) + (COALESCE(confirmed_shift_b, 0) + :w) + COALESCE(confirmed_shift_c, 0)"
#                     else:  # shift_letter == 'c'
#                         # For shift C: use old values for A and B, NEW value (old + :w) for C
#                         last_confirmed_calc = "COALESCE(confirmed_shift_a, 0) + COALESCE(confirmed_shift_b, 0) + (COALESCE(confirmed_shift_c, 0) + :w)"
                    
#                     # Execute the update with proper calculation
#                     update_sql = f"""
#                         UPDATE process_orders
#                         SET confirmed_shift_{shift_letter} = COALESCE(confirmed_shift_{shift_letter}, 0) + :w,
#                             last_confirmed_qty = {last_confirmed_calc},
#                             updated_at = NOW()
#                         WHERE id = :pid
#                     """
#                     tx.execute(text(update_sql), {
#                         "w": confirmed_weight,  # ✅ Add only what was just confirmed
#                         "pid": payload["process_order_id"]
#                     })
                    
#                     print(f"✅ Updated confirmed_shift_{shift_letter} by {confirmed_weight:.2f} and recalculated last_confirmed_qty")

#                     conf_type = "Mid-Shift Confirmed" if payload["shift"] == payload["order_current_shift"] else "Shift-End Confirmed"
                    
#                     results.append({
#                         "process_order": payload["po_number"],
#                         "status": conf_type,
#                         "confirmed_weight": confirmed_weight,
#                         "shift": payload["shift"],
#                     })

#             return jsonify({
#                 "message": "Push confirmation complete",
#                 "successful_count": len(success_ids),
#                 "failed_count": len(failed),
#                 "results": results
#             }), 200

#     except Exception as e:
#         return jsonify({"error": str(e)}), 500


# @process_orders_bp.post("/process_orders/test-confirmation")
# def test_confirmation():
#     """
#     Temporary API for testing:
#     - Builds SAP payload using existing SAPConfirmationService
#     - Does NOT send to SAP
#     - Stores payload in sap_confirmation_test table
#     - Returns the generated payloads for debugging
#     """
#     from services.sap_confirmation import SAPConfirmationService

#     try:
#         with postgres_engine.connect() as conn:

#             # ----------------------------------------------------
#             # 🔥 DEBUG INFORMATION (to verify DB connection)
#             # ----------------------------------------------------
#             db_info = conn.execute(text("SELECT current_database()")).scalar()
#             print("🔍 Connected DB:", db_info)

#             count = conn.execute(text("SELECT COUNT(*) FROM process_orders")).scalar()
#             print("🔍 process_orders count:", count)

#             statuses = conn.execute(text("SELECT DISTINCT status FROM process_orders")).fetchall()
#             print("🔍 statuses:", statuses)

#             # ----------------------------------------------------
#             # 1) Fetch orders that are Validated or InProgress
#             # ----------------------------------------------------
#             rows = conn.execute(text("""
#                 SELECT 
#                     order_id as po_number,
#                     material,
#                     version,
#                     material_desc,
#                     quantity as total_qty,
#                     confirmed_qty,
#                     unit as uom,
#                     plant,
#                     created_at,
#                     updated_at as confirmed_at,
#                     batch,
#                     priority as shift,
#                     confirmed_text,
#                     scrap,
#                     scale1,
#                     scale1_qty,
#                     scale2,
#                     scale2_qty,
#                     scale3,
#                     scale3_qty
#                 FROM process_orders
#                 WHERE status IN ('Validated', 'InProgress')
#                 ORDER BY id
#             """)).mappings().all()

#             print("🔍 rows fetched:", len(rows))

#             if not rows:
#                 return jsonify({
#                     "message": "No validated or in-progress orders found",
#                     "debug": {
#                         "connected_db": db_info,
#                         "process_orders_count": count,
#                         "statuses": [s[0] for s in statuses]
#                     }
#                 }), 200

#             # ----------------------------------------------------
#             # 2) Convert DB rows → SAP service payload structure
#             # ----------------------------------------------------
#             orders = []
#             for r in rows:
#                 orders.append({
#                     "po_number": r.po_number,
#                     "material": r.material,
#                     "version": r.version or "",
#                     "material_desc": r.material_desc or "",
#                     "total_qty": float(r.total_qty or 0),
#                     "confirmed_weight": float(r.confirmed_qty or 0),
#                     "uom": r.uom or "KG",
#                     "plant": r.plant,
#                     "created_at": r.created_at,
#                     "confirmed_at": r.confirmed_at,
#                     "batch": r.batch or "",
#                     "shift": "A",  # simple for testing
#                     "confirmed_text": r.confirmed_text or "",
#                     "scrap": float(r.scrap or 0),
#                     "scale1": r.scale1 or "",
#                     "scale1_qty": float(r.scale1_qty or 0),
#                     "scale2": r.scale2 or "",
#                     "scale2_qty": float(r.scale2_qty or 0),
#                     "scale3": r.scale3 or "",
#                     "scale3_qty": float(r.scale3_qty or 0),
#                 })

#             print("🔍 Converted orders:", len(orders))

#             # ----------------------------------------------------
#             # 3) Build SAP JSON payloads
#             # ----------------------------------------------------
#             sap = SAPConfirmationService()
#             payloads = sap._convert_to_json_format(orders, "online")

#             print("🔍 Payloads generated:", len(payloads))

#             # ----------------------------------------------------
#             # 4) Store payloads into sap_confirmation_test table
#             # ----------------------------------------------------
#             for p in payloads:
#                 conn.execute(text("""
#                     INSERT INTO sap_confirmation_test (po_number, payload, confirmation_type)
#                     VALUES (:po, :payload, 'online')
#                 """), {
#                     "po": p.get("PROCESS_ORDER"),
#                     "payload": json.dumps(p)
#                 })

#             conn.commit()

#             # ----------------------------------------------------
#             # 5) Final response
#             # ----------------------------------------------------
#             return jsonify({
#                 "message": "Test payloads generated (not sent to SAP)",
#                 "count": len(payloads),
#                 "payloads": payloads,
#                 "debug": {
#                     "connected_db": db_info,
#                     "process_orders_count": count,
#                     "statuses": [s[0] for s in statuses]
#                 }
#             }), 200

#     except Exception as e:
#         print("❌ ERROR:", e)
#         return jsonify({"error": f"Failed: {str(e)}"}), 500

# @process_orders_bp.post("/process_orders/manual-confirm")
# def manual_confirm():
#     from database import PostgresSessionLocal
#     from models.process_order_pg import ProcessOrderPG
#     from models.manual_confirmation import ManualConfirmation  # create this model

#     data = request.get_json(silent=True) or {}
#     po_number = data.get("po_number")
#     shift = data.get("shift")
#     weight = data.get("weight")
#     operator = data.get("operator", "manual")

#     if not po_number or not shift or weight is None:
#         return jsonify({"error": "po_number, shift, and weight are required"}), 400

#     db = PostgresSessionLocal()

#     try:
#         order = db.query(ProcessOrderPG).filter(
#             ProcessOrderPG.order_id == po_number
#         ).first()

#         if not order:
#             return jsonify({"error": f"Order {po_number} not found"}), 404

#         entry = ManualConfirmation(
#             process_order_id=order.id,
#             shift_code=shift.upper(),
#             confirmed_weight=float(weight),
#             synced_to_sap=False,
#             created_by=operator
#         )

#         db.add(entry)
#         db.commit()
#         db.refresh(entry)

#         return jsonify({
#             "success": True,
#             "message": "Manual confirmation stored",
#             "id": entry.id
#         })

#     except Exception as e:
#         db.rollback()
#         return jsonify({"error": str(e)}), 500
#     finally:
#         db.close()

# # backend/routes/process_orders.py
# # backend/routes/process_orders.py (around line 1200-1260)
# # Line 1201 - FIXED
# # backend/routes/process_orders.py
# # backend/routes/process_orders.py
# # backend/routes/process_orders.py


# @process_orders_bp.route("/process_orders/<string:orderid>/offline-confirm", methods=["POST", "OPTIONS"])
# def offline_manual_confirmation(orderid: str):
#     if request.method == "OPTIONS":
#         return jsonify(ok=True), 200

#     from services.sap_confirmation import SAPConfirmationService

#     data = request.get_json() or {}
#     scrap = float(data.get("scrap", 0.0))
#     confirmed_text = data.get("confirmed_text", "")

#     try:
#         with PostgresSessionLocal() as db:
#             order_result = db.execute(
#                 text("SELECT * FROM process_orders WHERE order_id = :orderid"), 
#                 {"orderid": orderid}
#             ).mappings().first()

#             if order_result is None:
#                 return jsonify(error=f"Order {orderid} not found"), 404

#             # ✅ CRITICAL: Convert Row to dict for easier access
#             # Using .mappings() returns a dict-like Row object
#             order = dict(order_result)
            
#             # ✅ CRITICAL: Get current confirmed_qty from database
#             confirmed_qty = float(order.get('confirmed_qty') or order.get('confirmedqty') or 0)
            
#             # ✅ CRITICAL: If confirmed_qty is 0 but there's production (delta showing 200kg),
#             # we need to calculate it from shift weights or current production
#             # Check if order has shift weights that indicate production
#             weight_shift_a = float(order.get('weight_shift_a') or 0)
#             weight_shift_b = float(order.get('weight_shift_b') or 0)
#             weight_shift_c = float(order.get('weight_shift_c') or 0)
#             shift_weights_sum = weight_shift_a + weight_shift_b + weight_shift_c
            
#             # ✅ CRITICAL: If confirmed_qty is 0 but shift weights show production, use shift weights
#             if confirmed_qty == 0.0 and shift_weights_sum > 0.0:
#                 confirmed_qty = shift_weights_sum
#                 print(f"📊 [ManualConfirm-{orderid}] confirmed_qty was 0, but shift weights show {shift_weights_sum:.2f} - using shift weights")
            
#             # ✅ CRITICAL: Also check if there's a current_shift weight that should be used
#             current_shift = (order.get('current_shift') or 'A').upper()
#             current_shift_weight_field = f"weight_shift_{current_shift.lower()}"
#             current_shift_weight = float(order.get(current_shift_weight_field) or 0)
            
#             # ✅ CRITICAL: If confirmed_qty is still 0 but current shift has weight, use it
#             if confirmed_qty == 0.0 and current_shift_weight > 0.0:
#                 confirmed_qty = current_shift_weight
#                 print(f"📊 [ManualConfirm-{orderid}] confirmed_qty was 0, but current shift ({current_shift}) weight shows {current_shift_weight:.2f} - using current shift weight")

#             # Build SAP payload in the format expected by confirm_offline
#             # The method expects lowercase field names that match the order structure
#             sappayload = {
#                 "po_number": order.get('order_id') or order.get('orderid'),
#                 "material": order.get('material'),
#                 "version": order.get('version') or '',
#                 "material_desc": order.get('material_desc') or '',
#                 "total_qty": float(order.get('quantity') or 0),
#                 "confirmed_weight": confirmed_qty,  # Full confirmed qty, no minus scrap
#                 "uom": order.get('unit') or order.get('uom') or 'KG',
#                 "plant": order.get('plant') or '',
#                 "batch": order.get('batch') or '',
#                 "created_at": order.get('created_at') or datetime.now(),
#                 "confirmed_text": confirmed_text,  # For offline confirmation
#                 "scrap": scrap,  # For offline confirmation
#                 "scale1": order.get('scale1') or '',
#                 "scale1_qty": float(order.get('scale1_qty') or 0),
#                 "scale2": order.get('scale2') or '',
#                 "scale2_qty": float(order.get('scale2_qty') or 0),
#                 "scale3": order.get('scale3') or '',
#                 "scale3_qty": float(order.get('scale3_qty') or 0),
#                 "last_confirmed_qty": float(order.get('last_confirmed_qty') or 0),
#                 "is_final_sent": bool(order.get('is_final_sent') or False),
#             }

#             sapservice = SAPConfirmationService()
#             sapresult = sapservice.confirm_offline([sappayload])

#             # ✅ CRITICAL: Update order with scrap, confirmed_text, validation method, AND confirmed_qty
#             # ⚠️ IMPORTANT: Do NOT change status - just send confirmation to SAP, keep order as InProgress
#             # This ensures confirmed_qty is preserved even if it was calculated from shift weights
#             update_sql = text("""
#                 UPDATE process_orders
#                 SET scrap = :scrap,
#                     confirmed_text = :confirmed_text,
#                     validation_method = 'Manual Offline',
#                     confirmed_qty = :confirmed_qty,
#                     updated_at = NOW()
#                 WHERE order_id = :orderid
#             """)
#             db.execute(update_sql, {
#                 "scrap": scrap,
#                 "confirmed_text": confirmed_text,
#                 "confirmed_qty": confirmed_qty,
#                 "orderid": orderid
#             })
#             db.commit()

#             return jsonify(
#                 success=True,
#                 message=sapresult.get("message", "Offline confirmation sent to SAP successfully."),
#                 orderid=orderid,
#                 confirmedqty=confirmed_qty,
#                 scrap=scrap,
#                 confirmed_text=confirmed_text
#             ), 200

#     except Exception as ex:
#         import traceback
#         error_trace = traceback.format_exc()
#         print(f"❌ [ManualConfirm-{orderid}] Error: {str(ex)}")
#         print(f"❌ [ManualConfirm-{orderid}] Traceback: {error_trace}")
#         return jsonify(error=f"Internal server error: {str(ex)}"), 500
# routes/process_orders.py
from __future__ import annotations

from typing import List, Dict, Any, Optional, Tuple
from flask import Blueprint, jsonify, request, abort
from sqlalchemy import text
from datetime import datetime, timedelta
import logging

from database import postgres_engine, PostgresSessionLocal

log = logging.getLogger(__name__)
from services.process_order_sync import sync_process_orders           # legacy/internal sync (optional)
from services.process_order_pull import pull_from_sap_once, test_sap_connection
from utils.shifts import get_current_shift
import json  # shared SAP -> Hercules pull
from models.manual_confirmation import ManualConfirmation
from datetime import datetime, timedelta


process_orders_bp = Blueprint("process_orders", __name__, url_prefix="/api")

print("=" * 60)
print("🔥🔥🔥 PROCESS_ORDERS.PY BLUEPRINT LOADED 🔥🔥🔥")
print("=" * 60)

# -------------------------------------------------------------------
# Helpers
# -------------------------------------------------------------------

def _row_to_api(row) -> dict:
    """Map DB row -> API shape (doc-aligned)."""
    return {
        "id": row.id,
        "po_number": row.order_id,  # order_id is the PO number from SAP
        "material": row.material,
        "version": row.version,
        "batch": row.batch,
        "quantity": float(row.quantity) if row.quantity is not None else None,
        "unit": row.unit,
        "status": row.status,
        "priority": getattr(row, 'hercules_priority', None) or row.priority,
        "priority_id": getattr(row, 'priority_id', None),
        "plant": getattr(row, 'plant', None),
        "confirmed_qty": float(row.confirmed_qty) if hasattr(row, 'confirmed_qty') and row.confirmed_qty is not None else None,
        "last_confirmed_qty": float(row.last_confirmed_qty) if hasattr(row, 'last_confirmed_qty') and row.last_confirmed_qty is not None else 0.0,
        "material_desc": getattr(row, 'material_desc', None),
        "expected_weight": float(row.expected_weight) if hasattr(row, 'expected_weight') and row.expected_weight is not None else None,
        "created_at": row.created_at.isoformat() if row.created_at else None,
        "order_type": getattr(row, 'order_type', None),
        "current_shift": getattr(row, 'current_shift', None),
        # Byproduct scale fields for MILLING orders
        "scale1": getattr(row, 'scale1', None),
        "scale1_qty": float(row.scale1_qty) if hasattr(row, 'scale1_qty') and row.scale1_qty is not None else None,
        "scale2": getattr(row, 'scale2', None),
        "scale2_qty": float(row.scale2_qty) if hasattr(row, 'scale2_qty') and row.scale2_qty is not None else None,
        "scale3": getattr(row, 'scale3', None),
        "scale3_qty": float(row.scale3_qty) if hasattr(row, 'scale3_qty') and row.scale3_qty is not None else None,
    }

def _queue_where_clause(statuses: Optional[List[str]] = None) -> Tuple[str, Dict[str, Any]]:
    """
    Build WHERE for queue. By default we queue only 'Open' or 'Pending'.
    """
    params: Dict[str, Any] = {}
    if not statuses:
        statuses = ["Open", "Pending"]
    placeholders = ", ".join([f":s{i}" for i, _ in enumerate(statuses)])
    for i, s in enumerate(statuses):
        params[f"s{i}"] = s
    where_sql = f" WHERE status IN ({placeholders})"
    return where_sql, params

def _queue_order_by_clause() -> str:
    """
    Hercules priority first (ascending: smaller number = higher priority),
    then FIFO by created_at (oldest first), finally by id to break ties.
    """
    return " ORDER BY COALESCE(hercules_priority, priority) ASC, created_at ASC NULLS LAST, id ASC "


def _ensure_order_from_po(conn, po_row_id: int) -> dict | None:
    """
    Create (or ensure) an 'orders' row from a claimed process_orders row.
    Returns the upserted order as a mapping (dict-like).
    """
    # 1) fetch the claimed process order row
    po = conn.execute(text("""
        SELECT order_id, material, version, batch, quantity, unit, plant, confirmed_qty, material_desc
        FROM process_orders
        WHERE id = :id
    """), {"id": po_row_id}).mappings().first()
    if not po:
        return None

    # 2) UPSERT into orders using po_number as unique key
    conn.execute(text("""
        INSERT INTO orders (po_number, material, version, batch, quantity, unit, plant, confirmed_qty, material_desc, status, created_at, updated_at)
        VALUES (:po_number, :material, :version, :batch, :quantity, :unit, :plant, :confirmed_qty, :material_desc, 'Pending', NOW(), NOW())
        ON CONFLICT (po_number) DO UPDATE
        SET material      = EXCLUDED.material,
            version       = EXCLUDED.version,
            batch         = EXCLUDED.batch,
            quantity      = EXCLUDED.quantity,
            unit          = EXCLUDED.unit,
            plant         = EXCLUDED.plant,
            confirmed_qty = EXCLUDED.confirmed_qty,
            material_desc = EXCLUDED.material_desc,
            updated_at    = NOW()
    """), {
        "po_number": po.order_id,
        "material":  po.material,
        "version":   po.version,
        "batch":     po.batch,
        "quantity":  po.quantity,
        "unit":      po.unit or "KG",
        "plant":     po.plant,
        "confirmed_qty": po.confirmed_qty,
        "material_desc": po.material_desc,
    })

    # 3) return the orders row
    order = conn.execute(text("""
        SELECT id, po_number, material, version, batch, quantity, unit, plant, confirmed_qty, material_desc, status, created_at, updated_at
        FROM orders
        WHERE po_number = :po
    """), {"po": po.order_id}).mappings().first()
    return order

# -------------------------------------------------------------------
# Routes
# -------------------------------------------------------------------

@process_orders_bp.get("/process_orders")
def list_process_orders():
    """
    List process orders (doc-aligned fields only).

    Query params:
      - status: filter by status (e.g., Open, Pending, Validated, Rejected)
      - limit: page size (default 50)
      - offset: page offset (default 0)
    """
    status = request.args.get("status")
    try:
        limit = int(request.args.get("limit", 50))
        offset = int(request.args.get("offset", 0))
    except ValueError:
        limit, offset = 50, 0

    base_sql = """
      SELECT
        id,
        order_id,
        material,
        version,
        batch,
        quantity,
        unit,
        status,
        priority,
        priority_id,
        hercules_priority,
        plant,
        confirmed_qty,
        material_desc,
        expected_weight,
        created_at,
        order_type,
        last_confirmed_qty,
        current_shift,
        scale1,
        scale1_qty,
        scale2,
        scale2_qty,
        scale3,
        scale3_qty
      FROM process_orders
    """

    params = {"limit": limit, "offset": offset}
    where_sql = ""
    if status and status != "All":
        where_sql = " WHERE status = :status"
        params["status"] = status

    # Order by hercules_priority first (ascending), then by id as tiebreaker
    sql = (
        base_sql
        + where_sql
        + " ORDER BY COALESCE(hercules_priority, priority) ASC NULLS LAST, id ASC LIMIT :limit OFFSET :offset"
    )

    try:
        with postgres_engine.connect() as conn:
            rows = conn.execute(text(sql), params).mappings().all()
        return jsonify([_row_to_api(r) for r in rows]), 200
    except Exception as e:
        # Dev-only fallback; remove in production
        print(f"[process_orders] list error: {e}")
        sample = [{
            "id": 1,
            "po_number": "PO-001",
            "material": "1300005",
            "version": "BKF1",
            "batch": "BATCH-001",
            "quantity": 1000.0,
            "unit": "KG",
            "status": "Open",
            "priority": 1,
            "created_at": (datetime.now() - timedelta(days=1)).isoformat(),
        }]
        return jsonify(sample), 200


@process_orders_bp.post("/process_orders/pull")
def pull_process_orders_from_sap():
    """
    Manual 'Pull New Orders' (SAP -> Hercules):
    - Fetch open POs from SAP using the shared service
    - Upsert by order_id (po_number)
    """
    try:
        count = pull_from_sap_once()
        return jsonify({"message": f"Pulled {count} orders from SAP"}), 200
    except Exception as e:
        return jsonify({"error": f"Pull failed: {str(e)}"}), 500


@process_orders_bp.post("/process_orders/sync")
def sync_process_orders_endpoint():
    """
    Optional legacy/internal sync (e.g., SQL Server -> Postgres).
    Keep if still in use alongside SAP Pull; otherwise safe to remove later.
    """
    try:
        success = sync_process_orders()
        if success:
            return jsonify({"message": "Process orders synced successfully"}), 200
        return jsonify({"error": "Failed to sync process orders"}), 500
    except Exception as e:
        return jsonify({"error": f"Sync failed: {str(e)}"}), 500


# -------------------------------
# FIFO queue (priority → FIFO)
# -------------------------------

@process_orders_bp.get("/process_orders/queue")
def list_process_orders_queue():
    """
    Returns the execution queue already sorted:
    - priority ASC
    - created_at ASC (FIFO)
    - id ASC (tie-breaker)

    Query params:
      - limit (default 50)
      - statuses CSV (default: Open,Pending) e.g. ?statuses=Open,Pending,Validated
    """
    try:
        limit = int(request.args.get("limit", 50))
    except ValueError:
        limit = 50

    statuses_param = request.args.get("statuses")
    statuses = [s.strip() for s in statuses_param.split(",")] if statuses_param else None

    base_sql = """
      SELECT
        id,
        order_id,
        material,
        version,
        batch,
        quantity,
        unit,
        status,
        priority,
        priority_id,
        hercules_priority,
        plant,
        confirmed_qty,
        material_desc,
        expected_weight,
        created_at
      FROM process_orders
    """

    where_sql, params = _queue_where_clause(statuses)
    sql = base_sql + where_sql + _queue_order_by_clause() + " LIMIT :limit"
    params["limit"] = limit

    with postgres_engine.connect() as conn:
        rows = conn.execute(text(sql), params).mappings().all()
    return jsonify([_row_to_api(r) for r in rows]), 200


@process_orders_bp.post("/process_orders/next")
def claim_next_process_order():
    """
    Returns the 'next' order by (priority → FIFO). If claim=true:
      1) atomically set process_orders.status='InProgress'
      2) upsert into orders (po_number unique) with status 'Pending'
      3) return both the claimed process order and the execution order
    Body (optional):
      { "claim": true }
    """
    payload = request.get_json(silent=True) or {}
    claim = bool(payload.get("claim", False))

    select_sql = """
      SELECT id, order_id, material, version, batch, quantity, unit, status, priority, plant, confirmed_qty, material_desc, created_at
      FROM process_orders
      WHERE status IN ('Open', 'Pending')
    """ + _queue_order_by_clause() + " LIMIT 1"

    with postgres_engine.connect() as conn:
        row = conn.execute(text(select_sql)).mappings().first()
        if not row:
            return jsonify({"message": "No eligible orders found"}), 200

        if not claim:
            return jsonify(_row_to_api(row)), 200

        # 1) claim the process order (atomic)
        claimed = conn.execute(text("""
            UPDATE process_orders
            SET status = 'InProgress', updated_at = NOW()
            WHERE id = :id AND status IN ('Open','Pending')
            RETURNING id, order_id, material, version, batch, quantity, unit, status, priority, plant, confirmed_qty, material_desc, created_at
        """), {"id": row.id}).mappings().first()
        if not claimed:
            conn.rollback()
            abort(409, description="Order already claimed by another worker")

        # 2) ensure an execution order exists (orders table)
        order_row = _ensure_order_from_po(conn, claimed.id)

        conn.commit()

        return jsonify({
            "claimed_process_order": _row_to_api(claimed),
            "execution_order": {
                "id": order_row["id"],
                "po_number": order_row["po_number"],
                "material": order_row["material"],
                "version": order_row["version"],
                "batch": order_row["batch"],
                "quantity": float(order_row["quantity"]) if order_row["quantity"] is not None else None,
                "unit": order_row["unit"],
                "plant": order_row["plant"],
                "confirmed_qty": float(order_row["confirmed_qty"]) if order_row["confirmed_qty"] is not None else None,
                "material_desc": order_row["material_desc"],
                "status": order_row["status"],
                "created_at": order_row["created_at"].isoformat() if order_row["created_at"] else None,
            }
        }), 200


@process_orders_bp.get("/process_orders/test-sap")
def test_sap_connection_endpoint():
    """
    Test SAP API connection.
    Returns connection status and basic info.
    """
    try:
        is_connected = test_sap_connection()
        return jsonify({
            "connected": is_connected,
            "message": "SAP connection test completed",
            "timestamp": datetime.now().isoformat()
        }), 200
    except Exception as e:
        return jsonify({
            "connected": False,
            "error": str(e),
            "message": "SAP connection test failed",
            "timestamp": datetime.now().isoformat()
        }), 500


# (Optional) claim a specific process order by id (supervisor override)
@process_orders_bp.post("/process_orders/<int:po_id>/claim")
def claim_specific_process_order(po_id: int):
    """
    Claim a specific process order by id, then ensure an 'orders' row exists.
    Returns both records.
    """
    with postgres_engine.connect() as conn:
        claimed = conn.execute(text("""
            UPDATE process_orders
            SET status = 'InProgress', updated_at = NOW()
            WHERE id = :id AND status IN ('Open','Pending')
            RETURNING id, order_id, material, version, batch, quantity, unit, status, priority, plant, confirmed_qty, material_desc, created_at
        """), {"id": po_id}).mappings().first()

        if not claimed:
            conn.rollback()
            return jsonify({"error": "Order not claimable (not found or already in progress)"}), 409

        order_row = _ensure_order_from_po(conn, claimed.id)

        conn.commit()

        return jsonify({
            "claimed_process_order": _row_to_api(claimed),
            "execution_order": {
                "id": order_row["id"],
                "po_number": order_row["po_number"],
                "material": order_row["material"],
                "version": order_row["version"],
                "batch": order_row["batch"],
                "quantity": float(order_row["quantity"]) if order_row["quantity"] is not None else None,
                "unit": order_row["unit"],
                "plant": order_row["plant"],
                "confirmed_qty": float(order_row["confirmed_qty"]) if order_row["confirmed_qty"] is not None else None,
                "material_desc": order_row["material_desc"],
                "status": order_row["status"],
                "created_at": order_row["created_at"].isoformat() if order_row["created_at"] else None,
            }
        }), 200


@process_orders_bp.post("/process_orders/<int:po_id>/validate")
def validate_process_order(po_id: int):
    """
    Validate a process order and store the result in the orders table.
    Body:
      { 
        "status": "Validated" | "Rejected", 
        "remarks": "validation notes",
        "confirmed_text": "confirmation text",
        "scrap": "scrap quantity",
        "confirmed_qty": "confirmed quantity (allows partial confirmation)"
      }
    """
    payload = request.get_json(silent=True) or {}
    status = payload.get("status")
    remarks = payload.get("remarks", "")
    confirmed_text = payload.get("confirmed_text")
    scrap = payload.get("scrap")
    confirmed_qty = payload.get("confirmed_qty")  # Allow partial confirmation
    
    if status not in ["Validated", "Rejected"]:
        return jsonify({"error": "Status must be 'Validated' or 'Rejected'"}), 400
    
    try:
        with postgres_engine.connect() as conn:
            # 1) Update the process_orders status
            # If confirmed_qty is provided, use it; otherwise keep the existing confirmed_qty
            update_query = """
                UPDATE process_orders
                SET status = :status, updated_at = NOW(), validation_method = :validation_method, 
                    confirmed_text = :confirmed_text, scrap = :scrap
            """
            params = {
                "id": po_id, 
                "status": status, 
                "validation_method": "Manual",
                "confirmed_text": confirmed_text,
                "scrap": scrap
            }
            
            # Add confirmed_qty update if provided (allows partial confirmation)
            if confirmed_qty is not None:
                update_query += ", confirmed_qty = :confirmed_qty"
                params["confirmed_qty"] = confirmed_qty
            
            update_query += """
                WHERE id = :id
                RETURNING id, order_id, material, version, batch, quantity, unit, status, priority, plant, confirmed_qty, material_desc, created_at
            """
            
            updated_po = conn.execute(text(update_query), params).mappings().first()
            
            if not updated_po:
                return jsonify({"error": "Process order not found"}), 404
            
            # 2) Store the validation result in orders table
            # Use the provided confirmed_qty if available, otherwise use the updated_po.confirmed_qty
            final_confirmed_qty = confirmed_qty if confirmed_qty is not None else updated_po.confirmed_qty
            
            conn.execute(text("""
                INSERT INTO orders (po_number, material, version, batch, quantity, unit, plant, confirmed_qty, material_desc, status, confirmed_text, scrap, created_at, updated_at)
                VALUES (:po_number, :material, :version, :batch, :quantity, :unit, :plant, :confirmed_qty, :material_desc, :status, :confirmed_text, :scrap, NOW(), NOW())
                ON CONFLICT (po_number) DO UPDATE
                SET material = EXCLUDED.material,
                    version = EXCLUDED.version,
                    batch = EXCLUDED.batch,
                    quantity = EXCLUDED.quantity,
                    unit = EXCLUDED.unit,
                    plant = EXCLUDED.plant,
                    confirmed_qty = EXCLUDED.confirmed_qty,
                    material_desc = EXCLUDED.material_desc,
                    status = EXCLUDED.status,
                    confirmed_text = EXCLUDED.confirmed_text,
                    scrap = EXCLUDED.scrap,
                    updated_at = NOW()
            """), {
                "po_number": updated_po.order_id,
                "material": updated_po.material,
                "version": updated_po.version,
                "batch": updated_po.batch,
                "quantity": updated_po.quantity,
                "unit": updated_po.unit,
                "plant": updated_po.plant,
                "confirmed_qty": final_confirmed_qty,
                "material_desc": updated_po.material_desc,
                "status": status,
                "confirmed_text": confirmed_text,
                "scrap": scrap
            })
            
            conn.commit()
            
            # Check if this is a partial confirmation
            is_partial = confirmed_qty is not None and confirmed_qty != updated_po.quantity
            partial_info = ""
            if is_partial:
                partial_info = f" (Partial: {final_confirmed_qty}/{updated_po.quantity} {updated_po.unit})"
            
            return jsonify({
                "message": f"Order {updated_po.order_id} {status.lower()} successfully{partial_info}",
                "process_order": _row_to_api(updated_po),
                "status": status,
                "remarks": remarks,
                "confirmed_text": confirmed_text,
                "scrap": scrap,
                "is_partial_confirmation": is_partial,
                "partial_info": {
                    "confirmed_qty": final_confirmed_qty,
                    "total_qty": updated_po.quantity,
                    "unit": updated_po.unit,
                    "completion_percentage": round((final_confirmed_qty / updated_po.quantity) * 100, 2) if updated_po.quantity > 0 else 0
                } if is_partial else None
            }), 200
            
    except Exception as e:
        return jsonify({"error": f"Validation failed: {str(e)}"}), 500

def get_shift_manual_used(conn, process_order_id, shift_letter):
    """
    Returns total manually confirmed weight for a specific order + shift.
    """
    rows = conn.execute(text("""
        SELECT COALESCE(SUM(confirmed_weight), 0) AS total
        FROM manual_confirmations
        WHERE process_order_id = :oid
          AND shift_code = :shift
          AND synced_to_sap = TRUE
    """), {
        "oid": process_order_id,
        "shift": shift_letter.upper()
    }).mappings().first()

    return float(rows.total or 0)
# @process_orders_bp.post("/process_orders/push-confirmation")
# def push_confirmation():
#     """
#     Clean + correct mid-shift manual + shift-end confirmation.
#     Fixes:
#       ✔ Correct WHERE clause (uses po.id instead of po.order_id)
#       ✔ Never duplicates manual confirmations
#       ✔ Prevents double-shift confirmation
#       ✔ Sends manual + shift-end in one single batch
#       ✔ Marks manual confirmations as synced safely
#       ✔ Updates shift flags, confirmed_shift_X, last_confirmed_qty
#     """
#     from services.system_logger import log_hercules_event
#     from services.sap_confirmation import confirm_orders_batch, SAPConfirmationService
#     import json

#     payload = request.get_json(silent=True) or {}
#     order_ids = payload.get("order_ids", [])
#     operator = payload.get("operator", "manual")

#     # Log start
#     try:
#         log_hercules_event(
#             action="Push Confirmation Started",
#             status="InProgress",
#             details=f"Pushing confirmations for {order_ids}",
#             operator=operator
#         )
#     except:
#         pass

#     try:
#         with postgres_engine.connect() as conn:

#             #---------------------------------------------------------
#             # 1) Load UNSYNCED manual confirmations
#             #---------------------------------------------------------
#             manual_rows = conn.execute(text("""
#                 SELECT mc.id manual_id,
#                        mc.process_order_id,
#                        po.order_id AS po_number,
#                        mc.shift_code,
#                        mc.confirmed_weight,
#                        po.material,
#                        po.version,
#                        po.material_desc,
#                        po.quantity as total_qty,
#                        po.unit as uom,
#                        po.plant,
#                        po.batch,
#                        po.created_at
#                 FROM manual_confirmations mc
#                 JOIN process_orders po ON po.id = mc.process_order_id
#                 WHERE mc.synced_to_sap = FALSE
#                 ORDER BY mc.id
#             """)).mappings().all()

#             manual_payloads = []
#             unsynced_sum = {}

#             for m in manual_rows:
#                 key = (m.process_order_id, m.shift_code.upper())
#                 unsynced_sum[key] = unsynced_sum.get(key, 0) + float(m.confirmed_weight)

#                 manual_payloads.append({
#                     "type": "manual",
#                     "manual_id": m.manual_id,
#                     "process_order_id": m.process_order_id,
#                     "po_number": m.po_number,
#                     "material": m.material,
#                     "version": m.version,
#                     "material_desc": m.material_desc,
#                     "total_qty": float(m.total_qty or 0),
#                     "confirmed_weight": float(m.confirmed_weight or 0),
#                     "uom": m.uom or "KG",
#                     "plant": m.plant,
#                     "batch": m.batch,
#                     "shift": m.shift_code.upper(),
#                     "confirmed_text": "MID-SHIFT MANUAL",
#                     "scrap": 0
#                 })

#             #---------------------------------------------------------
#             # 2) Load PROCESS ORDERS requested by frontend
#             #---------------------------------------------------------
#             if not order_ids:
#                 return jsonify({
#                     "message": "No orders selected",
#                     "successful_count": 0,
#                     "failed_count": 0,
#                     "results": []
#                 }), 200

#             placeholders = ", ".join([f":id{i}" for i in range(len(order_ids))])
#             params = {f"id{i}": int(oid) for i, oid in enumerate(order_ids)}

#             auto_rows = conn.execute(text(f"""
#                 SELECT  po.id AS pid,
#                         po.order_id AS po_number,
#                         po.material,
#                         po.version,
#                         po.material_desc,
#                         po.quantity AS total_qty,
#                         po.unit AS uom,
#                         po.plant,
#                         po.batch,
#                         po.created_at,
#                         po.last_confirmed_qty,
#                         po.current_shift,
#                         po.weight_shift_a,
#                         po.weight_shift_b,
#                         po.weight_shift_c,
#                         po.confirmed_shift_a,
#                         po.confirmed_shift_b,
#                         po.confirmed_shift_c,
#                         po.is_final_sent
#                 FROM process_orders po
#                 WHERE po.id IN ({placeholders})
#                   AND po.status IN ('Validated','InProgress')
#             """), params).mappings().all()

#             #---------------------------------------------------------
#             # 3) Prepare SHIFT-END payloads (skip active shift)
#             #---------------------------------------------------------
#             shift_payloads = []

#             # Preload already-synced manual confirmations
#             synced_rows = conn.execute(text("""
#                 SELECT process_order_id, shift_code, SUM(confirmed_weight) total
#                 FROM manual_confirmations
#                 WHERE synced_to_sap = TRUE
#                 GROUP BY process_order_id, shift_code
#             """)).mappings().all()

#             synced_sum = {
#                 (r.process_order_id, r.shift_code.upper()): float(r.total or 0)
#                 for r in synced_rows
#             }

#             for r in auto_rows:

#                 if r.is_final_sent:
#                     continue

#                 shifts = [
#                     ("A", r.weight_shift_a, r.confirmed_shift_a),
#                     ("B", r.weight_shift_b, r.confirmed_shift_b),
#                     ("C", r.weight_shift_c, r.confirmed_shift_c),
#                 ]

#                 current_shift = (r.current_shift or "").upper()

#                 for letter, raw_weight, confirmed_flag in shifts:

#                     if letter == current_shift:
#                         continue  # never confirm active shift

#                     raw_weight = float(raw_weight or 0)
#                     if raw_weight <= 0:
#                         continue

#                     confirmed_flag = float(confirmed_flag or 0)
#                     if confirmed_flag > 0:
#                         continue  # already confirmed earlier

#                     key = (r.pid, letter)
#                     used_manual = synced_sum.get(key, 0) + unsynced_sum.get(key, 0)
#                     remaining = raw_weight - used_manual

#                     if remaining <= 0:
#                         continue

#                     shift_payloads.append({
#                         "type": "shift",
#                         "process_order_id": r.pid,
#                         "po_number": r.po_number,
#                         "material": r.material,
#                         "version": r.version,
#                         "material_desc": r.material_desc,
#                         "total_qty": float(r.total_qty),
#                         "confirmed_weight": float(remaining),
#                         "uom": r.uom,
#                         "plant": r.plant,
#                         "batch": r.batch,
#                         "shift": letter,
#                         "last_confirmed_qty": float(r.last_confirmed_qty),
#                     })

#             #---------------------------------------------------------
#             # NO DATA?
#             #---------------------------------------------------------
#             if not manual_payloads and not shift_payloads:
#                 return jsonify({
#                     "message": "Nothing to confirm",
#                     "successful_count": 0,
#                     "failed_count": 0,
#                     "results": []
#                 }), 200

#             batch_payload = manual_payloads + shift_payloads

#             #---------------------------------------------------------
#             # 4) SEND TO SAP
#             #---------------------------------------------------------
#             try:
#                 result = confirm_orders_batch(batch_payload, "online")
#             except:
#                 sap = SAPConfirmationService()
#                 result = sap.confirm_orders_batch(batch_payload, "online")

#             success_ids = {str(x).lstrip("0") for x in result.get("successful_orders", [])}

#             results = []
#             failed = []

#             #---------------------------------------------------------
#             # 5) MARK manual confirmations as synced
#             #---------------------------------------------------------
#             with postgres_engine.begin() as tx:

#                 for m in manual_payloads:
#                     po_norm = str(m["po_number"]).lstrip("0")

#                     if po_norm in success_ids:
#                         tx.execute(text("""
#                             UPDATE manual_confirmations
#                             SET synced_to_sap = TRUE,
#                                 sap_response = :resp,
#                                 updated_at = NOW()
#                             WHERE id = :mid
#                         """), {"mid": m["manual_id"], "resp": json.dumps({"status": "confirmed"})})

#                         results.append({"process_order": m["po_number"], "status": "Manual Confirmed"})
#                     else:
#                         failed.append(m["po_number"])
#                         results.append({"process_order": m["po_number"], "status": "Manual Failed"})

#                 #-----------------------------------------------------
#                 # 6) APPLY shift-end confirmations to DB
#                 #-----------------------------------------------------
#                 for s in shift_payloads:
#                     po_norm = str(s["po_number"]).lstrip("0")

#                     if po_norm not in success_ids:
#                         failed.append(s["po_number"])
#                         results.append({"process_order": s["po_number"], "status": "Shift Failed"})
#                         continue

#                     new_last = s["last_confirmed_qty"] + s["confirmed_weight"]
#                     is_final = new_last >= s["total_qty"]

#                     letter = s["shift"].lower()

#                     tx.execute(text(f"""
#                         UPDATE process_orders
#                         SET confirmed_shift_{letter} = :w,
#                             last_confirmed_qty = :lc,
#                             is_final_sent = :final,
#                             updated_at = NOW(),
#                             status = CASE WHEN :final THEN 'Confirmed' ELSE 'InProgress' END
#                         WHERE order_id = :po
#                     """), {
#                         "w": s["confirmed_weight"],
#                         "lc": new_last,
#                         "final": is_final,
#                         "po": s["po_number"]
#                     })

#                     results.append({
#                         "process_order": s["po_number"],
#                         "status": "Shift Confirmed",
#                         "final": is_final
#                     })

#             return jsonify({
#                 "message": "Push confirmation complete",
#                 "successful_count": len(success_ids),
#                 "failed_count": len(failed),
#                 "results": results
#             }), 200

#     except Exception as e:
#         return jsonify({"error": str(e)}), 500
@process_orders_bp.post("/process_orders/push-confirmation")
def push_confirmation():
    """
    ✅ FIXED: Mid-shift + shift-end confirmation with proper deduplication.
    
    Features:
      - Mid-shift: User clicks button → sends current shift production
      - Shift-end: Auto-scheduler → sends remaining production only
      - Deduplication: weight_shift_X - confirmed_shift_X = remaining
      - Accumulates confirmed_shift_X properly (no double-counting)
    """
    from services.system_logger import log_hercules_event
    from services.sap_confirmation import SAPConfirmationService
    from datetime import datetime
    import json

    payload = request.get_json(silent=True) or {}
    order_ids = payload.get("order_ids", [])
    operator = payload.get("operator", "manual")
    confirm_current_shift = payload.get("confirm_current_shift", False)  # Mid-shift flag

    # Log start
    try:
        log_hercules_event(
            action="Push Confirmation Started",
            status="InProgress",
            details=f"Pushing confirmations for {order_ids} (mid_shift={confirm_current_shift})",
            operator=operator
        )
    except:
        pass

    try:
        with postgres_engine.connect() as conn:

            #---------------------------------------------------------
            # 1) Load PROCESS ORDERS
            #---------------------------------------------------------
            if not order_ids:
                return jsonify({
                    "message": "No orders selected",
                    "successful_count": 0,
                    "failed_count": 0,
                    "results": []
                }), 200

            placeholders = ", ".join([f":id{i}" for i in range(len(order_ids))])
            params = {f"id{i}": int(oid) for i, oid in enumerate(order_ids)}

            rows = conn.execute(text(f"""
                SELECT  
                    po.id AS pid,
                    po.order_id AS po_number,
                    po.material,
                    po.version,
                    po.material_desc,
                    po.quantity AS total_qty,
                    po.unit AS uom,
                    po.plant,
                    po.batch,
                    po.created_at,
                    po.last_confirmed_qty,
                    po.current_shift,
                    po.weight_shift_a,
                    po.weight_shift_b,
                    po.weight_shift_c,
                    po.confirmed_shift_a,
                    po.confirmed_shift_b,
                    po.confirmed_shift_c,
                    po.is_final_sent,
                    po.status,
                    po.priority,
                    po.scale1,
                    po.scale1_qty,
                    po.scale2,
                    po.scale2_qty,
                    po.scale3,
                    po.scale3_qty,
                    po.scrap
                FROM process_orders po
                WHERE po.id IN ({placeholders})
                  AND po.status IN ('Validated','Completed','InProgress')
            """), params).mappings().all()

            #---------------------------------------------------------
            # 2) ✅ Build SAP payloads with proper remaining calculation
            #---------------------------------------------------------
            sap_payloads = []
            skipped_orders = []  # Track orders skipped due to zero production

            for r in rows:

                # ✅ For validated orders, check remaining production even if is_final_sent is False
                # (is_final_sent might be False if order was validated mid-shift)
                order_status = getattr(r, 'status', 'InProgress') if hasattr(r, 'status') else 'InProgress'
                is_validated = (order_status or "").upper() in ("VALIDATED", "COMPLETED")
                
                # Only skip if is_final_sent AND no remaining production
                if r.is_final_sent and not is_validated:
                    continue

                shifts = [
                    ("A", r.weight_shift_a, r.confirmed_shift_a),
                    ("B", r.weight_shift_b, r.confirmed_shift_b),
                    ("C", r.weight_shift_c, r.confirmed_shift_c),
                ]

                order_current_shift = (r.current_shift or "").upper()

                # ✅ Calculate total already confirmed to SAP (from all shifts)
                total_confirmed_to_sap = float(r.confirmed_shift_a or 0) + float(r.confirmed_shift_b or 0) + float(r.confirmed_shift_c or 0)
                target = float(r.total_qty or 0)
                remaining_to_target = max(0, target - total_confirmed_to_sap)

                # ✅ CRITICAL: For validated orders, send remaining to target in ONE confirmation (not per shift)
                if is_validated and remaining_to_target > 0:
                    # ✅ For validated orders: Send remaining to target (target - already_sent)
                    # Example: target=500, already_sent=160, send=340 (not 500)
                    # Find the shift with the most remaining production to use for shift field
                    max_remaining_shift = None
                    max_remaining = 0
                    for shift_letter, weight_produced, weight_confirmed in shifts:
                        total_produced = float(weight_produced or 0)
                        already_sent_for_shift = float(weight_confirmed or 0)
                        remaining_in_shift = total_produced - already_sent_for_shift
                        if remaining_in_shift > max_remaining:
                            max_remaining = remaining_in_shift
                            max_remaining_shift = shift_letter
                    
                    if max_remaining_shift:
                        # ✅ Send remaining to target (not full target, not overflow)
                        remaining = remaining_to_target
                        is_final = True  # Always final for validated orders
                        
                        # ✅ Build payload (send only REMAINING to target, not full target)
                        sap_payloads.append({
                            "po_number": r.po_number,
                            "process_order_id": r.pid,
                            "material": r.material,
                            "version": r.version or "",
                            "material_desc": r.material_desc or "",
                            "total_qty": target,
                            "confirmed_weight": float(remaining),  # ✅ Only send remaining (target - already_sent)
                            "uom": r.uom or "KG",
                            "plant": r.plant,
                            "created_at": r.created_at.isoformat() if r.created_at else datetime.now().isoformat(),  # ✅ Convert datetime to string
                            "batch": r.batch or "",
                            "shift": max_remaining_shift,
                            "priority": r.priority or 1,
                            "last_confirmed_qty": float(r.last_confirmed_qty or 0),
                            "is_final_sent": False,
                            "order_current_shift": order_current_shift,
                            "order_status": order_status,
                            "is_final_confirmation": is_final,  # ✅ Final confirmation for validated orders
                            "scale1": r.scale1 or "",
                            "scale1_qty": float(r.scale1_qty or 0),
                            "scale2": r.scale2 or "",
                            "scale2_qty": float(r.scale2_qty or 0),
                            "scale3": r.scale3 or "",
                            "scale3_qty": float(r.scale3_qty or 0),
                            "scrap": float(r.scrap or 0),
                        })
                    else:
                        # Validated order but no remaining production in any shift
                        skipped_orders.append({
                            "po_number": r.po_number,
                            "process_order_id": r.pid,
                            "reason": f"Validated order has no remaining production to confirm (remaining_to_target={remaining_to_target:.2f})",
                            "shift": "N/A",
                            "order_status": order_status
                        })
                    continue  # Skip per-shift processing for validated orders

                # ✅ For InProgress orders: Process per shift
                order_has_production = False  # Track if order has any production to confirm
                for shift_letter, weight_produced, weight_confirmed in shifts:

                    # ✅ For inprogress orders, skip active shift UNLESS mid-shift confirmation requested
                    if shift_letter == order_current_shift and not confirm_current_shift:
                        continue

                    # ✅ Calculate REMAINING production for this shift
                    # Formula: total_produced - already_sent_to_SAP = remaining
                    total_produced = float(weight_produced or 0)
                    already_sent = float(weight_confirmed or 0)
                    remaining = total_produced - already_sent

                    if remaining <= 0:
                        continue  # Nothing new to confirm for this shift
                    
                    order_has_production = True  # Order has at least one shift with production
                    
                    # ✅ For InProgress orders, check if this is the final confirmation
                    current_last = float(r.last_confirmed_qty or 0)
                    new_total = current_last + remaining
                    is_final = new_total >= target

                    # ✅ Build payload (send only REMAINING production)
                    # ✅ CRITICAL: Always include byproduct scales (even if order not validated)
                    sap_payloads.append({
                        "po_number": r.po_number,
                        "process_order_id": r.pid,
                        "material": r.material,
                        "version": r.version or "",
                        "material_desc": r.material_desc or "",
                        "total_qty": float(r.total_qty),
                        "confirmed_weight": float(remaining),  # ✅ Only send remaining
                        "uom": r.uom or "KG",
                        "plant": r.plant,
                        "created_at": r.created_at.isoformat() if r.created_at else datetime.now().isoformat(),  # ✅ Convert datetime to string
                        "batch": r.batch or "",
                        "shift": shift_letter,
                        "priority": r.priority or 1,
                        "last_confirmed_qty": float(r.last_confirmed_qty or 0),
                        "is_final_sent": False,
                        "order_current_shift": order_current_shift,
                        "order_status": order_status,  # ✅ Add order status
                        "is_final_confirmation": is_final,  # ✅ Add final confirmation flag
                        # ✅ CRITICAL: Always include byproduct scales (scale1, scale2, scale3 and their quantities)
                        # This ensures they appear in SAP payload for mid-shift and end-shift confirmations
                        "scale1": r.scale1 or "",
                        "scale1_qty": float(r.scale1_qty or 0),
                        "scale2": r.scale2 or "",
                        "scale2_qty": float(r.scale2_qty or 0),
                        "scale3": r.scale3 or "",
                        "scale3_qty": float(r.scale3_qty or 0),
                        "scrap": float(r.scrap or 0),
                    })
                
                # If InProgress order has no production in any shift, add to skipped
                if not order_has_production and not is_validated:
                    skipped_orders.append({
                        "po_number": r.po_number,
                        "process_order_id": r.pid,
                        "reason": f"InProgress order has no remaining production to confirm (all shifts already confirmed or zero production)",
                        "shift": order_current_shift,
                        "order_status": order_status
                    })

            #---------------------------------------------------------
            # ✅ SKIPPED ORDERS - DO NOT log to error_log
            # Skipped orders (no production to confirm) are NOT errors
            # Error log should ONLY contain actual SAP communication errors
            # Just log to console for debugging purposes
            #---------------------------------------------------------
            if skipped_orders:
                for skipped in skipped_orders:
                    log.info(f"⏭️ Skipped order {skipped.get('po_number')}: {skipped.get('reason')}")

            #---------------------------------------------------------
            # NO DATA?
            #---------------------------------------------------------
            if not sap_payloads and not skipped_orders:
                return jsonify({
                    "message": "Nothing to confirm",
                    "successful_count": 0,
                    "failed_count": 0,
                    "skipped_count": 0,
                    "results": []
                }), 200
            
            # If only skipped orders, return them in response
            if not sap_payloads and skipped_orders:
                skipped_results = []
                for skipped in skipped_orders:
                    skipped_results.append({
                        "process_order": skipped.get("po_number"),
                        "status": "Skipped",
                        "message": skipped.get("reason", "No production to confirm"),
                        "shift": skipped.get("shift", "N/A")
                    })
                return jsonify({
                    "message": f"No orders to confirm. {len(skipped_orders)} order(s) skipped (zero production).",
                    "successful_count": 0,
                    "failed_count": 0,
                    "skipped_count": len(skipped_orders),
                    "skipped_orders": [s.get("po_number") for s in skipped_orders],
                    "results": skipped_results
                }), 200

            #---------------------------------------------------------
            # 3) ✅ SEND TO SAP
            #---------------------------------------------------------
            sap_service = SAPConfirmationService()
            
            # ✅ Import error logger
            #---------------------------------------------------------
            # 3) Check VPN and Push to SAP or Store Offline
            # Skip VPN check if using mock mode (demo server)
            # Use the same mock mode detection as SAPConfirmationService
            #---------------------------------------------------------
            if sap_service.mock_mode:
                # Mock mode: Skip VPN check, always send to demo server
                log.info("🔧 Mock mode enabled - skipping VPN check, sending to demo server")
                vpn_status = {"connected": True, "message": "Mock mode - using demo server"}
            else:
                # Real SAP mode: Check VPN connection
                from utils.vpn_check import check_vpn_connection
                vpn_status = check_vpn_connection()
            
            if not vpn_status["connected"]:
                # --- OFFLINE MODE ---
                # Store in offline_confirmations table
                log.warning(f"⚠️ VPN disconnected: Storing {len(sap_payloads)} orders for offline confirmation")
                
                stored_count = 0
                stored_orders = []
                processed_po_numbers = set()  # Track PO numbers processed in this batch
                
                # We need to serialize the payload to JSON string for the INSERT
                import json
                
                for p in sap_payloads:
                    try:
                        po_number = p.get("po_number")
                        if not po_number:
                            log.error(f"❌ No PO number found, skipping")
                            continue
                        
                        po_num_stripped = str(po_number).lstrip('0')
                        if not po_num_stripped or po_num_stripped == '':
                            po_num_stripped = str(po_number)
                        
                        log.info(f"🔍 [VPN Offline] Checking duplicate for PO: original={po_number}, stripped={po_num_stripped}")
                        
                        # Get order status first to determine duplicate handling
                        order_status = p.get("order_status", "").upper() if p.get("order_status") else ""
                        
                        # First check: Is this PO already processed in this batch?
                        if po_num_stripped in processed_po_numbers:
                            log.warning(f"⏭️ [VPN Offline] DUPLICATE IN BATCH: Order {po_number} (stripped: '{po_num_stripped}') already processed - skipping")
                            continue
                        
                        # Second check: Database duplicate check
                        # ✅ For ALL orders (validated or partial): Check for existing and UPDATE (accumulate)
                        all_pending = conn.execute(text("""
                            SELECT id, order_id, confirmed_weight, scrap FROM offline_confirmations 
                            WHERE status = 'pending'
                        """)).fetchall()
                        
                        log.info(f"🔍 [VPN Offline] Found {len(all_pending)} pending records in database, {len(processed_po_numbers)} in current batch")
                        
                        existing = None
                        existing_id = None
                        existing_weight = 0
                        existing_scrap = 0
                        for pending_row in all_pending:
                            pending_id = pending_row[0]
                            pending_order_id = pending_row[1]
                            pending_weight = float(pending_row[2] or 0)
                            pending_scrap = float(pending_row[3] or 0)
                            
                            if not pending_order_id:
                                continue
                            
                            pending_stripped = str(pending_order_id).lstrip('0')
                            if not pending_stripped or pending_stripped == '':
                                pending_stripped = str(pending_order_id)
                            
                            # Ensure both are non-empty before comparing
                            if not po_num_stripped or not pending_stripped:
                                log.warning(f"⚠️ [VPN Offline] Empty PO number detected: new={po_num_stripped}, existing={pending_stripped}")
                                continue
                            
                            # Exact string comparison (case-sensitive)
                            is_match = (pending_stripped == po_num_stripped)
                            log.info(f"   [VPN Offline] Compare: '{po_num_stripped}' == '{pending_stripped}'? {is_match} (existing order_id={pending_order_id})")
                            
                            if is_match:
                                existing = pending_row
                                existing_id = pending_id
                                existing_weight = pending_weight
                                existing_scrap = pending_scrap
                                log.info(f"🔍 [VPN Offline] Found existing offline record for PO {po_number}: ID={pending_id}, weight={pending_weight}")
                                break
                        
                        # ✅ CRITICAL FIX: If existing record found, UPDATE it (accumulate weight) instead of skipping
                        if existing:
                            new_weight = float(p.get('confirmed_weight', 0))
                            new_scrap = float(p.get('scrap', 0))
                            accumulated_weight = existing_weight + new_weight
                            accumulated_scrap = existing_scrap + new_scrap
                            is_final = p.get('is_final_confirmation', False)
                            
                            # ✅ FIX: Use empty string for confirmed_text - don't access undefined variable
                            confirmed_text = ""
                            
                            # Update existing record
                            conn.execute(text("""
                                UPDATE offline_confirmations
                                SET confirmed_weight = :weight,
                                    scrap = :scrap,
                                    sap_payload = :payload,
                                    updated_at = NOW()
                                WHERE id = :id
                            """), {
                                "weight": accumulated_weight,
                                "scrap": accumulated_scrap,
                                "payload": json.dumps(p, default=str),
                                "id": existing_id
                            })
                            
                            log.info(f"✅ [VPN Offline] UPDATED existing offline confirmation for PO {po_number}: {existing_weight:.2f} + {new_weight:.2f} = {accumulated_weight:.2f} (is_final={is_final})")
                            stored_count += 1
                            stored_orders.append(po_number)
                            processed_po_numbers.add(po_num_stripped)
                            continue  # Skip INSERT, we already updated
                        
                        # Mark this PO as processed in this batch
                        processed_po_numbers.add(po_num_stripped)
                        
                        log.info(f"✅ [VPN Offline] NEW ORDER: PO {po_number} (stripped: {po_num_stripped}) - storing...")
                        
                        # Insert into offline_confirmations
                        ins_sql = text("""
                            INSERT INTO offline_confirmations 
                            (order_id, process_order_id, material, version, confirmed_weight, total_qty, uom, 
                             plant, batch, shift, scrap, confirmed_text, sap_payload, validation_method, status, created_at, updated_at)
                            VALUES 
                            (:po_number, :pid, :material, :version, :confirmed_weight, :total_qty, :uom, 
                             :plant, :batch, :shift, :scrap, '', :sap_payload, :val_method, 'pending', NOW(), NOW())
                        """)
                        
                        # Determine validation method
                        val_method = "Automatic" if operator == "auto_validator" else "Manual"
                        if payload.get("operator") == "shift_auto_confirm":
                            val_method = "ShiftAuto"
                            
                        conn.execute(ins_sql, {
                            "po_number": p.get("po_number"),
                            "pid": p.get("process_order_id"),
                            "material": p.get("material"),
                            "version": p.get("version"),
                            "confirmed_weight": p.get("confirmed_weight"),
                            "total_qty": p.get("total_qty"),
                            "uom": p.get("uom"),
                            "plant": p.get("plant"),
                            "batch": p.get("batch"),
                            "shift": p.get("shift"),
                            "scrap": p.get("scrap", 0.0),
                            "sap_payload": json.dumps(p, default=str),  # Store the internal payload format (default=str handles datetime objects)
                            "val_method": val_method
                        })
                        stored_count += 1
                        stored_orders.append(p.get("po_number"))
                    except Exception as e:
                        log.error(f"Failed to store offline order {p.get('po_number')}: {e}")
                
                # ✅ Update process_orders - treat offline as confirmed (so order disappears from list)
                if stored_count > 0:
                    try:
                        for p in sap_payloads:
                            po_number = p.get("po_number")
                            if not po_number:
                                continue
                            
                            shift = (p.get('shift') or '').upper()
                            confirmed_weight = float(p.get('confirmed_weight', 0))
                            is_final = p.get('is_final', False)
                            
                            if shift in ('A', 'B', 'C'):
                                shift_col = f"confirmed_shift_{shift.lower()}"
                                
                                if shift == 'A':
                                    last_calc = f"(COALESCE(confirmed_shift_a, 0) + :w) + COALESCE(confirmed_shift_b, 0) + COALESCE(confirmed_shift_c, 0)"
                                elif shift == 'B':
                                    last_calc = f"COALESCE(confirmed_shift_a, 0) + (COALESCE(confirmed_shift_b, 0) + :w) + COALESCE(confirmed_shift_c, 0)"
                                else:
                                    last_calc = f"COALESCE(confirmed_shift_a, 0) + COALESCE(confirmed_shift_b, 0) + (COALESCE(confirmed_shift_c, 0) + :w)"
                                
                                # Use LTRIM to match regardless of leading zeros
                                conn.execute(text(f"""
                                    UPDATE process_orders
                                    SET {shift_col} = COALESCE({shift_col}, 0) + :w,
                                        last_confirmed_qty = {last_calc},
                                        is_final_sent = CASE WHEN :is_final THEN TRUE ELSE is_final_sent END,
                                        status = CASE WHEN :is_final THEN 'Validated' ELSE status END,
                                        updated_at = NOW()
                                    WHERE LTRIM(order_id, '0') = LTRIM(:po, '0')
                                """), {"w": confirmed_weight, "is_final": is_final, "po": str(po_number)})
                                log.info(f"✅ [VPN Offline] Updated PO {po_number} (shift {shift}) - status=Validated only when final")
                            else:
                                # No shift info: only set Validated when final, else keep current status
                                conn.execute(text("""
                                    UPDATE process_orders
                                    SET status = CASE WHEN :is_final THEN 'Validated' ELSE status END,
                                        updated_at = NOW()
                                    WHERE LTRIM(order_id, '0') = LTRIM(:po, '0')
                                """), {"po": str(po_number), "is_final": is_final})
                                log.info(f"✅ [VPN Offline] Updated PO {po_number} (no shift info) - status=Validated only when final")
                    except Exception as update_err:
                        log.error(f"❌ [VPN Offline] Failed to update process_orders: {update_err}")
                        import traceback
                        traceback.print_exc()
                
                conn.commit()
                
                return jsonify({
                    "success": False,
                    "offline_mode": True,
                    "message": "VPN disconnected - orders stored for offline confirmation",
                    "stored_count": stored_count,
                    "stored_orders": stored_orders,
                    "vpn_status": vpn_status
                }), 200

            # --- ONLINE MODE (Proceed as normal) ---
            from services.error_logger import log_order_error
            
            # ✅ LOG TO JSON FILE - Push Confirmation (Auto/Mid-shift)
            from utils.sap_logger import log_sap_request, log_sap_response
            import time as time_module
            start_time = time_module.time()
            
            # Log each order's request to JSON
            db_log_ids = {}
            for payload in sap_payloads:
                po_num = payload.get("po_number", "unknown")
                print(f"🚀🚀🚀 [PUSH CONFIRM] Logging SAP request for PO {po_num}")
                try:
                    db_log_id = log_sap_request(
                        endpoint=sap_service._get_url("/sap/opu/odata/sap/ZSFMSPP_PROCESSORDERS_SRV/ProcessOrdersConfirmationSet"),
                        method="POST",
                        payload=payload,
                        po_number=po_num,
                        log_type="push_confirmation"
                    )
                    db_log_ids[po_num] = db_log_id
                    print(f"✅ [PUSH CONFIRM] JSON log created for PO {po_num} with ID: {db_log_id}")
                except Exception as log_err:
                    print(f"⚠️ [PUSH CONFIRM] Failed to log request for PO {po_num}: {log_err}")
            
            try:
                result = sap_service.confirm_orders_batch(sap_payloads, "auto")
                
                # ✅ LOG SAP RESPONSE for each order
                elapsed_ms = int((time_module.time() - start_time) * 1000)
                success_orders = result.get("successful_orders", [])
                for payload in sap_payloads:
                    po_num = payload.get("po_number", "unknown")
                    db_log_id = db_log_ids.get(po_num)
                    if db_log_id:
                        po_success = str(po_num).lstrip("0") in {str(x).lstrip("0") for x in success_orders}
                        try:
                            log_sap_response(
                                log_id=db_log_id,
                                response_payload=result,
                                status_code=200 if po_success else 500,
                                error_message=None if po_success else result.get("error", "Order not in successful list"),
                                duration_ms=elapsed_ms
                            )
                            print(f"✅ [PUSH CONFIRM] JSON response logged for PO {po_num} - success={po_success}, duration={elapsed_ms}ms")
                        except Exception as log_err:
                            print(f"⚠️ [PUSH CONFIRM] Failed to log response for PO {po_num}: {log_err}")
                
            except Exception as sap_error:
                # If SAP service call itself fails (e.g., connection error), log all orders as failed
                log.error(f"❌ SAP service call failed: {sap_error}")
                elapsed_ms = int((time_module.time() - start_time) * 1000)
                
                for payload in sap_payloads:
                    po = str(payload.get("po_number", "")).lstrip("0")
                    po_num = payload.get("po_number", "unknown")
                    
                    # ✅ LOG ERROR RESPONSE TO JSON
                    db_log_id = db_log_ids.get(po_num)
                    if db_log_id:
                        try:
                            log_sap_response(
                                log_id=db_log_id,
                                response_payload={"error": str(sap_error), "error_type": type(sap_error).__name__},
                                status_code=500,
                                error_message=f"SAP service call failed: {str(sap_error)}",
                                duration_ms=elapsed_ms
                            )
                            print(f"❌ [PUSH CONFIRM] JSON error logged for PO {po_num}: {sap_error}")
                        except Exception as log_err:
                            print(f"⚠️ [PUSH CONFIRM] Failed to log error for PO {po_num}: {log_err}")
                    
                    log_order_error(
                        po_number=po,
                        error_type="sap_failed",
                        error_message=f"SAP service call failed: {str(sap_error)}",
                        payload={
                            "sent_payload": payload,
                            "error": str(sap_error),
                            "error_type": type(sap_error).__name__,
                            "confirmation_type": "auto",
                            "timestamp": datetime.now().isoformat()
                        },
                        source="sap_online"
                    )
                
                return jsonify({
                    "error": f"SAP service call failed: {str(sap_error)}",
                    "message": f"Failed to push {len(sap_payloads)} order(s) to SAP",
                    "successful_count": 0,
                    "failed_count": len(sap_payloads),
                    "results": [{"process_order": p.get("po_number"), "status": "Failed", "message": str(sap_error)} for p in sap_payloads]
                }), 500

            success_ids = {str(x).lstrip("0") for x in result.get("successful_orders", [])}
            failed_orders_list = result.get("failed_orders", [])
            results = []
            failed = []

            #---------------------------------------------------------
            # 4) ✅ FIXED: Update database after SAP success
            #---------------------------------------------------------
            with postgres_engine.begin() as tx:

                for payload in sap_payloads:
                    po_norm = str(payload["po_number"]).lstrip("0")

                    if po_norm not in success_ids:
                        failed.append(payload["po_number"])
                        
                        # ✅ Log failed SAP confirmation to error_log table
                        error_message = "Order not confirmed in SAP"
                        # Try to get more specific error message from failed_orders_list
                        for failed_order in failed_orders_list:
                            if isinstance(failed_order, dict):
                                failed_po = str(failed_order.get("po_number", "")).lstrip("0")
                                if failed_po == po_norm:
                                    error_message = failed_order.get("error", error_message)
                                    break
                            elif str(failed_order).lstrip("0") == po_norm:
                                error_message = "Order not confirmed in SAP"
                                break
                        
                        # Also check if result has an error message
                        if not error_message or error_message == "Order not confirmed in SAP":
                            if result.get("error"):
                                error_message = result.get("error")
                            elif result.get("message"):
                                error_message = result.get("message")
                        
                        log_order_error(
                            po_number=payload["po_number"],
                            error_type="sap_failed",
                            error_message=error_message,
                            payload={
                                "sent_payload": payload,
                                "sap_response": result.get("sap_response", "")[:500] if result.get("sap_response") else "",
                                "failed_orders": failed_orders_list,
                                "result": {
                                    "ok": result.get("ok", False),
                                    "successful_count": result.get("successful_count", 0),
                                    "failed_count": result.get("failed_count", 0)
                                }
                            },
                            source="sap_online"
                        )
                        
                        results.append({
                            "process_order": payload["po_number"],
                            "status": "Failed",
                            "shift": payload["shift"],
                            "message": error_message
                        })
                        continue

                    confirmed_weight = payload["confirmed_weight"]
                    shift_letter = payload["shift"].lower()

                    # ✅ CRITICAL FIX: ADD to confirmed_shift_X (accumulate, don't replace)
                    # This tracks cumulative confirmed weight for deduplication
                    # ✅ Update last_confirmed_qty with sum of all shift confirmations (using NEW value for updated shift)
                    # Calculate last_confirmed_qty using the NEW value for the shift being updated
                    if shift_letter == 'a':
                        # For shift A: use NEW value (old + :w) for A, old values for B and C
                        last_confirmed_calc = "(COALESCE(confirmed_shift_a, 0) + :w) + COALESCE(confirmed_shift_b, 0) + COALESCE(confirmed_shift_c, 0)"
                    elif shift_letter == 'b':
                        # For shift B: use old value for A, NEW value (old + :w) for B, old value for C
                        last_confirmed_calc = "COALESCE(confirmed_shift_a, 0) + (COALESCE(confirmed_shift_b, 0) + :w) + COALESCE(confirmed_shift_c, 0)"
                    else:  # shift_letter == 'c'
                        # For shift C: use old values for A and B, NEW value (old + :w) for C
                        last_confirmed_calc = "COALESCE(confirmed_shift_a, 0) + COALESCE(confirmed_shift_b, 0) + (COALESCE(confirmed_shift_c, 0) + :w)"
                    
                    # Execute the update with proper calculation
                    # ✅ Feb 6, 2026: Also update status to 'Validated' for Completed orders
                    # after successful SAP confirmation (final confirmation)
                    is_final = payload.get("is_final_confirmation", False)
                    order_status = payload.get("order_status", "")
                    
                    # Determine new status:
                    # - Completed + final → Validated (SAP confirmed)
                    # - Already Validated → keep Validated
                    # - Otherwise → keep current status
                    status_update = ""
                    if is_final and (order_status or "").upper() in ("COMPLETED", "VALIDATED"):
                        status_update = ", status = 'Validated'"
                    elif is_final:
                        status_update = ", status = 'Validated'"
                    
                    update_sql = f"""
                        UPDATE process_orders
                        SET confirmed_shift_{shift_letter} = COALESCE(confirmed_shift_{shift_letter}, 0) + :w,
                            last_confirmed_qty = {last_confirmed_calc},
                            updated_at = NOW()
                            {status_update}
                        WHERE id = :pid
                    """
                    tx.execute(text(update_sql), {
                        "w": confirmed_weight,  # ✅ Add only what was just confirmed
                        "pid": payload["process_order_id"]
                    })
                    
                    new_status_msg = f" → status=Validated" if status_update else ""
                    print(f"✅ Updated confirmed_shift_{shift_letter} by {confirmed_weight:.2f} and recalculated last_confirmed_qty{new_status_msg}")

                    conf_type = "Mid-Shift Confirmed" if payload["shift"] == payload["order_current_shift"] else "Shift-End Confirmed"
                    
                    results.append({
                        "process_order": payload["po_number"],
                        "status": conf_type,
                        "confirmed_weight": confirmed_weight,
                        "shift": payload["shift"],
                    })

            # Add skipped orders to results if any
            skipped_results = []
            for skipped in skipped_orders:
                skipped_results.append({
                    "process_order": skipped.get("po_number"),
                    "status": "Skipped",
                    "message": skipped.get("reason", "No production to confirm"),
                    "shift": skipped.get("shift", "N/A")
                })
            
            return jsonify({
                "message": "Push confirmation complete",
                "successful_count": len(success_ids),
                "failed_count": len(failed),
                "skipped_count": len(skipped_orders),
                "skipped_orders": [s.get("po_number") for s in skipped_orders],
                "results": results + skipped_results
            }), 200

    except Exception as e:
        return jsonify({"error": str(e)}), 500


@process_orders_bp.post("/process_orders/test-confirmation")
def test_confirmation():
    """
    Temporary API for testing:
    - Builds SAP payload using existing SAPConfirmationService
    - Does NOT send to SAP
    - Stores payload in sap_confirmation_test table
    - Returns the generated payloads for debugging
    """
    from services.sap_confirmation import SAPConfirmationService

    try:
        with postgres_engine.connect() as conn:

            # ----------------------------------------------------
            # 🔥 DEBUG INFORMATION (to verify DB connection)
            # ----------------------------------------------------
            db_info = conn.execute(text("SELECT current_database()")).scalar()
            print("🔍 Connected DB:", db_info)

            count = conn.execute(text("SELECT COUNT(*) FROM process_orders")).scalar()
            print("🔍 process_orders count:", count)

            statuses = conn.execute(text("SELECT DISTINCT status FROM process_orders")).fetchall()
            print("🔍 statuses:", statuses)

            # ----------------------------------------------------
            # 1) Fetch orders that are Validated or InProgress
            # ----------------------------------------------------
            rows = conn.execute(text("""
                SELECT 
                    order_id as po_number,
                    material,
                    version,
                    material_desc,
                    quantity as total_qty,
                    confirmed_qty,
                    unit as uom,
                    plant,
                    created_at,
                    updated_at as confirmed_at,
                    batch,
                    priority as shift,
                    confirmed_text,
                    scrap,
                    scale1,
                    scale1_qty,
                    scale2,
                    scale2_qty,
                    scale3,
                    scale3_qty
                FROM process_orders
                WHERE status IN ('Validated', 'InProgress')
                ORDER BY id
            """)).mappings().all()

            print("🔍 rows fetched:", len(rows))

            if not rows:
                return jsonify({
                    "message": "No validated or in-progress orders found",
                    "debug": {
                        "connected_db": db_info,
                        "process_orders_count": count,
                        "statuses": [s[0] for s in statuses]
                    }
                }), 200

            # ----------------------------------------------------
            # 2) Convert DB rows → SAP service payload structure
            # ----------------------------------------------------
            orders = []
            for r in rows:
                orders.append({
                    "po_number": r.po_number,
                    "material": r.material,
                    "version": r.version or "",
                    "material_desc": r.material_desc or "",
                    "total_qty": float(r.total_qty or 0),
                    "confirmed_weight": float(r.confirmed_qty or 0),
                    "uom": r.uom or "KG",
                    "plant": r.plant,
                    "created_at": r.created_at,
                    "confirmed_at": r.confirmed_at,
                    "batch": r.batch or "",
                    "shift": "A",  # simple for testing
                    "confirmed_text": r.confirmed_text or "",
                    "scrap": float(r.scrap or 0),
                    "scale1": r.scale1 or "",
                    "scale1_qty": float(r.scale1_qty or 0),
                    "scale2": r.scale2 or "",
                    "scale2_qty": float(r.scale2_qty or 0),
                    "scale3": r.scale3 or "",
                    "scale3_qty": float(r.scale3_qty or 0),
                })

            print("🔍 Converted orders:", len(orders))

            # ----------------------------------------------------
            # 3) Build SAP JSON payloads
            # ----------------------------------------------------
            sap = SAPConfirmationService()
            payloads = sap._convert_to_json_format(orders, "online")

            print("🔍 Payloads generated:", len(payloads))

            # ----------------------------------------------------
            # 4) Store payloads into sap_confirmation_test table
            # ----------------------------------------------------
            for p in payloads:
                conn.execute(text("""
                    INSERT INTO sap_confirmation_test (po_number, payload, confirmation_type)
                    VALUES (:po, :payload, 'online')
                """), {
                    "po": p.get("PROCESS_ORDER"),
                    "payload": json.dumps(p)
                })

            conn.commit()

            # ----------------------------------------------------
            # 5) Final response
            # ----------------------------------------------------
            return jsonify({
                "message": "Test payloads generated (not sent to SAP)",
                "count": len(payloads),
                "payloads": payloads,
                "debug": {
                    "connected_db": db_info,
                    "process_orders_count": count,
                    "statuses": [s[0] for s in statuses]
                }
            }), 200

    except Exception as e:
        print("❌ ERROR:", e)
        return jsonify({"error": f"Failed: {str(e)}"}), 500

@process_orders_bp.post("/process_orders/manual-confirm")
def manual_confirm():
    """
    Manual Confirmation for Accumulated Scale Values.
    
    Per Order Validation requirements:
    1. Send current accumulated values to SAP confirmation
    2. Reset confirmed_qty, scale1_qty, scale2_qty, scale3_qty to 0 after successful confirmation
    3. Update last_confirmed_qty (cumulative total)
    """
    from database import PostgresSessionLocal
    from models.process_order_pg import ProcessOrderPG
    from models.manual_confirmation import ManualConfirmation
    from services.sap_confirmation import SAPConfirmationService
    from utils.vpn_check import check_vpn_connection
    
    data = request.get_json(silent=True) or {}
    po_number = data.get("po_number")
    shift = data.get("shift")
    confirmed_qty = float(data.get("confirmed_qty", 0))  # Amount to confirm to SAP
    scale1_qty = float(data.get("scale1_qty", 0))        # Byproduct qty to confirm
    scale2_qty = float(data.get("scale2_qty", 0))
    scale3_qty = float(data.get("scale3_qty", 0))
    scrap = float(data.get("scrap", 0))
    confirmed_text = data.get("confirmed_text", "")  # User-provided confirmed text
    operator = data.get("operator", "manual")
    
    if not po_number:
        return jsonify({"error": "po_number is required"}), 400
    
    if confirmed_qty <= 0:
        return jsonify({"error": "confirmed_qty must be greater than 0"}), 400

    db = PostgresSessionLocal()

    try:
        order = db.query(ProcessOrderPG).filter(
            ProcessOrderPG.order_id == po_number
        ).first()

        if not order:
            return jsonify({"error": f"Order {po_number} not found"}), 404
        
        if order.status != 'InProgress':
            return jsonify({"error": f"Order must be InProgress to manually confirm. Current status: {order.status}"}), 400
        
        # Get current shift if not provided
        if not shift:
            shift = order.current_shift or 'A'
        
        # ✅ Calculate available for confirmation using the NEW approach:
        # Available = Total SCADA production - What's already been sent to SAP
        # weight_shift_X = total production from SCADA
        # confirmed_shift_X = what's been sent to SAP
        weight_shift_a = float(order.weight_shift_a or 0)
        weight_shift_b = float(order.weight_shift_b or 0)
        weight_shift_c = float(order.weight_shift_c or 0)
        weight_shift_total = weight_shift_a + weight_shift_b + weight_shift_c
        
        confirmed_shift_a = float(order.confirmed_shift_a or 0)
        confirmed_shift_b = float(order.confirmed_shift_b or 0)
        confirmed_shift_c = float(order.confirmed_shift_c or 0)
        confirmed_shift_total = confirmed_shift_a + confirmed_shift_b + confirmed_shift_c
        
        # Also check confirmed_qty (real-time from worker) as alternative source
        current_confirmed_qty = float(order.confirmed_qty or 0)
        
        # Use the higher of confirmed_qty or weight_shift_total as total production
        total_production = max(current_confirmed_qty, weight_shift_total)
        
        # Available = Total production - Already sent to SAP
        available_for_confirm = max(0, total_production - confirmed_shift_total)
        
        print(f"📊 [Manual Confirm] Calculation for {po_number}:")
        print(f"   Total production (SCADA): {total_production:.2f} (confirmed_qty={current_confirmed_qty:.2f}, weight_shift_total={weight_shift_total:.2f})")
        print(f"   Already sent to SAP: {confirmed_shift_total:.2f}")
        print(f"   Available for confirmation: {available_for_confirm:.2f}")
        print(f"   Requesting to confirm: {confirmed_qty:.2f}")
        
        # ✅ Validate: Cannot confirm more than available
        if confirmed_qty > available_for_confirm + 0.01:  # Small tolerance for float comparison
            return jsonify({
                "error": f"Cannot confirm {confirmed_qty:.2f} - only {available_for_confirm:.2f} available (Total: {total_production:.2f}, Already sent: {confirmed_shift_total:.2f})"
            }), 400
        
        # Calculate new last_confirmed_qty (cumulative total sent to SAP)
        current_last_confirmed = float(order.last_confirmed_qty or 0)
        new_last_confirmed = current_last_confirmed + confirmed_qty
        
        # Calculate remainder for response message
        remainder_qty = available_for_confirm - confirmed_qty
        
        print(f"   After confirmation: Remainder={remainder_qty:.2f}, Total sent to SAP={new_last_confirmed:.2f}")
        
        # Build SAP payload
        order_type = order.order_type or 'MILLING'
        target = float(order.expected_weight or order.quantity or 0) if order_type == 'MILLING' else float(order.quantity or 0)
        is_final = new_last_confirmed >= target
        
        # ✅ Convert datetime to string for JSON serialization
        created_at_str = order.created_at.isoformat() if order.created_at else datetime.now().isoformat()
        
        sap_payload = {
            'po_number': order.order_id,
            'confirmed_weight': confirmed_qty,
            'last_confirmed_qty': current_last_confirmed,
            'total_qty': target,
            'material': order.material,
            'version': order.version or '',
            'material_desc': order.material_desc or '',
            'batch': order.batch or '',
            'uom': 'KG' if order_type == 'MILLING' else 'BAG',
            'plant': order.plant,
            'created_at': created_at_str,  # ✅ Already converted to string
            'shift': shift.upper(),
            'validation_method': 'Manual',
            'confirmed_text': confirmed_text or '',  # Leave empty unless user explicitly adds text
            'scrap': scrap,
            'scale1': order.scale1 or '',
            'scale1_qty': scale1_qty,
            'scale2': order.scale2 or '',
            'scale2_qty': scale2_qty,
            'scale3': order.scale3 or '',
            'scale3_qty': scale3_qty,
            'final_confirmation': "X" if is_final else "",
            'is_final_confirmation': is_final,
            'order_status': 'InProgress',
            'process_order_id': order.id
        }
        
        # Check VPN and send to SAP
        sap_service = SAPConfirmationService()
        
        if sap_service.mock_mode:
            vpn_status = {"connected": True, "message": "Mock mode - using demo server"}
        else:
            vpn_status = check_vpn_connection()
        
        if not vpn_status.get("connected"):
            # Store in offline confirmations
            from models.offline_confirmation import OfflineConfirmation
            from sqlalchemy import func
            
            # ✅ LOG OFFLINE STORAGE TO JSON FILE
            from utils.sap_logger import log_sap_request
            print(f"🚀🚀🚀 [MANUAL CONFIRM OFFLINE] Logging offline storage for PO {po_number}")
            try:
                log_sap_request(
                    endpoint="OFFLINE_STORAGE",
                    method="STORE",
                    payload=sap_payload,
                    po_number=po_number,
                    log_type="manual_confirmation_offline"
                )
                print(f"✅ [MANUAL CONFIRM OFFLINE] JSON log created for offline storage")
            except Exception as log_err:
                print(f"⚠️ [MANUAL CONFIRM OFFLINE] Failed to log offline storage: {log_err}")
            
            # ✅ CRITICAL FIX: Check for existing pending offline confirmation for this order
            # If exists, UPDATE it by accumulating values instead of creating duplicates
            po_num_stripped = str(order.order_id).lstrip('0')
            existing_offline = db.query(OfflineConfirmation).filter(
                func.ltrim(OfflineConfirmation.order_id, '0') == po_num_stripped,
                OfflineConfirmation.status == 'pending'
            ).first()
            
            if existing_offline:
                # ✅ UPDATE existing record - accumulate values
                old_weight = existing_offline.confirmed_weight or 0
                accumulated_weight = old_weight + confirmed_qty
                existing_offline.confirmed_weight = accumulated_weight
                existing_offline.scrap = (existing_offline.scrap or 0) + scrap
                # Update SAP payload with accumulated values
                sap_payload['confirmed_weight'] = accumulated_weight
                existing_offline.sap_payload = sap_payload
                # ✅ Keep existing confirmed_text - don't overwrite user's manual notes
                # existing_offline.confirmed_text is preserved as-is
                print(f"✅ [Manual Confirm] UPDATED existing offline confirmation for {po_number}: {old_weight:.2f} + {confirmed_qty:.2f} = {accumulated_weight:.2f}")
            else:
                # Create new offline record
                offline_record = OfflineConfirmation(
                    order_id=order.order_id,
                    process_order_id=order.id,
                    material=order.material,
                    version=order.version,
                    confirmed_weight=confirmed_qty,
                    total_qty=target,
                    uom=sap_payload['uom'],
                    plant=order.plant,
                    batch=order.batch or '',
                    shift=shift.upper(),
                    scrap=scrap,
                    confirmed_text=sap_payload['confirmed_text'],
                    sap_payload=sap_payload,
                    validation_method='Manual',
                    status='pending'
                )
                db.add(offline_record)
                print(f"✅ [Manual Confirm] Created NEW offline confirmation for {po_number}: {confirmed_qty:.2f}")
            
            # Track byproduct overflow for next order before resetting
            # Overflow = Current accumulated - What user confirmed
            current_scale1 = float(order.scale1_qty or 0)
            current_scale2 = float(order.scale2_qty or 0)
            current_scale3 = float(order.scale3_qty or 0)
            
            # Store overflow for scales with positive difference
            if current_scale1 > scale1_qty and order.scale1:
                overflow1 = current_scale1 - scale1_qty
                db.execute(text("""
                    INSERT INTO scale_overflows (scale_tag, overflow_qty, last_updated)
                    VALUES (:tag, :qty, NOW())
                    ON CONFLICT (scale_tag) 
                    DO UPDATE SET overflow_qty = scale_overflows.overflow_qty + :qty, last_updated = NOW()
                """), {"tag": order.scale1, "qty": overflow1})
                print(f"🌊 [Manual Confirm Offline] Stored overflow for {order.scale1}: {overflow1:.2f}")
            
            if current_scale2 > scale2_qty and order.scale2:
                overflow2 = current_scale2 - scale2_qty
                db.execute(text("""
                    INSERT INTO scale_overflows (scale_tag, overflow_qty, last_updated)
                    VALUES (:tag, :qty, NOW())
                    ON CONFLICT (scale_tag) 
                    DO UPDATE SET overflow_qty = scale_overflows.overflow_qty + :qty, last_updated = NOW()
                """), {"tag": order.scale2, "qty": overflow2})
                print(f"🌊 [Manual Confirm Offline] Stored overflow for {order.scale2}: {overflow2:.2f}")
            
            if current_scale3 > scale3_qty and order.scale3:
                overflow3 = current_scale3 - scale3_qty
                db.execute(text("""
                    INSERT INTO scale_overflows (scale_tag, overflow_qty, last_updated)
                    VALUES (:tag, :qty, NOW())
                    ON CONFLICT (scale_tag) 
                    DO UPDATE SET overflow_qty = scale_overflows.overflow_qty + :qty, last_updated = NOW()
                """), {"tag": order.scale3, "qty": overflow3})
                print(f"🌊 [Manual Confirm Offline] Stored overflow for {order.scale3}: {overflow3:.2f}")
            
            # ✅ SIMPLE FIX: Don't touch confirmed_qty, weight_shift, or baselines
            # Let SCADA continue accumulating normally
            # Only track what was sent to SAP in last_confirmed_qty and confirmed_shift_X
            order.last_confirmed_qty = new_last_confirmed
            
            # ✅ CRITICAL FIX: Only update byproduct quantities if user provided explicit override (non-zero value)
            # If user didn't provide values (0), preserve the existing stored values in the database
            if scale1_qty > 0:
                order.scale1_qty = scale1_qty
                print(f"✅ [Manual Confirm Offline] Updated scale1_qty in DB: {scale1_qty:.4f}")
            if scale2_qty > 0:
                order.scale2_qty = scale2_qty
                print(f"✅ [Manual Confirm Offline] Updated scale2_qty in DB: {scale2_qty:.4f}")
            if scale3_qty > 0:
                order.scale3_qty = scale3_qty
                print(f"✅ [Manual Confirm Offline] Updated scale3_qty in DB: {scale3_qty:.4f}")
            
            # ✅ FIX: Reset byproduct baselines to current SCADA readings after storing offline confirmation
            # This prevents delta from being added again on next confirmation (fixes doubling bug)
            from services.scale_service import get_scada_reading
            
            if order.scale1:
                current1 = float(get_scada_reading(order.scale1) or 0.0)
                setattr(order, f"baseline_{order.scale1.lower()}", current1)
                print(f"🔄 [Manual Confirm Offline] Reset baseline for {order.scale1}: {current1:.4f}")
            
            if order.scale2:
                current2 = float(get_scada_reading(order.scale2) or 0.0)
                setattr(order, f"baseline_{order.scale2.lower()}", current2)
                print(f"🔄 [Manual Confirm Offline] Reset baseline for {order.scale2}: {current2:.4f}")
            
            if order.scale3:
                current3 = float(get_scada_reading(order.scale3) or 0.0)
                setattr(order, f"baseline_{order.scale3.lower()}", current3)
                print(f"🔄 [Manual Confirm Offline] Reset baseline for {order.scale3}: {current3:.4f}")
            
            shift_upper = shift.upper()
            if shift_upper == 'A':
                order.confirmed_shift_a = float(order.confirmed_shift_a or 0) + confirmed_qty
                print(f"📊 [Manual Confirm Offline] Updated confirmed_shift_a: +{confirmed_qty:.2f}")
            elif shift_upper == 'B':
                order.confirmed_shift_b = float(order.confirmed_shift_b or 0) + confirmed_qty
                print(f"📊 [Manual Confirm Offline] Updated confirmed_shift_b: +{confirmed_qty:.2f}")
            elif shift_upper == 'C':
                order.confirmed_shift_c = float(order.confirmed_shift_c or 0) + confirmed_qty
                print(f"📊 [Manual Confirm Offline] Updated confirmed_shift_c: +{confirmed_qty:.2f}")
            
            print(f"✅ [Manual Confirm Offline] Updated {po_number}: confirmed_qty={remainder_qty:.2f} (remainder kept for next confirmation)")
            
            # Record manual confirmation
            entry = ManualConfirmation(
                process_order_id=order.id,
                shift_code=shift.upper(),
                confirmed_weight=confirmed_qty,
                synced_to_sap=False,
                created_by=operator
            )
            db.add(entry)
            db.commit()
            
            return jsonify({
                "success": True,
                "offline_mode": True,
                "message": f"VPN disconnected - {confirmed_qty:.2f} stored for offline send. Remainder ({remainder_qty:.2f}) kept for next confirmation.",
                "last_confirmed_qty": new_last_confirmed,
                "confirmed_qty_sent": confirmed_qty,
                "remainder_qty": remainder_qty,
                "confirmed_at": datetime.now().isoformat()
            }), 200
        
        # VPN connected - send to SAP (use offline to include SCRAP and CONFIRMED_TEXT)
        # ✅ LOG TO JSON FILE - Manual Confirmation
        from utils.sap_logger import log_sap_request, log_sap_response
        import time
        start_time = time.time()
        
        print(f"🚀🚀🚀 [MANUAL CONFIRM] Logging SAP request for PO {po_number}")
        db_log_id = None
        try:
            db_log_id = log_sap_request(
                endpoint=sap_service._get_url("/sap/opu/odata/sap/ZSFMSPP_PROCESSORDERS_SRV/ProcessOrdersConfirmationSet"),
                method="POST",
                payload=sap_payload,
                po_number=po_number,
                log_type="manual_confirmation"
            )
            print(f"✅ [MANUAL CONFIRM] JSON log created with ID: {db_log_id}")
        except Exception as log_err:
            print(f"⚠️ [MANUAL CONFIRM] Failed to log request: {log_err}")
        
        sap_result = sap_service.confirm_offline([sap_payload])
        
        # ✅ LOG SAP RESPONSE
        try:
            elapsed_ms = int((time.time() - start_time) * 1000)
            log_sap_response(
                log_id=db_log_id,
                response_payload=sap_result,
                status_code=200 if sap_result.get("ok") else 500,
                error_message=sap_result.get("error") if not sap_result.get("ok") else None,
                duration_ms=elapsed_ms
            )
            print(f"✅ [MANUAL CONFIRM] JSON response logged - success={sap_result.get('ok')}, duration={elapsed_ms}ms")
        except Exception as log_err:
            print(f"⚠️ [MANUAL CONFIRM] Failed to log response: {log_err}")
        
        if sap_result.get("ok"):
            # SUCCESS: Track byproduct overflow for next order before resetting
            # Overflow = Current accumulated - What user confirmed
            current_scale1 = float(order.scale1_qty or 0)
            current_scale2 = float(order.scale2_qty or 0)
            current_scale3 = float(order.scale3_qty or 0)
            
            # Store overflow for scales with positive difference
            if current_scale1 > scale1_qty and order.scale1:
                overflow1 = current_scale1 - scale1_qty
                db.execute(text("""
                    INSERT INTO scale_overflows (scale_tag, overflow_qty, last_updated)
                    VALUES (:tag, :qty, NOW())
                    ON CONFLICT (scale_tag) 
                    DO UPDATE SET overflow_qty = scale_overflows.overflow_qty + :qty, last_updated = NOW()
                """), {"tag": order.scale1, "qty": overflow1})
                print(f"🌊 [Manual Confirm] Stored overflow for {order.scale1}: {overflow1:.2f}")
            
            if current_scale2 > scale2_qty and order.scale2:
                overflow2 = current_scale2 - scale2_qty
                db.execute(text("""
                    INSERT INTO scale_overflows (scale_tag, overflow_qty, last_updated)
                    VALUES (:tag, :qty, NOW())
                    ON CONFLICT (scale_tag) 
                    DO UPDATE SET overflow_qty = scale_overflows.overflow_qty + :qty, last_updated = NOW()
                """), {"tag": order.scale2, "qty": overflow2})
                print(f"🌊 [Manual Confirm] Stored overflow for {order.scale2}: {overflow2:.2f}")
            
            if current_scale3 > scale3_qty and order.scale3:
                overflow3 = current_scale3 - scale3_qty
                db.execute(text("""
                    INSERT INTO scale_overflows (scale_tag, overflow_qty, last_updated)
                    VALUES (:tag, :qty, NOW())
                    ON CONFLICT (scale_tag) 
                    DO UPDATE SET overflow_qty = scale_overflows.overflow_qty + :qty, last_updated = NOW()
                """), {"tag": order.scale3, "qty": overflow3})
                print(f"🌊 [Manual Confirm] Stored overflow for {order.scale3}: {overflow3:.2f}")
            
            # ✅ SIMPLE FIX: Don't touch baselines or weight_shift - let SCADA continue normally
            # Instead, just track what was sent to SAP in confirmed_shift_X
            # The worker will continue calculating weight_shift from SCADA as usual
            # 
            # Key insight: 
            # - weight_shift_X = total production from SCADA (don't touch this!)
            # - confirmed_shift_X = what has been sent to SAP
            # - confirmed_qty = weight_shift_X - confirmed_shift_X (calculated, not stored)
            #
            # For this manual confirmation:
            # - We only update last_confirmed_qty (total sent to SAP)
            # - We only update confirmed_shift_X (what was sent this shift)
            # - We DON'T touch weight_shift_X or baselines (SCADA continues as normal)
            
            order.last_confirmed_qty = new_last_confirmed
            
            # ✅ CRITICAL FIX: Only update byproduct quantities if user provided explicit override (non-zero value)
            # If user didn't provide values (0), preserve the existing stored values in the database
            if scale1_qty > 0:
                order.scale1_qty = scale1_qty
                print(f"✅ [Manual Confirm] Updated scale1_qty in DB: {scale1_qty:.4f}")
            if scale2_qty > 0:
                order.scale2_qty = scale2_qty
                print(f"✅ [Manual Confirm] Updated scale2_qty in DB: {scale2_qty:.4f}")
            if scale3_qty > 0:
                order.scale3_qty = scale3_qty
                print(f"✅ [Manual Confirm] Updated scale3_qty in DB: {scale3_qty:.4f}")
            
            # ✅ FIX: Reset byproduct baselines to current SCADA readings after successful confirmation
            # This prevents delta from being added again on next confirmation (fixes doubling bug)
            from services.scale_service import get_scada_reading
            
            if order.scale1:
                current1 = float(get_scada_reading(order.scale1) or 0.0)
                setattr(order, f"baseline_{order.scale1.lower()}", current1)
                print(f"🔄 [Manual Confirm] Reset baseline for {order.scale1}: {current1:.4f}")
            
            if order.scale2:
                current2 = float(get_scada_reading(order.scale2) or 0.0)
                setattr(order, f"baseline_{order.scale2.lower()}", current2)
                print(f"🔄 [Manual Confirm] Reset baseline for {order.scale2}: {current2:.4f}")
            
            if order.scale3:
                current3 = float(get_scada_reading(order.scale3) or 0.0)
                setattr(order, f"baseline_{order.scale3.lower()}", current3)
                print(f"🔄 [Manual Confirm] Reset baseline for {order.scale3}: {current3:.4f}")
            
            # DON'T set confirmed_qty here - let the worker calculate it from SCADA
            # DON'T touch weight_shift_X - let SCADA continue accumulating
            
            # Only update confirmed_shift_X to track what was sent to SAP
            shift_upper = shift.upper()
            if shift_upper == 'A':
                order.confirmed_shift_a = float(order.confirmed_shift_a or 0) + confirmed_qty
                print(f"📊 [Manual Confirm] Updated confirmed_shift_a: +{confirmed_qty:.2f} → {order.confirmed_shift_a:.2f}")
            elif shift_upper == 'B':
                order.confirmed_shift_b = float(order.confirmed_shift_b or 0) + confirmed_qty
                print(f"📊 [Manual Confirm] Updated confirmed_shift_b: +{confirmed_qty:.2f} → {order.confirmed_shift_b:.2f}")
            elif shift_upper == 'C':
                order.confirmed_shift_c = float(order.confirmed_shift_c or 0) + confirmed_qty
                print(f"📊 [Manual Confirm] Updated confirmed_shift_c: +{confirmed_qty:.2f} → {order.confirmed_shift_c:.2f}")
            
            print(f"✅ [Manual Confirm] Sent {confirmed_qty:.2f} to SAP. Total sent to SAP: {new_last_confirmed:.2f}")
            
            # Record manual confirmation as synced
            entry = ManualConfirmation(
                process_order_id=order.id,
                shift_code=shift.upper(),
                confirmed_weight=confirmed_qty,
                synced_to_sap=True,
                created_by=operator
            )
            db.add(entry)
            db.commit()
            
            return jsonify({
                "success": True,
                "message": f"Manual confirmation sent to SAP: {confirmed_qty:.2f}. Remainder ({remainder_qty:.2f}) kept for next confirmation.",
                "last_confirmed_qty": new_last_confirmed,
                "confirmed_qty_sent": confirmed_qty,
                "remainder_qty": remainder_qty,
                "confirmed_at": datetime.now().isoformat(),
                "sap_response": sap_result.get("sap_response", "")
            })
        else:
            # SAP failed - log to error_log (not offline_confirmations per fallback strategy)
            from services.error_logger import log_order_error
            log_order_error(
                po_number=str(order.order_id).lstrip("0"),
                error_type="sap_failed",
                error_message=sap_result.get("error", "Manual confirmation failed"),
                payload={
                    "sent_payload": sap_payload,
                    "sap_response": sap_result,
                    "confirmation_type": "manual",
                    "timestamp": datetime.now().isoformat(),
                    "vpn_connected": True
                },
                source="manual_confirm"
            )
            
            return jsonify({
                "success": False,
                "error": sap_result.get("error", "SAP confirmation failed"),
                "message": "Manual confirmation failed - logged to error_log for reprocess"
            }), 500

    except Exception as e:
        db.rollback()
        import traceback
        traceback.print_exc()
        return jsonify({"error": str(e)}), 500
    finally:
        db.close()

# backend/routes/process_orders.py
# backend/routes/process_orders.py (around line 1200-1260)
# Line 1201 - FIXED
# backend/routes/process_orders.py
# backend/routes/process_orders.py
# backend/routes/process_orders.py


@process_orders_bp.route("/process_orders/<string:orderid>/offline-confirm", methods=["POST", "OPTIONS"])
def offline_manual_confirmation(orderid: str):
    if request.method == "OPTIONS":
        return jsonify(ok=True), 200

    from services.sap_confirmation import SAPConfirmationService

    data = request.get_json() or {}
    scrap = float(data.get("scrap", 0.0))
    confirmed_text = data.get("confirmed_text", "")
    custom_byproducts = data.get("custom_byproducts", {})

    try:
        with PostgresSessionLocal() as db:
            order_result = db.execute(
                text("SELECT * FROM process_orders WHERE order_id = :orderid"), 
                {"orderid": orderid}
            ).mappings().first()

            if order_result is None:
                return jsonify(error=f"Order {orderid} not found"), 404

            # ✅ CRITICAL: Convert Row to dict for easier access
            # Using .mappings() returns a dict-like Row object
            order = dict(order_result)
            
            # ✅ CRITICAL: Get current confirmed_qty from database
            confirmed_qty = float(order.get('confirmed_qty') or order.get('confirmedqty') or 0)
            
            # ✅ CRITICAL: If confirmed_qty is 0 but there's production (delta showing 200kg),
            # we need to calculate it from shift weights or current production
            # Check if order has shift weights that indicate production
            weight_shift_a = float(order.get('weight_shift_a') or 0)
            weight_shift_b = float(order.get('weight_shift_b') or 0)
            weight_shift_c = float(order.get('weight_shift_c') or 0)
            shift_weights_sum = weight_shift_a + weight_shift_b + weight_shift_c
            
            # ✅ CRITICAL: If confirmed_qty is 0 but shift weights show production, use shift weights
            if confirmed_qty == 0.0 and shift_weights_sum > 0.0:
                confirmed_qty = shift_weights_sum
                print(f"📊 [ManualConfirm-{orderid}] confirmed_qty was 0, but shift weights show {shift_weights_sum:.2f} - using shift weights")
            
            # ✅ CRITICAL: Also check if there's a current_shift weight that should be used
            current_shift = (order.get('current_shift') or 'A').upper()
            current_shift_weight_field = f"weight_shift_{current_shift.lower()}"
            current_shift_weight = float(order.get(current_shift_weight_field) or 0)
            
            # ✅ CRITICAL: If confirmed_qty is still 0 but current shift has weight, use it
            if confirmed_qty == 0.0 and current_shift_weight > 0.0:
                confirmed_qty = current_shift_weight
                print(f"📊 [ManualConfirm-{orderid}] confirmed_qty was 0, but current shift ({current_shift}) weight shows {current_shift_weight:.2f} - using current shift weight")

            # Build SAP payload in the format expected by confirm_offline
            # The method expects lowercase field names that match the order structure
            created_at_value = order.get('created_at')
            if created_at_value:
                # Convert datetime to ISO format string if it's a datetime object
                created_at_str = created_at_value.isoformat() if hasattr(created_at_value, 'isoformat') else str(created_at_value)
            else:
                created_at_str = datetime.now().isoformat()
            
            sappayload = {
                "po_number": order.get('order_id') or order.get('orderid'),
                "material": order.get('material'),
                "version": order.get('version') or '',
                "material_desc": order.get('material_desc') or '',
                "total_qty": float(order.get('quantity') or 0),
                "confirmed_weight": confirmed_qty,  # Full confirmed qty, no minus scrap
                "uom": order.get('unit') or order.get('uom') or 'KG',
                "plant": order.get('plant') or '',
                "batch": order.get('batch') or '',
                "created_at": created_at_str,  # ✅ Already converted to string
                "confirmed_text": confirmed_text,  # For offline confirmation
                "scrap": scrap,  # For offline confirmation
                "scale1": order.get('scale1') or '',
                "scale1_qty": float(order.get('scale1_qty') or 0),
                "scale2": order.get('scale2') or '',
                "scale2_qty": float(order.get('scale2_qty') or 0),
                "scale3": order.get('scale3') or '',
                "scale3_qty": float(order.get('scale3_qty') or 0),
                "last_confirmed_qty": float(order.get('last_confirmed_qty') or 0),
                "is_final_sent": bool(order.get('is_final_sent') or False),
            }

            # ✅ Handle Custom Byproducts and Overflow
            # ⚠️ VALIDATION: Reject bypass values that exceed current scale readings
            if custom_byproducts:
                # Scale 1
                scale1_custom = custom_byproducts.get('scale1_qty')
                if scale1_custom is not None:
                    current_scale1 = sappayload['scale1_qty']
                    # ✅ FIX: Reject if bypass value is HIGHER than current reading
                    if float(scale1_custom) > current_scale1:
                        return jsonify(error=f"Invalid bypass value for Scale 1: entered {scale1_custom:.4f} exceeds current reading {current_scale1:.4f}. Bypass value cannot be higher than the actual scale reading."), 400
                    
                    sappayload['scale1_qty'] = float(scale1_custom)
                    overflow1 = current_scale1 - float(scale1_custom)
                    if overflow1 > 0 and sappayload['scale1']:
                        # Update ScaleOverflow - store excess for next order
                        db.execute(text("""
                            INSERT INTO scale_overflows (scale_tag, overflow_qty, last_updated)
                            VALUES (:tag, :qty, NOW())
                            ON CONFLICT (scale_tag) 
                            DO UPDATE SET overflow_qty = scale_overflows.overflow_qty + :qty, last_updated = NOW()
                        """), {"tag": sappayload['scale1'], "qty": overflow1})
                        print(f"🌊 Stored overflow for {sappayload['scale1']}: {overflow1:.4f}")

                # Scale 2
                scale2_custom = custom_byproducts.get('scale2_qty')
                if scale2_custom is not None:
                    current_scale2 = sappayload['scale2_qty']
                    # ✅ FIX: Reject if bypass value is HIGHER than current reading
                    if float(scale2_custom) > current_scale2:
                        return jsonify(error=f"Invalid bypass value for Scale 2: entered {scale2_custom:.4f} exceeds current reading {current_scale2:.4f}. Bypass value cannot be higher than the actual scale reading."), 400
                    
                    sappayload['scale2_qty'] = float(scale2_custom)
                    overflow2 = current_scale2 - float(scale2_custom)
                    if overflow2 > 0 and sappayload['scale2']:
                        # Update ScaleOverflow - store excess for next order
                        db.execute(text("""
                            INSERT INTO scale_overflows (scale_tag, overflow_qty, last_updated)
                            VALUES (:tag, :qty, NOW())
                            ON CONFLICT (scale_tag) 
                            DO UPDATE SET overflow_qty = scale_overflows.overflow_qty + :qty, last_updated = NOW()
                        """), {"tag": sappayload['scale2'], "qty": overflow2})
                        print(f"🌊 Stored overflow for {sappayload['scale2']}: {overflow2:.4f}")

                # Scale 3
                scale3_custom = custom_byproducts.get('scale3_qty')
                if scale3_custom is not None:
                    current_scale3 = sappayload['scale3_qty']
                    # ✅ FIX: Reject if bypass value is HIGHER than current reading
                    if float(scale3_custom) > current_scale3:
                        return jsonify(error=f"Invalid bypass value for Scale 3: entered {scale3_custom:.4f} exceeds current reading {current_scale3:.4f}. Bypass value cannot be higher than the actual scale reading."), 400
                    
                    sappayload['scale3_qty'] = float(scale3_custom)
                    overflow3 = current_scale3 - float(scale3_custom)
                    if overflow3 > 0 and sappayload['scale3']:
                        # Update ScaleOverflow - store excess for next order
                        db.execute(text("""
                            INSERT INTO scale_overflows (scale_tag, overflow_qty, last_updated)
                            VALUES (:tag, :qty, NOW())
                            ON CONFLICT (scale_tag) 
                            DO UPDATE SET overflow_qty = scale_overflows.overflow_qty + :qty, last_updated = NOW()
                        """), {"tag": sappayload['scale3'], "qty": overflow3})
                        print(f"🌊 Stored overflow for {sappayload['scale3']}: {overflow3:.4f}")

            # ✅ CHECK VPN CONNECTION BEFORE SAP CALL
            # Skip VPN check if using mock mode (demo server)
            # Use SAPConfirmationService to get mock mode status
            sapservice = SAPConfirmationService()
            
            if sapservice.mock_mode:
                # Mock mode: Skip VPN check, always send to demo server
                print("🔧 Mock mode enabled - skipping VPN check, sending to demo server")
                vpn_status = {"connected": True, "message": "Mock mode - using demo server"}
            else:
                # Real SAP mode: Check VPN connection
                from utils.vpn_check import check_vpn_connection
                vpn_status = check_vpn_connection()
            
            from models.offline_confirmation import OfflineConfirmation
            
            if not vpn_status.get("connected"):
                # VPN is disconnected - store for offline confirmation
                # ✅ Store both validated and partial confirmation orders offline (allows duplicates for partial confirmations)
                order_status = (order.get('status') or "").upper()
                print(f"⚠️ [ManualConfirm-{orderid}] VPN disconnected - storing for offline confirmation (status: {order_status})")
                
                try:
                    # Get current shift for the order
                    current_shift = order.get('current_shift') or 'A'
                    
                    # ✅ sappayload already has datetime converted to string, safe to store directly
                    # Store in offline_confirmations table for later retry
                    offline_record = OfflineConfirmation(
                        order_id=orderid,
                        process_order_id=order.get('id'),  # Link to process_orders table
                        material=sappayload.get('material'),
                        version=sappayload.get('version'),
                        total_qty=sappayload.get('total_qty'),
                        confirmed_weight=confirmed_qty,
                        uom=sappayload.get('uom', 'KG'),
                        shift=current_shift,
                        plant=sappayload.get('plant'),
                        batch=sappayload.get('batch'),
                        status='pending',
                        validation_method='Manual',
                        scrap=scrap,
                        confirmed_text=confirmed_text,
                        sap_payload=sappayload  # ✅ Already serialized (datetime converted to string)
                    )
                    db.add(offline_record)
                    
                    # Update order with scrap, confirmed_text (but note it's queued, not sent)
                    update_sql = text("""
                        UPDATE process_orders
                        SET scrap = :scrap,
                            confirmed_text = :confirmed_text,
                            validation_method = 'Manual (Queued)',
                            confirmed_qty = :confirmed_qty,
                            updated_at = NOW()
                        WHERE order_id = :orderid
                    """)
                    db.execute(update_sql, {
                        "scrap": scrap,
                        "confirmed_text": confirmed_text,
                        "confirmed_qty": confirmed_qty,
                        "orderid": orderid
                    })
                    db.commit()
                    
                    print(f"✅ [ManualConfirm-{orderid}] Queued for offline confirmation (VPN disconnected)")
                    
                    return jsonify(
                        success=True,
                        offline_queued=True,
                        message="SAP unreachable - confirmation queued for later. Check Offline Orders to resend.",
                        orderid=orderid,
                        confirmedqty=confirmed_qty,
                        scrap=scrap,
                        confirmed_text=confirmed_text
                    ), 200
                    
                except Exception as offline_err:
                    print(f"❌ [ManualConfirm-{orderid}] Failed to store offline: {offline_err}")
                    db.rollback()
                    return jsonify(
                        success=False,
                        error=f"SAP unreachable and failed to queue for offline: {str(offline_err)}"
                    ), 500
            
            # ✅ VPN is connected - proceed with SAP call
            print(f"✅ [ManualConfirm-{orderid}] VPN connected - sending to SAP")
            sapservice = SAPConfirmationService()
            sapresult = sapservice.confirm_offline([sappayload])

            # ✅ CRITICAL: Update order with scrap, confirmed_text, validation method, AND confirmed_qty
            # ⚠️ IMPORTANT: Do NOT change status - just send confirmation to SAP, keep order as InProgress
            # This ensures confirmed_qty is preserved even if it was calculated from shift weights
            update_sql = text("""
                UPDATE process_orders
                SET scrap = :scrap,
                    confirmed_text = :confirmed_text,
                    validation_method = 'Manual Offline',
                    confirmed_qty = :confirmed_qty,
                    updated_at = NOW()
                WHERE order_id = :orderid
            """)
            db.execute(update_sql, {
                "scrap": scrap,
                "confirmed_text": confirmed_text,
                "confirmed_qty": confirmed_qty,
                "orderid": orderid
            })
            db.commit()

            return jsonify(
                success=True,
                message=sapresult.get("message", "Offline confirmation sent to SAP successfully."),
                orderid=orderid,
                confirmedqty=confirmed_qty,
                scrap=scrap,
                confirmed_text=confirmed_text
            ), 200

    except Exception as ex:
        import traceback
        error_trace = traceback.format_exc()
        print(f"❌ [ManualConfirm-{orderid}] Error: {str(ex)}")
        print(f"❌ [ManualConfirm-{orderid}] Traceback: {error_trace}")
        return jsonify(error=f"Internal server error: {str(ex)}"), 500


@process_orders_bp.get("/process_orders/shift-confirmations")
def get_recent_shift_confirmations():
    """
    Get recent successful shift-end auto confirmations for frontend notifications.
    Returns ONLY shift-end confirmations (not mid-shift) from the last 2 minutes.
    Prevents duplicate notifications by only returning very recent confirmations.
    """
    try:
        # ✅ Get confirmations from the last 1 minute only (reduced from 2 to prevent old notifications)
        # This ensures we only show TRULY NEW confirmations, not ones from several minutes ago
        from datetime import timezone
        now_utc = datetime.now(timezone.utc)
        since_time = now_utc - timedelta(minutes=1)  # Only last 1 minute
        
        print(f"🔍 Fetching shift confirmations since: {since_time} (UTC) - Only NEW confirmations (last 1 minute)")
        print(f"🔍 Current time (UTC): {now_utc}")
        
        with postgres_engine.connect() as conn:
            # ✅ Get only successful shift-end confirmations (not mid-shift)
            # Filter by action = 'Auto Shift-End Confirmation' to ensure we only get auto-triggered confirmations
            # Use explicit timezone-aware comparison
            rows = conn.execute(text("""
                SELECT 
                    id,
                    timestamp,
                    action,
                    status,
                    details,
                    log_metadata
                FROM system_logs
                WHERE action = 'Auto Shift-End Confirmation'
                    AND status IN ('Success', 'PartialSuccess')
                    AND timestamp >= :since_time
                ORDER BY timestamp DESC, id DESC
                LIMIT 5
            """), {"since_time": since_time}).mappings().all()
            
            # ✅ CRITICAL FIX: Double-check timestamps are actually recent (handle timezone issues)
            valid_rows = []
            for row in rows:
                row_timestamp = row.get('timestamp')
                if row_timestamp:
                    # Normalize timestamp to UTC for comparison
                    if row_timestamp.tzinfo is None:
                        # Naive timestamp - assume it's UTC
                        row_timestamp_utc = row_timestamp.replace(tzinfo=timezone.utc)
                    else:
                        # Convert to UTC
                        row_timestamp_utc = row_timestamp.astimezone(timezone.utc)
                    
                    # Calculate age in seconds
                    age_seconds = (now_utc - row_timestamp_utc).total_seconds()
                    age_minutes = age_seconds / 60.0
                    
                    # ✅ ONLY include if truly recent (within last 1 minute, not old)
                    if 0 <= age_seconds <= 60:  # Between 0 and 60 seconds old
                        valid_rows.append(row)
                        print(f"✅ Valid recent confirmation: ID={row.get('id')}, Age={age_minutes:.2f} min")
                    else:
                        print(f"⏭️ Skipping old confirmation: ID={row.get('id')}, Age={age_minutes:.2f} min (too old)")
                else:
                    print(f"⚠️ Skipping confirmation with no timestamp: ID={row.get('id')}")
            
            rows = valid_rows
            
            print(f"✅ Found {len(rows)} valid recent shift-end confirmations (after filtering old ones)")
            
            # ✅ Return only the MOST RECENT confirmation to prevent duplicate popups
            # This ensures frontend only shows one notification per shift end
            if len(rows) > 0:
                # Sort by timestamp (most recent first), then by ID (highest first) as tiebreaker
                rows = sorted(rows, key=lambda x: (
                    x.get('timestamp') or datetime.min.replace(tzinfo=timezone.utc),
                    x.get('id', 0)
                ), reverse=True)
                
                # ✅ Only return the latest one to prevent multiple popups
                latest_row = rows[0]
                rows = [latest_row]  # Return only the most recent
                
                latest_timestamp = latest_row.get('timestamp')
                if latest_timestamp:
                    if latest_timestamp.tzinfo is None:
                        latest_timestamp_utc = latest_timestamp.replace(tzinfo=timezone.utc)
                    else:
                        latest_timestamp_utc = latest_timestamp.astimezone(timezone.utc)
                    age_seconds = (now_utc - latest_timestamp_utc).total_seconds()
                    age_minutes = age_seconds / 60.0
                    print(f"📌 Returning only the latest confirmation (ID: {latest_row.get('id')}, Timestamp: {latest_timestamp}, Age: {age_minutes:.2f} min)")
                else:
                    print(f"📌 Returning only the latest confirmation (ID: {latest_row.get('id')}, Timestamp: None)")
            else:
                print("ℹ️ No new shift-end confirmations found in the last 1 minute")
            
            confirmations = []
            for row in rows:
                metadata = {}
                # Try to get metadata from log_metadata column
                log_metadata = row.get("log_metadata")
                if log_metadata:
                    try:
                        if isinstance(log_metadata, str):
                            metadata = json.loads(log_metadata)
                        elif isinstance(log_metadata, dict):
                            metadata = log_metadata
                        else:
                            metadata = {}
                    except Exception as e:
                        print(f"⚠️ Failed to parse metadata: {e}")
                        metadata = {}
                
                # Extract counts from metadata
                successful_count = metadata.get("successful", 0)
                failed_count = metadata.get("failed", 0)
                successful_details = metadata.get("successful_details", [])
                successful_shifts = metadata.get("successful_shifts", [])  # ✅ Get shift letters (A, B, C)
                
                # ✅ Detailed debug logging to verify correct data
                # Use offset-naive datetime for current time since database timestamp is likely naive
                current_time = datetime.now()
                row_timestamp = row.get('timestamp')
                
                # Handle potential timezone mismatch
                if row_timestamp:
                    if row_timestamp.tzinfo is None:
                        # Database timestamp is naive, use naive current time
                        age_seconds = (current_time - row_timestamp).total_seconds()
                    else:
                        # Database timestamp is aware, make current time aware
                        current_time_aware = datetime.now(row_timestamp.tzinfo)
                        age_seconds = (current_time_aware - row_timestamp).total_seconds()
                else:
                    age_seconds = None

                age_minutes = age_seconds / 60 if age_seconds is not None else None
                
                print(f"📋 Shift confirmation log:")
                print(f"   - ID: {row.get('id')}")
                print(f"   - Timestamp: {row_timestamp}")
                print(f"   - Age: {age_minutes:.2f} minutes ago" if age_minutes is not None else "   - Age: Unknown")
                print(f"   - Status: {row.get('status')}")
                print(f"   - Successful count: {successful_count}")
                print(f"   - Failed count: {failed_count}")
                print(f"   - Successful details count: {len(successful_details)}")
                print(f"   - Successful details: {successful_details}")
                if successful_details:
                    for detail in successful_details:
                        print(f"      → {detail}")
                print(f"   - Full metadata keys: {list(metadata.keys())}")
                
                confirmations.append({
                    "id": row["id"],
                    "timestamp": row["timestamp"].isoformat() if row["timestamp"] else None,
                    "status": row["status"],
                    "details": row["details"],
                    "successful_count": successful_count,
                    "failed_count": failed_count,
                    "successful_details": successful_details,
                    "successful_shifts": successful_shifts  # ✅ Include shift letters for frontend
                })
            
            return jsonify({
                "success": True,
                "confirmations": confirmations,
                "count": len(confirmations)
            }), 200
            
    except Exception as e:
        print(f"❌ Error fetching shift confirmations: {e}")
        import traceback
        traceback.print_exc()
        return jsonify({
            "success": False,
            "error": str(e),
            "confirmations": [],
            "count": 0
        }), 500


@process_orders_bp.route("/process_orders/test-json-log", methods=["GET"])
def test_json_log():
    """
    Test endpoint to verify JSON logging is working.
    Call this endpoint to write a test entry to sap_confirmations.json
    """
    from utils.sap_logger import log_sap_request, log_sap_response, SAP_LOG_JSON_FILE
    import time
    
    print("=" * 60)
    print("🧪 TEST JSON LOG ENDPOINT CALLED")
    print(f"🧪 JSON file path: {SAP_LOG_JSON_FILE}")
    print("=" * 60)
    
    start_time = time.time()
    
    test_payload = {
        "po_number": "TEST_PO_123",
        "confirmed_weight": 100.0,
        "test_field": "This is a test entry"
    }
    
    try:
        # Test log_sap_request
        db_log_id = log_sap_request(
            endpoint="TEST_ENDPOINT",
            method="TEST",
            payload=test_payload,
            po_number="TEST_PO_123",
            log_type="test_log"
        )
        print(f"✅ log_sap_request returned ID: {db_log_id}")
        
        # Test log_sap_response
        elapsed_ms = int((time.time() - start_time) * 1000)
        log_sap_response(
            log_id=db_log_id,
            response_payload={"test_response": "success"},
            status_code=200,
            error_message=None,
            duration_ms=elapsed_ms
        )
        print(f"✅ log_sap_response completed")
        
        # Check if file exists and has content
        import os
        file_exists = os.path.exists(SAP_LOG_JSON_FILE)
        file_size = os.path.getsize(SAP_LOG_JSON_FILE) if file_exists else 0
        
        return jsonify({
            "success": True,
            "message": "Test log written successfully",
            "json_file_path": SAP_LOG_JSON_FILE,
            "file_exists": file_exists,
            "file_size_bytes": file_size,
            "db_log_id": db_log_id
        }), 200
        
    except Exception as e:
        import traceback
        error_trace = traceback.format_exc()
        print(f"❌ Test log failed: {e}")
        print(error_trace)
        return jsonify({
            "success": False,
            "error": str(e),
            "traceback": error_trace
        }), 500
