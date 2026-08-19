from sqlalchemy import Column, Integer, String, Text, DateTime, func
from sqlalchemy.dialects.postgresql import JSONB
from database import PostgresBase

class SapLog(PostgresBase):
    __tablename__ = "sap_logs"
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    direction = Column(String(10), nullable=False)  # 'sent' or 'received'
    endpoint = Column(String(200), nullable=True)  # SAP endpoint URL
    method = Column(String(10), nullable=True)  # 'GET', 'POST', etc.
    request_payload = Column(JSONB, nullable=True)  # JSON sent to SAP
    response_payload = Column(JSONB, nullable=True)  # JSON received from SAP
    status_code = Column(Integer, nullable=True)  # HTTP status code
    error_message = Column(Text, nullable=True)  # Error message if failed
    duration_ms = Column(Integer, nullable=True)  # Request duration in milliseconds
    po_number = Column(String(50), nullable=True, index=True)  # Related order (if applicable)
    log_type = Column(String(50), nullable=True)  # 'order_confirmation', 'order_sync', 'kpi', 'raw_data', etc.
    created_at = Column(DateTime(timezone=True), server_default=func.now(), index=True)
    
    def __repr__(self):
        return f"<SapLog(id={self.id}, direction={self.direction}, endpoint={self.endpoint})>"

