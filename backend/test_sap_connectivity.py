#!/usr/bin/env python3
"""
Test script to verify SAP connectivity and endpoints.
Run this script to check if the SAP server is accessible.
"""

import requests
import sys
from requests.auth import HTTPBasicAuth

def test_sap_connectivity():
    """Test SAP server connectivity and endpoints."""
    
    # SAP Configuration
    base_url = "http://vhmioqs4ci.sap.mc3.com.sa:8000"
    username = "99999"
    password = "P@ssw0rdP@ssw0rd"
    client = "200"
    timeout = 30
    
    print("🔍 Testing SAP Connectivity...")
    print(f"Server: {base_url}")
    print(f"Username: {username}")
    print(f"Client: {client}")
    print("-" * 50)
    
    # Test 1: Basic connectivity
    print("1. Testing basic connectivity...")
    try:
        response = requests.get(f"{base_url}?sap-client={client}", 
                              auth=HTTPBasicAuth(username, password), 
                              timeout=timeout)
        print(f"   ✅ Basic connectivity: {response.status_code}")
    except requests.exceptions.ConnectionError:
        print("   ❌ Connection failed: Cannot reach SAP server")
        return False
    except requests.exceptions.Timeout:
        print("   ❌ Connection timeout: SAP server not responding")
        return False
    except Exception as e:
        print(f"   ❌ Connection error: {e}")
        return False
    
    # Test 2: Online confirmation endpoint
    print("2. Testing online confirmation endpoint...")
    try:
        url = f"{base_url}/zmi_conf_online/CONF?sap-client={client}"
        headers = {
            'x-csrf-token': 'fetch',
            'Accept': 'application/json',
            'Content-Type': 'application/json'
        }
        response = requests.get(url, 
                              headers=headers,
                              auth=HTTPBasicAuth(username, password), 
                              timeout=timeout)
        print(f"   Status: {response.status_code}")
        if response.status_code == 200:
            csrf_token = response.headers.get('x-csrf-token')
            if csrf_token:
                print(f"   ✅ CSRF token retrieved: {csrf_token[:10]}...")
            else:
                print("   ⚠️  No CSRF token in response headers")
                print(f"   Available headers: {list(response.headers.keys())}")
        else:
            print(f"   ❌ HTTP Error: {response.status_code}")
            print(f"   Response: {response.text[:200]}")
    except Exception as e:
        print(f"   ❌ Error: {e}")
    
    # Test 3: Offline confirmation endpoint
    print("3. Testing offline confirmation endpoint...")
    try:
        url = f"{base_url}/zmi_conf_offlin/CONFOFF?sap-client={client}"
        headers = {
            'x-csrf-token': 'fetch',
            'Accept': 'application/json',
            'Content-Type': 'application/json'
        }
        response = requests.get(url, 
                              headers=headers,
                              auth=HTTPBasicAuth(username, password), 
                              timeout=timeout)
        print(f"   Status: {response.status_code}")
        if response.status_code == 200:
            csrf_token = response.headers.get('x-csrf-token')
            if csrf_token:
                print(f"   ✅ CSRF token retrieved: {csrf_token[:10]}...")
            else:
                print("   ⚠️  No CSRF token in response headers")
                print(f"   Available headers: {list(response.headers.keys())}")
        else:
            print(f"   ❌ HTTP Error: {response.status_code}")
            print(f"   Response: {response.text[:200]}")
    except Exception as e:
        print(f"   ❌ Error: {e}")
    
    print("-" * 50)
    print("✅ SAP connectivity test completed!")
    return True

if __name__ == "__main__":
    test_sap_connectivity()
