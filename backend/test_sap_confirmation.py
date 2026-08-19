#!/usr/bin/env python3
"""
Test script for SAP Confirmation Service
"""
import sys
import os
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from services.sap_confirmation import SAPConfirmationService
from datetime import datetime

def test_sap_confirmation():
    """Test the SAP confirmation service with sample data."""
    
    # Create service instance
    service = SAPConfirmationService()
    
    # Sample order data for testing
    sample_orders = [
        {
            "po_number": "13006742",
            "material": "1400001",
            "version": "BKL1",
            "material_desc": "MMC BAKERIES FLOUR 80% - 45 KG",
            "total_qty": 1000.0,
            "confirmed_weight": 30.0,
            "uom": "BAG",
            "plant": "3130",
            "created_at": datetime.now(),
            "confirmed_at": datetime.now(),
            "batch": "B-20250928-01",
            "status": "Validated",
            "shift": 1,
            "confirmed_text": "Test confirmation",
            "scrap": 1.0
        }
    ]
    
    print("Testing SAP Confirmation Service...")
    print("=" * 50)
    
    # Test online confirmation
    print("\n1. Testing Online Confirmation:")
    print("-" * 30)
    try:
        result = service.confirm_online(sample_orders)
        print(f"Result: {result}")
        if result.get("ok"):
            print("✅ Online confirmation test passed")
        else:
            print(f"❌ Online confirmation test failed: {result.get('error')}")
    except Exception as e:
        print(f"❌ Online confirmation test error: {e}")
    
    # Test offline confirmation
    print("\n2. Testing Offline Confirmation:")
    print("-" * 30)
    try:
        result = service.confirm_offline(sample_orders)
        print(f"Result: {result}")
        if result.get("ok"):
            print("✅ Offline confirmation test passed")
        else:
            print(f"❌ Offline confirmation test failed: {result.get('error')}")
    except Exception as e:
        print(f"❌ Offline confirmation test error: {e}")
    
    # Test batch confirmation (auto)
    print("\n3. Testing Batch Confirmation (Auto):")
    print("-" * 30)
    try:
        result = service.confirm_orders_batch(sample_orders, "auto")
        print(f"Result: {result}")
        if result.get("ok"):
            print("✅ Batch auto confirmation test passed")
        else:
            print(f"❌ Batch auto confirmation test failed: {result.get('error')}")
    except Exception as e:
        print(f"❌ Batch auto confirmation test error: {e}")
    
    # Test batch confirmation (manual)
    print("\n4. Testing Batch Confirmation (Manual):")
    print("-" * 30)
    try:
        result = service.confirm_orders_batch(sample_orders, "manual")
        print(f"Result: {result}")
        if result.get("ok"):
            print("✅ Batch manual confirmation test passed")
        else:
            print(f"❌ Batch manual confirmation test failed: {result.get('error')}")
    except Exception as e:
        print(f"❌ Batch manual confirmation test error: {e}")
    
    print("\n" + "=" * 50)
    print("Test completed!")

if __name__ == "__main__":
    test_sap_confirmation()
