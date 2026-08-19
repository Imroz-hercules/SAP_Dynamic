# backend/models/order_model.py
from __future__ import annotations

from sqlalchemy import Column, Integer, String, Numeric, DateTime, Text
from sqlalchemy.sql import func
from sqlalchemy.schema import Index

try:
    from ..database import Base  # make sure Base/SessionLocal bind to Postgres engine
except Exception:
    from database import Base

class Order(Base):
    """
    Execution/Validation orders (PostgreSQL).
    Joined to process_orders via po_number (== process_orders.order_id).
    """
    __tablename__ = "orders"

    id = Column(Integer, primary_key=True, autoincrement=True)

    # SAP process order number (PO); unique so we can upsert by po_number
    po_number = Column(String(64), nullable=False, unique=True, index=True)

    # Business fields
    material = Column(String(128), nullable=False)
    version  = Column(String(32),  nullable=False, default="v1.0")
    batch    = Column(String(64),  nullable=False)

    # Quantities
    quantity = Column(Numeric(18, 3), nullable=False, default=0)  # safer than Float for PG
    unit     = Column(String(16), nullable=False, default="KG")   # <-- use 'unit' (not 'uom')
    
    # NEW COLUMNS
    plant            = Column(String(50), nullable=True)         # Plant
    confirmed_qty    = Column(Numeric(18, 3), nullable=True)     # Confirmed Quantity
    material_desc    = Column(String(200), nullable=True)        # Material Description

    # Status (Pending | InProgress | Validated | Rejected)
    status = Column(String(32), nullable=False, default="Pending")

    # Metadata
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())

    # Helpful composite index for UI filters
    __table_args__ = (
        Index("idx_orders_status_created", "status", "created_at"),
    )

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "po_number": self.po_number,
            "material": self.material,
            "version": self.version,
            "batch": self.batch,
            "quantity": float(self.quantity) if self.quantity is not None else None,
            "unit": self.unit,  # frontend expects 'unit'
            "status": self.status,
            "plant": self.plant,
            "confirmed_qty": float(self.confirmed_qty) if self.confirmed_qty is not None else None,
            "material_desc": self.material_desc,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None,
        }
