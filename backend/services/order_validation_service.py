# services/order_validation_service.py
import re
from typing import Dict, Any
from services.scale_service import get_order_end_time, get_wg202_for_order, get_outputs_for_order
from services.sap_client import SAPClient   # real client (replace SAPStub)
from database import postgres_session
from models.order_model import Order

# Define recipe percentages per version
RECIPE_MAP = {
    "BKL1": {"flour_pct": 0.80, "bran_pct": 0.20},
    "BKL2": {"flour_pct": 0.75, "bran_pct": 0.25},
    "BKF1": {"flour_pct": 0.78, "bran_pct": 0.22},
    "BKF2": {"flour_pct": 0.76, "bran_pct": 0.24},
    "BKF3": {"flour_pct": 0.74, "bran_pct": 0.26},
}


def convert_to_tons(total_qty: float, uom: str, material_desc: str) -> float:
    """Convert SAP order qty → tons (base unit for validation)."""
    uom = (uom or "").upper()
    if uom == "BAG":
        # Try to parse bag size (e.g., "... 45 KG")
        match = re.search(r"(\d+(\.\d+)?)\s*KG", (material_desc or "").upper())
        bag_size = float(match.group(1)) if match else 45.0
        return (total_qty * bag_size) / 1000.0
    elif uom == "KG":
        return total_qty / 1000.0
    elif uom == "TON":
        return total_qty
    else:
        raise ValueError(f"Unsupported UOM: {uom}")


def validate_order(po_number: str, tolerance_pct: float = 0.5) -> Dict[str, Any]:
    """
    Validate an SAP process order against SCADA scales.
    """
    sap = SAPClient()
    po = sap.get_order(po_number)
    if not po:
        return {"valid": False, "reason": "PO_NOT_FOUND"}

    # Step 1: convert expected SAP qty → tons
    expected_tons = convert_to_tons(
        float(po["TOTAL_QTY"]), po["UOM"], po.get("MATERIAL_DESC", "")
    )
    version = po.get("VERSION", "").upper()
    recipe = RECIPE_MAP.get(version)

    # Step 2: get time window
    start_time = f"{po['CREATED_ON']} 00:00:00"
    end_time = get_order_end_time(start_time)
    if not end_time:
        return {"valid": False, "reason": "NO_SCALE_ACTIVITY"}

    # Step 3: fetch WG202 input + outputs
    wg202_data = get_wg202_for_order(start_time, end_time)
    outputs = get_outputs_for_order(start_time, end_time)

    actual_tons = wg202_data["actual_tons"] if wg202_data else 0
    flour_tons = outputs["flour_tons"] if outputs else 0
    bran_tons = outputs["bran_tons"] if outputs else 0

    mismatches = []
    tolerance_amount = expected_tons * (tolerance_pct / 100.0)

    # Step 4a: input validation
    diff_in = abs(actual_tons - expected_tons)
    if diff_in > tolerance_amount:
        mismatches.append({
            "material": "WG202",
            "expected": expected_tons,
            "actual": actual_tons,
            "uom": "TON",
            "reason": "INPUT_SCALE_MISMATCH"
        })

    # Step 4b: output validation
    if recipe:
        exp_flour = actual_tons * recipe["flour_pct"]
        exp_bran  = actual_tons * recipe["bran_pct"]

        flour_diff = abs(flour_tons - exp_flour)
        bran_diff  = abs(bran_tons - exp_bran)

        if flour_diff > exp_flour * (tolerance_pct / 100.0):
            mismatches.append({
                "material": "WG501+WG502",
                "expected": exp_flour,
                "actual": flour_tons,
                "uom": "TON",
                "reason": "FLOUR_OUTPUT_MISMATCH"
            })

        if bran_diff > exp_bran * (tolerance_pct / 100.0):
            mismatches.append({
                "material": "WG503",
                "expected": exp_bran,
                "actual": bran_tons,
                "uom": "TON",
                "reason": "BRAN_OUTPUT_MISMATCH"
            })

    # Step 5: confirm or reject
    ok = len(mismatches) == 0
    with postgres_session() as db:
        order = db.query(Order).filter(Order.po_number == po_number).first()
        if order:
            order.status = "Validated" if ok else "Rejected"
            order.confirmed_qty = float(po["TOTAL_QTY"]) if ok else 0
            db.add(order)
            db.commit()

    if ok:
        sap.confirm_order(
            po_number=po_number,
            status="Completed",
            confirmation_time="now",  # use datetime.utcnow().isoformat()
            remarks="Auto-confirmed after successful validation"
        )

    return {
        "po_number": po_number,
        "valid": ok,
        "expected_tons": expected_tons,
        "actual_tons": actual_tons,
        "outputs": {"flour": flour_tons, "bran": bran_tons},
        "mismatches": mismatches
    }
