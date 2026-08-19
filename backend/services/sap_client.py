# services/sap_client.py
from typing import List, Dict, Literal, Protocol

OrderStatus = Literal["Pending", "Validated", "Rejected"]

class SAPClient(Protocol):
    def get_po(self, po_number: str) -> Dict: ...
    def get_po_items(self, po_number: str) -> List[Dict]: ...
    def confirm_order(self, po_number: str, status: str, confirmation_time: str, remarks: str | None, payload: Dict | None) -> Dict: ...
    # NEW: list open process orders (required by /process_orders/pull)
    def get_process_orders(self) -> List[Dict]: ...

class SAPStub:
    def get_po(self, po_number: str) -> Dict:
        return {
            "po_number": po_number, 
            "vendor": "VENDOR-01", 
            "currency": "INR",
            "TOTAL_QTY": 160.0,
            "UOM": "TON",
            "MATERIAL_DESC": "Gluten-Free Flour - Grade A",
            "VERSION": "BKF3",
            "CREATED_ON": "20240903"  # Format: YYYYMMDD
        }

    def get_po_items(self, po_number: str) -> List[Dict]:
        # demo data — qtys in base unit
        return [
            {"material_code": "Flour A", "ordered_qty": 5000, "uom": "KG"},
            {"material_code": "Bran B",  "ordered_qty": 3200, "uom": "KG"},
        ]

    def confirm_order(
        self,
        po_number: str,
        status: str,                # Completed | Partial | Rejected
        confirmation_time: str,     # ISO timestamp
        remarks: str | None = None,
        payload: Dict | None = None
    ) -> Dict:
        # In production, call SAP API here and return its response
        return {
            "ok": True,
            "echo": {
                "po_number": po_number,
                "status": status,
                "confirmation_time": confirmation_time,
                "remarks": remarks,
                "payload": payload or {},
            }
        }

    # NEW: implement list of open process orders for /pull
  # services/sap_client.py (inside SAPStub)
    def get_process_orders(self) -> List[Dict]:
        return [
            {
                "po_number": "4500003155",
                "material": "1300005",
                "version": "BKF1",
                "batch": "B-240822-01",
                "quantity": 100.0,
                "unit": "TON",
                "status": "Open",
                "priority": 2,
                "created_at": "2025-08-22T10:30:00Z",
            }
        ]
