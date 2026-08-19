"""
Migration script to add last_scada_values JSON column to process_orders table.
This column stores the last SCADA reading per equipment tag for delta calculation.
"""
import sys
import os
from sqlalchemy import text, create_engine
from sqlalchemy.dialects import postgresql
from database import postgres_engine

def run_migration():
    print("🚀 Starting database migration: Adding last_scada_values JSON column...")

    try:
        with postgres_engine.connect() as conn:
            trans = conn.begin()
            try:
                # Check if column already exists
                check_column_sql = text("""
                    SELECT column_name 
                    FROM information_schema.columns 
                    WHERE table_name = 'process_orders' 
                    AND column_name = 'last_scada_values'
                """)
                result = conn.execute(check_column_sql).fetchone()
                
                if result:
                    print("  ⚠️  Column 'last_scada_values' already exists - skipping")
                else:
                    # Add the JSON column
                    alter_sql = text("""
                        ALTER TABLE process_orders 
                        ADD COLUMN last_scada_values JSONB DEFAULT '{}'::jsonb
                    """)
                    conn.execute(alter_sql)
                    print("  ✅ Added column 'last_scada_values' (JSONB)")
                
                trans.commit()
                print(f"\n✅ Migration completed successfully!")

            except Exception as e:
                trans.rollback()
                print(f"❌ Migration failed: {e}")
                import traceback
                traceback.print_exc()
                sys.exit(1)

    except Exception as e:
        print(f"❌ Database connection failed: {e}")
        sys.exit(1)

if __name__ == "__main__":
    # Ensure the script is run from the backend directory
    script_dir = os.path.dirname(__file__)
    if script_dir:
        os.chdir(script_dir)
    
    # Add parent directory to path for module imports
    sys.path.insert(0, os.path.abspath(os.path.join(script_dir, '..')))
    
    run_migration()

