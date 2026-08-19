# create_user_roles_tables.py
"""
Script to create user roles and sync interval settings tables in PostgreSQL database.
Run this script to set up the role-based access control system.
"""

from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker
from models.user_roles import User, Role, UserRole, SyncIntervalSettings, PERMISSIONS, PostgresBase
import logging
import json
from datetime import datetime, timedelta

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def create_tables():
    """Create the user roles and sync interval tables in PostgreSQL"""
    try:
        # Use PostgreSQL engine
        postgres_engine = create_engine("postgresql+psycopg2://postgres:Hercules@localhost:5432/sap")
        
        # Create all tables
        PostgresBase.metadata.create_all(bind=postgres_engine)
        
        logger.info("✅ User roles and sync interval tables created successfully!")
        
        # Verify tables were created
        with postgres_engine.connect() as connection:
            result = connection.execute(text("""
                SELECT table_name 
                FROM information_schema.tables 
                WHERE table_schema = 'public' 
                AND table_name IN ('users', 'roles', 'user_roles', 'sync_interval_settings')
                ORDER BY table_name
            """))
            
            table_names = [row[0] for row in result]
            logger.info(f"Created tables: {table_names}")
        
        return postgres_engine
        
    except Exception as e:
        logger.error(f"❌ Error creating tables: {e}")
        raise

def seed_initial_data():
    """Seed initial roles and sync interval settings"""
    try:
        postgres_engine = create_engine("postgresql+psycopg2://postgres:Hercules@localhost:5432/sap")
        PostgresSessionLocal = sessionmaker(bind=postgres_engine, autocommit=False, autoflush=False)
        
        with PostgresSessionLocal() as db:
            # Create roles
            roles_data = [
                {
                    'name': 'admin',
                    'description': 'System Administrator - Full access to all features',
                    'permissions': json.dumps(PERMISSIONS['admin'])
                },
                {
                    'name': 'manager',
                    'description': 'Manager - Can view and modify sync settings',
                    'permissions': json.dumps(PERMISSIONS['manager'])
                },
                {
                    'name': 'operator',
                    'description': 'Operator - Can view and operate systems',
                    'permissions': json.dumps(PERMISSIONS['operator'])
                },
                {
                    'name': 'milling_operator',
                    'description': 'Milling Operator - Access to milling orders only',
                    'permissions': json.dumps(PERMISSIONS['milling_operator'])
                },
                {
                    'name': 'packing_operator',
                    'description': 'Packing Operator - Access to packing orders only',
                    'permissions': json.dumps(PERMISSIONS['packing_operator'])
                },
                {
                    'name': 'guest',
                    'description': 'Guest - Limited access',
                    'permissions': json.dumps(PERMISSIONS['guest'])
                }
            ]
            
            for role_data in roles_data:
                existing_role = db.query(Role).filter(Role.name == role_data['name']).first()
                if not existing_role:
                    role = Role(**role_data)
                    db.add(role)
                    logger.info(f"✅ Created role: {role_data['name']}")
                else:
                    logger.info(f"⚠️ Role already exists: {role_data['name']}")
            
            # Create default admin user (password: admin123)
            admin_user_data = {
                'username': 'admin',
                'email': 'admin@hercules.com',
                'password_hash': '$2b$12$LQv3c1yqBWVHxkd0LHAkCOYz6TtxMQJqhN8/LewdBPj4J/8.8.8.8',  # admin123
                'full_name': 'System Administrator',
                'is_active': True
            }
            
            existing_admin = db.query(User).filter(User.username == 'admin').first()
            if not existing_admin:
                admin_user = User(**admin_user_data)
                db.add(admin_user)
                db.flush()  # Get the ID
                
                # Assign admin role
                admin_role = db.query(Role).filter(Role.name == 'admin').first()
                if admin_role:
                    user_role = UserRole(user_id=admin_user.id, role_id=admin_role.id)
                    db.add(user_role)
                    logger.info("✅ Created admin user with admin role")
            else:
                logger.info("⚠️ Admin user already exists")
            
            # Create sync interval settings
            sync_settings_data = [
                {
                    'sync_type': 'raw_data',
                    'interval_minutes': 60,  # 1 hour
                    'is_enabled': True,
                    'description': 'Raw data sync from ASMReporting_5 to SAP'
                },
                {
                    'sync_type': 'kpi',
                    'interval_minutes': 30,  # 30 minutes
                    'is_enabled': True,
                    'description': 'KPI data sync to SAP'
                },
                {
                    'sync_type': 'process_orders',
                    'interval_minutes': 180,  # 3 hours
                    'is_enabled': True,
                    'description': 'Process orders sync from SAP'
                }
            ]
            
            for setting_data in sync_settings_data:
                existing_setting = db.query(SyncIntervalSettings).filter(
                    SyncIntervalSettings.sync_type == setting_data['sync_type']
                ).first()
                
                if not existing_setting:
                    # Get admin user ID for created_by
                    admin_user = db.query(User).filter(User.username == 'admin').first()
                    created_by = admin_user.id if admin_user else None
                    
                    sync_setting = SyncIntervalSettings(
                        sync_type=setting_data['sync_type'],
                        interval_minutes=setting_data['interval_minutes'],
                        is_enabled=setting_data['is_enabled'],
                        created_by=created_by,
                        updated_by=created_by
                    )
                    db.add(sync_setting)
                    logger.info(f"✅ Created sync setting: {setting_data['sync_type']}")
                else:
                    logger.info(f"⚠️ Sync setting already exists: {setting_data['sync_type']}")
            
            db.commit()
            logger.info("✅ Initial data seeded successfully!")
            
    except Exception as e:
        logger.error(f"❌ Error seeding initial data: {e}")
        raise

def verify_setup():
    """Verify the setup by querying the created data"""
    try:
        postgres_engine = create_engine("postgresql+psycopg2://postgres:Hercules@localhost:5432/sap")
        PostgresSessionLocal = sessionmaker(bind=postgres_engine, autocommit=False, autoflush=False)
        
        with PostgresSessionLocal() as db:
            # Check roles
            roles = db.query(Role).all()
            logger.info(f"📋 Found {len(roles)} roles:")
            for role in roles:
                logger.info(f"  - {role.name}: {role.description}")
            
            # Check users
            users = db.query(User).all()
            logger.info(f"👥 Found {len(users)} users:")
            for user in users:
                user_roles = [ur.role.name for ur in user.roles]
                logger.info(f"  - {user.username} ({user.email}): {', '.join(user_roles)}")
            
            # Check sync settings
            sync_settings = db.query(SyncIntervalSettings).all()
            logger.info(f"⚙️ Found {len(sync_settings)} sync settings:")
            for setting in sync_settings:
                logger.info(f"  - {setting.sync_type}: {setting.interval_minutes} minutes (enabled: {setting.is_enabled})")
                
    except Exception as e:
        logger.error(f"❌ Error verifying setup: {e}")
        raise

if __name__ == "__main__":
    try:
        logger.info("🚀 Starting user roles and sync interval setup...")
        
        # Create tables
        create_tables()
        
        # Seed initial data
        seed_initial_data()
        
        # Verify setup
        verify_setup()
        
        logger.info("🎉 Setup completed successfully!")
        logger.info("📝 Default credentials:")
        logger.info("  Username: admin")
        logger.info("  Password: admin123")
        logger.info("  Role: admin (full access)")
        
    except Exception as e:
        logger.error(f"💥 Setup failed: {e}")
        raise
