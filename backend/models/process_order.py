# backend/models/process_order.py
from sqlalchemy import Column, Integer, String, Float, DateTime, Index
from sqlalchemy.sql import func
from database import engine as mssql_engine, Base

class ProcessOrder(Base):
    __tablename__ = "process_orders"

    id         = Column(Integer, primary_key=True, autoincrement=True)
    order_id   = Column(String(50), nullable=False, index=True)  # Order ID (PROCESS_ORDER from SAP)
    material   = Column(String(100), nullable=False)             # Material (MATERIAL from SAP)
    version    = Column(String(20), nullable=False, default="v1.0")  # Version (VERSION from SAP)
    batch      = Column(String(50), nullable=True)               # Batch (generated or from SAP)
    quantity   = Column(Float, nullable=False, default=0.0)      # Quantity (TOTAL_QTY from SAP)
    unit       = Column(String(10), nullable=False, default="KG")  # Unit (UOM from SAP)
    status     = Column(String(20), nullable=False, default="Open")  # Status (Open/Pending/InProgress/Validated/Rejected)
    priority   = Column(Integer, nullable=False, default=0)      # Priority (PRIORITY_ID from SAP)
    date       = Column(DateTime(timezone=True), nullable=False, server_default=func.now())  # Date
    created_at = Column(DateTime(timezone=True), nullable=False, server_default=func.now())
    updated_at = Column(DateTime(timezone=True), nullable=False, server_default=func.now())
    
    # SAP API COLUMNS
    plant            = Column(String(50), nullable=True)         # Plant (PLANT from SAP)
    confirmed_qty    = Column(Float, nullable=True)              # Confirmed Quantity (CONFIRMED_QTY from SAP)
    material_desc    = Column(String(200), nullable=True)        # Material Description (MATERIAL_DESC from SAP)
    sap_created_on   = Column(DateTime(timezone=True), nullable=True)  # CREATED_ON from SAP (YYYYMMDD format)

Index("idx_process_order_order_id", ProcessOrder.order_id)
Index("idx_process_order_status", ProcessOrder.status)
Index("idx_process_order_date", ProcessOrder.date)
Index("idx_process_order_priority", ProcessOrder.priority)

def create_process_order_schema():
    Base.metadata.create_all(bind=mssql_engine, tables=[ProcessOrder.__table__])
