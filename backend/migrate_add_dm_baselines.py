"""
Migration script to add DM baseline columns and baseline_fixed_flags JSON column to process_orders table.
"""
import sys
import os
from sqlalchemy import text
from sqlalchemy.dialects import postgresql
from database import postgres_engine

def run_migration():
    print("🚀 Starting database migration: Adding DM baseline columns and baseline_fixed_flags...")

    try:
        with postgres_engine.connect() as conn:
            trans = conn.begin()
            try:
                # Check existing columns
                check_column_sql = text("""
                    SELECT column_name 
                    FROM information_schema.columns 
                    WHERE table_name = 'process_orders' 
                    AND column_name IN ('baseline_dm101', 'baseline_dm102', 'baseline_dm201', 'baseline_dm202', 'baseline_dm203', 'baseline_fixed_flags')
                """)
                existing_columns = {row[0] for row in conn.execute(check_column_sql).fetchall()}
                
                columns_to_add = [
                    ("baseline_dm101", "FLOAT DEFAULT 0.0"),
                    ("baseline_dm102", "FLOAT DEFAULT 0.0"),
                    ("baseline_dm201", "FLOAT DEFAULT 0.0"),
                    ("baseline_dm202", "FLOAT DEFAULT 0.0"),
                    ("baseline_dm203", "FLOAT DEFAULT 0.0"),
                    ("baseline_fixed_flags", "JSONB DEFAULT '{}'::jsonb"),
                ]
                
                added_count = 0
                for col_name, col_type in columns_to_add:
                    if col_name not in existing_columns:
                        alter_sql = text(f"ALTER TABLE process_orders ADD COLUMN {col_name} {col_type}")
                        conn.execute(alter_sql)
                        print(f"  ✅ Added column '{col_name}' ({col_type})")
                        added_count += 1
                    else:
                        print(f"  ⚠️  Column '{col_name}' already exists - skipping")
                
                trans.commit()
                print(f"\n✅ Migration completed successfully! Added {added_count} columns.")

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
    script_dir = os.path.dirname(__file__)
    if script_dir:
        os.chdir(script_dir)
    
    sys.path.insert(0, os.path.abspath(os.path.join(script_dir, '..')))
    
    run_migration()

