# backend/models/scada_tag.py
"""
SCADA tag registry - Workstream B.

Replaces the five hardcoded field lists in services/scale_service.py:725-768,
the duplicated lists in routes/scada_routes.py:300 and :636, SCALE_CATEGORIES /
REALISTIC_STARTING_VALUES in services/embedded_emulator.py:59-87, and
SCADA_KEYS in app_scheduler.py:272.

Schema is fixed as of commit 0. Extend it through your own
backend/migrate_*.py, not by editing setup_sap_postgres.sql.
"""
from sqlalchemy import (
    Column, Integer, String, Boolean, Numeric, DateTime, Index
)
from sqlalchemy.sql import func

from database import PostgresBase

# category
CAT_INPUT = "INPUT"
CAT_MILLING = "MILLING"
CAT_WATER = "WATER"
CAT_PACKING = "PACKING"
CAT_DAMAGED = "DAMAGED"

# reading_type
READ_HI_LO = "hi_lo"      # WG scales: source split across _HI / _LO columns
READ_SINGLE = "single"    # PL/SL counters: one cumulative column
READ_AVERAGE = "average"  # DM meters: 30-second average, must be summed


class ScadaTag(PostgresBase):
    __tablename__ = "scada_tags"

    id = Column(Integer, primary_key=True, autoincrement=True)

    # Logical tag used throughout the app, e.g. 'WG501', 'PL601_TOT'
    tag = Column(String(50), nullable=False, unique=True)

    category = Column(String(20), nullable=False)
    reading_type = Column(String(20), nullable=False)

    # Exact source column in ASMArchive_DB5. For hi_lo this is the base name
    # (WG501 -> WG501_HI / WG501_LO). Source casing is inconsistent
    # (SL601_Product vs SL602_PRODUCT) so store it verbatim.
    source_column = Column(String(64), nullable=True)

    # Counter wrap point: 100000 for palletizers, 1000000 for a _LO word.
    # NULL means the counter does not roll over.
    rollover_max = Column(Numeric(18, 3), nullable=True)

    unit = Column(String(16), nullable=True)

    # Included in the scheduler poll set
    is_pollable = Column(Boolean, nullable=False, default=True)
    is_active = Column(Boolean, nullable=False, default=True)

    # Starting value used by the embedded emulator in demo mode
    emulator_seed = Column(Numeric(18, 3), nullable=True, default=0)

    display_name = Column(String(100), nullable=True)
    sort_order = Column(Integer, nullable=False, default=0)

    created_at = Column(DateTime(timezone=True), nullable=False, server_default=func.now())
    updated_at = Column(DateTime(timezone=True), nullable=False, server_default=func.now(), onupdate=func.now())

    __table_args__ = (
        Index("idx_scada_tag_category", "category", "is_active"),
        Index("idx_scada_tag_pollable", "is_pollable", "is_active"),
    )

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "tag": self.tag,
            "category": self.category,
            "reading_type": self.reading_type,
            "source_column": self.source_column,
            "rollover_max": float(self.rollover_max) if self.rollover_max is not None else None,
            "unit": self.unit,
            "is_pollable": self.is_pollable,
            "is_active": self.is_active,
            "emulator_seed": float(self.emulator_seed) if self.emulator_seed is not None else 0.0,
            "display_name": self.display_name,
            "sort_order": self.sort_order,
        }

    def __repr__(self) -> str:
        return f"<ScadaTag({self.tag} {self.category}/{self.reading_type})>"
