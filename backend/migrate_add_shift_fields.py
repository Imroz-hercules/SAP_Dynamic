#!/usr/bin/env python3
"""
Database Migration Script: Add shift-based tracking columns to process_orders table

This script adds all the new shift-based fields to the process_orders table
to match the ProcessOrderPG model definition.
"""

import sys
import os
from sqlalchemy import text
from database import postgres_engine

def run_migration():
    """Add shift-based tracking columns to process_orders table."""
    
    print("🚀 Starting database migration: Adding shift-based tracking columns...")
    
    # List of all new columns to add
    new_columns = [
        # SHIFT IDENTIFICATION
        ("current_shift", "VARCHAR(1)"),
        ("shift_start_time", "TIMESTAMP WITH TIME ZONE"),
        ("shift_end_time", "TIMESTAMP WITH TIME ZONE"),
        
        # PER-SHIFT WEIGHT PRODUCED
        ("weight_shift_a", "DOUBLE PRECISION DEFAULT 0.0"),
        ("weight_shift_b", "DOUBLE PRECISION DEFAULT 0.0"),
        ("weight_shift_c", "DOUBLE PRECISION DEFAULT 0.0"),
        
        # PER-SHIFT CONFIRMED TO SAP
        ("confirmed_shift_a", "DOUBLE PRECISION DEFAULT 0.0"),
        ("confirmed_shift_b", "DOUBLE PRECISION DEFAULT 0.0"),
        ("confirmed_shift_c", "DOUBLE PRECISION DEFAULT 0.0"),
        
        # SHIFT CONFIRMATION STATUS FLAGS
        ("shift_a_confirmed", "BOOLEAN DEFAULT FALSE"),
        ("shift_b_confirmed", "BOOLEAN DEFAULT FALSE"),
        ("shift_c_confirmed", "BOOLEAN DEFAULT FALSE"),
        
        # OVERFLOW HANDLING
        ("overflow_weight", "DOUBLE PRECISION DEFAULT 0.0"),
        ("is_target_reached", "BOOLEAN DEFAULT FALSE"),
        
        # SHIFT METADATA
        ("total_shifts_used", "INTEGER DEFAULT 0"),
        ("last_shift_completed", "VARCHAR(1)"),
        
        # SHIFT BASELINE TRACKING (JSON)
        ("baseline_shift_a_start", "JSONB"),
        ("baseline_shift_b_start", "JSONB"),
        ("baseline_shift_c_start", "JSONB"),
    ]
    
    try:
        with postgres_engine.connect() as conn:
            # Start transaction
            trans = conn.begin()
            
            try:
                # Check which columns already exist
                print("📝 Checking existing columns...")
                check_columns_sql = """
                    SELECT column_name 
                    FROM information_schema.columns 
                    WHERE table_name = 'process_orders'
                """
                existing_columns = {row[0] for row in conn.execute(text(check_columns_sql)).fetchall()}
                
                # Add missing columns
                added_count = 0
                skipped_count = 0
                
                for column_name, column_type in new_columns:
                    if column_name in existing_columns:
                        print(f"  ⚠️  Column '{column_name}' already exists - skipping")
                        skipped_count += 1
                    else:
                        try:
                            alter_sql = f"ALTER TABLE process_orders ADD COLUMN {column_name} {column_type}"
                            conn.execute(text(alter_sql))
                            print(f"  ✅ Added column '{column_name}' ({column_type})")
                            added_count += 1
                        except Exception as e:
                            print(f"  ❌ Error adding column '{column_name}': {e}")
                            raise
                
                # Create indexes for shift-based fields
                print("\n📊 Creating indexes for shift-based fields...")
                indexes = [
                    ("idx_current_shift", "current_shift"),
                    ("idx_shift_confirmed", "shift_a_confirmed", "shift_b_confirmed", "shift_c_confirmed"),
                    ("idx_target_reached", "is_target_reached"),
                ]
                
                for index_name, *columns in indexes:
                    try:
                        # Check if index already exists
                        check_index_sql = """
                            SELECT indexname 
                            FROM pg_indexes 
                            WHERE tablename = 'process_orders' AND indexname = :index_name
                        """
                        existing_index = conn.execute(text(check_index_sql), {"index_name": index_name}).first()
                        
                        if existing_index:
                            print(f"  ⚠️  Index '{index_name}' already exists - skipping")
                        else:
                            columns_str = ", ".join(columns)
                            create_index_sql = f"CREATE INDEX {index_name} ON process_orders ({columns_str})"
                            conn.execute(text(create_index_sql))
                            print(f"  ✅ Created index '{index_name}' on ({columns_str})")
                    except Exception as e:
                        print(f"  ⚠️  Could not create index '{index_name}': {e}")
                        # Don't fail migration if index creation fails
                
                # Commit transaction
                trans.commit()
                
                print(f"\n✅ Migration completed successfully!")
                print(f"   - Added {added_count} new columns")
                print(f"   - Skipped {skipped_count} existing columns")
                print(f"   - Created indexes for shift-based fields")
                
            except Exception as e:
                trans.rollback()
                print(f"\n❌ Migration failed: {e}")
                raise
                
    except Exception as e:
        print(f"❌ Error during migration: {e}")
        import traceback
        traceback.print_exc()
        return False
    
    return True

if __name__ == "__main__":
    success = run_migration()
    sys.exit(0 if success else 1)

