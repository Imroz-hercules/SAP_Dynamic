# backend/models/kpi_config.py
"""
KPI definitions - Workstream B.

Replaces the nine hardcoded min() ceilings in routes/kpi_routes.py:272-383 and
the MILLING_MAP / PACKING_MAP display-name maps in services/kpi_store_flat.py:6
and :20.

The mill nameplate rate (routes/kpi_routes.py:262, repeated at :328) is a plant
constant rather than a per-KPI value - it belongs in system_settings under
'mill_nameplate_tph', which already has get/set helpers.

Schema is fixed as of commit 0. Extend it through your own
backend/migrate_*.py, not by editing setup_sap_postgres.sql.
"""
from sqlalchemy import (
    Column, Integer, String, Boolean, Numeric, DateTime, Index
)
from sqlalchemy.sql import func

from database import PostgresBase

DEPT_MILLING = "MILLING"
DEPT_PACKING = "PACKING"


class KpiConfig(PostgresBase):
    __tablename__ = "kpi_config"

    id = Column(Integer, primary_key=True, autoincrement=True)

    # Stable internal key, e.g. 'mill_throughput_pct'
    kpi_key = Column(String(64), nullable=False, unique=True)

    # API/display name, e.g. 'Mill Throughput (%)' - the key used in the
    # /api/kpi response and by kpi_store_flat when writing snapshots.
    display_name = Column(String(128), nullable=False)

    department = Column(String(20), nullable=False)

    # Column in milling_kpi_snapshots / packing_kpi_snapshots
    target_column = Column(String(64), nullable=True)

    # Upper clamp applied to the computed result. NULL means uncapped.
    max_value = Column(Numeric(18, 3), nullable=True)

    unit = Column(String(16), nullable=True)

    is_active = Column(Boolean, nullable=False, default=True)
    sort_order = Column(Integer, nullable=False, default=0)

    created_at = Column(DateTime(timezone=True), nullable=False, server_default=func.now())
    updated_at = Column(DateTime(timezone=True), nullable=False, server_default=func.now(), onupdate=func.now())

    __table_args__ = (
        Index("idx_kpi_config_dept", "department", "is_active"),
    )

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "kpi_key": self.kpi_key,
            "display_name": self.display_name,
            "department": self.department,
            "target_column": self.target_column,
            "max_value": float(self.max_value) if self.max_value is not None else None,
            "unit": self.unit,
            "is_active": self.is_active,
            "sort_order": self.sort_order,
        }

    def __repr__(self) -> str:
        return f"<KpiConfig({self.kpi_key} cap={self.max_value})>"
