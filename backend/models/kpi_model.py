# models/kpi_model.py
from sqlalchemy import Column, Float, Integer, String
from sqlalchemy.ext.declarative import declarative_base

Base = declarative_base()

class KpiCalculations(Base):
    __tablename__ = "kpicalculations"

    id = Column(Integer, primary_key=True, autoincrement=True)

    # Milling Fields (WG and DM)
    WG202 = Column(Float)
    WG201 = Column(Float)
    WG101 = Column(Float)
    WG301 = Column(Float)
    WG302 = Column(Float)
    WG501 = Column(Float)
    WG502 = Column(Float)
    WG503 = Column(Float)
    WG202_Total_Running_Time = Column(Float)
    WG202_Stop_Start = Column(Float)
    Daily_Hours = Column(Float)

    DM101 = Column(Float)
    DM102 = Column(Float)
    DM201 = Column(Float)
    DM202 = Column(Float)
    DM203 = Column(Float)

    # Packing Fields (PL)
    PL601 = Column(Float)

    # Optional Metadata
    timestamp = Column(String)  # You can use datetime if needed

