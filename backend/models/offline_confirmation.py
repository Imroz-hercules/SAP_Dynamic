from sqlalchemy import Column, Integer, String, Float, DateTime, JSON, func, Text
from database import PostgresBase
from datetime import datetime

class OfflineConfirmation(PostgresBase):
    __tablename__ = "offline_confirmations"
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    order_id = Column(String(50), nullable=False, index=True)  # PO number
    process_order_id = Column(Integer, nullable=True)  # Internal process order ID
    material = Column(String(200), nullable=True)
    version = Column(String(50), nullable=True)
    confirmed_weight = Column(Float, nullable=False)
    total_qty = Column(Float, nullable=False)
    uom = Column(String(10), nullable=True)
    plant = Column(String(50), nullable=True)
    batch = Column(String(50), nullable=True)
    shift = Column(String(10), nullable=True)
    scrap = Column(Float, default=0.0)  # User-entered scrap value
    confirmed_text = Column(String(500), nullable=True)  # User-entered confirmed text
    sap_payload = Column(JSON, nullable=True)  # Store full SAP payload for retry
    validation_method = Column(String(50), nullable=True)  # 'Manual' or 'Automatic'
    
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())
    sent_at = Column(DateTime(timezone=True), nullable=True)  # When successfully sent to SAP
    
    retry_count = Column(Integer, default=0)  # Number of retry attempts
    status = Column(String(20), default='pending', index=True)  # 'pending', 'sent', 'failed'
    error_message = Column(Text, nullable=True)  # Error message when SAP call fails

    def _format_datetime(self, dt, use_now_as_fallback=False):
        """Format datetime to ISO 8601 string that JavaScript can parse."""
        if dt is None:
            if use_now_as_fallback:
                dt = datetime.now()
            else:
                return None
        # Convert to string format: YYYY-MM-DDTHH:MM:SS (without timezone offset for JS compatibility)
        if hasattr(dt, 'replace'):
            # Remove timezone info for consistent JS parsing
            dt_naive = dt.replace(tzinfo=None) if dt.tzinfo else dt
            return dt_naive.strftime('%Y-%m-%dT%H:%M:%S')
        return str(dt)

    def to_dict(self):
        return {
            "id": self.id,
            "order_id": self.order_id,
            "process_order_id": self.process_order_id,
            "material": self.material,
            "version": self.version,
            "confirmed_weight": self.confirmed_weight,
            "total_qty": self.total_qty,
            "uom": self.uom,
            "plant": self.plant,
            "batch": self.batch,
            "shift": self.shift,
            "scrap": self.scrap,
            "confirmed_text": self.confirmed_text,
            "validation_method": self.validation_method,
            "created_at": self._format_datetime(self.created_at, use_now_as_fallback=True),
            "updated_at": self._format_datetime(self.updated_at),
            "sent_at": self._format_datetime(self.sent_at),
            "retry_count": self.retry_count,
            "status": self.status,
            "error_message": self.error_message
        }

