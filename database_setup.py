#!/usr/bin/env python3
"""
Database Setup Script for Hercules KPI
This script creates the required database tables after installation.
"""

import sys
import os
import json
import pyodbc
import psycopg2
from sqlalchemy import create_engine, text
from sqlalchemy.exc import SQLAlchemyError

def create_mssql_connection(server, database, username, password, driver="ODBC Driver 17 for SQL Server"):
    """Create MSSQL connection string"""
    username = username.strip() if username else ""
    password = password.strip() if password else ""
    
    # If username/password are empty, use Windows Authentication
    if not username or not password:
        return f"mssql+pyodbc://{server}/{database}?driver={driver}&trusted_connection=yes"
    else:
        return f"mssql+pyodbc://{username}:{password}@{server}/{database}?driver={driver}"

def create_postgres_connection(host, port, database, username, password):
    """Create PostgreSQL connection string"""
    return f"postgresql://{username}:{password}@{host}:{port}/{database}"

def test_mssql_connection(connection_string):
    """Test MSSQL connection"""
    try:
        engine = create_engine(connection_string)
        with engine.connect() as conn:
            conn.execute(text("SELECT 1"))
        return True, "MSSQL connection successful"
    except Exception as e:
        return False, f"MSSQL connection failed: {str(e)}"

def test_postgres_connection(connection_string):
    """Test PostgreSQL connection"""
    try:
        engine = create_engine(connection_string)
        with engine.connect() as conn:
            conn.execute(text("SELECT 1"))
        return True, "PostgreSQL connection successful"
    except Exception as e:
        return False, f"PostgreSQL connection failed: {str(e)}"

def create_mssql_tables(connection_string):
    """Create MSSQL tables"""
    try:
        engine = create_engine(connection_string)
        
        # Add backend path to sys.path
        backend_path = os.path.join(os.path.dirname(__file__), 'backend')
        if backend_path not in sys.path:
            sys.path.append(backend_path)
        
        # Try to import models, but don't fail if they don't exist
        try:
            from models.kpi_model import Base as KpiBase
            KpiBase.metadata.create_all(engine)
            print("   ✅ KPI tables created")
        except ImportError as e:
            print(f"   ⚠️ KPI models not found: {e}")
        
        try:
            from models.material_model import Base as MaterialBase
            MaterialBase.metadata.create_all(engine)
            print("   ✅ Material tables created")
        except ImportError as e:
            print(f"   ⚠️ Material models not found: {e}")
        
        try:
            from models.order_validation import Base as OrderValidation
            OrderValidation.metadata.create_all(engine)
            print("   ✅ Order validation tables created")
        except ImportError as e:
            print(f"   ⚠️ Order validation models not found: {e}")
        
        try:
            from models.order_model import Base as OrderBase
            OrderBase.metadata.create_all(engine)
            print("   ✅ Order tables created")
        except ImportError as e:
            print(f"   ⚠️ Order models not found: {e}")
        
        try:
            from models.process_order import create_process_order_schema
            create_process_order_schema()
            print("   ✅ Process order schema created")
        except ImportError as e:
            print(f"   ⚠️ Process order models not found: {e}")
        
        return True, "MSSQL tables created successfully"
    except Exception as e:
        return False, f"Failed to create MSSQL tables: {str(e)}"

def create_postgres_tables(connection_string):
    """Create PostgreSQL tables"""
    try:
        engine = create_engine(connection_string)
        
        # Add backend path to sys.path
        backend_path = os.path.join(os.path.dirname(__file__), 'backend')
        if backend_path not in sys.path:
            sys.path.append(backend_path)
        
        # Try to import and create schemas, but don't fail if they don't exist
        try:
            from services.create_scada_table import create_scada_schema
            create_scada_schema()
            print("   ✅ SCADA schema created")
        except ImportError as e:
            print(f"   ⚠️ SCADA schema not found: {e}")
        
        try:
            from models.milling_kpi_snapshot import create_milling_kpi_schema
            create_milling_kpi_schema()
            print("   ✅ Milling KPI schema created")
        except ImportError as e:
            print(f"   ⚠️ Milling KPI schema not found: {e}")
        
        try:
            from models.packing_kpi_snapshot import create_packing_kpi_schema
            create_packing_kpi_schema()
            print("   ✅ Packing KPI schema created")
        except ImportError as e:
            print(f"   ⚠️ Packing KPI schema not found: {e}")
        
        try:
            from models.process_order_pg import create_process_order_pg_schema
            create_process_order_pg_schema()
            print("   ✅ Process order PG schema created")
        except ImportError as e:
            print(f"   ⚠️ Process order PG schema not found: {e}")
        
        try:
            from models.user_roles import PostgresBase
            PostgresBase.metadata.create_all(bind=engine)
            print("   ✅ User roles tables created")
        except ImportError as e:
            print(f"   ⚠️ User roles models not found: {e}")
        
        return True, "PostgreSQL tables created successfully"
    except Exception as e:
        return False, f"Failed to create PostgreSQL tables: {str(e)}"

def save_database_config(config):
    """Save database configuration to file"""
    config_file = os.path.join(os.path.dirname(__file__), 'backend', 'database_config.json')
    try:
        with open(config_file, 'w') as f:
            json.dump(config, f, indent=2)
        return True, "Database configuration saved successfully"
    except Exception as e:
        return False, f"Failed to save configuration: {str(e)}"

def main():
    """Main function to handle database setup"""
    if len(sys.argv) < 2:
        print("Usage: python database_setup.py <config_json>")
        sys.exit(1)
    
    try:
        config = json.loads(sys.argv[1])
        
        print("🔧 Setting up Hercules KPI Database...")
        print("=" * 50)
        
        overall_success = True
        
        # Test and setup MSSQL
        if config.get('mssql'):
            print("📊 Setting up MSSQL Database...")
            mssql_config = config['mssql']
            
            # Handle empty username/password for Windows Auth
            username = mssql_config.get('username', '').strip()
            password = mssql_config.get('password', '').strip()
            
            mssql_conn = create_mssql_connection(
                mssql_config['server'],
                mssql_config['database'],
                username,
                password
            )
            
            success, message = test_mssql_connection(mssql_conn)
            print(f"   Connection Test: {message}")
            
            if success:
                success, message = create_mssql_tables(mssql_conn)
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
            
            success, message = test_postgres_connection(pg_conn)
            print(f"   Connection Test: {message}")
            
            if success:
                success, message = create_postgres_tables(pg_conn)
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
            print("   The application may still work with existing tables.")
        
    except Exception as e:
        print(f"❌ Database setup failed: {str(e)}")
        import traceback
        traceback.print_exc()
        sys.exit(1)

if __name__ == "__main__":
    main()
