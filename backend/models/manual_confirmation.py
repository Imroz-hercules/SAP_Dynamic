from sqlalchemy import Column, Integer, Float, String, Boolean, DateTime, ForeignKey, JSON
from sqlalchemy.sql import func
from database import PostgresBase
class ManualConfirmation(PostgresBase):
    __tablename__ = "manual_confirmations"

    id = Column(Integer, primary_key=True, autoincrement=True)

    process_order_id = Column(Integer, 
        ForeignKey("process_orders.id", ondelete="CASCADE"), 
        nullable=False
    )

    shift_code = Column(String(1), nullable=False)
    confirmed_weight = Column(Float, nullable=False)

    created_at = Column(DateTime(timezone=True), server_default=func.now())

    synced_to_sap = Column(Boolean, 
        server_default='false',     # REAL FIX
        nullable=False              # REAL FIX
    )

    sap_response = Column(JSON, nullable=True)
    created_by = Column(String(100), nullable=True)
