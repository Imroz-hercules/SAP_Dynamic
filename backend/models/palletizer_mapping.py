from sqlalchemy import Column, Integer, String, Float, DateTime, func
from database import Base

class PalletizerMapping(Base):
    __tablename__ = "palletizer_mapping"

    id = Column(Integer, primary_key=True, autoincrement=True)
    version = Column(String(20), unique=True, nullable=False)
    palletizer = Column(String(50), nullable=False)
    bag_size_kg = Column(Float, nullable=False)
    bags_per_pallet = Column(Float, nullable=False)
    kg_per_pallet = Column(Float, nullable=False)
    
    # Description field for additional info about the mapping
    description = Column(String(255), nullable=True)

    # Optional: Only include if column exists in database
    # created_at = Column(DateTime, server_default=func.now())
    # updated_at = Column(DateTime, onupdate=func.now())
