# backend/models/material_map.py  (optional but helpful)
from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy import String, Integer, UniqueConstraint
from .base import Base, TimestampMixin

class MaterialMap(Base, TimestampMixin):
    __tablename__ = "material_map"
    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    internal_code: Mapped[str] = mapped_column(String(32), index=True)
    sap_code: Mapped[str] = mapped_column(String(32), index=True)
    name: Mapped[str] = mapped_column(String(128))

    __table_args__ = (UniqueConstraint("internal_code", "sap_code", name="uq_map_internal_sap"), )
