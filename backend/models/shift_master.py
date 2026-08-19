from database import PostgresBase
from sqlalchemy import Column, Integer, String, Time

class ShiftMaster(PostgresBase):
    __tablename__ = "shift_master"

    id = Column(Integer, primary_key=True, index=True)
    plant = Column(String(20), nullable=False)
    department = Column(String(20), nullable=False)  # MILLING / PACKING
    shift_code = Column(String(10), nullable=False)
    start_time = Column(Time, nullable=False)
    end_time = Column(Time, nullable=False)
    sort_order = Column(Integer, nullable=False)
