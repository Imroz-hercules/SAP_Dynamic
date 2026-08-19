"""
Model to track last sent KPI baseline values for incremental sending
"""
from sqlalchemy import Column, Integer, Float, String, DateTime, Text, JSON
from sqlalchemy.sql import func
from database import PostgresBase, postgres_engine

class KpiSendTracking(PostgresBase):
    __tablename__ = "kpi_send_tracking"
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    department = Column(String(20), nullable=False)  # MILLING or PACKING
    shift_code = Column(String(10), nullable=True)  # A, B, C for tracking per shift
    
    # Timestamp of last send
    last_sent_at = Column(DateTime(timezone=True), nullable=False, server_default=func.now())
    
    # SCADA baseline values at last send (for incremental calculation)
    # Milling fields
    baseline_WG101 = Column(Float, default=0.0)
    baseline_WG201 = Column(Float, default=0.0)
    baseline_WG202 = Column(Float, default=0.0)
    baseline_WG301 = Column(Float, default=0.0)
    baseline_WG302 = Column(Float, default=0.0)
    baseline_WG501 = Column(Float, default=0.0)
    baseline_WG502 = Column(Float, default=0.0)
    baseline_WG503 = Column(Float, default=0.0)
    
    # Water fields
    baseline_DM101 = Column(Float, default=0.0)
    baseline_DM102 = Column(Float, default=0.0)
    baseline_DM201 = Column(Float, default=0.0)
    baseline_DM202 = Column(Float, default=0.0)
    baseline_DM203 = Column(Float, default=0.0)
    
    # Packing fields
    baseline_PL601_TOT = Column(Float, default=0.0)
    baseline_PL602_TOT = Column(Float, default=0.0)
    baseline_PL603_TOT = Column(Float, default=0.0)
    
    # Metadata
    send_type = Column(String(20), nullable=False)  # 'manual' or 'auto_shift_end'
    notes = Column(Text, nullable=True)
    
    # KPI payload sent to SAP (for auditing)
    kpi_payload_sent = Column(JSON, nullable=True)  # Stores the full SAP payload

