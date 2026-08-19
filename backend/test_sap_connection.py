#!/usr/bin/env python3
"""
Test script to verify SAP API connection and data retrieval.
Run this script to test the SAP connection before deploying.
"""

import sys
import os
import logging
from datetime import datetime

# Add the backend directory to the Python path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from services.sap_real_client import SAPRealClient
from services.process_order_pull import pull_from_sap_once, test_sap_connection

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
log = logging.getLogger(__name__)

def test_sap_client():
    """Test the SAP client directly."""
    print("=" * 60)
    print("Testing SAP Client Direct Connection")
    print("=" * 60)
    
    try:
        client = SAPRealClient()
        
        # Test connection
        print("1. Testing SAP API connection...")
        is_connected = client.test_connection()
        print(f"   Connection status: {'✓ SUCCESS' if is_connected else '✗ FAILED'}")
        
        if is_connected:
            print("\n2. Fetching process orders...")
            orders = client.get_process_orders()
            print(f"   Retrieved {len(orders)} orders")
            
            if orders:
                print("\n3. Sample order data:")
                sample_order = orders[0]
                for key, value in sample_order.items():
                    print(f"   {key}: {value}")
            else:
                print("   No orders returned from SAP")
        
        return is_connected
        
    except Exception as e:
        print(f"   ✗ ERROR: {e}")
        return False

def test_pull_service():
    """Test the pull service."""
    print("\n" + "=" * 60)
    print("Testing Process Order Pull Service")
    print("=" * 60)
    
    try:
        print("1. Testing pull service connection...")
        is_connected = test_sap_connection()
        print(f"   Connection status: {'✓ SUCCESS' if is_connected else '✗ FAILED'}")
        
        if is_connected:
            print("\n2. Running pull service...")
            count = pull_from_sap_once()
            print(f"   Processed {count} orders")
            return True
        else:
            print("   Skipping pull test due to connection failure")
            return False
            
    except Exception as e:
        print(f"   ✗ ERROR: {e}")
        return False

def main():
    """Main test function."""
    print("SAP API Connection Test")
    print(f"Timestamp: {datetime.now().isoformat()}")
    print(f"SAP Endpoint: http://vhmioqs4ci.sap.mc3.com.sa:8000/zmi_get_orders/GETORD")
    print(f"Client: 200")
    
    # Test 1: Direct SAP client
    client_success = test_sap_client()
    
    # Test 2: Pull service
    service_success = test_pull_service()
    
    # Summary
    print("\n" + "=" * 60)
    print("TEST SUMMARY")
    print("=" * 60)
    print(f"SAP Client Test:     {'✓ PASS' if client_success else '✗ FAIL'}")
    print(f"Pull Service Test:   {'✓ PASS' if service_success else '✗ FAIL'}")
    
    if client_success and service_success:
        print("\n🎉 All tests passed! SAP integration is working correctly.")
        return 0
    else:
        print("\n❌ Some tests failed. Check the errors above.")
        return 1

if __name__ == "__main__":
    exit_code = main()
    sys.exit(exit_code)
