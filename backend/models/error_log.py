# backend/models/error_log.py
from sqlalchemy import Column, Integer, String, Text, DateTime
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.sql import func
from database import PostgresBase

class ErrorLog(PostgresBase):
    __tablename__ = "error_log"

    id = Column(Integer, primary_key=True, autoincrement=True)
    po_number = Column(String(50), nullable=True, index=True)
    error_type = Column(String(50), nullable=False)        # sap_failed / validation_rejected / shift_failed
    error_message = Column(Text, nullable=True)
    source = Column(String(50), nullable=True)            # sap_online / sap_offline / validator / worker
    payload = Column(JSONB, nullable=True)                # JSON snapshot for resend/debugging
    status = Column(String(20), nullable=False, default="Open")
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    resolved_at = Column(DateTime(timezone=True), nullable=True)

    def __repr__(self):
        return f"<ErrorLog(id={self.id}, po={self.po_number}, type={self.error_type}, status={self.status})>"
