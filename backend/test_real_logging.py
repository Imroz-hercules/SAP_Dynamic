#!/usr/bin/env python3
"""
Test script to verify real-time logging is working
"""
import requests
import time
from services.system_logger import system_logger

def test_real_logging():
    print("🧪 Testing Real-Time Logging Integration")
    print("=" * 50)
    
    # Get initial log count
    initial_logs = system_logger.get_logs(limit=100)
    initial_count = len(initial_logs)
    print(f"Initial log count: {initial_count}")
    
    # Test 1: Manual sync via API
    print("\n1. Testing Manual Sync API...")
    try:
        response = requests.post('http://localhost:5000/api/system-logs/manual-sync', 
                               json={'operator': 'Test User'})
        print(f"   API Response: {response.status_code}")
        if response.status_code == 200:
            data = response.json()
            print(f"   Response: {data.get('message', 'No message')}")
        else:
            print(f"   Error: {response.text}")
    except Exception as e:
        print(f"   Error: {e}")
    
    time.sleep(1)
    
    # Test 2: SAP Sync via API
    print("\n2. Testing SAP Sync API...")
    try:
        response = requests.post('http://localhost:5000/api/sap-sync/seed-orders', json={})
        print(f"   API Response: {response.status_code}")
        if response.status_code == 200:
            data = response.json()
            print(f"   Response: {data.get('message', 'No message')}")
        else:
            print(f"   Error: {response.text}")
    except Exception as e:
        print(f"   Error: {e}")
    
    time.sleep(1)
    
    # Test 3: Raw Data Sync via API
    print("\n3. Testing Raw Data Sync API...")
    try:
        response = requests.post('http://localhost:5000/api/sap-sync/send-raw-data', json={})
        print(f"   API Response: {response.status_code}")
        if response.status_code == 200:
            data = response.json()
            print(f"   Response: {data.get('message', 'No message')}")
        else:
            print(f"   Error: {response.text}")
    except Exception as e:
        print(f"   Error: {e}")
    
    time.sleep(1)
    
    # Check final log count
    final_logs = system_logger.get_logs(limit=100)
    final_count = len(final_logs)
    new_logs = final_count - initial_count
    
    print(f"\n📊 Results:")
    print(f"   Initial logs: {initial_count}")
    print(f"   Final logs: {final_count}")
    print(f"   New logs created: {new_logs}")
    
    if new_logs > 0:
        print(f"\n✅ SUCCESS: {new_logs} new logs were created!")
        print("\nRecent logs:")
        for i, log in enumerate(final_logs[:5], 1):
            print(f"   {i}. {log['timestamp']} | {log['source']} | {log['action']} | {log['status']}")
    else:
        print(f"\n❌ ISSUE: No new logs were created. The logging integration may not be working.")
        
        # Check if the server is running the updated code
        print("\n🔍 Debugging:")
        print("   - Check if the backend server is running")
        print("   - Check if the server has the updated code with logging")
        print("   - Check if there are any import errors in the server logs")

if __name__ == "__main__":
    test_real_logging()
