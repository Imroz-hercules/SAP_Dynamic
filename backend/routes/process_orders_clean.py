# routes/process_orders.py
from __future__ import annotations

from typing import List, Dict, Any, Optional, Tuple
from flask import Blueprint, jsonify, request, abort
from sqlalchemy import text
from datetime import datetime, timedelta

from database import postgres_engine
from services.process_order_sync import sync_process_orders           # legacy/internal sync (optional)
from services.process_order_pull import pull_from_sap_once, test_sap_connection  # shared SAP -> Hercules pull

process_orders_bp = Blueprint("process_orders", __name__, url_prefix="/api")

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
        "priority": row.priority,
        "plant": getattr(row, 'plant', None),
        "confirmed_qty": float(row.confirmed_qty) if hasattr(row, 'confirmed_qty') and row.confirmed_qty is not None else None,
        "material_desc": getattr(row, 'material_desc', None),
        "expected_weight": float(row.expected_weight) if hasattr(row, 'expected_weight') and row.expected_weight is not None else None,
        "created_at": row.created_at.isoformat() if row.created_at else None,
        "order_type": getattr(row, 'order_type', None),  # Add order_type field
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
    Priority first (ascending: smaller number = higher priority),
    then FIFO by created_at (oldest first), finally by id to break ties.
    """
    return " ORDER BY priority ASC, created_at ASC NULLS LAST, id ASC "

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
        plant,
        confirmed_qty,
        material_desc,
        expected_weight,
        created_at
      FROM process_orders
    """

    params = {"limit": limit, "offset": offset}
    where_sql = ""
    if status and status != "All":
        where_sql = " WHERE status = :status"
        params["status"] = status

    sql = (
        base_sql
        + where_sql
        + " ORDER BY created_at DESC NULLS LAST LIMIT :limit OFFSET :offset"
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
      { "status": "Validated" | "Rejected", "remarks": "validation notes" }
    """
    payload = request.get_json(silent=True) or {}
    status = payload.get("status")
    remarks = payload.get("remarks", "")
    
    if status not in ["Validated", "Rejected"]:
        return jsonify({"error": "Status must be 'Validated' or 'Rejected'"}), 400
    
    try:
        with postgres_engine.connect() as conn:
            # 1) Update the process_orders status
            updated_po = conn.execute(text("""
                UPDATE process_orders
                SET status = :status, updated_at = NOW()
                WHERE id = :id
                RETURNING id, order_id, material, version, batch, quantity, unit, status, priority, plant, confirmed_qty, material_desc, created_at
            """), {"id": po_id, "status": status}).mappings().first()
            
            if not updated_po:
                return jsonify({"error": "Process order not found"}), 404
            
            # 2) Store the validation result in orders table
            conn.execute(text("""
                INSERT INTO orders (po_number, material, version, batch, quantity, unit, plant, confirmed_qty, material_desc, status, created_at, updated_at)
                VALUES (:po_number, :material, :version, :batch, :quantity, :unit, :plant, :confirmed_qty, :material_desc, :status, NOW(), NOW())
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
                    updated_at = NOW()
            """), {
                "po_number": updated_po.order_id,
                "material": updated_po.material,
                "version": updated_po.version,
                "batch": updated_po.batch,
                "quantity": updated_po.quantity,
                "unit": updated_po.unit,
                "plant": updated_po.plant,
                "confirmed_qty": updated_po.confirmed_qty,
                "material_desc": updated_po.material_desc,
                "status": status
            })
            
            conn.commit()
            
            return jsonify({
                "message": f"Order {updated_po.order_id} {status.lower()} successfully",
                "process_order": _row_to_api(updated_po),
                "status": status,
                "remarks": remarks
            }), 200
            
    except Exception as e:
        return jsonify({"error": f"Validation failed: {str(e)}"}), 500
