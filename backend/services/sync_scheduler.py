#!/usr/bin/env python3
"""
Background sync scheduler service for automatic data synchronization - Time-based version
"""

import threading
import time
import schedule
import logging
from datetime import datetime, timedelta, timezone, time as dt_time
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
    """Background scheduler for automatic data synchronization - Time-based"""
    
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
        
        logger.info("🚀 Time-based sync scheduler started")
        
    def stop(self):
        """Stop the background scheduler"""
        self.running = False
        if self.scheduler_thread:
            self.scheduler_thread.join(timeout=5)
        logger.info("⏹️ Sync scheduler stopped")
        
    def _run_scheduler(self):
        """Main scheduler loop. Uses 15s sleep so 1-min interval jobs run on time."""
        while self.running:
            try:
                schedule.run_pending()
                time.sleep(15)  # Check every 15s so 1-min process_orders sync runs when due
            except Exception as e:
                logger.error(f"Error in scheduler loop: {e}")
                time.sleep(15)
                
    def _schedule_sync_jobs(self):
        """Schedule sync jobs based on database settings - Time-based or Interval-based"""
        with PostgresSessionLocal() as db:
            sync_settings = db.query(SyncIntervalSettings).filter(
                SyncIntervalSettings.is_enabled == True
            ).all()
            
            # Clear existing jobs
            schedule.clear()
            
            for setting in sync_settings:
                try:
                    # Check for interval-based scheduling first
                    if hasattr(setting, 'sync_interval_minutes') and setting.sync_interval_minutes and setting.sync_interval_minutes >= 1:
                        schedule.every(setting.sync_interval_minutes).minutes.do(
                            self._execute_sync,
                            sync_type=setting.sync_type,
                            setting_id=setting.id
                        )
                        logger.info(f"📅 Scheduled {setting.sync_type} sync every {setting.sync_interval_minutes} minutes")
                    
                    # Fallback to time-based scheduling
                    elif setting.sync_time:
                        # Parse sync time (HH:MM format)
                        hour, minute = map(int, setting.sync_time.split(':'))
                        
                        # Schedule the job for daily execution at the specified time
                        schedule.every().day.at(setting.sync_time).do(
                            self._execute_sync,
                            sync_type=setting.sync_type,
                            setting_id=setting.id
                        )
                        logger.info(f"📅 Scheduled {setting.sync_type} sync daily at {setting.sync_time}")
                        
                except (ValueError, AttributeError) as e:
                    logger.error(f"Invalid sync configuration for {setting.sync_type}: {e}")
                    # Schedule with default time (9:00 AM) if everything else fails
                    schedule.every().day.at("09:00").do(
                        self._execute_sync,
                        sync_type=setting.sync_type,
                        setting_id=setting.id
                    )
                    logger.info(f"📅 Scheduled {setting.sync_type} sync daily at 09:00 (default fallback)")
                    
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
            
            # Execute the appropriate sync based on type
            if sync_type == 'raw_data':
                result = self.sync_service.send_raw_data_to_sap()
                records_processed = result.get('records_sent', 0)
                records_successful = records_processed
                sync_result = result
                
            elif sync_type == 'kpi':
                result = self.kpi_service.send_all_kpis_to_sap()
                records_processed = result.get('total_records', 0)
                records_successful = result.get('successful_records', 0)
                records_failed = result.get('failed_records', 0)
                sync_result = result
                
            elif sync_type == 'process_orders':
                result = self.process_order_service.sync_process_orders_from_sap()
                # Service returns orders_synced; map for status record
                orders_synced = result.get('orders_synced', 0)
                records_processed = result.get('orders_processed', orders_synced)
                records_successful = result.get('orders_successful', orders_synced if result.get('success') else 0)
                records_failed = result.get('orders_failed', 0)
                sync_result = result
                
            else:
                raise ValueError(f"Unknown sync type: {sync_type}")
            
            # Update sync status to success
            status = "success"
            logger.info(f"✅ {sync_type} sync completed successfully")
            
        except Exception as e:
            status = "error"
            error_message = str(e)
            logger.error(f"❌ {sync_type} sync failed: {e}")
            
        finally:
            # Update sync status record
            end_time = get_utc_now()
            duration_ms = int((end_time - start_time).total_seconds() * 1000)
            
            self._update_sync_status_record(
                sync_status_id, 
                status, 
                end_time, 
                duration_ms,
                records_processed,
                records_successful,
                records_failed,
                error_message,
                sync_result
            )
            
            # Update the sync setting with last sync time and calculate next sync
            self._update_sync_setting(setting_id, end_time, sync_type)
            
    def _create_sync_status_record(self, sync_type: str, start_time: datetime, status: str) -> int:
        """Create a sync status record"""
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
            
    def _update_sync_status_record(self, sync_status_id: int, status: str, end_time: datetime, 
                                 duration_ms: int, records_processed: int, records_successful: int, 
                                 records_failed: int, error_message: str, sync_result: dict):
        """Update sync status record with results"""
        with PostgresSessionLocal() as db:
            sync_status = db.query(SyncStatus).filter(SyncStatus.id == sync_status_id).first()
            if sync_status:
                sync_status.status = status
                sync_status.end_time = end_time
                sync_status.duration_ms = duration_ms
                sync_status.records_processed = records_processed
                sync_status.records_successful = records_successful
                sync_status.records_failed = records_failed
                sync_status.error_message = error_message
                if sync_result:
                    sync_status.sync_result = json.dumps(sync_result)
                db.commit()
                
    def _update_sync_setting(self, setting_id: int, last_sync_time: datetime, sync_type: str):
        """Update sync setting with last sync time and next sync from table (interval or daily time)."""
        with PostgresSessionLocal() as db:
            setting = db.query(SyncIntervalSettings).filter(SyncIntervalSettings.id == setting_id).first()
            if setting:
                setting.last_sync = last_sync_time
                # Use table dynamically: interval-based vs time-based
                if getattr(setting, 'sync_interval_minutes', None) and setting.sync_interval_minutes >= 1:
                    setting.next_sync = calculate_next_sync_time(last_sync_time, interval_minutes=setting.sync_interval_minutes)
                else:
                    setting.next_sync = calculate_next_sync_time(last_sync_time, sync_time_str=setting.sync_time, sync_date_str=setting.sync_date)
                db.commit()
                logger.info(f"📅 Next {sync_type} sync scheduled for: {setting.next_sync}")
                
    def get_scheduled_jobs(self):
        """Get information about currently scheduled jobs"""
        jobs = []
        for job in schedule.jobs:
            jobs.append({
                'job': str(job.job_func),
                'next_run': job.next_run.isoformat() if job.next_run else None,
                'interval': str(job.interval),
                'unit': job.unit
            })
        return jobs
        
    def refresh_schedule(self):
        """Refresh the schedule based on current database settings"""
        logger.info("🔄 Refreshing sync schedule...")
        if self.running:
            self._schedule_sync_jobs()
            logger.info("✅ Sync schedule refreshed with new settings")
        else:
            logger.warning("⚠️ Scheduler not running - cannot refresh schedule")
    
    def get_scheduler_status(self):
        """Get current scheduler status"""
        return {
            'running': self.running,
            'jobs_count': len(schedule.jobs),
            'jobs': self.get_scheduled_jobs()
        }

# Global scheduler instance
sync_scheduler = SyncScheduler()

def start_sync_scheduler():
    """Start the global sync scheduler"""
    sync_scheduler.start()

def stop_sync_scheduler():
    """Stop the global sync scheduler"""
    sync_scheduler.stop()

def refresh_sync_schedule():
    """Refresh the global sync schedule"""
    sync_scheduler.refresh_schedule()

def get_scheduler_status():
    """Get the global scheduler status"""
    return sync_scheduler.get_scheduler_status()
