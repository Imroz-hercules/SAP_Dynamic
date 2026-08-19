# services/auth_service.py
"""
Authentication and authorization service for role-based access control
"""

import jwt
import bcrypt
from datetime import datetime, timedelta
from functools import wraps
from flask import request, jsonify, current_app
from sqlalchemy.orm import sessionmaker
from database import postgres_engine
from models.user_roles import User, Role, UserRole, PERMISSIONS
import json
import logging

logger = logging.getLogger(__name__)

# JWT Secret (in production, use environment variable)
JWT_SECRET = "hercules_sfms_secret_key_2024"
JWT_ALGORITHM = "HS256"
JWT_EXPIRATION_HOURS = 24

# Database session
PostgresSessionLocal = sessionmaker(bind=postgres_engine, autocommit=False, autoflush=False)

class AuthService:
    """Authentication and authorization service"""
    
    @staticmethod
    def hash_password(password: str) -> str:
        """Hash a password using bcrypt"""
        salt = bcrypt.gensalt()
        hashed = bcrypt.hashpw(password.encode('utf-8'), salt)
        return hashed.decode('utf-8')
    
    @staticmethod
    def verify_password(password: str, hashed: str) -> bool:
        """Verify a password against its hash"""
        return bcrypt.checkpw(password.encode('utf-8'), hashed.encode('utf-8'))
    
    @staticmethod
    def generate_token(user_id: int, username: str, roles: list) -> str:
        """Generate JWT token for user"""
        payload = {
            'user_id': user_id,
            'username': username,
            'roles': roles,
            'exp': datetime.utcnow() + timedelta(hours=JWT_EXPIRATION_HOURS),
            'iat': datetime.utcnow()
        }
        return jwt.encode(payload, JWT_SECRET, algorithm=JWT_ALGORITHM)
    
    @staticmethod
    def verify_token(token: str) -> dict:
        """Verify and decode JWT token"""
        try:
            payload = jwt.decode(token, JWT_SECRET, algorithms=[JWT_ALGORITHM])
            return payload
        except jwt.ExpiredSignatureError:
            raise Exception("Token has expired")
        except jwt.InvalidTokenError:
            raise Exception("Invalid token")
    
    @staticmethod
    def authenticate_user(username: str, password: str) -> dict:
        """Authenticate user and return user info with roles"""
        with PostgresSessionLocal() as db:
            user = db.query(User).filter(
                User.username == username,
                User.is_active == True
            ).first()
            
            if not user:
                raise Exception("User not found or inactive")
            
            if not AuthService.verify_password(password, user.password_hash):
                raise Exception("Invalid password")
            
            # Get user roles
            user_roles = db.query(Role).join(UserRole).filter(
                UserRole.user_id == user.id
            ).all()
            
            roles = [role.name for role in user_roles]
            
            return {
                'user_id': user.id,
                'username': user.username,
                'email': user.email,
                'full_name': user.full_name,
                'roles': roles,
                'permissions': AuthService.get_user_permissions(roles)
            }
    
    @staticmethod
    def get_user_permissions(roles: list) -> dict:
        """Get combined permissions for user roles"""
        permissions = {}
        
        # Start with guest permissions (most restrictive)
        permissions.update(PERMISSIONS.get('guest', {}))
        
        # Apply role permissions (higher roles override lower ones)
        for role in roles:
            role_permissions = PERMISSIONS.get(role, {})
            for permission, value in role_permissions.items():
                if value:  # Only set True permissions, don't override with False
                    permissions[permission] = value
        
        return permissions
    
    @staticmethod
    def get_current_user() -> dict:
        """Get current user from JWT token in request"""
        auth_header = request.headers.get('Authorization')
        if not auth_header:
            raise Exception("No authorization header")
        
        try:
            token = auth_header.split(' ')[1]  # Bearer <token>
            payload = AuthService.verify_token(token)
            return payload
        except IndexError:
            raise Exception("Invalid authorization header format")
        except Exception as e:
            raise Exception(f"Authentication failed: {str(e)}")

def require_auth(f):
    """Decorator to require authentication"""
    @wraps(f)
    def decorated_function(*args, **kwargs):
        try:
            user = AuthService.get_current_user()
            request.current_user = user
            return f(*args, **kwargs)
        except Exception as e:
            return jsonify({'error': str(e)}), 401
    return decorated_function

def require_permission(permission: str):
    """Decorator to require specific permission"""
    def decorator(f):
        @wraps(f)
        def decorated_function(*args, **kwargs):
            try:
                user = AuthService.get_current_user()
                user_permissions = AuthService.get_user_permissions(user.get('roles', []))
                
                if not user_permissions.get(permission, False):
                    return jsonify({
                        'error': f'Insufficient permissions. Required: {permission}'
                    }), 403
                
                request.current_user = user
                return f(*args, **kwargs)
            except Exception as e:
                return jsonify({'error': str(e)}), 401
        return decorated_function
    return decorator

def require_role(required_roles: list):
    """Decorator to require specific roles"""
    def decorator(f):
        @wraps(f)
        def decorated_function(*args, **kwargs):
            try:
                user = AuthService.get_current_user()
                user_roles = user.get('roles', [])
                
                if not any(role in user_roles for role in required_roles):
                    return jsonify({
                        'error': f'Insufficient role. Required: {required_roles}'
                    }), 403
                
                request.current_user = user
                return f(*args, **kwargs)
            except Exception as e:
                return jsonify({'error': str(e)}), 401
        return decorated_function
    return decorator

def get_allowed_order_types(user_roles: list) -> list:
    """Derive allowed order types (MILLING / PACKING) from the user's roles.

    Returns a list such as ['MILLING'], ['PACKING'], or ['MILLING', 'PACKING'].
    An empty list means no order access at all.
    """
    permissions = AuthService.get_user_permissions(user_roles)
    allowed = []
    if permissions.get('order_access_milling'):
        allowed.append('MILLING')
    if permissions.get('order_access_packing'):
        allowed.append('PACKING')
    return allowed

def optional_auth(f):
    """Decorator that attaches current_user when a valid token is present,
    but does NOT reject the request when no token is provided.
    This allows endpoints to work for both authenticated and unauthenticated
    callers (e.g. the emulator) while still enforcing order-type filtering
    when a token IS present."""
    @wraps(f)
    def decorated_function(*args, **kwargs):
        try:
            user = AuthService.get_current_user()
            request.current_user = user
        except Exception:
            request.current_user = None
        return f(*args, **kwargs)
    return decorated_function

# Convenience decorators for common permissions
require_sync_interval_view = require_permission('view_sync_interval')
require_sync_interval_change = require_permission('change_sync_interval')
require_admin = require_role(['admin'])
require_manager_or_admin = require_role(['admin', 'manager'])
