# backend/models/material_model.py
from sqlalchemy import Column, Integer, String
from sqlalchemy.ext.declarative import declarative_base

Base = declarative_base()

class MaterialMapping(Base):
    __tablename__ = "material_mappings"

    id = Column(Integer, primary_key=True, autoincrement=True)
    material = Column(String(100), nullable=False)
    version = Column(String(50), nullable=False)
    scale = Column(String(100))
    recipe = Column(String(100))
    packingLine = Column(String(100))
