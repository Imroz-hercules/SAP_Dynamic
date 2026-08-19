#!/usr/bin/env python3
"""
Verify that shift data is NOT cumulative - each shift sends only its own data.
"""

import sys
import os
import json
from datetime import datetime
from typing import Dict, Any, List

# Add the backend directory to Python path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

# Import the SAP confirmation service
from services.sap_confirmation import SAPConfirmationService

def verify_non_cumulative_shift_data():
    """Verify that each shift sends only its own data, not cumulative."""
    
    print("=" * 80)
    print("VERIFYING NON-CUMULATIVE SHIFT DATA")
    print("=" * 80)
    print("Testing if each shift sends ONLY its own data (not cumulative)")
    print("=" * 80)
    
    # Create test data with KNOWN individual shift quantities
    test_orders = [
        # SHIFT A ORDERS (should total 950 KG)
        {
            "po_number": "PO001",
            "material": "1300005",
            "version": "BKF1",
            "material_desc": "Cement Clinker",
            "total_qty": 1000.0,
            "confirmed_weight": 500.0,  # Individual order weight
            "uom": "KG",
            "plant": "3130",
            "created_at": datetime(2024, 1, 15, 8, 30),  # Shift A time
            "confirmed_at": datetime(2024, 1, 15, 10, 45),
            "batch": "BATCH001",
            "status": "Validated",
            "shift": 1,  # Shift A
            "confirmed_text": "Auto validated",
            "scrap": 50.0
        },
        {
            "po_number": "PO002",
            "material": "1300006",
            "version": "BKF2",
            "material_desc": "Raw Material Mix",
            "total_qty": 800.0,
            "confirmed_weight": 450.0,  # Individual order weight
            "uom": "KG",
            "plant": "3130",
            "created_at": datetime(2024, 1, 15, 9, 15),  # Shift A time
            "confirmed_at": datetime(2024, 1, 15, 11, 30),
            "batch": "BATCH002",
            "status": "Validated",
            "shift": 1,  # Shift A
            "confirmed_text": "Manual validated",
            "scrap": 25.0
        },
        
        # SHIFT B ORDERS (should total 1000 KG - NOT 1950)
        {
            "po_number": "PO003",
            "material": "1300007",
            "version": "BKF3",
            "material_desc": "Finished Cement",
            "total_qty": 1200.0,
            "confirmed_weight": 600.0,  # Individual order weight
            "uom": "KG",
            "plant": "3130",
            "created_at": datetime(2024, 1, 15, 16, 30),  # Shift B time
            "confirmed_at": datetime(2024, 1, 15, 18, 45),
            "batch": "BATCH003",
            "status": "Validated",
            "shift": 2,  # Shift B
            "confirmed_text": "Auto validated",
            "scrap": 30.0
        },
        {
            "po_number": "PO004",
            "material": "1300008",
            "version": "BKF4",
            "material_desc": "Quality Cement",
            "total_qty": 900.0,
            "confirmed_weight": 400.0,  # Individual order weight
            "uom": "KG",
            "plant": "3130",
            "created_at": datetime(2024, 1, 15, 17, 45),  # Shift B time
            "confirmed_at": datetime(2024, 1, 15, 19, 20),
            "batch": "BATCH004",
            "status": "Validated",
            "shift": 2,  # Shift B
            "confirmed_text": "Manual validated",
            "scrap": 20.0
        }
    ]
    
    sap_service = SAPConfirmationService()
    
    print("\n1. INDIVIDUAL ORDER WEIGHTS (From Database)")
    print("-" * 60)
    shift_a_total = 0
    shift_b_total = 0
    
    for order in test_orders:
        shift_num = order['shift']
        weight = order['confirmed_weight']
        po_number = order['po_number']
        
        if shift_num == 1:  # Shift A
            shift_a_total += weight
            print(f"Shift A - {po_number}: {weight} KG")
        elif shift_num == 2:  # Shift B
            shift_b_total += weight
            print(f"Shift B - {po_number}: {weight} KG")
    
    print(f"\nExpected Totals:")
    print(f"  Shift A Total: {shift_a_total} KG")
    print(f"  Shift B Total: {shift_b_total} KG")
    
    print("\n2. JSON FORMAT FOR SAP (What Actually Gets Sent)")
    print("-" * 60)
    online_json = sap_service._convert_to_json_format(test_orders, "online")
    
    print("Individual orders sent to SAP:")
    for order in online_json:
        po = order['process_order']
        shift = order['shift']
        weight = order['confirmed_weight']
        print(f"  {po}: Shift {shift}, Weight {weight} KG")
    
    print("\n3. SHIFT-WISE GROUPING ANALYSIS")
    print("-" * 60)
    
    # Group by shift and calculate totals
    shift_groups = {}
    for order in online_json:
        shift = order['shift']
        if shift not in shift_groups:
            shift_groups[shift] = []
        shift_groups[shift].append(order)
    
    for shift, orders in shift_groups.items():
        print(f"\nShift {shift} Orders:")
        total_weight = 0
        for order in orders:
            weight = float(order['confirmed_weight'])
            total_weight += weight
            print(f"  - PO {order['process_order']}: {weight} KG")
        print(f"  📊 Total Weight for Shift {shift}: {total_weight} KG")
    
    print("\n4. VERIFICATION RESULTS")
    print("-" * 60)
    
    # Get actual totals from JSON
    actual_shift_a = sum(float(order['confirmed_weight']) for order in online_json if order['shift'] == 'A')
    actual_shift_b = sum(float(order['confirmed_weight']) for order in online_json if order['shift'] == 'B')
    
    print(f"Expected vs Actual:")
    print(f"  Shift A: Expected {shift_a_total} KG, Actual {actual_shift_a} KG")
    print(f"  Shift B: Expected {shift_b_total} KG, Actual {actual_shift_b} KG")
    
    # Check if data is cumulative
    if actual_shift_b > shift_b_total:
        print(f"\n❌ PROBLEM DETECTED: Shift B shows {actual_shift_b} KG")
        print(f"   This is MORE than expected {shift_b_total} KG")
        print(f"   Difference: {actual_shift_b - shift_b_total} KG")
        print(f"   This suggests cumulative data!")
    else:
        print(f"\n✅ NO PROBLEM: Each shift sends only its own data")
        print(f"   Shift A: {actual_shift_a} KG (only Shift A orders)")
        print(f"   Shift B: {actual_shift_b} KG (only Shift B orders)")
        print(f"   No cumulative calculation detected!")
    
    print("\n5. CONCLUSION")
    print("-" * 60)
    if actual_shift_a == shift_a_total and actual_shift_b == shift_b_total:
        print("✅ CONFIRMED: Your system sends SEPARATE shift data")
        print("✅ Each shift sends only its own orders")
        print("✅ No cumulative calculation is happening")
        print("✅ SAP receives individual shift confirmations")
    else:
        print("❌ ISSUE FOUND: Data appears to be cumulative")
        print("❌ Need to investigate the calculation logic")

if __name__ == "__main__":
    verify_non_cumulative_shift_data()
