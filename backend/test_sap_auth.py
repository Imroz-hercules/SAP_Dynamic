#!/usr/bin/env python3
"""
Test different authentication methods for SAP endpoints
"""

import requests
import json
from requests.auth import HTTPBasicAuth

def test_sap_endpoint_auth():
    """Test different authentication methods for SAP endpoint"""
    
    # Test data
    test_payload = {
        "MILL_THROUGHPUT": "150.0",
        "MILL_TIME_EFFICIENCY": "33.33",
        "TOTAL_UTILIZATION": "50.0"
    }
    
    # SAP endpoint
    sap_url = "http://vhmioqs4ci.sap.mc3.com.sa:8000/zmi_kpi_mill/MKPI?sap-client=200&spnego=disabled"
    
    print("🔍 Testing SAP Authentication Methods")
    print("=" * 60)
    
    # Test 1: Basic Auth (current method)
    print("\n1️⃣ Testing Basic Authentication...")
    try:
        response = requests.post(
            sap_url,
            json=test_payload,
            auth=HTTPBasicAuth('99999', 'P@ssw0rdP@ssw0rd'),
            timeout=10,
            verify=False
        )
        print(f"   Status: {response.status_code}")
        print(f"   Response length: {len(response.text)}")
        if "Sign in to your account" in response.text:
            print("   ❌ Microsoft login page returned (authentication failed)")
        else:
            print("   ✅ Different response received")
            print(f"   Response preview: {response.text[:200]}...")
    except Exception as e:
        print(f"   ❌ Error: {e}")
    
    # Test 2: No authentication
    print("\n2️⃣ Testing No Authentication...")
    try:
        response = requests.post(
            sap_url,
            json=test_payload,
            timeout=10,
            verify=False
        )
        print(f"   Status: {response.status_code}")
        print(f"   Response length: {len(response.text)}")
        if "Sign in to your account" in response.text:
            print("   ❌ Microsoft login page returned")
        else:
            print("   ✅ Different response received")
            print(f"   Response preview: {response.text[:200]}...")
    except Exception as e:
        print(f"   ❌ Error: {e}")
    
    # Test 3: Different credentials
    print("\n3️⃣ Testing Different Credentials...")
    test_creds = [
        ('admin', 'admin'),
        ('SAP*', 'PASS'),
        ('DDIC', '19920706'),
        ('99999', 'P@ssw0rd'),
        ('99999', 'P@ssw0rdP@ssw0rd'),
    ]
    
    for username, password in test_creds:
        try:
            response = requests.post(
                sap_url,
                json=test_payload,
                auth=HTTPBasicAuth(username, password),
                timeout=5,
                verify=False
            )
            print(f"   {username}/{password}: Status {response.status_code}")
            if "Sign in to your account" not in response.text:
                print(f"   ✅ SUCCESS! Different response with {username}")
                print(f"   Response preview: {response.text[:200]}...")
                break
        except Exception as e:
            print(f"   {username}/{password}: Error - {e}")
    
    # Test 4: GET request (check if endpoint exists)
    print("\n4️⃣ Testing GET Request...")
    try:
        response = requests.get(
            sap_url,
            auth=HTTPBasicAuth('99999', 'P@ssw0rdP@ssw0rd'),
            timeout=10,
            verify=False
        )
        print(f"   Status: {response.status_code}")
        print(f"   Response length: {len(response.text)}")
        print(f"   Response preview: {response.text[:200]}...")
    except Exception as e:
        print(f"   ❌ Error: {e}")
    
    # Test 5: Check if endpoint is accessible
    print("\n5️⃣ Testing Endpoint Accessibility...")
    base_url = "http://vhmioqs4ci.sap.mc3.com.sa:8000"
    try:
        response = requests.get(
            base_url,
            timeout=5,
            verify=False
        )
        print(f"   Base URL Status: {response.status_code}")
        print(f"   Response preview: {response.text[:200]}...")
    except Exception as e:
        print(f"   ❌ Base URL Error: {e}")

if __name__ == "__main__":
    test_sap_endpoint_auth()
    print("\n" + "=" * 60)
    print("💡 Next Steps:")
    print("1. Contact SAP administrator for correct authentication method")
    print("2. Verify if endpoint requires SAML/SSO authentication")
    print("3. Check if different credentials are needed")
    print("4. Confirm if endpoint URL is correct")
