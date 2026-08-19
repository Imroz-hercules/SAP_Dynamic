# backend/models/shift_report.py
from __future__ import annotations

from sqlalchemy import Column, Integer, String, Numeric, DateTime, Text, Boolean
from sqlalchemy.sql import func
from sqlalchemy.schema import Index

from database import PostgresBase as Base

class ShiftReport(Base):
    """
    Shift Report model for production reports (PostgreSQL).
    Stores shift-wise production data with timestamps.
    """
    __tablename__ = "shift_reports"

    id = Column(Integer, primary_key=True, autoincrement=True)

    # Production Order details
    po_number = Column(String(64), nullable=False, index=True)
    material = Column(String(128), nullable=False)
    version = Column(String(32), nullable=False, default="v1.0")

    # Quantities
    planned_quantity = Column(Numeric(18, 3), nullable=False, default=0)
    actual_quantity = Column(Numeric(18, 3), nullable=False, default=0)
    unit = Column(String(16), nullable=False, default="T")  # Tons

    # Performance metrics
    flour_extraction_percent = Column(Numeric(5, 2), nullable=False, default=0)
    utilization_percent = Column(Numeric(5, 2), nullable=False, default=0)
    loss_percent = Column(Numeric(5, 2), nullable=False, default=0)

    # Status
    status = Column(String(32), nullable=False, default="Pending")  # Accepted, Rejected, Pending

    # Timestamp for when the report was generated
    timestamp = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)

    # Metadata
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())

    # Indexes for better query performance
    __table_args__ = (
        Index("idx_shift_reports_po_number", "po_number"),
        Index("idx_shift_reports_timestamp", "timestamp"),
        Index("idx_shift_reports_status", "status"),
        Index("idx_shift_reports_material", "material"),
    )

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "po_number": self.po_number,
            "material": self.material,
            "version": self.version,
            "planned_quantity": float(self.planned_quantity) if self.planned_quantity is not None else 0,
            "actual_quantity": float(self.actual_quantity) if self.actual_quantity is not None else 0,
            "unit": self.unit,
            "flour_extraction_percent": float(self.flour_extraction_percent) if self.flour_extraction_percent is not None else 0,
            "utilization_percent": float(self.utilization_percent) if self.utilization_percent is not None else 0,
            "loss_percent": float(self.loss_percent) if self.loss_percent is not None else 0,
            "status": self.status,
            "timestamp": self.timestamp.isoformat() if self.timestamp else None,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None,
        }

class DailySummary(Base):
    """
    Daily Summary model for aggregated production data (PostgreSQL).
    Stores daily aggregated metrics.
    """
    __tablename__ = "daily_summaries"

    id = Column(Integer, primary_key=True, autoincrement=True)

    # Date for the summary
    report_date = Column(DateTime(timezone=True), nullable=False, index=True)

    # Aggregated metrics
    total_wheat = Column(Numeric(18, 3), nullable=False, default=0)
    total_flour = Column(Numeric(18, 3), nullable=False, default=0)
    total_bran = Column(Numeric(18, 3), nullable=False, default=0)
    total_water = Column(Numeric(18, 3), nullable=False, default=0)
    total_packing = Column(Numeric(18, 3), nullable=False, default=0)
    efficiency_percent = Column(Numeric(5, 2), nullable=False, default=0)

    # Units
    wheat_unit = Column(String(16), nullable=False, default="T")
    flour_unit = Column(String(16), nullable=False, default="T")
    bran_unit = Column(String(16), nullable=False, default="T")
    water_unit = Column(String(16), nullable=False, default="m³")
    packing_unit = Column(String(16), nullable=False, default="Bags")

    # Metadata
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())

    # Indexes
    __table_args__ = (
        Index("idx_daily_summaries_date", "report_date"),
    )

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "report_date": self.report_date.isoformat() if self.report_date else None,
            "total_wheat": float(self.total_wheat) if self.total_wheat is not None else 0,
            "total_flour": float(self.total_flour) if self.total_flour is not None else 0,
            "total_bran": float(self.total_bran) if self.total_bran is not None else 0,
            "total_water": float(self.total_water) if self.total_water is not None else 0,
            "total_packing": float(self.total_packing) if self.total_packing is not None else 0,
            "efficiency_percent": float(self.efficiency_percent) if self.efficiency_percent is not None else 0,
            "wheat_unit": self.wheat_unit,
            "flour_unit": self.flour_unit,
            "bran_unit": self.bran_unit,
            "water_unit": self.water_unit,
            "packing_unit": self.packing_unit,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None,
        }
