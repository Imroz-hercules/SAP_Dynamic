# backend/models/scada_schema.py
from sqlalchemy import Column, Integer, String, Float, DateTime
from sqlalchemy.sql import func
from sqlalchemy import Index, text
from database import postgres_engine, Base

class ScadaAggregateValues(Base):
    __tablename__ = "scada_aggregate_values"

    id           = Column(Integer, primary_key=True, autoincrement=True)
    created_at   = Column(DateTime(timezone=True), nullable=False, server_default=func.now())
    mode         = Column(String(16), nullable=False, server_default=text("'latest'"))  # 'range' or 'latest'
    window_start = Column(DateTime(timezone=True), nullable=True)
    window_end   = Column(DateTime(timezone=True), nullable=True)

    # SCADA-style aggregated columns (exact names)
    VALUE_WG101 = Column(Float)
    VALUE_WG201 = Column(Float)
    VALUE_WG202 = Column(Float)
    VALUE_WG301 = Column(Float)
    VALUE_WG302 = Column(Float)
    VALUE_WG501 = Column(Float)
    VALUE_WG502 = Column(Float)
    VALUE_WG503 = Column(Float)
    VALUE_DM101 = Column(Float)
    VALUE_DM102 = Column(Float)
    VALUE_DM201 = Column(Float)
    VALUE_DM202 = Column(Float)
    VALUE_DM203 = Column(Float)
    VALUE_PL601_TOT = Column(Float)

# Helpful indexes
Index("idx_scada_agg_created_at", ScadaAggregateValues.created_at)
Index("idx_scada_agg_mode", ScadaAggregateValues.mode)

def create_scada_schema():
    """
    Create only the scada_aggregate_values table on the PostgreSQL engine.
    Safe to run multiple times (no-op if already exists).
    """
    if postgres_engine is None:
        raise RuntimeError("postgres_engine is not configured. Check database.py PG DSN.")
    Base.metadata.create_all(bind=postgres_engine, tables=[ScadaAggregateValues.__table__])
    print("Created (or verified) table: scada_aggregate_values")

if __name__ == "__main__":
    create_scada_schema()
