#!/usr/bin/env python3
"""
Seed script to populate the new columns (PLANT, CONFIRMED_QTY, MATERIAL_DESC) 
with sample data for testing purposes.
"""

import sys
from sqlalchemy import text
from database import postgres_engine

def seed_new_columns_data():
    """Populate the new columns with sample data."""
    
    print("🌱 Seeding new columns with sample data...")
    
    try:
        with postgres_engine.connect() as conn:
            # Start transaction
            trans = conn.begin()
            
            try:
                # Sample data for the new columns
                sample_data = [
                    {
                        'plant': 'PLANT-001',
                        'confirmed_qty': 95.5,
                        'material_desc': 'Premium Wheat Flour - Grade A'
                    },
                    {
                        'plant': 'PLANT-002', 
                        'confirmed_qty': 88.2,
                        'material_desc': 'Organic Whole Wheat Flour'
                    },
                    {
                        'plant': 'PLANT-001',
                        'confirmed_qty': 102.1,
                        'material_desc': 'All-Purpose Flour - Standard Grade'
                    },
                    {
                        'plant': 'PLANT-003',
                        'confirmed_qty': 76.8,
                        'material_desc': 'Specialty Bread Flour - High Protein'
                    },
                    {
                        'plant': 'PLANT-002',
                        'confirmed_qty': 91.3,
                        'material_desc': 'Cake Flour - Fine Texture'
                    }
                ]
                
                # Update process_orders table
                print("📝 Updating process_orders table...")
                
                # Get existing process orders
                existing_orders = conn.execute(text("""
                    SELECT id, order_id, material 
                    FROM process_orders 
                    WHERE plant IS NULL OR confirmed_qty IS NULL OR material_desc IS NULL
                    ORDER BY id
                    LIMIT 10
                """)).fetchall()
                
                print(f"Found {len(existing_orders)} orders to update")
                
                for i, order in enumerate(existing_orders):
                    if i < len(sample_data):
                        data = sample_data[i]
                        conn.execute(text("""
                            UPDATE process_orders 
                            SET plant = :plant, 
                                confirmed_qty = :confirmed_qty, 
                                material_desc = :material_desc,
                                updated_at = NOW()
                            WHERE id = :id
                        """), {
                            'id': order.id,
                            'plant': data['plant'],
                            'confirmed_qty': data['confirmed_qty'],
                            'material_desc': data['material_desc']
                        })
                        print(f"  ✅ Updated order {order.order_id} with plant: {data['plant']}")
                
                # Update orders table
                print("📝 Updating orders table...")
                
                # Get existing orders
                existing_execution_orders = conn.execute(text("""
                    SELECT id, po_number, material 
                    FROM orders 
                    WHERE plant IS NULL OR confirmed_qty IS NULL OR material_desc IS NULL
                    ORDER BY id
                    LIMIT 10
                """)).fetchall()
                
                print(f"Found {len(existing_execution_orders)} execution orders to update")
                
                for i, order in enumerate(existing_execution_orders):
                    if i < len(sample_data):
                        data = sample_data[i]
                        conn.execute(text("""
                            UPDATE orders 
                            SET plant = :plant, 
                                confirmed_qty = :confirmed_qty, 
                                material_desc = :material_desc,
                                updated_at = NOW()
                            WHERE id = :id
                        """), {
                            'id': order.id,
                            'plant': data['plant'],
                            'confirmed_qty': data['confirmed_qty'],
                            'material_desc': data['material_desc']
                        })
                        print(f"  ✅ Updated execution order {order.po_number} with plant: {data['plant']}")
                
                # Commit transaction
                trans.commit()
                print("✅ Sample data seeding completed successfully!")
                
                # Verify the updates
                print("🔍 Verifying updates...")
                
                # Check process_orders
                updated_process_orders = conn.execute(text("""
                    SELECT order_id, plant, confirmed_qty, material_desc 
                    FROM process_orders 
                    WHERE plant IS NOT NULL 
                    LIMIT 5
                """)).fetchall()
                
                print("📋 Updated process_orders:")
                for order in updated_process_orders:
                    print(f"  - {order.order_id}: Plant={order.plant}, Qty={order.confirmed_qty}, Desc={order.material_desc}")
                
                # Check orders
                updated_orders = conn.execute(text("""
                    SELECT po_number, plant, confirmed_qty, material_desc 
                    FROM orders 
                    WHERE plant IS NOT NULL 
                    LIMIT 5
                """)).fetchall()
                
                print("📋 Updated orders:")
                for order in updated_orders:
                    print(f"  - {order.po_number}: Plant={order.plant}, Qty={order.confirmed_qty}, Desc={order.material_desc}")
                
            except Exception as e:
                trans.rollback()
                print(f"❌ Seeding failed: {e}")
                raise
                
    except Exception as e:
        print(f"❌ Database connection failed: {e}")
        sys.exit(1)

if __name__ == "__main__":
    seed_new_columns_data()
