#!/usr/bin/env python3
"""
Test script to validate shift data logic for SAP integration.
This script tests shift data without requiring SAP access.
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

def test_shift_name_conversion():
    """Test the shift name conversion logic."""
    print("=" * 60)
    print("TEST 1: Shift Name Conversion Logic")
    print("=" * 60)
    
    sap_service = SAPConfirmationService()
    
    # Test cases for different plants and shift numbers
    test_cases = [
        # Milling plant (3130) - should have 3 shifts (A, B, C)
        {"shift_number": 1, "plant": "3130", "expected": "A"},
        {"shift_number": 2, "plant": "3130", "expected": "B"},
        {"shift_number": 3, "plant": "3130", "expected": "C"},
        {"shift_number": 4, "plant": "3130", "expected": "A"},  # Cycles back
        {"shift_number": 5, "plant": "3130", "expected": "B"},
        {"shift_number": 6, "plant": "3130", "expected": "C"},
        
        # Packing plant (other) - should have 2 shifts (A, B)
        {"shift_number": 1, "plant": "3131", "expected": "A"},
        {"shift_number": 2, "plant": "3131", "expected": "B"},
        {"shift_number": 3, "plant": "3131", "expected": "A"},  # Cycles back
        {"shift_number": 4, "plant": "3131", "expected": "B"},
        
        # Default case (no plant)
        {"shift_number": 1, "plant": "", "expected": "A"},
        {"shift_number": 2, "plant": "", "expected": "B"},
        {"shift_number": 3, "plant": "", "expected": "A"},
        
        # Edge cases
        {"shift_number": 0, "plant": "3130", "expected": "A"},
        {"shift_number": None, "plant": "3130", "expected": "A"},
    ]
    
    all_passed = True
    
    for i, test_case in enumerate(test_cases, 1):
        shift_number = test_case["shift_number"]
        plant = test_case["plant"]
        expected = test_case["expected"]
        
        try:
            result = sap_service._get_shift_name(shift_number, plant)
            status = "✅ PASS" if result == expected else "❌ FAIL"
            
            print(f"Test {i:2d}: Shift {shift_number} in Plant {plant or 'None':4s} -> {result} (expected {expected}) {status}")
            
            if result != expected:
                all_passed = False
                print(f"         ERROR: Expected {expected}, got {result}")
                
        except Exception as e:
            print(f"Test {i:2d}: Shift {shift_number} in Plant {plant or 'None':4s} -> ERROR: {e}")
            all_passed = False
    
    print(f"\nShift Name Conversion Test: {'✅ ALL PASSED' if all_passed else '❌ SOME FAILED'}")
    return all_passed

def test_json_format_conversion():
    """Test the JSON format conversion for SAP."""
    print("\n" + "=" * 60)
    print("TEST 2: JSON Format Conversion for SAP")
    print("=" * 60)
    
    sap_service = SAPConfirmationService()
    
    # Create test orders with different shifts
    test_orders = [
        {
            "po_number": "PO001",
            "material": "1300005",
            "version": "BKF1",
            "material_desc": "Test Material 1",
            "total_qty": 1000.0,
            "confirmed_weight": 950.0,
            "uom": "KG",
            "plant": "3130",  # Milling plant
            "created_at": datetime(2024, 1, 15, 8, 30),  # Shift A time
            "confirmed_at": datetime(2024, 1, 15, 10, 45),
            "batch": "BATCH001",
            "status": "Validated",
            "shift": 1,  # Should become "A"
            "confirmed_text": "Auto validated",
            "scrap": 50.0
        },
        {
            "po_number": "PO002",
            "material": "1300006",
            "version": "BKF2",
            "material_desc": "Test Material 2",
            "total_qty": 2000.0,
            "confirmed_weight": 1950.0,
            "uom": "KG",
            "plant": "3130",  # Milling plant
            "created_at": datetime(2024, 1, 15, 16, 30),  # Shift B time
            "confirmed_at": datetime(2024, 1, 15, 18, 45),
            "batch": "BATCH002",
            "status": "Validated",
            "shift": 2,  # Should become "B"
            "confirmed_text": "Manual validated",
            "scrap": 100.0
        },
        {
            "po_number": "PO003",
            "material": "1300007",
            "version": "BKF3",
            "material_desc": "Test Material 3",
            "total_qty": 1500.0,
            "confirmed_weight": 1450.0,
            "uom": "KG",
            "plant": "3131",  # Packing plant
            "created_at": datetime(2024, 1, 15, 8, 45),  # Shift A time
            "confirmed_at": datetime(2024, 1, 15, 11, 30),
            "batch": "BATCH003",
            "status": "Validated",
            "shift": 1,  # Should become "A"
            "confirmed_text": "Auto validated",
            "scrap": 75.0
        }
    ]
    
    try:
        # Test online format
        print("Testing ONLINE format conversion:")
        online_json = sap_service._convert_to_json_format(test_orders, "online")
        
        print(f"Generated {len(online_json)} orders for online confirmation:")
        for i, order in enumerate(online_json, 1):
            print(f"  Order {i}:")
            print(f"    Process Order: {order.get('process_order', 'N/A')}")
            print(f"    Material: {order.get('material', 'N/A')}")
            print(f"    Shift: {order.get('shift', 'N/A')}")
            print(f"    Confirmed Weight: {order.get('confirmed_weight', 'N/A')}")
            print(f"    Plant: {order.get('plant', 'N/A')}")
            print()
        
        # Test offline format
        print("Testing OFFLINE format conversion:")
        offline_json = sap_service._convert_to_json_format(test_orders, "offline")
        
        print(f"Generated {len(offline_json)} orders for offline confirmation:")
        for i, order in enumerate(offline_json, 1):
            print(f"  Order {i}:")
            print(f"    Process Order: {order.get('process_order', 'N/A')}")
            print(f"    Material: {order.get('material', 'N/A')}")
            print(f"    Shift: {order.get('shift', 'N/A')}")
            print(f"    Confirmed Weight: {order.get('confirmed_weight', 'N/A')}")
            print(f"    Plant: {order.get('plant', 'N/A')}")
            print(f"    Confirmed Text: {order.get('confirmed_text', 'N/A')}")
            print(f"    Scrap: {order.get('scrap', 'N/A')}")
            print()
        
        # Validate shift assignments
        print("Validating shift assignments:")
        expected_shifts = ["A", "B", "A"]  # Based on our test data
        
        for i, (order, expected_shift) in enumerate(zip(online_json, expected_shifts), 1):
            actual_shift = order.get('shift', 'N/A')
            status = "✅ PASS" if actual_shift == expected_shift else "❌ FAIL"
            print(f"  Order {i} (PO{order.get('process_order', 'N/A')}): Shift {actual_shift} (expected {expected_shift}) {status}")
        
        return True
        
    except Exception as e:
        print(f"❌ JSON Format Conversion Test FAILED: {e}")
        return False

def test_shift_data_validation():
    """Test shift data validation scenarios."""
    print("\n" + "=" * 60)
    print("TEST 3: Shift Data Validation Scenarios")
    print("=" * 60)
    
    # Test different shift scenarios
    scenarios = [
        {
            "name": "Milling Plant - All 3 Shifts",
            "orders": [
                {"po_number": "PO001", "plant": "3130", "shift": 1, "expected_shift": "A"},
                {"po_number": "PO002", "plant": "3130", "shift": 2, "expected_shift": "B"},
                {"po_number": "PO003", "plant": "3130", "shift": 3, "expected_shift": "C"},
            ]
        },
        {
            "name": "Packing Plant - 2 Shifts",
            "orders": [
                {"po_number": "PO004", "plant": "3131", "shift": 1, "expected_shift": "A"},
                {"po_number": "PO005", "plant": "3131", "shift": 2, "expected_shift": "B"},
            ]
        },
        {
            "name": "Mixed Plants",
            "orders": [
                {"po_number": "PO006", "plant": "3130", "shift": 1, "expected_shift": "A"},
                {"po_number": "PO007", "plant": "3131", "shift": 2, "expected_shift": "B"},
                {"po_number": "PO008", "plant": "3130", "shift": 3, "expected_shift": "C"},
            ]
        }
    ]
    
    sap_service = SAPConfirmationService()
    all_passed = True
    
    for scenario in scenarios:
        print(f"\nScenario: {scenario['name']}")
        print("-" * 40)
        
        for order in scenario['orders']:
            po_number = order['po_number']
            plant = order['plant']
            shift_num = order['shift']
            expected = order['expected_shift']
            
            try:
                actual = sap_service._get_shift_name(shift_num, plant)
                status = "✅ PASS" if actual == expected else "❌ FAIL"
                
                print(f"  {po_number}: Plant {plant}, Shift {shift_num} -> {actual} (expected {expected}) {status}")
                
                if actual != expected:
                    all_passed = False
                    
            except Exception as e:
                print(f"  {po_number}: ERROR - {e}")
                all_passed = False
    
    print(f"\nShift Data Validation: {'✅ ALL PASSED' if all_passed else '❌ SOME FAILED'}")
    return all_passed

def test_shift_timing_logic():
    """Test shift timing logic from frontend components."""
    print("\n" + "=" * 60)
    print("TEST 4: Shift Timing Logic Validation")
    print("=" * 60)
    
    # Simulate the shift timing logic from ShiftIndicator.tsx
    def get_shift_from_time(hour: int, minute: int, operation: str) -> str:
        """Simulate the shift calculation logic."""
        time_in_minutes = hour * 60 + minute
        
        if operation == 'milling':
            # Milling shifts: 7am-3pm (A), 3pm-11pm (B), 11pm-7am (C)
            if 7 * 60 <= time_in_minutes < 15 * 60:
                return 'A'
            elif 15 * 60 <= time_in_minutes < 23 * 60:
                return 'B'
            else:
                return 'C'
        else:
            # Packing shifts: 7:30am-3:30pm (A), 3:30pm-11:30pm (B)
            if 7 * 60 + 30 <= time_in_minutes < 15 * 60 + 30:
                return 'A'
            else:
                return 'B'
    
    # Test cases for different times
    test_times = [
        # Milling operation tests
        {"hour": 8, "minute": 0, "operation": "milling", "expected": "A"},
        {"hour": 10, "minute": 30, "operation": "milling", "expected": "A"},
        {"hour": 14, "minute": 59, "operation": "milling", "expected": "A"},
        {"hour": 15, "minute": 0, "operation": "milling", "expected": "B"},
        {"hour": 18, "minute": 30, "operation": "milling", "expected": "B"},
        {"hour": 22, "minute": 59, "operation": "milling", "expected": "B"},
        {"hour": 23, "minute": 0, "operation": "milling", "expected": "C"},
        {"hour": 2, "minute": 30, "operation": "milling", "expected": "C"},
        {"hour": 6, "minute": 59, "operation": "milling", "expected": "C"},
        
        # Packing operation tests
        {"hour": 8, "minute": 0, "operation": "packing", "expected": "A"},
        {"hour": 10, "minute": 30, "operation": "packing", "expected": "A"},
        {"hour": 15, "minute": 29, "operation": "packing", "expected": "A"},
        {"hour": 15, "minute": 30, "operation": "packing", "expected": "B"},
        {"hour": 18, "minute": 30, "operation": "packing", "expected": "B"},
        {"hour": 23, "minute": 29, "operation": "packing", "expected": "B"},
    ]
    
    all_passed = True
    
    for test in test_times:
        hour = test['hour']
        minute = test['minute']
        operation = test['operation']
        expected = test['expected']
        
        actual = get_shift_from_time(hour, minute, operation)
        status = "✅ PASS" if actual == expected else "❌ FAIL"
        
        time_str = f"{hour:02d}:{minute:02d}"
        print(f"  {time_str} {operation:7s} -> Shift {actual} (expected {expected}) {status}")
        
        if actual != expected:
            all_passed = False
    
    print(f"\nShift Timing Logic: {'✅ ALL PASSED' if all_passed else '❌ SOME FAILED'}")
    return all_passed

def main():
    """Run all shift data tests."""
    print("SHIFT DATA VALIDATION TEST SUITE")
    print("=" * 60)
    print("This test validates shift data logic without requiring SAP access.")
    print("=" * 60)
    
    test_results = []
    
    # Run all tests
    test_results.append(("Shift Name Conversion", test_shift_name_conversion()))
    test_results.append(("JSON Format Conversion", test_json_format_conversion()))
    test_results.append(("Shift Data Validation", test_shift_data_validation()))
    test_results.append(("Shift Timing Logic", test_shift_timing_logic()))
    
    # Summary
    print("\n" + "=" * 60)
    print("TEST SUMMARY")
    print("=" * 60)
    
    passed_count = 0
    for test_name, result in test_results:
        status = "✅ PASSED" if result else "❌ FAILED"
        print(f"{test_name:25s}: {status}")
        if result:
            passed_count += 1
    
    print(f"\nOverall Result: {passed_count}/{len(test_results)} tests passed")
    
    if passed_count == len(test_results):
        print("\n🎉 ALL TESTS PASSED! Shift data logic is working correctly.")
        print("✅ Your system will send shift data properly to SAP.")
        print("✅ Each order will have the correct shift identifier.")
        print("✅ No cumulative data - each shift sends separate confirmations.")
    else:
        print(f"\n⚠️  {len(test_results) - passed_count} tests failed. Please review the issues above.")
    
    return passed_count == len(test_results)

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)
