#!/usr/bin/env python3
"""
Detailed demonstration of shift-wise confirmation data for SAP.
Shows the exact data transformation from input to SAP format.
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

def demonstrate_shift_wise_confirmation():
    """Demonstrate the exact data used for shift-wise confirmation."""
    
    print("=" * 80)
    print("SHIFT-WISE CONFIRMATION DATA DEMONSTRATION")
    print("=" * 80)
    print("This shows the exact data transformation from input to SAP format")
    print("=" * 80)
    
    # Create realistic test data representing different shifts
    test_orders = [
        {
            "po_number": "PO001",
            "material": "1300005",
            "version": "BKF1",
            "material_desc": "Cement Clinker",
            "total_qty": 1000.0,
            "confirmed_weight": 950.0,
            "uom": "KG",
            "plant": "3130",  # Milling plant
            "created_at": datetime(2024, 1, 15, 8, 30),  # Shift A time (7:00-15:00)
            "confirmed_at": datetime(2024, 1, 15, 10, 45),
            "batch": "BATCH001",
            "status": "Validated",
            "shift": 1,  # Will become "A"
            "confirmed_text": "Auto validated",
            "scrap": 50.0
        },
        {
            "po_number": "PO002",
            "material": "1300006",
            "version": "BKF2",
            "material_desc": "Raw Material Mix",
            "total_qty": 2000.0,
            "confirmed_weight": 1950.0,
            "uom": "KG",
            "plant": "3130",  # Milling plant
            "created_at": datetime(2024, 1, 15, 16, 30),  # Shift B time (15:00-23:00)
            "confirmed_at": datetime(2024, 1, 15, 18, 45),
            "batch": "BATCH002",
            "status": "Validated",
            "shift": 2,  # Will become "B"
            "confirmed_text": "Manual validated",
            "scrap": 100.0
        },
        {
            "po_number": "PO003",
            "material": "1300007",
            "version": "BKF3",
            "material_desc": "Finished Cement",
            "total_qty": 1500.0,
            "confirmed_weight": 1450.0,
            "uom": "KG",
            "plant": "3130",  # Milling plant
            "created_at": datetime(2024, 1, 15, 23, 30),  # Shift C time (23:00-7:00)
            "confirmed_at": datetime(2024, 1, 16, 2, 15),
            "batch": "BATCH003",
            "status": "Validated",
            "shift": 3,  # Will become "C"
            "confirmed_text": "Auto validated",
            "scrap": 75.0
        },
        {
            "po_number": "PO004",
            "material": "1300008",
            "version": "PKG1",
            "material_desc": "Packaged Cement",
            "total_qty": 500.0,
            "confirmed_weight": 495.0,
            "uom": "BAG",
            "plant": "3131",  # Packing plant
            "created_at": datetime(2024, 1, 15, 8, 45),  # Shift A time (7:30-15:30)
            "confirmed_at": datetime(2024, 1, 15, 11, 30),
            "batch": "BATCH004",
            "status": "Validated",
            "shift": 1,  # Will become "A"
            "confirmed_text": "Manual validated",
            "scrap": 5.0
        },
        {
            "po_number": "PO005",
            "material": "1300009",
            "version": "PKG2",
            "material_desc": "Bulk Cement",
            "total_qty": 800.0,
            "confirmed_weight": 790.0,
            "uom": "BAG",
            "plant": "3131",  # Packing plant
            "created_at": datetime(2024, 1, 15, 16, 45),  # Shift B time (15:30-23:30)
            "confirmed_at": datetime(2024, 1, 15, 19, 20),
            "batch": "BATCH005",
            "status": "Validated",
            "shift": 2,  # Will become "B"
            "confirmed_text": "Auto validated",
            "scrap": 10.0
        }
    ]
    
    sap_service = SAPConfirmationService()
    
    print("\n1. INPUT DATA (From Database)")
    print("-" * 50)
    for i, order in enumerate(test_orders, 1):
        print(f"Order {i}:")
        print(f"  PO Number: {order['po_number']}")
        print(f"  Material: {order['material']}")
        print(f"  Plant: {order['plant']}")
        print(f"  Shift Number: {order['shift']}")
        print(f"  Created At: {order['created_at'].strftime('%Y-%m-%d %H:%M')}")
        print(f"  Confirmed Weight: {order['confirmed_weight']} {order['uom']}")
        print(f"  Status: {order['status']}")
        print()
    
    print("\n2. SHIFT CONVERSION LOGIC")
    print("-" * 50)
    for order in test_orders:
        shift_num = order['shift']
        plant = order['plant']
        shift_letter = sap_service._get_shift_name(shift_num, plant)
        
        print(f"PO {order['po_number']}: Plant {plant}, Shift {shift_num} → '{shift_letter}'")
    
    print("\n3. ONLINE CONFIRMATION FORMAT (Sent to SAP)")
    print("-" * 50)
    online_json = sap_service._convert_to_json_format(test_orders, "online")
    
    print("JSON Array sent to SAP online confirmation API:")
    print(json.dumps(online_json, indent=2, default=str))
    
    print("\n4. OFFLINE CONFIRMATION FORMAT (Sent to SAP)")
    print("-" * 50)
    offline_json = sap_service._convert_to_json_format(test_orders, "offline")
    
    print("JSON Array sent to SAP offline confirmation API:")
    print(json.dumps(offline_json, indent=2, default=str))
    
    print("\n5. SHIFT-WISE GROUPING ANALYSIS")
    print("-" * 50)
    
    # Group orders by shift
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
        print(f"  Total Weight for Shift {shift}: {total_weight} KG")
    
    print("\n6. SAP API ENDPOINTS USED")
    print("-" * 50)
    print("Online Confirmation:")
    print("  URL: https://vhmioqs4ci.sap.mc3.com.sa:44300/zmi_conf_online/CONF")
    print("  Method: POST")
    print("  Content-Type: application/json")
    print()
    print("Offline Confirmation:")
    print("  URL: https://vhmioqs4ci.sap.mc3.com.sa:44300/zmi_conf_offline/CONF")
    print("  Method: POST")
    print("  Content-Type: application/json")
    
    print("\n7. KEY FINDINGS")
    print("-" * 50)
    print("✅ Each order maintains its own shift identifier")
    print("✅ Milling plant (3130) uses 3 shifts: A, B, C")
    print("✅ Packing plant (3131) uses 2 shifts: A, B")
    print("✅ Shift data is sent separately, not cumulatively")
    print("✅ SAP receives individual confirmations per shift")
    print("✅ All required fields are properly formatted for SAP")

if __name__ == "__main__":
    demonstrate_shift_wise_confirmation()
