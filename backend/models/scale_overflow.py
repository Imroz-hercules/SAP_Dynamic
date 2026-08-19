from sqlalchemy import Column, String, Float, DateTime, func
from database import PostgresBase

class ScaleOverflow(PostgresBase):
    __tablename__ = "scale_overflows"
    
    scale_tag = Column(String(50), primary_key=True)
    overflow_qty = Column(Float, default=0.0)
    last_updated = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())

