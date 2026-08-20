# routes/auth_routes.py
"""
Authentication routes for user login and role management
"""

from flask import Blueprint, request, jsonify
from sqlalchemy.orm import sessionmaker
from database import postgres_engine
from models.user_roles import User, Role, UserRole
from services.auth_service import AuthService, require_auth, require_admin
from datetime import datetime
import logging

logger = logging.getLogger(__name__)

# Database session
PostgresSessionLocal = sessionmaker(bind=postgres_engine, autocommit=False, autoflush=False)

auth_bp = Blueprint("auth", __name__, url_prefix="/api/auth")

@auth_bp.route("/login", methods=["POST"])
def login():
    """User login endpoint"""
    try:
        data = request.get_json()
        username = data.get('username')
        password = data.get('password')

        if not username or not password:
            return jsonify({'error': 'Username and password are required'}), 400
        
        # Authenticate user
        user_info = AuthService.authenticate_user(username, password)
        
        # Generate token
        token = AuthService.generate_token(
            user_info['user_id'],
            user_info['username'],
            user_info['roles']
        )
        
        return jsonify({
            'success': True,
            'token': token,
            'user': {
                'id': user_info['user_id'],
                'username': user_info['username'],
                'email': user_info['email'],
                'full_name': user_info['full_name'],
                'roles': user_info['roles'],
                'permissions': user_info['permissions']
            }
        })
        
    except Exception as e:
        logger.error(f"Login failed: {str(e)}")
        return jsonify({'error': str(e)}), 401

@auth_bp.route("/me", methods=["GET"])
@require_auth
def get_current_user():
    """Get current user information"""
    try:
        user = request.current_user
        return jsonify({
            'success': True,
            'user': {
                'id': user['user_id'],
                'username': user['username'],
                'roles': user['roles'],
                'permissions': AuthService.get_user_permissions(user['roles'])
            }
        })
    except Exception as e:
        return jsonify({'error': str(e)}), 401

@auth_bp.route("/setup-admin", methods=["POST"])
def setup_initial_admin():
    """Create the first admin user (no authentication required, only works if no admin exists)"""
    try:
        with PostgresSessionLocal() as db:
            # Check if any admin users already exist
            admin_role = db.query(Role).filter(Role.name == 'admin').first()
            if admin_role:
                # Explicitly specify the join condition to avoid ambiguity
                admin_users = db.query(User).join(
                    UserRole, User.id == UserRole.user_id
                ).filter(
                    UserRole.role_id == admin_role.id
                ).count()
                
                if admin_users > 0:
                    return jsonify({
                        'error': 'Admin user already exists. Please use /api/auth/users endpoint with admin authentication.'
                    }), 403
            
            # Get request data
            data = request.get_json()
            username = data.get('username')
            password = data.get('password')
            email = data.get('email')
            full_name = data.get('full_name', 'System Administrator')
            
            if not username or not password or not email:
                return jsonify({'error': 'Username, password, and email are required'}), 400
            
            # Check if user already exists
            existing_user = db.query(User).filter(User.username == username).first()
            if existing_user:
                return jsonify({'error': 'Username already exists'}), 400
            
            existing_email = db.query(User).filter(User.email == email).first()
            if existing_email:
                return jsonify({'error': 'Email already exists'}), 400
            
            # Ensure admin role exists
            if not admin_role:
                # Create admin role if it doesn't exist
                from models.user_roles import PERMISSIONS
                import json
                admin_role = Role(
                    name='admin',
                    description='System Administrator - Full access to all features',
                    permissions=json.dumps(PERMISSIONS.get('admin', {}))
                )
                db.add(admin_role)
                db.flush()
            
            # Hash password
            password_hash = AuthService.hash_password(password)
            
            # Create user
            new_user = User(
                username=username,
                email=email,
                password_hash=password_hash,
                full_name=full_name,
                is_active=True
            )
            db.add(new_user)
            db.flush()  # Get the user ID
            
            # Assign admin role
            user_role = UserRole(user_id=new_user.id, role_id=admin_role.id)
            db.add(user_role)
            
            db.commit()
            
            return jsonify({
                'success': True,
                'message': 'Initial admin user created successfully',
                'user': {
                    'id': new_user.id,
                    'username': new_user.username,
                    'email': new_user.email,
                    'full_name': new_user.full_name,
                    'roles': ['admin'],
                    'is_active': new_user.is_active
                }
            }), 201
                
    except Exception as e:
        logger.error(f"Failed to setup initial admin: {str(e)}")
        return jsonify({'error': str(e)}), 500

@auth_bp.route("/users", methods=["GET", "POST"])
@require_admin
def manage_users():
    """List all users (GET) or create new user (POST) - admin only"""
    if request.method == "GET":
        try:
            with PostgresSessionLocal() as db:
                users = db.query(User).all()
                
                user_list = []
                for user in users:
                    user_roles = [ur.role.name for ur in user.roles]
                    user_list.append({
                        'id': user.id,
                        'username': user.username,
                        'email': user.email,
                        'full_name': user.full_name,
                        'is_active': user.is_active,
                        'roles': user_roles,
                        'created_at': user.created_at.isoformat() if user.created_at else None
                    })
                
                return jsonify({
                    'success': True,
                    'users': user_list
                })
                
        except Exception as e:
            logger.error(f"Failed to list users: {str(e)}")
            return jsonify({'error': str(e)}), 500
    
    elif request.method == "POST":
        """Create a new user (admin only)"""
        try:
            data = request.get_json()
            username = data.get('username')
            password = data.get('password')
            email = data.get('email')
            full_name = data.get('full_name', '')
            roles = data.get('roles', [])  # List of role names like ['admin', 'manager']
            
            if not username or not password or not email:
                return jsonify({'error': 'Username, password, and email are required'}), 400
            
            with PostgresSessionLocal() as db:
                # Check if user already exists
                existing_user = db.query(User).filter(User.username == username).first()
                if existing_user:
                    return jsonify({'error': 'Username already exists'}), 400
                
                existing_email = db.query(User).filter(User.email == email).first()
                if existing_email:
                    return jsonify({'error': 'Email already exists'}), 400
                
                # Hash password
                password_hash = AuthService.hash_password(password)
                
                # Create user
                new_user = User(
                    username=username,
                    email=email,
                    password_hash=password_hash,
                    full_name=full_name,
                    is_active=True
                )
                db.add(new_user)
                db.flush()  # Get the user ID
                
                # Assign roles
                if roles:
                    for role_name in roles:
                        role = db.query(Role).filter(Role.name == role_name.lower()).first()
                        if role:
                            user_role = UserRole(user_id=new_user.id, role_id=role.id)
                            db.add(user_role)
                        else:
                            logger.warning(f"Role '{role_name}' not found, skipping")
                
                db.commit()
                
                # Get user roles for response
                user_roles = [ur.role.name for ur in new_user.roles]
                
                return jsonify({
                    'success': True,
                    'message': 'User created successfully',
                    'user': {
                        'id': new_user.id,
                        'username': new_user.username,
                        'email': new_user.email,
                        'full_name': new_user.full_name,
                        'roles': user_roles,
                        'is_active': new_user.is_active
                    }
                }), 201
                
        except Exception as e:
            logger.error(f"Failed to create user: {str(e)}")
            return jsonify({'error': str(e)}), 500

@auth_bp.route("/roles", methods=["GET"])
@require_auth
def list_roles():
    """List all available roles"""
    try:
        with PostgresSessionLocal() as db:
            roles = db.query(Role).all()
            
            role_list = []
            for role in roles:
                role_list.append({
                    'id': role.id,
                    'name': role.name,
                    'description': role.description,
                    'permissions': role.permissions
                })
            
            return jsonify({
                'success': True,
                'roles': role_list
            })
            
    except Exception as e:
        logger.error(f"Failed to list roles: {str(e)}")
        return jsonify({'error': str(e)}), 500

@auth_bp.route("/users/<int:user_id>/roles", methods=["PUT"])
@require_admin
def update_user_roles(user_id):
    """Update user roles (admin only)"""
    try:
        data = request.get_json()
        role_names = data.get('roles', [])
        
        with PostgresSessionLocal() as db:
            user = db.query(User).filter(User.id == user_id).first()
            if not user:
                return jsonify({'error': 'User not found'}), 404
            
            # Remove existing roles
            db.query(UserRole).filter(UserRole.user_id == user_id).delete()
            
            # Add new roles
            for role_name in role_names:
                role = db.query(Role).filter(Role.name == role_name).first()
                if role:
                    user_role = UserRole(user_id=user_id, role_id=role.id)
                    db.add(user_role)
            
            db.commit()
            
            # Get updated user info
            user_roles = [ur.role.name for ur in user.roles]
            
            return jsonify({
                'success': True,
                'message': 'User roles updated successfully',
                'user': {
                    'id': user.id,
                    'username': user.username,
                    'roles': user_roles
                }
            })
            
    except Exception as e:
        logger.error(f"Failed to update user roles: {str(e)}")
        return jsonify({'error': str(e)}), 500

@auth_bp.route("/users/<int:user_id>", methods=["DELETE"])
@require_admin
def delete_user(user_id):
    """Delete a user (admin only)"""
    try:
        # Get current user from token
        current_user = request.current_user
        
        # Prevent self-deletion
        if current_user['user_id'] == user_id:
            return jsonify({'error': 'Cannot delete your own account'}), 400
        
        with PostgresSessionLocal() as db:
            user = db.query(User).filter(User.id == user_id).first()
            if not user:
                return jsonify({'error': 'User not found'}), 404
            
            username = user.username
            
            # Delete user roles first
            db.query(UserRole).filter(UserRole.user_id == user_id).delete()
            
            # Delete user
            db.delete(user)
            db.commit()
            
            return jsonify({
                'success': True,
                'message': f'User {username} deleted successfully'
            })
            
    except Exception as e:
        logger.error(f"Failed to delete user: {str(e)}")
        return jsonify({'error': str(e)}), 500