# services/sap_confirm.py
import os, requests, datetime as dt
from typing import Dict, Any, List

SAP_BASE = os.getenv("SAP_BASE", "http://sap.example.com")   # set in prod
SAP_TIMEOUT = 10

def confirm_order(po_number: str, status: str, when: str | None = None) -> dict:
    payload = {
        "po_number": po_number,
        "status": status,  # Completed | Partial | Rejected
        "confirmation_time": when or dt.datetime.utcnow().isoformat() + "Z",
    }
    # dev: stub this to just return payload
    if os.getenv("SAP_MODE", "stub") == "stub":
        return {"ok": True, "echo": payload}

    r = requests.post(f"{SAP_BASE}/api/confirm_order", json=payload, timeout=SAP_TIMEOUT)
    r.raise_for_status()
    return r.json()

def confirm_orders_batch(orders_data: List[Dict[str, Any]]) -> Dict[str, Any]:
    """
    Send batch confirmation to SAP with the required payload format.
    
    Args:
        orders_data: List of order dictionaries with required fields:
            - PROCESS_ORDER
            - MATERIAL
            - VERSION
            - MATERIAL_DESC
            - TOTAL_QTY
            - CONFIRMED_WEIGHT
            - UOM
            - PLANT
            - CREATED_ON
            - CONFIRMED_AT
            - BATCH
            - STATUS
            - SHIFT
    
    Returns:
        Dict with confirmation results
    """
    # Prepare the payload in the format expected by SAP
    sap_payload = {
        "confirmation_type": "BATCH_CONFIRMATION",
        "timestamp": dt.datetime.utcnow().isoformat() + "Z",
        "orders": orders_data
    }
    
    # In development/stub mode, return the payload
    if os.getenv("SAP_MODE", "stub") == "stub":
        return {
            "ok": True,
            "message": f"Stub mode: Would send {len(orders_data)} orders to SAP",
            "echo": sap_payload,
            "successful_count": len(orders_data),
            "failed_count": 0
        }
    
    try:
        # Send to real SAP system
        r = requests.post(
            f"{SAP_BASE}/api/confirm_orders_batch", 
            json=sap_payload, 
            timeout=SAP_TIMEOUT
        )
        r.raise_for_status()
        return r.json()
    except requests.exceptions.RequestException as e:
        return {
            "ok": False,
            "error": f"SAP API error: {str(e)}",
            "successful_count": 0,
            "failed_count": len(orders_data)
        }
