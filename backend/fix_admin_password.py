# fix_admin_password.py
"""
Script to fix the admin user password hash
"""

from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker
from models.user_roles import User
import bcrypt
import logging

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def fix_admin_password():
    """Fix the admin user password hash"""
    try:
        # Use PostgreSQL engine
        postgres_engine = create_engine("postgresql+psycopg2://postgres:Hercules2@localhost:5432/sap")
        PostgresSessionLocal = sessionmaker(bind=postgres_engine, autocommit=False, autoflush=False)
        
        with PostgresSessionLocal() as db:
            # Get the admin user
            admin_user = db.query(User).filter(User.username == 'admin').first()
            
            if not admin_user:
                logger.error("❌ Admin user not found!")
                return
            
            # Generate correct password hash for 'admin123'
            password = 'admin123'
            salt = bcrypt.gensalt()
            hashed = bcrypt.hashpw(password.encode('utf-8'), salt)
            password_hash = hashed.decode('utf-8')
            
            logger.info(f"🔐 Updating admin password hash...")
            logger.info(f"📝 New hash: {password_hash}")
            
            # Update the password hash
            admin_user.password_hash = password_hash
            db.commit()
            
            logger.info("✅ Admin password updated successfully!")
            
            # Test the password
            test_result = bcrypt.checkpw(password.encode('utf-8'), admin_user.password_hash.encode('utf-8'))
            logger.info(f"🧪 Password test result: {test_result}")
            
    except Exception as e:
        logger.error(f"❌ Error fixing admin password: {e}")
        raise

if __name__ == "__main__":
    fix_admin_password()
