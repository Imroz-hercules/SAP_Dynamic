#!/usr/bin/env python3
"""
Simple Database Setup Script for Hercules KPI
This script creates basic database tables without complex model dependencies.
"""

import sys
import os
import json
from sqlalchemy import create_engine, text

def create_mssql_connection(server, database, username, password):
    """Create MSSQL connection string"""
    username = username.strip() if username else ""
    password = password.strip() if password else ""
    
    # If username/password are empty, use Windows Authentication
    if not username or not password:
        return f"mssql+pyodbc://{server}/{database}?driver=ODBC+Driver+17+for+SQL+Server&trusted_connection=yes"
    else:
        return f"mssql+pyodbc://{username}:{password}@{server}/{database}?driver=ODBC+Driver+17+for+SQL+Server"

def create_postgres_connection(host, port, database, username, password):
    """Create PostgreSQL connection string"""
    return f"postgresql://{username}:{password}@{host}:{port}/{database}"

def test_connection(connection_string, db_type):
    """Test database connection"""
    try:
        engine = create_engine(connection_string)
        with engine.connect() as conn:
            conn.execute(text("SELECT 1"))
        return True, f"{db_type} connection successful"
    except Exception as e:
        return False, f"{db_type} connection failed: {str(e)}"

def create_basic_tables(connection_string, db_type):
    """Create basic tables"""
    try:
        engine = create_engine(connection_string)
        
        if db_type == "MSSQL":
            # Create basic tables for MSSQL
            basic_tables = [
                """
                IF NOT EXISTS (SELECT * FROM sysobjects WHERE name='sync_interval_settings' AND xtype='U')
                CREATE TABLE sync_interval_settings (
                    id INT IDENTITY(1,1) PRIMARY KEY,
                    sync_type NVARCHAR(50) NOT NULL,
                    sync_time TIME,
                    sync_date DATE,
                    is_enabled BIT DEFAULT 1,
                    last_sync DATETIME,
                    next_sync DATETIME,
                    created_at DATETIME DEFAULT GETDATE()
                )
                """,
                """
                IF NOT EXISTS (SELECT * FROM sysobjects WHERE name='sync_status' AND xtype='U')
                CREATE TABLE sync_status (
                    id INT IDENTITY(1,1) PRIMARY KEY,
                    sync_type NVARCHAR(50) NOT NULL,
                    status NVARCHAR(20) NOT NULL,
                    message TEXT,
                    timestamp DATETIME DEFAULT GETDATE()
                )
                """
            ]
        else:  # PostgreSQL
            # Create basic tables for PostgreSQL
            basic_tables = [
                """
                CREATE TABLE IF NOT EXISTS sync_interval_settings (
                    id SERIAL PRIMARY KEY,
                    sync_type VARCHAR(50) NOT NULL,
                    sync_time TIME,
                    sync_date DATE,
                    is_enabled BOOLEAN DEFAULT TRUE,
                    last_sync TIMESTAMP,
                    next_sync TIMESTAMP,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
                """,
                """
                CREATE TABLE IF NOT EXISTS sync_status (
                    id SERIAL PRIMARY KEY,
                    sync_type VARCHAR(50) NOT NULL,
                    status VARCHAR(20) NOT NULL,
                    message TEXT,
                    timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
                """
            ]
        
        with engine.connect() as conn:
            for table_sql in basic_tables:
                conn.execute(text(table_sql))
            conn.commit()
        
        return True, f"{db_type} basic tables created successfully"
    except Exception as e:
        return False, f"Failed to create {db_type} basic tables: {str(e)}"

def save_database_config(config):
    """Save database configuration to file"""
    config_file = os.path.join(os.path.dirname(__file__), 'backend', 'database_config.json')
    try:
        os.makedirs(os.path.dirname(config_file), exist_ok=True)
        with open(config_file, 'w') as f:
            json.dump(config, f, indent=2)
        return True, "Database configuration saved successfully"
    except Exception as e:
        return False, f"Failed to save configuration: {str(e)}"

def main():
    """Main function to handle database setup"""
    if len(sys.argv) < 2:
        print("Usage: python database_setup_simple.py <config_json>")
        sys.exit(1)
    
    try:
        config = json.loads(sys.argv[1])
        
        print("🔧 Setting up Hercules KPI Database (Simple Mode)...")
        print("=" * 50)
        
        overall_success = True
        
        # Test and setup MSSQL
        if config.get('mssql'):
            print("📊 Setting up MSSQL Database...")
            mssql_config = config['mssql']
            
            username = mssql_config.get('username', '').strip()
            password = mssql_config.get('password', '').strip()
            
            mssql_conn = create_mssql_connection(
                mssql_config['server'],
                mssql_config['database'],
                username,
                password
            )
            
            success, message = test_connection(mssql_conn, "MSSQL")
            print(f"   Connection Test: {message}")
            
            if success:
                success, message = create_basic_tables(mssql_conn, "MSSQL")
                print(f"   Table Creation: {message}")
                if not success:
                    overall_success = False
            else:
                print(f"   ❌ MSSQL setup failed: {message}")
                overall_success = False
        
        # Test and setup PostgreSQL
        if config.get('postgresql'):
            print("🐘 Setting up PostgreSQL Database...")
            pg_config = config['postgresql']
            pg_conn = create_postgres_connection(
                pg_config['host'],
                pg_config['port'],
                pg_config['database'],
                pg_config['username'],
                pg_config['password']
            )
            
            success, message = test_connection(pg_conn, "PostgreSQL")
            print(f"   Connection Test: {message}")
            
            if success:
                success, message = create_basic_tables(pg_conn, "PostgreSQL")
                print(f"   Table Creation: {message}")
                if not success:
                    overall_success = False
            else:
                print(f"   ❌ PostgreSQL setup failed: {message}")
                overall_success = False
        
        # Save configuration
        success, message = save_database_config(config)
        print(f"💾 Configuration Save: {message}")
        if not success:
            overall_success = False
        
        print("=" * 50)
        if overall_success:
            print("✅ Database setup completed successfully!")
        else:
            print("⚠️ Database setup completed with some issues.")
        
    except Exception as e:
        print(f"❌ Database setup failed: {str(e)}")
        import traceback
        traceback.print_exc()
        sys.exit(1)

if __name__ == "__main__":
    main()
