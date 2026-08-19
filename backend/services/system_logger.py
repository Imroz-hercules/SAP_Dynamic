# backend/services/system_logger.py
import logging
import json
from datetime import datetime, timezone, timedelta
from typing import Optional, Dict, Any, List
from sqlalchemy import text
from database import postgres_engine
from contextlib import contextmanager

log = logging.getLogger(__name__)

class SystemLogger:
    """
    Centralized logging service for system events.
    Captures sync events, operator actions, and system activities.
    """
    
    def __init__(self):
        self.engine = postgres_engine
    
    def get_current_shift(self) -> str:
        """
        Determine the current shift based on the current time.
        
        Returns:
            Shift name (e.g., 'A', 'B', 'C')
        """
        current_hour = datetime.now().hour
        
        if 6 <= current_hour < 14:
            return "A"
        elif 14 <= current_hour < 22:
            return "B"
        else:
            return "C"
    
    def log_event(
        self,
        source: str,
        action: str,
        status: str,
        details: Optional[str] = None,
        operator: Optional[str] = None,
        duration_ms: Optional[int] = None,
        error_code: Optional[str] = None,
        metadata: Optional[Dict[str, Any]] = None,
        shift: Optional[str] = None
    ) -> int:
        """
        Log a system event to the database.
        
        Args:
            source: Source of the event (e.g., 'SAP', 'Hercules', 'SCADA', 'Operator')
            action: Action performed (e.g., 'Manual Sync Triggered', 'Order Push to Hercules')
            status: Status of the action (e.g., 'Success', 'Error', 'Warning')
            details: Additional details about the event
            operator: Operator name if applicable
            duration_ms: Duration of the operation in milliseconds
            error_code: Error code if applicable
            metadata: Additional metadata as JSON
            shift: Shift information (e.g., 'A', 'B', 'C')
            
        Returns:
            ID of the created log entry
        """
        try:
            with self.engine.connect() as conn:
                # Prepare metadata as JSON string
                metadata_json = json.dumps(metadata) if metadata else None
                
                # Set shift if not provided
                if shift is None:
                    shift = self.get_current_shift()
                
                # Insert log entry
                result = conn.execute(
                    text("""
                        INSERT INTO system_logs 
                        (timestamp, source, action, status, details, operator, duration_ms, error_code, log_metadata, created_at, shift)
                        VALUES (:timestamp, :source, :action, :status, :details, :operator, :duration_ms, :error_code, :metadata, :created_at, :shift)
                        RETURNING id
                    """),
                    {
                        'timestamp': datetime.now(timezone.utc),
                        'source': source,
                        'action': action,
                        'status': status,
                        'details': details,
                        'operator': operator,
                        'duration_ms': duration_ms,
                        'error_code': error_code,
                        'metadata': metadata_json,
                        'created_at': datetime.now(timezone.utc),
                        'shift': shift
                    }
                )
                
                log_id = result.fetchone()[0]
                conn.commit()
                
                log.info(f"Logged event: {source} - {action} - {status} (ID: {log_id})")
                return log_id
                
        except Exception as e:
            log.error(f"Failed to log event: {e}")
            raise
    
    @contextmanager
    def log_operation(self, source: str, action: str, operator: Optional[str] = None, metadata: Optional[Dict[str, Any]] = None, shift: Optional[str] = None):
        """
        Context manager to log operation start/end with duration.
        
        Usage:
            with system_logger.log_operation('SAP', 'Order Sync', 'Operator A') as log_id:
                # Perform operation
                pass
        """
        start_time = datetime.now(timezone.utc)
        log_id = None
        
        try:
            # Log operation start
            log_id = self.log_event(
                source=source,
                action=f"{action} - Started",
                status="InProgress",
                operator=operator,
                metadata=metadata,
                shift=shift
            )
            
            yield log_id
            
            # Log operation success
            duration_ms = int((datetime.now(timezone.utc) - start_time).total_seconds() * 1000)
            self.log_event(
                source=source,
                action=f"{action} - Completed",
                status="Success",
                operator=operator,
                duration_ms=duration_ms,
                metadata=metadata,
                shift=shift
            )
            
        except Exception as e:
            # Log operation failure
            duration_ms = int((datetime.now(timezone.utc) - start_time).total_seconds() * 1000)
            self.log_event(
                source=source,
                action=f"{action} - Failed",
                status="Error",
                details=str(e),
                operator=operator,
                duration_ms=duration_ms,
                error_code=getattr(e, 'code', None),
                metadata=metadata,
                shift=shift
            )
            raise
    
    def get_logs(
        self,
        limit: int = 100,
        offset: int = 0,
        source_filter: Optional[str] = None,
        status_filter: Optional[str] = None,
        operator_filter: Optional[str] = None,
        start_date: Optional[datetime] = None,
        end_date: Optional[datetime] = None
    ) -> List[Dict[str, Any]]:
        """
        Retrieve system logs with filtering options.
        
        Args:
            limit: Maximum number of logs to return
            offset: Number of logs to skip
            source_filter: Filter by source
            status_filter: Filter by status
            operator_filter: Filter by operator
            start_date: Filter logs after this date
            end_date: Filter logs before this date
            
        Returns:
            List of log entries
        """
        try:
            with self.engine.connect() as conn:
                # Build query with filters
                where_conditions = []
                params = {'limit': limit, 'offset': offset}
                
                if source_filter:
                    where_conditions.append("source = :source_filter")
                    params['source_filter'] = source_filter
                
                if status_filter:
                    where_conditions.append("status = :status_filter")
                    params['status_filter'] = status_filter
                
                if operator_filter:
                    where_conditions.append("operator = :operator_filter")
                    params['operator_filter'] = operator_filter
                
                if start_date:
                    where_conditions.append("timestamp >= :start_date")
                    params['start_date'] = start_date
                
                if end_date:
                    where_conditions.append("timestamp <= :end_date")
                    params['end_date'] = end_date
                
                where_clause = "WHERE " + " AND ".join(where_conditions) if where_conditions else ""
                
                query = f"""
                    SELECT id, timestamp, source, action, status, details, operator, 
                           duration_ms, error_code, log_metadata, created_at, shift
                    FROM system_logs
                    {where_clause}
                    ORDER BY timestamp DESC
                    LIMIT :limit OFFSET :offset
                """
                
                result = conn.execute(text(query), params)
                
                logs = []
                for row in result:
                    log_entry = {
                        'id': row.id,
                        'timestamp': row.timestamp.isoformat() if row.timestamp else None,
                        'source': row.source,
                        'action': row.action,
                        'status': row.status,
                        'details': row.details,
                        'operator': row.operator,
                        'duration_ms': row.duration_ms,
                        'error_code': row.error_code,
                        'metadata': json.loads(row.log_metadata) if row.log_metadata and isinstance(row.log_metadata, str) else row.log_metadata,
                        'created_at': row.created_at.isoformat() if row.created_at else None,
                        'shift': row.shift
                    }
                    logs.append(log_entry)
                
                return logs
                
        except Exception as e:
            log.error(f"Failed to retrieve logs: {e}")
            raise
    
    def get_shift_logs(self, shift_date: datetime) -> List[Dict[str, Any]]:
        """
        Get logs for a specific shift date.
        Assumes 3 shifts: 06:00-14:00, 14:00-22:00, 22:00-06:00
        """
        try:
            # Calculate shift boundaries
            shift_start = shift_date.replace(hour=6, minute=0, second=0, microsecond=0)
            shift_end = shift_date.replace(hour=22, minute=0, second=0, microsecond=0)
            
            # Handle night shift (22:00-06:00)
            if shift_date.hour >= 22 or shift_date.hour < 6:
                if shift_date.hour >= 22:
                    shift_start = shift_date.replace(hour=22, minute=0, second=0, microsecond=0)
                    shift_end = (shift_date + timedelta(days=1)).replace(hour=6, minute=0, second=0, microsecond=0)
                else:
                    shift_start = (shift_date - timedelta(days=1)).replace(hour=22, minute=0, second=0, microsecond=0)
                    shift_end = shift_date.replace(hour=6, minute=0, second=0, microsecond=0)
            
            return self.get_logs(
                start_date=shift_start,
                end_date=shift_end,
                limit=1000
            )
            
        except Exception as e:
            log.error(f"Failed to get shift logs: {e}")
            raise
    
    def clear_logs(self, older_than_days: int = 30) -> int:
        """
        Clear logs older than specified days.
        
        Args:
            older_than_days: Delete logs older than this many days
            
        Returns:
            Number of logs deleted
        """
        try:
            with self.engine.connect() as conn:
                cutoff_date = datetime.now(timezone.utc) - timedelta(days=older_than_days)
                
                result = conn.execute(
                    text("DELETE FROM system_logs WHERE created_at < :cutoff_date"),
                    {'cutoff_date': cutoff_date}
                )
                
                deleted_count = result.rowcount
                conn.commit()
                
                log.info(f"Cleared {deleted_count} logs older than {older_than_days} days")
                return deleted_count
                
        except Exception as e:
            log.error(f"Failed to clear logs: {e}")
            raise

# Global instance
system_logger = SystemLogger()

# Convenience functions
def log_sync_event(source: str, action: str, status: str, **kwargs):
    """Convenience function to log sync events."""
    return system_logger.log_event(source, action, status, **kwargs)

def log_operator_action(operator: str, action: str, status: str, **kwargs):
    """Convenience function to log operator actions."""
    return system_logger.log_event(source="Operator", action=action, status=status, operator=operator, **kwargs)

def log_sap_event(action: str, status: str, **kwargs):
    """Convenience function to log SAP events."""
    return system_logger.log_event(source="SAP", action=action, status=status, **kwargs)

def log_hercules_event(action: str, status: str, **kwargs):
    """Convenience function to log Hercules events."""
    return system_logger.log_event(source="Hercules", action=action, status=status, **kwargs)

def log_scada_event(action: str, status: str, **kwargs):
    """Convenience function to log SCADA events."""
    return system_logger.log_event(source="SCADA", action=action, status=status, **kwargs)
