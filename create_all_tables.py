"""
setup_demo_server_db.py

Creates the demo_server database and all required tables for the SAP demo server.

Usage:
  python setup_demo_server_db.py

Requirements:
  pip install psycopg2-binary
"""

import psycopg2
from psycopg2 import Error
from psycopg2.extensions import ISOLATION_LEVEL_AUTOCOMMIT

# -------------------------
# CONFIG: Edit if needed
# -------------------------
PG_HOST = "localhost"
PG_PORT = 5432
PG_USER = "postgres"
PG_PASS = "Hercules"
PG_DB_NAME = "demo_server"  # Database to create

def create_database():
    """Create the demo_server database if it doesn't exist"""
    connection = None
    cursor = None
    
    try:
        # Connect to default postgres database to create our database
        print("Connecting to PostgreSQL server...")
        connection = psycopg2.connect(
            host=PG_HOST,
            port=PG_PORT,
            user=PG_USER,
            password=PG_PASS,
            database="postgres"  # Connect to default database first
        )
        
        # Set isolation level for database creation
        connection.set_isolation_level(ISOLATION_LEVEL_AUTOCOMMIT)
        cursor = connection.cursor()
        
        # Check if database exists
        cursor.execute(
            "SELECT 1 FROM pg_database WHERE datname = %s",
            (PG_DB_NAME,)
        )
        exists = cursor.fetchone()
        
        if exists:
            print(f"✓ Database '{PG_DB_NAME}' already exists")
        else:
            # Create database
            print(f"Creating database '{PG_DB_NAME}'...")
            cursor.execute(f'CREATE DATABASE {PG_DB_NAME}')
            print(f"✓ Database '{PG_DB_NAME}' created successfully!")
        
        cursor.close()
        connection.close()
        return True
        
    except Error as e:
        print(f"✗ Error creating database: {e}")
        return False
    
    finally:
        if cursor:
            cursor.close()
        if connection:
            connection.close()

def create_tables():
    """Create all required tables in the demo_server database"""
    connection = None
    cursor = None
    
    try:
        # Connect to the demo_server database
        print(f"\nConnecting to '{PG_DB_NAME}' database...")
        connection = psycopg2.connect(
            host=PG_HOST,
            port=PG_PORT,
            user=PG_USER,
            password=PG_PASS,
            database=PG_DB_NAME
        )
        
        cursor = connection.cursor()
        
        # Create confirmations table
        print("\nCreating 'confirmations' table...")
        create_confirmations_table = """
        CREATE TABLE IF NOT EXISTS confirmations (
            id SERIAL PRIMARY KEY,
            po_number TEXT,
            material TEXT,
            confirmed_qty DOUBLE PRECISION,
            final_flag TEXT,
            payload JSONB,
            created_at TIMESTAMP DEFAULT NOW()
        );
        
        CREATE INDEX IF NOT EXISTS idx_confirmations_po_number ON confirmations(po_number);
        CREATE INDEX IF NOT EXISTS idx_confirmations_created_at ON confirmations(created_at DESC);
        """
        cursor.execute(create_confirmations_table)
        print("✓ 'confirmations' table created successfully!")
        
        # Create raw_data table
        print("\nCreating 'raw_data' table...")
        create_raw_data_table = """
        CREATE TABLE IF NOT EXISTS raw_data (
            id SERIAL PRIMARY KEY,
            payload JSONB,
            created_at TIMESTAMP DEFAULT NOW()
        );
        
        CREATE INDEX IF NOT EXISTS idx_raw_data_created_at ON raw_data(created_at DESC);
        """
        cursor.execute(create_raw_data_table)
        print("✓ 'raw_data' table created successfully!")
        
        # Create orders table
        print("\nCreating 'orders' table...")
        create_orders_table = """
        CREATE TABLE IF NOT EXISTS orders (
            id SERIAL PRIMARY KEY,
            payload JSONB,
            created_at TIMESTAMP DEFAULT NOW()
        );
        
        CREATE INDEX IF NOT EXISTS idx_orders_created_at ON orders(created_at DESC);
        """
        cursor.execute(create_orders_table)
        print("✓ 'orders' table created successfully!")
        
        # Commit all changes
        connection.commit()
        
        # Display table information
        print("\n" + "="*70)
        print("DATABASE SETUP COMPLETE!")
        print("="*70)
        
        # Get row counts
        cursor.execute("SELECT COUNT(*) FROM confirmations")
        conf_count = cursor.fetchone()[0]
        
        cursor.execute("SELECT COUNT(*) FROM raw_data")
        raw_count = cursor.fetchone()[0]
        
        cursor.execute("SELECT COUNT(*) FROM orders")
        orders_count = cursor.fetchone()[0]
        
        print(f"\nDatabase: {PG_DB_NAME}")
        print(f"Host: {PG_HOST}:{PG_PORT}")
        print("\nTables created:")
        print(f"  1. confirmations      (rows: {conf_count})")
        print(f"  2. raw_data          (rows: {raw_count})")
        print(f"  3. orders            (rows: {orders_count})")
        
        print("\nTable Schemas:")
        print("\n1. confirmations:")
        print("   - id (SERIAL PRIMARY KEY)")
        print("   - po_number (TEXT)")
        print("   - material (TEXT)")
        print("   - confirmed_qty (DOUBLE PRECISION)")
        print("   - final_flag (TEXT)")
        print("   - payload (JSONB)")
        print("   - created_at (TIMESTAMP)")
        
        print("\n2. raw_data:")
        print("   - id (SERIAL PRIMARY KEY)")
        print("   - payload (JSONB)")
        print("   - created_at (TIMESTAMP)")
        
        print("\n3. orders:")
        print("   - id (SERIAL PRIMARY KEY)")
        print("   - payload (JSONB)")
        print("   - created_at (TIMESTAMP)")
        
        print("\n" + "="*70)
        print("You can now run: python demo_sap_server_gui_postgres.py")
        print("="*70 + "\n")
        
        cursor.close()
        connection.close()
        return True
        
    except Error as e:
        print(f"✗ Error creating tables: {e}")
        if connection:
            connection.rollback()
        return False
    
    finally:
        if cursor:
            cursor.close()
        if connection:
            connection.close()

def verify_setup():
    """Verify the database and tables are set up correctly"""
    connection = None
    cursor = None
    
    try:
        connection = psycopg2.connect(
            host=PG_HOST,
            port=PG_PORT,
            user=PG_USER,
            password=PG_PASS,
            database=PG_DB_NAME
        )
        
        cursor = connection.cursor()
        
        # Check all tables exist
        cursor.execute("""
            SELECT table_name 
            FROM information_schema.tables 
            WHERE table_schema = 'public' 
            AND table_type = 'BASE TABLE'
            ORDER BY table_name
        """)
        
        tables = [row[0] for row in cursor.fetchall()]
        expected_tables = ['confirmations', 'orders', 'raw_data']
        
        missing_tables = [t for t in expected_tables if t not in tables]
        
        if missing_tables:
            print(f"\n⚠ Warning: Missing tables: {missing_tables}")
            return False
        else:
            print(f"\n✓ Verification successful: All tables exist!")
            return True
        
    except Error as e:
        print(f"✗ Verification error: {e}")
        return False
    
    finally:
        if cursor:
            cursor.close()
        if connection:
            connection.close()

def main():
    print("="*70)
    print("DEMO SAP SERVER - DATABASE SETUP")
    print("="*70)
    print(f"\nConfiguration:")
    print(f"  Host: {PG_HOST}")
    print(f"  Port: {PG_PORT}")
    print(f"  User: {PG_USER}")
    print(f"  Database: {PG_DB_NAME}")
    print("\n" + "="*70 + "\n")
    
    # Step 1: Create database
    if not create_database():
        print("\n✗ Database creation failed. Exiting.")
        return
    
    # Step 2: Create tables
    if not create_tables():
        print("\n✗ Table creation failed. Exiting.")
        return
    
    # Step 3: Verify setup
    verify_setup()

if __name__ == "__main__":
    main()

