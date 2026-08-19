#!/usr/bin/env python3
"""
Diagnostic tool to check why "No validated orders found" message appears.
"""

import sys
import os
from sqlalchemy import text
from database import postgres_engine

def diagnose_push_confirmation_issue():
    """Diagnose why push confirmation returns no validated orders."""
    
    print("=" * 80)
    print("DIAGNOSING PUSH CONFIRMATION ISSUE")
    print("=" * 80)
    print("Checking why 'No validated orders found' message appears")
    print("=" * 80)
    
    try:
        with postgres_engine.connect() as conn:
            print("\n1. CHECKING ALL ORDERS IN DATABASE")
            print("-" * 60)
            
            # Check all orders
            all_orders_query = text("""
                SELECT 
                    po.id,
                    po.order_id,
                    po.status,
                    po.priority,
                    po.quantity,
                    po.unit,
                    po.plant,
                    po.created_at
                FROM process_orders po
                ORDER BY po.id
                LIMIT 10
            """)
            
            all_orders = conn.execute(all_orders_query).mappings().all()
            
            print("All orders in database:")
            for order in all_orders:
                print(f"  ID: {order.id}, PO: {order.order_id}, Status: {order.status}, Priority: {order.priority}")
            
            print("\n2. CHECKING VALIDATED ORDERS")
            print("-" * 60)
            
            # Check validated orders
            validated_orders_query = text("""
                SELECT 
                    po.id,
                    po.order_id,
                    po.status,
                    po.priority,
                    po.quantity,
                    po.unit,
                    po.plant
                FROM process_orders po
                WHERE po.status = 'Validated'
                ORDER BY po.id
            """)
            
            validated_orders = conn.execute(validated_orders_query).mappings().all()
            
            print(f"Found {len(validated_orders)} validated orders:")
            for order in validated_orders:
                print(f"  ID: {order.id}, PO: {order.order_id}, Status: {order.status}, Priority: {order.priority}")
            
            print("\n3. CHECKING CONFIRMED ORDERS")
            print("-" * 60)
            
            # Check confirmed orders
            confirmed_orders_query = text("""
                SELECT 
                    po.id,
                    po.order_id,
                    po.status,
                    po.priority,
                    po.quantity,
                    po.unit,
                    po.plant
                FROM process_orders po
                WHERE po.status = 'Confirmed'
                ORDER BY po.id
            """)
            
            confirmed_orders = conn.execute(confirmed_orders_query).mappings().all()
            
            print(f"Found {len(confirmed_orders)} confirmed orders:")
            for order in confirmed_orders:
                print(f"  ID: {order.id}, PO: {order.order_id}, Status: {order.status}, Priority: {order.priority}")
            
            print("\n4. CHECKING PUSH CONFIRMATION QUERY")
            print("-" * 60)
            
            # Simulate the exact query used in push confirmation
            push_query = text("""
                SELECT 
                    po.id as process_order_id,
                    po.order_id as po_number,
                    po.material,
                    po.version,
                    po.material_desc,
                    po.quantity as total_qty,
                    po.confirmed_qty,
                    po.unit as uom,
                    po.plant,
                    po.created_at,
                    po.updated_at as confirmed_at,
                    po.batch,
                    po.status,
                    po.priority as shift,
                    po.validation_method,
                    po.confirmed_text,
                    po.scrap
                FROM process_orders po
                WHERE po.status = 'Validated'
                AND po.status != 'Confirmed'
                ORDER BY po.id
            """)
            
            push_orders = conn.execute(push_query).mappings().all()
            
            print(f"Orders that would be sent to SAP: {len(push_orders)}")
            for order in push_orders:
                print(f"  PO: {order.po_number}, Status: {order.status}, Shift: {order.shift}")
            
            print("\n5. ANALYSIS")
            print("-" * 60)
            
            if len(validated_orders) == 0:
                print("❌ ISSUE: No orders have status = 'Validated'")
                print("   Solution: Orders need to be validated first")
                print("   Use: POST /api/process_orders/{id}/validate")
            elif len(push_orders) == 0:
                print("❌ ISSUE: Validated orders exist but query returns none")
                print("   This suggests a query logic problem")
            else:
                print("✅ Orders found that can be sent to SAP")
                print(f"   {len(push_orders)} orders ready for confirmation")
            
            print("\n6. RECOMMENDATIONS")
            print("-" * 60)
            
            if len(validated_orders) == 0:
                print("1. Validate orders first:")
                print("   POST /api/process_orders/{id}/validate")
                print("   Body: {\"status\": \"Validated\"}")
                print()
                print("2. Then push to SAP:")
                print("   POST /api/process_orders/push-confirmation")
                print("   Body: {\"status\": \"Validated\"}")
            else:
                print("1. Orders are validated, try pushing again")
                print("2. Check if there are any database connection issues")
                print("3. Verify the API request format")
                
    except Exception as e:
        print(f"❌ Database connection error: {e}")
        print("Check database connection and credentials")

if __name__ == "__main__":
    diagnose_push_confirmation_issue()
