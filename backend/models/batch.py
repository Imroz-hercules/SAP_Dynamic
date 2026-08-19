# backend/models/batch.py
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy import String, Integer, Numeric, ForeignKey, DateTime, UniqueConstraint
from sqlalchemy.sql import func
from .base import Base, TimestampMixin

class Batch(Base, TimestampMixin):
    __tablename__ = "batches"
    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    process_order_id: Mapped[int] = mapped_column(ForeignKey("process_orders.id"), index=True)
    batch_no: Mapped[str] = mapped_column(String(32))                         # SCADA/plant batch
    set_point_qty: Mapped[float] = mapped_column(Numeric(18,3))
    actual_qty: Mapped[float] = mapped_column(Numeric(18,3))
    uom: Mapped[str] = mapped_column(String(8), default="KG")
    silo: Mapped[str] = mapped_column(String(32), nullable=True)
    rfid_badge: Mapped[str] = mapped_column(String(64), nullable=True)
    timestamp: Mapped[DateTime] = mapped_column(DateTime, server_default=func.now())

    process_order = relationship("ProcessOrder", back_populates="batches")

    __table_args__ = (UniqueConstraint("process_order_id", "batch_no", name="uq_po_batch"), )
