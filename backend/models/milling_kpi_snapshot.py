# backend/models/milling_kpi_snapshot.py
from sqlalchemy import Column, Integer, Float, String, DateTime, Index, text
from sqlalchemy.sql import func
from database import postgres_engine, Base

class MillingKpiSnapshot(Base):
    __tablename__ = "milling_kpi_snapshots"

    id         = Column(Integer, primary_key=True, autoincrement=True)
    created_at = Column(DateTime(timezone=True), nullable=False, server_default=func.now())
    mode       = Column(String(16), nullable=False, server_default=text("'latest'"))

    # Core Milling KPIs based on the image
    mill_throughput_pct        = Column(Float)   # "Mill Throughput (%)" - Actual vs. standard milling capacity
    mill_time_efficiency_pct   = Column(Float)   # "Mill Time Efficiency (%)" - Net hours divided by total available hours
    total_utilization_pct      = Column(Float)   # "Total Utilization (%)" - Product of time efficiency and throughput
    milling_gain_pct           = Column(Float)   # "Milling Gain (%)" - Output ratio (flour, bran, screenings) to input
    milling_screening_pct      = Column(Float)   # "Milling Screening (%)" - Screening ratios as % of input
    water_consumption_m3       = Column(Float)   # "Water Consumption (m³)" - Total water used per shift/day
    flour_extraction_pct       = Column(Float)   # "Flour Extraction (%)" - Flour percentage extracted from wheat
    bran_extraction_pct        = Column(Float)   # "Bran Extraction (%)" - Bran percentage extracted from wheat
    milling_loss_pct           = Column(Float)   # "Milling Loss (%)" - Losses during milling as % of input
    net_hours_hrs              = Column(Float)   # "Net Hours (hrs)" - Actual running hours
    downtime_hrs               = Column(Float)   # "Downtime (hrs)" - Total downtime

Index("idx_milling_kpi_created_at", MillingKpiSnapshot.created_at)
Index("idx_milling_kpi_mode", MillingKpiSnapshot.mode)

def create_milling_kpi_schema():
    Base.metadata.create_all(bind=postgres_engine, tables=[MillingKpiSnapshot.__table__])
