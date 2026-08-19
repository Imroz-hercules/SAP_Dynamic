#!/usr/bin/env python3
"""
Test script to verify direct logging functionality
"""
from services.system_logger import system_logger, log_sap_event, log_hercules_event, log_operator_action
from datetime import datetime

def test_direct_logging():
    print("🧪 Testing Direct Logging Functions")
    print("=" * 40)
    
    # Get initial count
    initial_logs = system_logger.get_logs(limit=100)
    initial_count = len(initial_logs)
    print(f"Initial log count: {initial_count}")
    
    # Test direct logging
    print("\n1. Testing direct SAP event logging...")
    log_id1 = log_sap_event(
        action="Direct Test - Order Sync",
        status="Success",
        details="Testing direct logging functionality",
        metadata={"test": True, "timestamp": datetime.now().isoformat()}
    )
    print(f"   ✅ Created log entry with ID: {log_id1}")
    
    print("\n2. Testing direct Hercules event logging...")
    log_id2 = log_hercules_event(
        action="Direct Test - Data Push",
        status="Success",
        details="Testing direct Hercules logging",
        metadata={"test": True, "timestamp": datetime.now().isoformat()}
    )
    print(f"   ✅ Created log entry with ID: {log_id2}")
    
    print("\n3. Testing direct operator action logging...")
    log_id3 = log_operator_action(
        operator="Test User",
        action="Direct Test - Manual Action",
        status="Success",
        metadata={"test": True, "timestamp": datetime.now().isoformat()}
    )
    print(f"   ✅ Created log entry with ID: {log_id3}")
    
    # Check final count
    final_logs = system_logger.get_logs(limit=100)
    final_count = len(final_logs)
    new_logs = final_count - initial_count
    
    print(f"\n📊 Results:")
    print(f"   Initial logs: {initial_count}")
    print(f"   Final logs: {final_count}")
    print(f"   New logs created: {new_logs}")
    
    if new_logs >= 3:
        print(f"\n✅ SUCCESS: Direct logging is working!")
        print("\nRecent test logs:")
        for i, log in enumerate(final_logs[:3], 1):
            print(f"   {i}. {log['timestamp']} | {log['source']} | {log['action']} | {log['status']}")
    else:
        print(f"\n❌ ISSUE: Direct logging is not working properly.")
    
    return new_logs >= 3

if __name__ == "__main__":
    success = test_direct_logging()
    if success:
        print("\n🎉 Direct logging is working! The issue is likely that the server needs to be restarted.")
        print("\n📋 Next Steps:")
        print("1. Stop the current backend server (Ctrl+C)")
        print("2. Restart the backend server: python app.py")
        print("3. Test the API endpoints again")
    else:
        print("\n❌ Direct logging is not working. Check the database connection and system_logger.py")
