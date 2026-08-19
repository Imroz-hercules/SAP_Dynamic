#!/usr/bin/env python3
"""
Script to help restart the server and test the logging integration
"""
import subprocess
import time
import requests
import sys
import os

def restart_server():
    """Restart the Flask server"""
    print("🔄 Restarting the Flask server...")
    
    # Kill any existing Flask processes
    try:
        if os.name == 'nt':  # Windows
            subprocess.run(['taskkill', '/f', '/im', 'python.exe'], capture_output=True)
        else:  # Unix/Linux/Mac
            subprocess.run(['pkill', '-f', 'python.*app.py'], capture_output=True)
    except:
        pass
    
    time.sleep(2)
    
    # Start the server in the background
    print("🚀 Starting Flask server...")
    if os.name == 'nt':  # Windows
        subprocess.Popen([sys.executable, 'app.py'], 
                        creationflags=subprocess.CREATE_NEW_CONSOLE)
    else:  # Unix/Linux/Mac
        subprocess.Popen([sys.executable, 'app.py'], 
                        stdout=subprocess.DEVNULL, 
                        stderr=subprocess.DEVNULL)
    
    # Wait for server to start
    print("⏳ Waiting for server to start...")
    time.sleep(5)
    
    return True

def test_server_health():
    """Test if the server is running and healthy"""
    try:
        response = requests.get('http://localhost:5000/', timeout=5)
        if response.status_code == 200:
            print("✅ Server is running and healthy")
            return True
        else:
            print(f"❌ Server returned status {response.status_code}")
            return False
    except requests.exceptions.RequestException as e:
        print(f"❌ Server is not responding: {e}")
        return False

def test_logging_endpoints():
    """Test the logging endpoints"""
    print("\n🧪 Testing logging endpoints...")
    
    # Test 1: Get logs
    try:
        response = requests.get('http://localhost:5000/api/system-logs/')
        if response.status_code == 200:
            data = response.json()
            print(f"✅ GET /api/system-logs/ - {len(data.get('logs', []))} logs found")
        else:
            print(f"❌ GET /api/system-logs/ - Status {response.status_code}")
    except Exception as e:
        print(f"❌ GET /api/system-logs/ - Error: {e}")
    
    # Test 2: Manual sync
    try:
        response = requests.post('http://localhost:5000/api/system-logs/manual-sync', 
                               json={'operator': 'Test User'})
        if response.status_code == 200:
            data = response.json()
            print(f"✅ POST /api/system-logs/manual-sync - {data.get('message', 'Success')}")
        else:
            print(f"❌ POST /api/system-logs/manual-sync - Status {response.status_code}")
    except Exception as e:
        print(f"❌ POST /api/system-logs/manual-sync - Error: {e}")
    
    # Test 3: SAP sync
    try:
        response = requests.post('http://localhost:5000/api/sap-sync/seed-orders', json={})
        if response.status_code == 200:
            data = response.json()
            print(f"✅ POST /api/sap-sync/seed-orders - {data.get('message', 'Success')}")
        else:
            print(f"❌ POST /api/sap-sync/seed-orders - Status {response.status_code}")
    except Exception as e:
        print(f"❌ POST /api/sap-sync/seed-orders - Error: {e}")

def main():
    print("🔧 Server Restart and Testing Tool")
    print("=" * 40)
    
    # Check if server is already running
    if test_server_health():
        print("Server is already running. Testing endpoints...")
        test_logging_endpoints()
    else:
        print("Server is not running. Restarting...")
        if restart_server():
            if test_server_health():
                test_logging_endpoints()
            else:
                print("❌ Failed to start server")
        else:
            print("❌ Failed to restart server")
    
    print("\n📋 Manual Steps:")
    print("1. If the server is not running, start it manually:")
    print("   python app.py")
    print("2. Open the frontend and test the Logs page")
    print("3. Use the 'Test Log' button to create test entries")
    print("4. Check that logs appear in real-time")

if __name__ == "__main__":
    main()
