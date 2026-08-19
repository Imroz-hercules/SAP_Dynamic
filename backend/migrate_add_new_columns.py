#!/usr/bin/env python3
"""
Database Migration Script: Add new columns to process_orders and orders tables
- PLANT (VARCHAR(50))
- CONFIRMED_QTY (NUMERIC(18,3) for orders, DOUBLE PRECISION for process_orders)
- MATERIAL_DESC (VARCHAR(200))

This script adds the new columns to both tables to match the frontend structure.
"""

import sys
import os
from sqlalchemy import text, create_engine
from database import postgres_engine

def run_migration():
    """Add new columns to both process_orders and orders tables."""
    
    print("🚀 Starting database migration: Adding new columns...")
    
    try:
        with postgres_engine.connect() as conn:
            # Start transaction
            trans = conn.begin()
            
            try:
                # 1. Add columns to process_orders table
                print("📝 Adding columns to process_orders table...")
                
                # Check if columns already exist
                check_columns_sql = """
                    SELECT column_name 
                    FROM information_schema.columns 
                    WHERE table_name = 'process_orders' 
                    AND column_name IN ('plant', 'confirmed_qty', 'material_desc')
                """
                existing_columns = [row[0] for row in conn.execute(text(check_columns_sql)).fetchall()]
                
                if 'plant' not in existing_columns:
                    conn.execute(text("ALTER TABLE process_orders ADD COLUMN plant VARCHAR(50)"))
                    print("  ✅ Added 'plant' column")
                else:
                    print("  ⚠️  'plant' column already exists")
                
                if 'confirmed_qty' not in existing_columns:
                    conn.execute(text("ALTER TABLE process_orders ADD COLUMN confirmed_qty DOUBLE PRECISION"))
                    print("  ✅ Added 'confirmed_qty' column")
                else:
                    print("  ⚠️  'confirmed_qty' column already exists")
                
                if 'material_desc' not in existing_columns:
                    conn.execute(text("ALTER TABLE process_orders ADD COLUMN material_desc VARCHAR(200)"))
                    print("  ✅ Added 'material_desc' column")
                else:
                    print("  ⚠️  'material_desc' column already exists")
                
                # 2. Add columns to orders table
                print("📝 Adding columns to orders table...")
                
                check_orders_columns_sql = """
                    SELECT column_name 
                    FROM information_schema.columns 
                    WHERE table_name = 'orders' 
                    AND column_name IN ('plant', 'confirmed_qty', 'material_desc')
                """
                existing_orders_columns = [row[0] for row in conn.execute(text(check_orders_columns_sql)).fetchall()]
                
                if 'plant' not in existing_orders_columns:
                    conn.execute(text("ALTER TABLE orders ADD COLUMN plant VARCHAR(50)"))
                    print("  ✅ Added 'plant' column to orders")
                else:
                    print("  ⚠️  'plant' column already exists in orders")
                
                if 'confirmed_qty' not in existing_orders_columns:
                    conn.execute(text("ALTER TABLE orders ADD COLUMN confirmed_qty NUMERIC(18,3)"))
                    print("  ✅ Added 'confirmed_qty' column to orders")
                else:
                    print("  ⚠️  'confirmed_qty' column already exists in orders")
                
                if 'material_desc' not in existing_orders_columns:
                    conn.execute(text("ALTER TABLE orders ADD COLUMN material_desc VARCHAR(200)"))
                    print("  ✅ Added 'material_desc' column to orders")
                else:
                    print("  ⚠️  'material_desc' column already exists in orders")
                
                # 3. Add indexes for better performance
                print("📊 Adding indexes for new columns...")
                
                try:
                    conn.execute(text("CREATE INDEX IF NOT EXISTS idx_process_orders_plant ON process_orders(plant)"))
                    print("  ✅ Added index on process_orders.plant")
                except Exception as e:
                    print(f"  ⚠️  Index on process_orders.plant may already exist: {e}")
                
                try:
                    conn.execute(text("CREATE INDEX IF NOT EXISTS idx_orders_plant ON orders(plant)"))
                    print("  ✅ Added index on orders.plant")
                except Exception as e:
                    print(f"  ⚠️  Index on orders.plant may already exist: {e}")
                
                # Commit transaction
                trans.commit()
                print("✅ Migration completed successfully!")
                
                # 4. Verify the changes
                print("🔍 Verifying table structures...")
                
                # Check process_orders structure
                process_orders_columns = conn.execute(text("""
                    SELECT column_name, data_type 
                    FROM information_schema.columns 
                    WHERE table_name = 'process_orders' 
                    ORDER BY ordinal_position
                """)).fetchall()
                
                print("📋 process_orders table structure:")
                for col_name, col_type in process_orders_columns:
                    print(f"  - {col_name}: {col_type}")
                
                # Check orders structure
                orders_columns = conn.execute(text("""
                    SELECT column_name, data_type 
                    FROM information_schema.columns 
                    WHERE table_name = 'orders' 
                    ORDER BY ordinal_position
                """)).fetchall()
                
                print("📋 orders table structure:")
                for col_name, col_type in orders_columns:
                    print(f"  - {col_name}: {col_type}")
                
            except Exception as e:
                trans.rollback()
                print(f"❌ Migration failed: {e}")
                raise
                
    except Exception as e:
        print(f"❌ Database connection failed: {e}")
        sys.exit(1)

if __name__ == "__main__":
    run_migration()
