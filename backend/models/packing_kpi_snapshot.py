# backend/models/packing_kpi_snapshot.py
from sqlalchemy import Column, Integer, Float, String, DateTime, Index, text
from sqlalchemy.sql import func
from database import postgres_engine, Base

class PackingKpiSnapshot(Base):
    __tablename__ = "packing_kpi_snapshots"

    id         = Column(Integer, primary_key=True, autoincrement=True)
    timestamp  = Column(DateTime(timezone=True), nullable=False, server_default=func.now())

    daily_packing_output_bags   = Column(Float)  # "Daily Packing Output (bags)"
    downtime_hrs                = Column(Float)  # "Downtime (hrs)"
    machine_utilization_pct     = Column(Float)  # "Machine Utilization (%)"
    net_hours_hrs               = Column(Float)  # "Net Hours (hrs)"
    packing_line_capacity_bags_hr = Column(Float)  # "Packing Line Capacity (bags/hr)"

Index("idx_packing_kpi_timestamp", PackingKpiSnapshot.timestamp)

def create_packing_kpi_schema():
    Base.metadata.create_all(bind=postgres_engine, tables=[PackingKpiSnapshot.__table__])
