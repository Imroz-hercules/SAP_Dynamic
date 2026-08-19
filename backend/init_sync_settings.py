#!/usr/bin/env python3
"""
Initialize default sync interval settings for SAP synchronization
"""

import logging
from datetime import datetime, timezone
from database import PostgresSessionLocal
from models.user_roles import SyncIntervalSettings

logger = logging.getLogger(__name__)

def init_default_sync_settings():
    """Initialize default sync interval settings"""
    try:
        with PostgresSessionLocal() as db:
            # Check if settings already exist
            existing_settings = db.query(SyncIntervalSettings).all()
            if existing_settings:
                logger.info(f"Found {len(existing_settings)} existing sync settings")
                for setting in existing_settings:
                    logger.info(f"  - {setting.sync_type}: {setting.sync_time} (enabled: {setting.is_enabled})")
                return
            
            # Create default sync settings
            default_settings = [
                {
                    'sync_type': 'raw_data',
                    'sync_time': '09:00',
                    'sync_date': None,
                    'is_enabled': True,
                    'description': 'Raw data sync from ASMReporting_5 to SAP'
                },
                {
                    'sync_type': 'kpi',
                    'sync_time': '09:30',
                    'sync_date': None,
                    'is_enabled': True,
                    'description': 'KPI data sync to SAP (milling and packing)'
                },
                {
                    'sync_type': 'process_orders',
                    'sync_time': '10:00',
                    'sync_interval_minutes': 60,
                    'sync_date': None,
                    'is_enabled': True,
                    'description': 'Process orders sync from SAP'
                }
            ]
            
            for setting_data in default_settings:
                sync_setting = SyncIntervalSettings(
                    sync_type=setting_data['sync_type'],
                    sync_time=setting_data['sync_time'],
                    sync_interval_minutes=setting_data.get('sync_interval_minutes'),
                    sync_date=setting_data['sync_date'],
                    is_enabled=setting_data['is_enabled'],
                    created_at=datetime.now(timezone.utc),
                    updated_at=datetime.now(timezone.utc)
                )
                db.add(sync_setting)
                logger.info(f"Created sync setting: {setting_data['sync_type']} at {setting_data['sync_time']}")
            
            db.commit()
            logger.info("✅ Default sync interval settings initialized successfully")
            
    except Exception as e:
        logger.error(f"❌ Failed to initialize sync settings: {e}")
        raise

if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    init_default_sync_settings()
