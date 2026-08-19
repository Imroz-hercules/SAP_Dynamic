#!/usr/bin/env python3
"""
Background sync scheduler service for automatic data synchronization
"""

import threading
import time
import schedule
import logging
from datetime import datetime, timedelta, timezone
from sqlalchemy.orm import sessionmaker
from database import PostgresSessionLocal, postgres_engine
from models.user_roles import SyncIntervalSettings, SyncStatus
from services.sap_sync_service import SAPSyncService
from services.kpi_service import KPIService
from services.process_order_service import ProcessOrderService
from utils.timezone_utils import get_utc_now, calculate_next_sync_time
import json

logger = logging.getLogger(__name__)

class SyncScheduler:
    """Background scheduler for automatic data synchronization"""
    
    def __init__(self):
        self.running = False
        self.scheduler_thread = None
        self.sync_service = SAPSyncService()
        self.kpi_service = KPIService()
        self.process_order_service = ProcessOrderService()
        
    def start(self):
        """Start the background scheduler"""
        if self.running:
            logger.warning("Sync scheduler is already running")
            return
            
        self.running = True
        self.scheduler_thread = threading.Thread(target=self._run_scheduler, daemon=True)
        self.scheduler_thread.start()
        
        # Schedule initial jobs
        self._schedule_sync_jobs()
        
        logger.info("🚀 Sync scheduler started")
        
    def stop(self):
        """Stop the background scheduler"""
        self.running = False
        if self.scheduler_thread:
            self.scheduler_thread.join(timeout=5)
        logger.info("⏹️ Sync scheduler stopped")
        
    def _run_scheduler(self):
        """Main scheduler loop"""
        while self.running:
            try:
                schedule.run_pending()
                time.sleep(60)  # Check every minute
            except Exception as e:
                logger.error(f"Error in scheduler loop: {e}")
                time.sleep(60)
                
    def _schedule_sync_jobs(self):
        """Schedule sync jobs based on database settings"""
        with PostgresSessionLocal() as db:
            sync_settings = db.query(SyncIntervalSettings).filter(
                SyncIntervalSettings.is_enabled == True
            ).all()
            
            # Clear existing jobs
            schedule.clear()
            
            for setting in sync_settings:
                if setting.interval_minutes > 0:
                    # Schedule the job
                    schedule.every(setting.interval_minutes).minutes.do(
                        self._execute_sync,
                        sync_type=setting.sync_type,
                        setting_id=setting.id
                    )
                    logger.info(f"📅 Scheduled {setting.sync_type} sync every {setting.interval_minutes} minutes")
                    
    def _execute_sync(self, sync_type: str, setting_id: int):
        """Execute a sync operation"""
        start_time = get_utc_now()
        status = "running"
        error_message = None
        records_processed = 0
        records_successful = 0
        records_failed = 0
        sync_result = None
        
        # Create initial sync status record
        sync_status_id = self._create_sync_status_record(sync_type, start_time, "scheduled")
        
        try:
            logger.info(f"🔄 Starting {sync_type} sync...")
            
            # Update status to running
            self._update_sync_status_record(sync_status_id, "running", start_time)
            
            if sync_type == "raw_data":
                result = self.sync_service.send_raw_data_to_sap()
                records_processed = result.get('records_sent', 0)
                records_successful = records_processed if result.get('success', False) else 0
                records_failed = records_processed - records_successful
                sync_result = result
                
            elif sync_type == "kpi":
                result = self.kpi_service.send_all_kpis_to_sap()
                records_processed = result.get('kpis_sent', 0)
                records_successful = records_processed if result.get('success', False) else 0
                records_failed = records_processed - records_successful
                sync_result = result
                
            elif sync_type == "process_orders":
                result = self.process_order_service.sync_process_orders_from_sap()
                records_processed = result.get('orders_synced', 0)
                records_successful = records_processed if result.get('success', False) else 0
                records_failed = records_processed - records_successful
                sync_result = result
                
                # Log additional details for process orders
                if result.get('details'):
                    details = result['details']
                    if details.get('used_fallback'):
                        logger.warning(f"Process order sync used fallback data - SAP API error: {details.get('sap_api_error')}")
                    if details.get('skipped_orders'):
                        logger.info(f"Skipped {len(details['skipped_orders'])} existing orders")
                
            else:
                raise Exception(f"Unknown sync type: {sync_type}")
            
            # Determine final status
            if result.get('success', False):
                status = "success"
                logger.info(f"✅ {sync_type} sync completed successfully. Records processed: {records_processed}")
            else:
                status = "failed"
                error_message = result.get('message', 'Sync completed with errors')
                logger.warning(f"⚠️ {sync_type} sync completed with errors: {error_message}")
            
        except Exception as e:
            status = "error"
            error_message = str(e)
            logger.error(f"❌ {sync_type} sync failed: {e}")
            
        finally:
            end_time = get_utc_now()
            duration_ms = int((end_time - start_time).total_seconds() * 1000)
            
            # Update final sync status record
            self._update_sync_status_record(
                sync_status_id, status, start_time, end_time, duration_ms,
                records_processed, records_successful, records_failed,
                error_message, sync_result
            )
            
            # Update sync interval settings
            self._update_sync_interval_status(setting_id, start_time, status, error_message, records_processed)
    
    def _create_sync_status_record(self, sync_type: str, start_time: datetime, status: str) -> int:
        """Create a new sync status record"""
        try:
            with PostgresSessionLocal() as db:
                sync_status = SyncStatus(
                    sync_type=sync_type,
                    status=status,
                    start_time=start_time,
                    triggered_by="scheduled"
                )
                db.add(sync_status)
                db.commit()
                return sync_status.id
        except Exception as e:
            logger.error(f"Error creating sync status record: {e}")
            return None
    
    def _update_sync_status_record(self, sync_status_id: int, status: str, start_time: datetime = None, 
                                 end_time: datetime = None, duration_ms: int = None,
                                 records_processed: int = None, records_successful: int = None,
                                 records_failed: int = None, error_message: str = None, sync_result: dict = None):
        """Update an existing sync status record"""
        try:
            with PostgresSessionLocal() as db:
                sync_status = db.query(SyncStatus).filter(SyncStatus.id == sync_status_id).first()
                if sync_status:
                    sync_status.status = status
                    if start_time:
                        sync_status.start_time = start_time
                    if end_time:
                        sync_status.end_time = end_time
                    if duration_ms is not None:
                        sync_status.duration_ms = duration_ms
                    if records_processed is not None:
                        sync_status.records_processed = records_processed
                    if records_successful is not None:
                        sync_status.records_successful = records_successful
                    if records_failed is not None:
                        sync_status.records_failed = records_failed
                    if error_message:
                        sync_status.error_message = error_message
                    if sync_result:
                        sync_status.sync_result = json.dumps(sync_result)
                    
                    db.commit()
        except Exception as e:
            logger.error(f"Error updating sync status record: {e}")
    
    def _update_sync_interval_status(self, setting_id: int, start_time: datetime, status: str, error_message: str, records_processed: int):
        """Update sync status in database"""
        try:
            with PostgresSessionLocal() as db:
                setting = db.query(SyncIntervalSettings).filter(
                    SyncIntervalSettings.id == setting_id
                ).first()
                
                if setting:
                    setting.last_sync = start_time
                    
                    # Calculate next sync time
                    if setting.is_enabled and setting.interval_minutes > 0:
                        setting.next_sync = calculate_next_sync_time(start_time, setting.interval_minutes)
                    
                    db.commit()
                    
                # Log the sync activity
                self._log_sync_activity(setting_id, setting.sync_type if setting else "unknown", 
                                      start_time, status, error_message, records_processed)
                                      
        except Exception as e:
            logger.error(f"Error updating sync status: {e}")
            
    def _log_sync_activity(self, setting_id: int, sync_type: str, start_time: datetime, 
                          status: str, error_message: str, records_processed: int):
        """Log sync activity to system logs"""
        try:
            with PostgresSessionLocal() as db:
                from models.user_roles import SystemLog
                
                log_entry = SystemLog(
                    level="INFO" if status == "success" else "ERROR",
                    message=f"Sync {sync_type} {'completed' if status == 'success' else 'failed'}",
                    details=json.dumps({
                        "sync_type": sync_type,
                        "setting_id": setting_id,
                        "status": status,
                        "records_processed": records_processed,
                        "error_message": error_message,
                        "duration_seconds": (datetime.utcnow() - start_time).total_seconds()
                    }),
                    category="sync",
                    source="sync_scheduler"
                )
                
                db.add(log_entry)
                db.commit()
                
        except Exception as e:
            logger.error(f"Error logging sync activity: {e}")
            
    def refresh_schedule(self):
        """Refresh the schedule based on current database settings"""
        self._schedule_sync_jobs()
        logger.info("🔄 Sync schedule refreshed")

# Global scheduler instance
sync_scheduler = SyncScheduler()

def start_sync_scheduler():
    """Start the global sync scheduler"""
    sync_scheduler.start()
    sync_scheduler.refresh_schedule()

def stop_sync_scheduler():
    """Stop the global sync scheduler"""
    sync_scheduler.stop()

def refresh_sync_schedule():
    """Refresh the sync schedule"""
    sync_scheduler.refresh_schedule()
