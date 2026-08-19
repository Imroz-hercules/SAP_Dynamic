# routes/sync_interval_routes.py
"""
Sync interval management routes with role-based access control - Clean Time and Date based version
"""

from flask import Blueprint, request, jsonify
from sqlalchemy.orm import sessionmaker
from database import postgres_engine
from models.user_roles import SyncIntervalSettings, SystemLog, SyncStatus
from services.auth_service import (
    require_auth, 
    require_sync_interval_view, 
    require_sync_interval_change,
    require_manager_or_admin
)
from services.sync_scheduler import refresh_sync_schedule
from datetime import datetime, timedelta, timezone
from utils.timezone_utils import get_utc_now, format_datetime_for_api, calculate_next_sync_time
import logging
import json

logger = logging.getLogger(__name__)

# Database session
PostgresSessionLocal = sessionmaker(bind=postgres_engine, autocommit=False, autoflush=False)

sync_interval_bp = Blueprint("sync_interval", __name__, url_prefix="/api/sync-interval")

@sync_interval_bp.route("/settings", methods=["GET"])
@require_sync_interval_view
def get_sync_settings():
    """Get all sync interval settings (viewable by users with view permission)"""
    try:
        with PostgresSessionLocal() as db:
            settings = db.query(SyncIntervalSettings).all()
            
            settings_list = []
            for setting in settings:
                settings_list.append({
                    'id': setting.id,
                    'sync_type': setting.sync_type,
                    'sync_time': setting.sync_time,
                    'sync_date': setting.sync_date,
                    'is_enabled': setting.is_enabled,
                    'last_sync': format_datetime_for_api(setting.last_sync),
                    'next_sync': format_datetime_for_api(setting.next_sync),
                    'created_at': setting.created_at.isoformat() if setting.created_at else None,
                    'updated_at': setting.updated_at.isoformat() if setting.updated_at else None,
                    'description': get_sync_type_description(setting.sync_type)
                })
            
            return jsonify({
                'success': True,
                'settings': settings_list
            })
            
    except Exception as e:
        logger.error(f"Failed to get sync settings: {str(e)}")
        return jsonify({'error': str(e)}), 500

@sync_interval_bp.route("/settings/<string:sync_type>", methods=["GET"])
@require_sync_interval_view
def get_sync_setting(sync_type):
    """Get specific sync interval setting"""
    try:
        with PostgresSessionLocal() as db:
            setting = db.query(SyncIntervalSettings).filter(
                SyncIntervalSettings.sync_type == sync_type
            ).first()
            
            if not setting:
                return jsonify({'error': 'Sync setting not found'}), 404
            
            return jsonify({
                'success': True,
                'setting': {
                    'id': setting.id,
                    'sync_type': setting.sync_type,
                    'sync_time': setting.sync_time,
                    'sync_date': setting.sync_date,
                    'is_enabled': setting.is_enabled,
                    'last_sync': format_datetime_for_api(setting.last_sync),
                    'next_sync': format_datetime_for_api(setting.next_sync),
                    'created_at': setting.created_at.isoformat() if setting.created_at else None,
                    'updated_at': setting.updated_at.isoformat() if setting.updated_at else None,
                    'description': get_sync_type_description(setting.sync_type)
                }
            })
            
    except Exception as e:
        logger.error(f"Failed to get sync setting: {str(e)}")
        return jsonify({'error': str(e)}), 500

@sync_interval_bp.route("/settings/<string:sync_type>", methods=["PUT"])
@require_sync_interval_change
def update_sync_setting(sync_type):
    """Update sync interval setting (requires change permission)"""
    try:
        data = request.get_json()
        sync_time = data.get('sync_time')
        sync_date = data.get('sync_date')
        is_enabled = data.get('is_enabled')
        
        if sync_time is None and sync_date is None and is_enabled is None:
            return jsonify({'error': 'At least one field (sync_time, sync_date, or is_enabled) is required'}), 400
        
        if sync_time is not None:
            # Validate sync_time format (HH:MM)
            try:
                hour, minute = map(int, sync_time.split(':'))
                if not (0 <= hour <= 23 and 0 <= minute <= 59):
                    return jsonify({'error': 'sync_time must be in HH:MM format with valid time'}), 400
            except (ValueError, AttributeError):
                return jsonify({'error': 'sync_time must be in HH:MM format (e.g., 09:00)'}), 400
        
        if sync_date is not None and sync_date != '':
            # Validate sync_date format (YYYY-MM-DD)
            try:
                from datetime import datetime
                datetime.strptime(sync_date, '%Y-%m-%d')
            except ValueError:
                return jsonify({'error': 'sync_date must be in YYYY-MM-DD format (e.g., 2025-12-25)'}), 400
        
        with PostgresSessionLocal() as db:
            setting = db.query(SyncIntervalSettings).filter(
                SyncIntervalSettings.sync_type == sync_type
            ).first()
            
            if not setting:
                return jsonify({'error': 'Sync setting not found'}), 404
            
            # Update fields
            if sync_time is not None:
                setting.sync_time = sync_time
                # Update next_sync based on new sync time
                if setting.is_enabled:
                    setting.next_sync = calculate_next_sync_time(setting.last_sync, sync_time_str=sync_time, sync_date_str=setting.sync_date)
            
            if sync_date is not None:
                setting.sync_date = sync_date if sync_date != '' else None
                # Update next_sync based on new sync date
                if setting.is_enabled:
                    setting.next_sync = calculate_next_sync_time(setting.last_sync, sync_time_str=setting.sync_time, sync_date_str=setting.sync_date)
            
            if is_enabled is not None:
                setting.is_enabled = is_enabled
                if is_enabled:
                    # If enabling, set next sync based on current sync time and date
                    setting.next_sync = calculate_next_sync_time(setting.last_sync, sync_time_str=setting.sync_time, sync_date_str=setting.sync_date)
                elif not is_enabled:
                    # If disabling, clear next sync
                    setting.next_sync = None
            
            setting.updated_at = get_utc_now()
            setting.updated_by = request.current_user['user_id']
            
            db.commit()
            
            # Refresh the sync scheduler
            try:
                from services.sync_scheduler import sync_scheduler
                sync_scheduler.refresh_schedule()
            except Exception as e:
                logger.error(f"Error refreshing sync schedule: {e}")
            
            # Log the sync setting change
            try:
                log_entry = SystemLog(
                    level="INFO",
                    message=f"Sync interval setting updated for {sync_type}",
                    details=json.dumps({
                        "sync_type": sync_type,
                        "sync_time": setting.sync_time,
                        "sync_date": setting.sync_date,
                        "is_enabled": setting.is_enabled,
                        "updated_by": request.current_user.get('username', 'unknown')
                    }),
                    category="sync",
                    source="sync_interval_routes",
                    action="update_sync_interval",
                    status="success"
                )
                db.add(log_entry)
                db.commit()
            except Exception as log_error:
                logger.warning(f"Failed to log sync setting change: {log_error}")
                # Don't fail the main operation if logging fails
            
            # Refresh the scheduler with new settings
            try:
                refresh_sync_schedule()
                logger.info(f"Sync schedule refreshed after updating {sync_type}")
            except Exception as e:
                logger.error(f"Failed to refresh sync schedule: {e}")
            
            return jsonify({
                'success': True,
                'message': f'Sync setting for {sync_type} updated successfully',
                'setting': {
                    'id': setting.id,
                    'sync_type': setting.sync_type,
                    'sync_time': setting.sync_time,
                    'sync_date': setting.sync_date,
                    'is_enabled': setting.is_enabled,
                    'last_sync': format_datetime_for_api(setting.last_sync),
                    'next_sync': format_datetime_for_api(setting.next_sync),
                    'updated_at': setting.updated_at.isoformat(),
                    'description': get_sync_type_description(setting.sync_type)
                }
            })
            
    except Exception as e:
        logger.error(f"Failed to update sync setting: {str(e)}")
        # Log the error
        try:
            with PostgresSessionLocal() as db:
                error_log = SystemLog(
                    level="ERROR",
                    message=f"Failed to update sync setting for {sync_type}",
                    details=json.dumps({
                        "sync_type": sync_type,
                        "error": str(e),
                        "updated_by": getattr(request, 'current_user', {}).get('username', 'unknown')
                    }),
                    category="sync",
                    source="sync_interval_routes",
                    action="update_sync_interval",
                    status="error",
                    error_code="UPDATE_FAILED"
                )
                db.add(error_log)
                db.commit()
        except:
            pass  # Don't fail if logging fails
        
        return jsonify({
            'error': 'Failed to update sync setting',
            'message': 'An error occurred while updating the sync interval. Please try again.',
            'details': str(e)
        }), 500

@sync_interval_bp.route("/settings/<string:sync_type>/save", methods=["POST"])
@require_sync_interval_change
def save_sync_setting(sync_type):
    """Save sync setting and refresh scheduler"""
    try:
        data = request.get_json()
        sync_time = data.get('sync_time')
        sync_date = data.get('sync_date')
        is_enabled = data.get('is_enabled')
        
        if sync_time is None and sync_date is None and is_enabled is None:
            return jsonify({'error': 'At least one field (sync_time, sync_date, or is_enabled) is required'}), 400
        
        if sync_time is not None:
            # Validate sync_time format (HH:MM)
            try:
                hour, minute = map(int, sync_time.split(':'))
                if not (0 <= hour <= 23 and 0 <= minute <= 59):
                    return jsonify({'error': 'sync_time must be in HH:MM format with valid time'}), 400
            except (ValueError, AttributeError):
                return jsonify({'error': 'sync_time must be in HH:MM format (e.g., 09:00)'}), 400
        
        if sync_date is not None and sync_date != '':
            # Validate sync_date format (YYYY-MM-DD)
            try:
                from datetime import datetime
                datetime.strptime(sync_date, '%Y-%m-%d')
            except ValueError:
                return jsonify({'error': 'sync_date must be in YYYY-MM-DD format (e.g., 2025-12-25)'}), 400
        
        with PostgresSessionLocal() as db:
            setting = db.query(SyncIntervalSettings).filter(
                SyncIntervalSettings.sync_type == sync_type
            ).first()
            
            if not setting:
                return jsonify({'error': 'Sync setting not found'}), 404
            
            # Update fields
            if sync_time is not None:
                setting.sync_time = sync_time
                # Update next_sync based on new sync time
                if setting.is_enabled:
                    setting.next_sync = calculate_next_sync_time(setting.last_sync, sync_time_str=sync_time, sync_date_str=setting.sync_date)
            
            if sync_date is not None:
                setting.sync_date = sync_date if sync_date != '' else None
                # Update next_sync based on new sync date
                if setting.is_enabled:
                    setting.next_sync = calculate_next_sync_time(setting.last_sync, sync_time_str=setting.sync_time, sync_date_str=setting.sync_date)
            
            if is_enabled is not None:
                setting.is_enabled = is_enabled
                if is_enabled:
                    # If enabling, set next sync based on current sync time and date
                    setting.next_sync = calculate_next_sync_time(setting.last_sync, sync_time_str=setting.sync_time, sync_date_str=setting.sync_date)
                elif not is_enabled:
                    # If disabling, clear next sync
                    setting.next_sync = None
            
            setting.updated_at = get_utc_now()
            setting.updated_by = request.current_user['user_id']
            
            db.commit()
            
            # Refresh the sync scheduler
            try:
                from services.sync_scheduler import sync_scheduler
                sync_scheduler.refresh_schedule()
            except Exception as e:
                logger.error(f"Error refreshing sync schedule: {e}")
            
            # Log the sync setting change
            try:
                log_entry = SystemLog(
                    level="INFO",
                    message=f"Sync interval setting saved for {sync_type}",
                    details=json.dumps({
                        "sync_type": sync_type,
                        "sync_time": setting.sync_time,
                        "sync_date": setting.sync_date,
                        "is_enabled": setting.is_enabled,
                        "updated_by": request.current_user.get('username', 'unknown')
                    }),
                    category="sync",
                    source="sync_interval_routes",
                    action="save_sync_interval",
                    status="success"
                )
                db.add(log_entry)
                db.commit()
            except Exception as log_error:
                logger.warning(f"Failed to log sync setting save: {log_error}")
                # Don't fail the main operation if logging fails
            
            # Refresh the scheduler with new settings
            try:
                refresh_sync_schedule()
                logger.info(f"Sync schedule refreshed after saving {sync_type}")
            except Exception as e:
                logger.error(f"Failed to refresh sync schedule: {e}")
            
            return jsonify({
                'success': True,
                'message': f'Sync setting for {sync_type} saved successfully',
                'setting': {
                    'id': setting.id,
                    'sync_type': setting.sync_type,
                    'sync_time': setting.sync_time,
                    'sync_date': setting.sync_date,
                    'is_enabled': setting.is_enabled,
                    'last_sync': format_datetime_for_api(setting.last_sync),
                    'next_sync': format_datetime_for_api(setting.next_sync),
                    'updated_at': setting.updated_at.isoformat(),
                    'description': get_sync_type_description(setting.sync_type)
                }
            })
            
    except Exception as e:
        logger.error(f"Failed to save sync setting: {str(e)}")
        # Log the error
        try:
            with PostgresSessionLocal() as db:
                error_log = SystemLog(
                    level="ERROR",
                    message=f"Failed to save sync setting for {sync_type}",
                    details=json.dumps({
                        "sync_type": sync_type,
                        "error": str(e),
                        "updated_by": getattr(request, 'current_user', {}).get('username', 'unknown')
                    }),
                    category="sync",
                    source="sync_interval_routes",
                    action="save_sync_interval",
                    status="error",
                    error_code="SAVE_FAILED"
                )
                db.add(error_log)
                db.commit()
        except:
            pass  # Don't fail if logging fails
        
        return jsonify({
            'error': 'Failed to save sync setting',
            'message': 'An error occurred while saving the sync interval. Please try again.',
            'details': str(e)
        }), 500

@sync_interval_bp.route("/logs", methods=["GET"])
@require_sync_interval_view
def get_sync_logs():
    """Get sync activity logs"""
    try:
        page = request.args.get('page', 1, type=int)
        per_page = request.args.get('per_page', 50, type=int)
        category = request.args.get('category', 'sync')
        
        with PostgresSessionLocal() as db:
            query = db.query(SystemLog).filter(SystemLog.category == category)
            
            # Get total count
            total = query.count()
            
            # Get paginated results
            logs = query.order_by(SystemLog.created_at.desc()).offset(
                (page - 1) * per_page
            ).limit(per_page).all()
            
            log_list = []
            for log in logs:
                details = {}
                if log.details:
                    try:
                        details = json.loads(log.details)
                    except:
                        details = {"raw": log.details}
                
                log_list.append({
                    'id': log.id,
                    'level': log.level,
                    'message': log.message,
                    'details': details,
                    'category': log.category,
                    'source': log.source,
                    'created_at': log.created_at.isoformat()
                })
            
            return jsonify({
                'success': True,
                'logs': log_list,
                'pagination': {
                    'page': page,
                    'per_page': per_page,
                    'total': total,
                    'pages': (total + per_page - 1) // per_page
                }
            })
            
    except Exception as e:
        logger.error(f"Failed to get sync logs: {str(e)}")
        return jsonify({'error': str(e)}), 500

@sync_interval_bp.route("/status", methods=["GET"])
@require_sync_interval_view
def get_sync_status():
    """Get current sync status for all sync types"""
    try:
        with PostgresSessionLocal() as db:
            # Get latest sync status for each sync type
            sync_types = ['raw_data', 'kpi', 'process_orders']
            status_list = []
            
            for sync_type in sync_types:
                latest_status = db.query(SyncStatus).filter(
                    SyncStatus.sync_type == sync_type
                ).order_by(SyncStatus.start_time.desc()).first()
                
                if latest_status:
                    status_list.append({
                        'sync_type': latest_status.sync_type,
                        'status': latest_status.status,
                        'start_time': latest_status.start_time.isoformat() if latest_status.start_time else None,
                        'end_time': latest_status.end_time.isoformat() if latest_status.end_time else None,
                        'duration_ms': latest_status.duration_ms,
                        'records_processed': latest_status.records_processed,
                        'records_successful': latest_status.records_successful,
                        'records_failed': latest_status.records_failed,
                        'error_message': latest_status.error_message,
                        'triggered_by': latest_status.triggered_by,
                        'created_at': latest_status.created_at.isoformat()
                    })
                else:
                    # No sync status found, return default
                    status_list.append({
                        'sync_type': sync_type,
                        'status': 'never_run',
                        'start_time': None,
                        'end_time': None,
                        'duration_ms': None,
                        'records_processed': 0,
                        'records_successful': 0,
                        'records_failed': 0,
                        'error_message': None,
                        'triggered_by': None,
                        'created_at': None
                    })
            
            return jsonify({
                'success': True,
                'status_list': status_list
            })
            
    except Exception as e:
        logger.error(f"Failed to get sync status: {str(e)}")
        return jsonify({'error': str(e)}), 500

@sync_interval_bp.route("/status/<string:sync_type>", methods=["GET"])
@require_sync_interval_view
def get_sync_status_by_type(sync_type):
    """Get sync status history for a specific sync type"""
    try:
        page = request.args.get('page', 1, type=int)
        per_page = request.args.get('per_page', 20, type=int)
        
        with PostgresSessionLocal() as db:
            query = db.query(SyncStatus).filter(SyncStatus.sync_type == sync_type)
            
            # Get total count
            total = query.count()
            
            # Get paginated results
            status_history = query.order_by(SyncStatus.start_time.desc()).offset(
                (page - 1) * per_page
            ).limit(per_page).all()
            
            status_list = []
            for status in status_history:
                status_list.append({
                    'id': status.id,
                    'sync_type': status.sync_type,
                    'status': status.status,
                    'start_time': status.start_time.isoformat() if status.start_time else None,
                    'end_time': status.end_time.isoformat() if status.end_time else None,
                    'duration_ms': status.duration_ms,
                    'records_processed': status.records_processed,
                    'records_successful': status.records_successful,
                    'records_failed': status.records_failed,
                    'error_message': status.error_message,
                    'error_details': json.loads(status.error_details) if status.error_details else None,
                    'sync_result': json.loads(status.sync_result) if status.sync_result else None,
                    'triggered_by': status.triggered_by,
                    'created_at': status.created_at.isoformat()
                })
            
            return jsonify({
                'success': True,
                'status_history': status_list,
                'pagination': {
                    'page': page,
                    'per_page': per_page,
                    'total': total,
                    'pages': (total + per_page - 1) // per_page
                }
            })
            
    except Exception as e:
        logger.error(f"Failed to get sync status history: {str(e)}")
        return jsonify({'error': str(e)}), 500

@sync_interval_bp.route("/settings", methods=["POST"])
@require_manager_or_admin
def create_sync_setting():
    """Create new sync interval setting (manager/admin only)"""
    try:
        data = request.get_json()
        sync_type = data.get('sync_type')
        sync_time = data.get('sync_time', '09:00')
        sync_date = data.get('sync_date')
        is_enabled = data.get('is_enabled', True)
        
        if not sync_type:
            return jsonify({'error': 'sync_type is required'}), 400
        
        # Validate sync_time format (HH:MM)
        try:
            hour, minute = map(int, sync_time.split(':'))
            if not (0 <= hour <= 23 and 0 <= minute <= 59):
                return jsonify({'error': 'sync_time must be in HH:MM format with valid time'}), 400
        except (ValueError, AttributeError):
            return jsonify({'error': 'sync_time must be in HH:MM format (e.g., 09:00)'}), 400
        
        if sync_date is not None and sync_date != '':
            # Validate sync_date format (YYYY-MM-DD)
            try:
                from datetime import datetime
                datetime.strptime(sync_date, '%Y-%m-%d')
            except ValueError:
                return jsonify({'error': 'sync_date must be in YYYY-MM-DD format (e.g., 2025-12-25)'}), 400
        
        with PostgresSessionLocal() as db:
            # Check if setting already exists
            existing = db.query(SyncIntervalSettings).filter(
                SyncIntervalSettings.sync_type == sync_type
            ).first()
            
            if existing:
                return jsonify({'error': f'Sync setting for {sync_type} already exists'}), 409
            
            # Create new setting
            setting = SyncIntervalSettings(
                sync_type=sync_type,
                sync_time=sync_time,
                sync_date=sync_date if sync_date != '' else None,
                is_enabled=is_enabled,
                created_by=request.current_user['user_id'],
                updated_by=request.current_user['user_id']
            )
            
            db.add(setting)
            db.commit()
            
            return jsonify({
                'success': True,
                'message': f'Sync setting for {sync_type} created successfully',
                'setting': {
                    'id': setting.id,
                    'sync_type': setting.sync_type,
                    'sync_time': setting.sync_time,
                    'sync_date': setting.sync_date,
                    'is_enabled': setting.is_enabled,
                    'created_at': setting.created_at.isoformat(),
                    'description': get_sync_type_description(setting.sync_type)
                }
            }), 201
            
    except Exception as e:
        logger.error(f"Failed to create sync setting: {str(e)}")
        return jsonify({'error': str(e)}), 500

def get_sync_type_description(sync_type):
    """Get human-readable description for sync type"""
    descriptions = {
        'raw_data': 'Raw data sync from ASMReporting_5 to SAP',
        'kpi': 'KPI data sync to SAP (milling and packing)',
        'process_orders': 'Process orders sync from SAP',
        'scada': 'SCADA data sync',
        'reports': 'Reports data sync'
    }
    return descriptions.get(sync_type, f'{sync_type} data sync')
