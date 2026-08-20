# backend/models/classification_rule.py
"""
Classification rules - Workstream A.

Replaces the hardcoded order-routing decisions:
  - material prefix "13" -> MILLING / "14" -> PACKING  (order_validation.py:6247)
  - plant "3130" -> MILLING, anything else -> PACKING  (16 call sites)

Schema is fixed as of commit 0. Extend it through your own
backend/migrate_*.py, not by editing setup_sap_postgres.sql.
"""
from sqlalchemy import (
    Column, Integer, String, Boolean, DateTime, UniqueConstraint, Index
)
from sqlalchemy.sql import func

from database import PostgresBase

RULE_MATERIAL_PREFIX = "material_prefix"
RULE_PLANT_DEPARTMENT = "plant_department"

WILDCARD = "*"


class ClassificationRule(PostgresBase):
    __tablename__ = "classification_rules"

    id = Column(Integer, primary_key=True, autoincrement=True)

    # 'material_prefix' | 'plant_department'
    rule_type = Column(String(32), nullable=False)

    # '13', '14', '3130', or '*' for the catch-all
    match_value = Column(String(32), nullable=False)

    # 'MILLING' | 'PACKING'
    result_value = Column(String(32), nullable=False)

    # Lower number wins. The '*' catch-all should sort last.
    priority = Column(Integer, nullable=False, default=100)

    is_active = Column(Boolean, nullable=False, default=True)
    description = Column(String(255), nullable=True)

    created_at = Column(DateTime(timezone=True), nullable=False, server_default=func.now())
    updated_at = Column(DateTime(timezone=True), nullable=False, server_default=func.now(), onupdate=func.now())

    __table_args__ = (
        UniqueConstraint("rule_type", "match_value", name="uq_classification_rule"),
        Index("idx_classification_rule_lookup", "rule_type", "is_active", "priority"),
    )

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "rule_type": self.rule_type,
            "match_value": self.match_value,
            "result_value": self.result_value,
            "priority": self.priority,
            "is_active": self.is_active,
            "description": self.description,
        }

    def __repr__(self) -> str:
        return f"<ClassificationRule({self.rule_type} {self.match_value} -> {self.result_value})>"
