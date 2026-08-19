#!/usr/bin/env python3
import sys
sys.path.append('.')
from database import postgres_engine
from sqlalchemy import text

print('Adding missing columns to process_orders table...')
try:
    with postgres_engine.connect() as conn:
        # Add order_type column
        conn.execute(text('ALTER TABLE process_orders ADD COLUMN IF NOT EXISTS order_type VARCHAR(50)'))
        print('✅ Added order_type column')
        
        # Add packing_line column  
        conn.execute(text('ALTER TABLE process_orders ADD COLUMN IF NOT EXISTS packing_line VARCHAR(10)'))
        print('✅ Added packing_line column')
        
        # Add bag_size column
        conn.execute(text('ALTER TABLE process_orders ADD COLUMN IF NOT EXISTS bag_size VARCHAR(10)'))
        print('✅ Added bag_size column')
        
        # Add index for order_type
        conn.execute(text('CREATE INDEX IF NOT EXISTS idx_process_order_type ON process_orders(order_type)'))
        print('✅ Added order_type index')
        
        conn.commit()
        print('🎉 All columns added successfully!')
        
except Exception as e:
    print(f'❌ Error: {e}')
