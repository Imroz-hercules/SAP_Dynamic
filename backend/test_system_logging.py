# backend/test_system_logging.py
"""
Test script to demonstrate the comprehensive system logging functionality.
This script simulates various sync operations and shows how they are logged.
"""

import sys
import os
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from services.system_logger import (
    system_logger, 
    log_sap_event, 
    log_hercules_event, 
    log_scada_event, 
    log_operator_action
)
from datetime import datetime, timedelta
import time

def test_comprehensive_logging():
    """Test all types of logging operations."""
    
    print("🧪 Testing Comprehensive System Logging")
    print("=" * 50)
    
    # Test 1: SAP Order Sync Events
    print("\n1. Testing SAP Order Sync Events...")
    
    # Simulate order sync start
    log_id1 = log_sap_event(
        action="Order Sync Started",
        status="InProgress",
        details="Fetching process orders from SAP API",
        metadata={"api_endpoint": "/zmi_get_orders/GETORD", "client": "250"}
    )
    print(f"   ✅ Logged order sync start: ID {log_id1}")
    
    time.sleep(1)  # Simulate processing time
    
    # Simulate order sync success
    log_sap_event(
        action="Order Sync Completed",
        status="Success",
        details="Successfully synced 15 orders from SAP",
        metadata={
            "orders_fetched": 15,
            "orders_inserted": 12,
            "orders_skipped": 3,
            "duration_seconds": 1.2
        }
    )
    print("   ✅ Logged order sync success")
    
    # Test 2: Confirmation Push Events
    print("\n2. Testing Confirmation Push Events...")
    
    # Simulate online confirmation
    log_sap_event(
        action="Online Confirmation Started",
        status="InProgress",
        details="Starting online confirmation for 8 orders",
        metadata={"order_count": 8, "endpoint": "/zmi_conf_online/CONF"}
    )
    
    time.sleep(0.5)
    
    log_sap_event(
        action="Online Confirmation Completed",
        status="Success",
        details="Successfully sent 8 orders for online confirmation",
        metadata={
            "order_count": 8,
            "successful_count": 8,
            "failed_count": 0
        }
    )
    print("   ✅ Logged online confirmation")
    
    # Simulate offline confirmation
    log_sap_event(
        action="Offline Confirmation Started",
        status="InProgress",
        details="Starting offline confirmation for 3 orders",
        metadata={"order_count": 3, "endpoint": "/zmi_conf_offlin/CONFOFF"}
    )
    
    time.sleep(0.3)
    
    log_sap_event(
        action="Offline Confirmation Completed",
        status="Success",
        details="Successfully sent 3 orders for offline confirmation",
        metadata={
            "order_count": 3,
            "successful_count": 3,
            "failed_count": 0
        }
    )
    print("   ✅ Logged offline confirmation")
    
    # Test 3: Hercules System Events
    print("\n3. Testing Hercules System Events...")
    
    # Simulate push confirmation
    log_hercules_event(
        action="Push Confirmation Started",
        status="InProgress",
        details="Starting push confirmation for validated orders",
        operator="Operator A",
        metadata={
            "order_ids": [1, 2, 3, 4, 5],
            "status_filter": "Validated",
            "triggered_by": "api"
        }
    )
    
    time.sleep(0.8)
    
    log_hercules_event(
        action="Push Confirmation Completed",
        status="Success",
        details="Push confirmation completed for 5 orders (3 auto, 2 manual)",
        operator="Operator A",
        metadata={
            "total_orders": 5,
            "auto_orders_count": 3,
            "manual_orders_count": 2,
            "successful_count": 5,
            "failed_count": 0
        }
    )
    print("   ✅ Logged push confirmation")
    
    # Simulate raw data sync
    log_hercules_event(
        action="Raw Data Sync Started",
        status="InProgress",
        details="Fetching data from ASMReporting_5 and sending to SAP"
    )
    
    time.sleep(1.5)
    
    log_hercules_event(
        action="Raw Data Sync Completed",
        status="Success",
        details="Successfully sent 20 latest records from ASMReporting_5 to SAP",
        metadata={
            "records_fetched": 20,
            "records_sent": 20
        }
    )
    print("   ✅ Logged raw data sync")
    
    # Test 4: SCADA Events
    print("\n4. Testing SCADA Events...")
    
    # Simulate SCADA data sync
    log_scada_event(
        action="SCADA Data Sync Started",
        status="InProgress",
        details="Reading latest SCADA data from SQL Server"
    )
    
    time.sleep(0.2)
    
    log_scada_event(
        action="SCADA Data Sync Completed",
        status="Success",
        details="Successfully synced SCADA data with 14 values",
        metadata={
            "scada_keys_count": 14,
            "triggered_by": "scheduler",
            "source_table": "[HerculesV2].[dbo].[ASMReporting_5]"
        }
    )
    print("   ✅ Logged SCADA data sync")
    
    # Test 5: Operator Actions
    print("\n5. Testing Operator Actions...")
    
    # Simulate manual sync trigger
    log_operator_action(
        operator="Operator A",
        action="Manual Sync Triggered",
        status="InProgress",
        metadata={"triggered_by": "ui", "timestamp": datetime.now().isoformat()}
    )
    
    time.sleep(0.5)
    
    log_operator_action(
        operator="Operator A",
        action="Manual Sync Completed",
        status="Success",
        metadata={"sync_duration": 0.5}
    )
    print("   ✅ Logged manual sync")
    
    # Simulate shift end
    log_operator_action(
        operator="Operator A",
        action="Shift End Sync to SAP",
        status="InProgress",
        metadata={"shift": "Day Shift", "end_time": datetime.now().isoformat()}
    )
    
    time.sleep(1.0)
    
    log_operator_action(
        operator="Operator A",
        action="Shift End Sync Completed",
        status="Success",
        metadata={
            "shift": "Day Shift",
            "orders_processed": 25,
            "confirmations_sent": 20
        }
    )
    print("   ✅ Logged shift end")
    
    # Test 6: Error Scenarios
    print("\n6. Testing Error Scenarios...")
    
    # Simulate SAP connection error
    log_sap_event(
        action="Order Sync Failed",
        status="Error",
        details="SAP API connection timeout after 30 seconds",
        error_code="SAP_CONNECTION_TIMEOUT",
        metadata={
            "timeout_seconds": 30,
            "retry_count": 3,
            "last_error": "Connection timeout"
        }
    )
    print("   ✅ Logged SAP connection error")
    
    # Simulate confirmation failure
    log_sap_event(
        action="Online Confirmation Failed",
        status="Error",
        details="SAP online confirmation error: Invalid CSRF token",
        error_code="CONFIRMATION_ERROR",
        metadata={
            "order_count": 5,
            "successful_count": 0,
            "failed_count": 5,
            "error": "Invalid CSRF token"
        }
    )
    print("   ✅ Logged confirmation error")
    
    # Test 7: Scheduled Operations
    print("\n7. Testing Scheduled Operations...")
    
    # Simulate scheduled sync
    log_sap_event(
        action="Scheduled Order Sync Started",
        status="InProgress",
        details="Automatic scheduled sync of process orders from SAP"
    )
    
    time.sleep(0.3)
    
    log_sap_event(
        action="Scheduled Order Sync Completed",
        status="Success",
        details="Successfully pulled 7 orders from SAP",
        metadata={
            "orders_pulled": 7,
            "triggered_by": "scheduler"
        }
    )
    print("   ✅ Logged scheduled sync")
    
    print("\n" + "=" * 50)
    print("🎉 All logging tests completed successfully!")
    print("\nTo view the logs, you can:")
    print("1. Check the system_logs table in PostgreSQL")
    print("2. Use the API endpoint: GET /api/system-logs/")
    print("3. Use the frontend Logs page")
    print("4. Filter by source, status, or operator")

def test_shift_logging():
    """Test shift-specific logging."""
    print("\n🕐 Testing Shift-Specific Logging")
    print("=" * 30)
    
    # Create logs for different times to simulate shift activities
    now = datetime.now()
    
    # Morning shift (06:00-14:00)
    morning_time = now.replace(hour=8, minute=30, second=0, microsecond=0)
    
    # Simulate morning shift activities
    log_operator_action(
        operator="Operator A",
        action="Morning Shift Started",
        status="Success",
        metadata={"shift": "Morning", "start_time": morning_time.isoformat()}
    )
    
    log_sap_event(
        action="Morning Order Sync",
        status="Success",
        details="Synced 12 orders for morning shift",
        metadata={"shift": "Morning", "orders_count": 12}
    )
    
    # Afternoon shift (14:00-22:00)
    afternoon_time = now.replace(hour=16, minute=45, second=0, microsecond=0)
    
    log_operator_action(
        operator="Operator B",
        action="Afternoon Shift Started",
        status="Success",
        metadata={"shift": "Afternoon", "start_time": afternoon_time.isoformat()}
    )
    
    log_hercules_event(
        action="Afternoon Data Push",
        status="Success",
        details="Pushed afternoon production data to SAP",
        operator="Operator B",
        metadata={"shift": "Afternoon", "records_count": 18}
    )
    
    # Night shift (22:00-06:00)
    night_time = now.replace(hour=23, minute=15, second=0, microsecond=0)
    
    log_operator_action(
        operator="Operator C",
        action="Night Shift Started",
        status="Success",
        metadata={"shift": "Night", "start_time": night_time.isoformat()}
    )
    
    log_scada_event(
        action="Night SCADA Sync",
        status="Success",
        details="Synced night shift SCADA data",
        metadata={"shift": "Night", "data_points": 22}
    )
    
    print("✅ Created logs for all three shifts")
    print("   - Morning Shift (06:00-14:00)")
    print("   - Afternoon Shift (14:00-22:00)")
    print("   - Night Shift (22:00-06:00)")

if __name__ == "__main__":
    try:
        test_comprehensive_logging()
        test_shift_logging()
        
        print("\n📊 Log Statistics:")
        logs = system_logger.get_logs(limit=100)
        print(f"   Total logs created: {len(logs)}")
        
        # Group by source
        sources = {}
        for log in logs:
            source = log['source']
            sources[source] = sources.get(source, 0) + 1
        
        print("   Logs by source:")
        for source, count in sources.items():
            print(f"     - {source}: {count}")
        
        # Group by status
        statuses = {}
        for log in logs:
            status = log['status']
            statuses[status] = statuses.get(status, 0) + 1
        
        print("   Logs by status:")
        for status, count in statuses.items():
            print(f"     - {status}: {count}")
            
    except Exception as e:
        print(f"❌ Test failed: {e}")
        import traceback
        traceback.print_exc()
