# backend/models/product.py
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy import String, Boolean, Integer
from .base import Base, TimestampMixin

class Product(Base, TimestampMixin):
    __tablename__ = "products"
    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    code: Mapped[str] = mapped_column(String(32), unique=True, index=True)   # e.g. SAP material code for FG
    name: Mapped[str] = mapped_column(String(128))
    uom:  Mapped[str] = mapped_column(String(8), default="KG")
    active: Mapped[bool] = mapped_column(Boolean, default=True)

    process_orders = relationship("ProcessOrder", back_populates="product")
