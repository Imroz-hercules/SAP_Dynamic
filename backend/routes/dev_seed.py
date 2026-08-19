from flask import Blueprint, jsonify
from database import SessionLocal
from models.order_model import Order
from models.material_model import MaterialMapping

dev_bp = Blueprint("dev", __name__, url_prefix="/api/dev")

@dev_bp.post("/seed-order")
def seed_order():
    with SessionLocal() as db:
        o = Order(
            po_number="PO-ANY",   # any string works with your stub
            material="Demo Mix",
            version="v1.0",
            batch="B-DEV-001",
            quantity=0,
            uom="KG",
            status="Pending",
            description="Seeded for demo",
        )
        db.add(o); db.commit(); db.refresh(o)
        return jsonify({"ok": True, "order_id": o.id, "po_number": o.po_number})

@dev_bp.post("/seed-materials")
def seed_materials():
    """Seed sample material mappings for testing"""
    with SessionLocal() as db:
        # Check if materials already exist
        existing = db.query(MaterialMapping).count()
        if existing > 0:
            return jsonify({"ok": True, "message": f"Already have {existing} materials"})
        
        # Add sample materials
        sample_materials = [
            MaterialMapping(
                material="Flour Type A",
                version="v1.2",
                scale="Scale 1",
                recipe="Recipe A1",
                packingLine="Line 1"
            ),
            MaterialMapping(
                material="Flour Type B",
                version="v1.1",
                scale="Scale 2",
                recipe="Recipe B1",
                packingLine="Line 2"
            ),
            MaterialMapping(
                material="Bran Premium",
                version="v2.0",
                scale="Scale 1",
                recipe="Recipe C1",
                packingLine="Line 1"
            ),
            MaterialMapping(
                material="Semolina Fine",
                version="v1.5",
                scale="Scale 3",
                recipe="Recipe D1",
                packingLine="Line 3"
            ),
        ]
        
        for material in sample_materials:
            db.add(material)
        
        db.commit()
        return jsonify({"ok": True, "message": f"Added {len(sample_materials)} sample materials"})

@dev_bp.get("/demo-receipts/pass")
def demo_receipts_pass():
    return jsonify({
        "po_number": "PO-ANY",
        "tolerance_pct": 0.5,
        "receipts": [
            { "material_code": "Flour A", "gross_qty": 5000, "tare_qty": 0, "uom": "KG" },
            { "material_code": "Bran B",  "gross_qty": 3200, "tare_qty": 0, "uom": "KG" }
        ]
    })

@dev_bp.get("/demo-receipts/fail")
def demo_receipts_fail():
    return jsonify({
        "po_number": "PO-ANY",
        "tolerance_pct": 0.5,
        "receipts": [
            { "material_code": "Flour A", "gross_qty": 4800, "tare_qty": 0, "uom": "KG" },
            { "material_code": "Bran B",  "gross_qty": 3200, "tare_qty": 0, "uom": "KG" }
        ]
    })
