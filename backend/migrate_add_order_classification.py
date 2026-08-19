#!/usr/bin/env python3
"""
Migration script to add order classification columns to process_orders table
"""

import sys
import os
from sqlalchemy import text

# Add backend to path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from database import postgres_engine

def migrate_add_order_classification():
    """Add order_type, packing_line, and bag_size columns to process_orders table"""
    
    migration_sql = """
    -- Add order classification columns if they don't exist
    DO $$ 
    BEGIN
        -- Add order_type column
        IF NOT EXISTS (SELECT 1 FROM information_schema.columns 
                      WHERE table_name = 'process_orders' AND column_name = 'order_type') THEN
            ALTER TABLE process_orders ADD COLUMN order_type VARCHAR(50);
        END IF;
        
        -- Add packing_line column
        IF NOT EXISTS (SELECT 1 FROM information_schema.columns 
                      WHERE table_name = 'process_orders' AND column_name = 'packing_line') THEN
            ALTER TABLE process_orders ADD COLUMN packing_line VARCHAR(10);
        END IF;
        
        -- Add bag_size column
        IF NOT EXISTS (SELECT 1 FROM information_schema.columns 
                      WHERE table_name = 'process_orders' AND column_name = 'bag_size') THEN
            ALTER TABLE process_orders ADD COLUMN bag_size VARCHAR(10);
        END IF;
        
        -- Add index for order_type if it doesn't exist
        IF NOT EXISTS (SELECT 1 FROM pg_indexes 
                      WHERE tablename = 'process_orders' AND indexname = 'idx_process_order_type') THEN
            CREATE INDEX idx_process_order_type ON process_orders(order_type);
        END IF;
    END $$;
    """
    
    try:
        with postgres_engine.connect() as conn:
            conn.execute(text(migration_sql))
            conn.commit()
            print("✅ Successfully added order classification columns to process_orders table")
            return True
    except Exception as e:
        print(f"❌ Migration failed: {e}")
        return False

if __name__ == "__main__":
    print("🔄 Running migration to add order classification columns...")
    success = migrate_add_order_classification()
    if success:
        print("🎉 Migration completed successfully!")
    else:
        print("💥 Migration failed!")
        sys.exit(1)
