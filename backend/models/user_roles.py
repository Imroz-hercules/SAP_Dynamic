# models/user_roles.py
from sqlalchemy import Column, Integer, String, Boolean, DateTime, Text, ForeignKey
from sqlalchemy.orm import relationship
from database import PostgresBase
from datetime import datetime, timezone

class User(PostgresBase):
    """User table for role-based access control"""
    __tablename__ = 'users'
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    username = Column(String(100), unique=True, nullable=False)
    email = Column(String(255), unique=True, nullable=False)
    password_hash = Column(String(255), nullable=False)
    full_name = Column(String(255), nullable=True)
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))
    updated_at = Column(DateTime, default=lambda: datetime.now(timezone.utc), onupdate=lambda: datetime.now(timezone.utc))
    
    # Relationship to user roles
    roles = relationship("UserRole", back_populates="user", foreign_keys="UserRole.user_id")

class Role(PostgresBase):
    """Role table defining different access levels"""
    __tablename__ = 'roles'
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    name = Column(String(50), unique=True, nullable=False)  # admin, manager, user, guest
    description = Column(Text, nullable=True)
    permissions = Column(Text, nullable=True)  # JSON string of permissions
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))
    updated_at = Column(DateTime, default=lambda: datetime.now(timezone.utc), onupdate=lambda: datetime.now(timezone.utc))
    
    # Relationship to user roles
    users = relationship("UserRole", back_populates="role")

class UserRole(PostgresBase):
    """Many-to-many relationship between users and roles"""
    __tablename__ = 'user_roles'
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    user_id = Column(Integer, ForeignKey('users.id'), nullable=False)
    role_id = Column(Integer, ForeignKey('roles.id'), nullable=False)
    assigned_at = Column(DateTime, default=datetime.utcnow)
    assigned_by = Column(Integer, ForeignKey('users.id'), nullable=True)
    
    # Relationships - specify foreign_keys to avoid ambiguity
    user = relationship("User", foreign_keys=[user_id], back_populates="roles")
    role = relationship("Role", back_populates="users")

class SyncIntervalSettings(PostgresBase):
    """Table for storing data sync time-based settings"""
    __tablename__ = 'sync_interval_settings'
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    sync_type = Column(String(50), unique=True, nullable=False)  # 'raw_data', 'kpi', 'process_orders'
    sync_time = Column(String(5), nullable=False, default='09:00')  # Sync time in HH:MM format (24-hour)
    sync_interval_minutes = Column(Integer, nullable=True)  # Interval in minutes (e.g., 15, 30, 60)
    sync_date = Column(String(10), nullable=True)  # Sync date in YYYY-MM-DD format (optional, for one-time syncs)
    is_enabled = Column(Boolean, default=True)
    last_sync = Column(DateTime(timezone=True), nullable=True)
    next_sync = Column(DateTime(timezone=True), nullable=True)
    created_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))
    updated_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), onupdate=lambda: datetime.now(timezone.utc))
    created_by = Column(Integer, ForeignKey('users.id'), nullable=True)
    updated_by = Column(Integer, ForeignKey('users.id'), nullable=True)
    
    # Relationships
    creator = relationship("User", foreign_keys=[created_by])
    updater = relationship("User", foreign_keys=[updated_by])

class SystemLog(PostgresBase):
    """Table for storing system logs and sync activities"""
    __tablename__ = 'system_logs'
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    timestamp = Column(DateTime, default=datetime.utcnow)
    source = Column(String(100), nullable=True)  # sync_scheduler, auth_service, etc.
    action = Column(String(100), nullable=True)  # update_sync_interval, save_sync_interval, etc.
    status = Column(String(50), nullable=True)  # success, error, etc.
    details = Column(Text, nullable=True)  # JSON string with additional details
    log_metadata = Column(Text, nullable=True)  # JSON metadata
    operator = Column(String(100), nullable=True)
    duration_ms = Column(Integer, nullable=True)
    error_code = Column(String(100), nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    shift = Column(String(50), nullable=True)
    level = Column(String(20), nullable=True)  # INFO, WARNING, ERROR, DEBUG
    message = Column(Text, nullable=True)
    category = Column(String(50), nullable=True)  # sync, auth, system, etc.

class SyncStatus(PostgresBase):
    """Table for storing detailed sync status and results"""
    __tablename__ = 'sync_status'
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    sync_type = Column(String(50), nullable=False)  # raw_data, kpi, process_orders
    status = Column(String(20), nullable=False)  # running, success, error, failed
    start_time = Column(DateTime, nullable=False)
    end_time = Column(DateTime, nullable=True)
    duration_ms = Column(Integer, nullable=True)
    records_processed = Column(Integer, nullable=True)
    records_successful = Column(Integer, nullable=True)
    records_failed = Column(Integer, nullable=True)
    error_message = Column(Text, nullable=True)
    error_details = Column(Text, nullable=True)  # JSON string with detailed error info
    sync_result = Column(Text, nullable=True)  # JSON string with sync results
    triggered_by = Column(String(50), nullable=True)  # manual, scheduled, api
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))
    updated_at = Column(DateTime, default=lambda: datetime.now(timezone.utc), onupdate=lambda: datetime.now(timezone.utc))

# Permission constants
PERMISSIONS = {
    'admin': {
        'view_sync_interval': True,
        'change_sync_interval': True,
        'view_all_data': True,
        'manage_users': True,
        'system_admin': True,
        'order_access_milling': True,
        'order_access_packing': True
    },
    'manager': {
        'view_sync_interval': True,
        'change_sync_interval': True,
        'view_all_data': True,
        'manage_users': False,
        'system_admin': False,
        'order_access_milling': True,
        'order_access_packing': True
    },
    'operator': {
        'view_sync_interval': True,
        'change_sync_interval': False,
        'view_all_data': False,
        'manage_users': False,
        'system_admin': False,
        'order_access_milling': True,
        'order_access_packing': True
    },
    'milling_operator': {
        'view_sync_interval': True,
        'change_sync_interval': False,
        'view_all_data': False,
        'manage_users': False,
        'system_admin': False,
        'order_access_milling': True,
        'order_access_packing': False
    },
    'packing_operator': {
        'view_sync_interval': True,
        'change_sync_interval': False,
        'view_all_data': False,
        'manage_users': False,
        'system_admin': False,
        'order_access_milling': False,
        'order_access_packing': True
    },
    'guest': {
        'view_sync_interval': False,
        'change_sync_interval': False,
        'view_all_data': False,
        'manage_users': False,
        'system_admin': False,
        'order_access_milling': False,
        'order_access_packing': False
    }
}
