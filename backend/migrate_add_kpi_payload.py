"""
Migration: Add kpi_payload_sent column to kpi_send_tracking table
Run this once to add the new JSON column for storing SAP payloads.

Usage: python migrate_add_kpi_payload.py
"""
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from sqlalchemy import text
from database import postgres_engine

def run_migration():
    """Add kpi_payload_sent column to kpi_send_tracking table."""
    print("=" * 60)
    print("Migration: Adding kpi_payload_sent column to kpi_send_tracking")
    print("=" * 60)
    
    try:
        with postgres_engine.connect() as conn:
            # Check if column already exists
            check_sql = text("""
                SELECT column_name 
                FROM information_schema.columns 
                WHERE table_name = 'kpi_send_tracking' 
                AND column_name = 'kpi_payload_sent'
            """)
            result = conn.execute(check_sql).fetchone()
            
            if result:
                print("[OK] Column 'kpi_payload_sent' already exists. No migration needed.")
                return True
            
            # Add the new column
            alter_sql = text("""
                ALTER TABLE kpi_send_tracking 
                ADD COLUMN kpi_payload_sent JSONB
            """)
            conn.execute(alter_sql)
            conn.commit()
            
            print("[OK] Successfully added 'kpi_payload_sent' column (JSONB type)")
            print("")
            print("This column will now store the full KPI payload sent to SAP:")
            print("- For MILLING: NET_HOURS, TOTAL_WATER, MILLING_GAIN, etc.")
            print("- For PACKING: PACKING_BAG, PACKING_HOURS, etc.")
            print("")
            print("Migration completed successfully!")
            return True
            
    except Exception as e:
        print(f"[ERROR] Migration failed: {e}")
        return False


if __name__ == "__main__":
    success = run_migration()
    sys.exit(0 if success else 1)
