# backend/models/order_validation_model.py
from sqlalchemy import (
    Column, Integer, String, Float, DateTime, JSON, Index
)
from sqlalchemy.sql import func

# import Base the same way you do in kpi/material models
try:
    from ..database import Base
except Exception:
    from database import Base  # fallback if models are imported differently


class OrderValidation(Base):
    """
    Snapshot of a single PO validation run
    - Compares actual (from plant/SCADA) vs planned (from SAP) for a PO line
    - Keeps an auditable history you can show in the Validation page or Logs
    """
    __tablename__ = "order_validations"

    id = Column(Integer, primary_key=True, autoincrement=True)

    # SAP identity
    po_number = Column(String(32), index=True, nullable=False)     # e.g., process order number
    sap_item  = Column(String(8),  nullable=True)                  # optional: SAP line item (e.g., 00010)

    # Material + UoM
    material_code = Column(String(64), nullable=False)             # SAP material or mapped code
    unit          = Column(String(8),  nullable=False, default="KG")

    # Quantities (snapshot at validation time)
    planned_qty   = Column(Float, nullable=False, default=0.0)     # from SAP GET /api/process_orders
    actual_qty    = Column(Float, nullable=False, default=0.0)     # from your plant totals
    diff_qty      = Column(Float, nullable=False, default=0.0)     # actual - planned (normalized to unit)

    # Rule/decision
    tolerance_pct = Column(Float, nullable=False, default=1.0)     # ±% window applied
    result        = Column(String(16), nullable=False)             # MATCH | UNDER | OVER | MISMATCH
    reasons       = Column(JSON, nullable=True)                    # [{code, severity, message}, ...]

    # Traceability
    created_at    = Column(DateTime, server_default=func.now())
    validated_by  = Column(String(64), nullable=True)              # user/automation id if you want

    __table_args__ = (
        Index("ix_order_validations_po_item", "po_number", "sap_item"),
    )
