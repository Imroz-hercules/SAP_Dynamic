# backend/models/milling_version_mapping.py
from sqlalchemy import Column, Integer, String, JSON
from database import PostgresBase

class MillingVersionMapping(PostgresBase):
    __tablename__ = "milling_version_mappings"

    id = Column(Integer, primary_key=True, autoincrement=True)

    # Version name (LWSM, CWIM, CKF1, etc)
    version = Column(String(50), unique=True, nullable=False)

    # Scales used for confirmed weight (main formula input)
    # Example: ["WG201", "WG301", "DM201", "DM202", "DM203"]
    scales = Column(JSON, nullable=False)

    # Formula for total weight (same as currently stored in MILLING_PV_SPECS)
    # Example: "(WG201-WG301)+(DM201+DM202+DM203)"
    formula = Column(String(200), nullable=False)

    # Byproduct scale mapping (scale1/2/3)
    # These were in MILLING_BYPRODUCT_MAPPING
    scale1 = Column(String(50), nullable=True)
    scale2 = Column(String(50), nullable=True)
    scale3 = Column(String(50), nullable=True)  # Optional third byproduct scale
    
    # Description field for additional info about the mapping
    description = Column(String(255), nullable=True)

    # SCADA recipe name(s) – e.g. "F80", "F80 + F70" (comma-separated if multiple)
    scada_recipe_name = Column(String(255), nullable=True)
