#!/usr/bin/env python3
"""
Test partial confirmation functionality
"""

import requests
import json

def test_partial_confirmation():
    """Test partial confirmation with a sample order."""
    
    # Test data - simulate confirming only 10 bags out of 100 bags
    test_payload = {
        "status": "Validated",
        "remarks": "Partial confirmation test - 10 bags confirmed out of 100",
        "confirmed_text": "Partial: 10/100 bags",
        "scrap": 0,
        "confirmed_qty": 10  # This is the key - partial quantity
    }
    
    # You'll need to replace this with an actual order ID from your database
    test_order_id = 867  # Replace with actual order ID
    
    print("Testing partial confirmation functionality...")
    print(f"Order ID: {test_order_id}")
    print(f"Payload: {json.dumps(test_payload, indent=2)}")
    
    try:
        # Send validation request
        response = requests.post(
            f'http://localhost:5000/api/process_orders/{test_order_id}/validate',
            json=test_payload,
            headers={'Content-Type': 'application/json'},
            timeout=10
        )
        
        print(f'\nResponse Status: {response.status_code}')
        
        if response.status_code == 200:
            result = response.json()
            print('✅ Partial confirmation successful!')
            print(f'Message: {result.get("message", "No message")}')
            print(f'Is Partial: {result.get("is_partial_confirmation", False)}')
            
            if result.get("partial_info"):
                partial_info = result["partial_info"]
                print(f'Partial Info:')
                print(f'  - Confirmed Qty: {partial_info["confirmed_qty"]} {partial_info["unit"]}')
                print(f'  - Total Qty: {partial_info["total_qty"]} {partial_info["unit"]}')
                print(f'  - Completion: {partial_info["completion_percentage"]}%')
            
            # Now test push confirmation
            print('\n' + '='*50)
            print('Testing push confirmation for partial order...')
            
            push_payload = {
                "order_ids": [test_order_id],
                "operator": "Partial Test"
            }
            
            push_response = requests.post(
                'http://localhost:5000/api/process_orders/push-confirmation',
                json=push_payload,
                headers={'Content-Type': 'application/json'},
                timeout=30
            )
            
            print(f'Push Response Status: {push_response.status_code}')
            
            if push_response.status_code == 200:
                push_result = push_response.json()
                print('✅ Push confirmation successful!')
                print(f'Message: {push_result.get("message", "No message")}')
                print(f'Successful Count: {push_result.get("successful_count", 0)}')
                print(f'Failed Count: {push_result.get("failed_count", 0)}')
                
                if push_result.get("results"):
                    for result in push_result["results"]:
                        print(f'Order: {result.get("process_order")} - Status: {result.get("status")}')
                        print(f'  Confirmed Weight: {result.get("confirmed_weight")} {result.get("uom")}')
                        print(f'  Message: {result.get("message")}')
            else:
                print(f'❌ Push confirmation failed: {push_response.text}')
                
        else:
            print(f'❌ Validation failed: {response.text}')
            
    except requests.exceptions.ConnectionError:
        print('❌ Connection error - Flask app might not be running')
    except Exception as e:
        print(f'❌ Error: {e}')

def test_full_confirmation():
    """Test full confirmation for comparison."""
    
    # Test data - full confirmation
    test_payload = {
        "status": "Validated",
        "remarks": "Full confirmation test",
        "confirmed_text": "Full confirmation",
        "scrap": 0
        # No confirmed_qty - should use full quantity
    }
    
    test_order_id = 867  # Replace with actual order ID
    
    print("\n" + "="*50)
    print("Testing full confirmation for comparison...")
    print(f"Order ID: {test_order_id}")
    print(f"Payload: {json.dumps(test_payload, indent=2)}")
    
    try:
        response = requests.post(
            f'http://localhost:5000/api/process_orders/{test_order_id}/validate',
            json=test_payload,
            headers={'Content-Type': 'application/json'},
            timeout=10
        )
        
        print(f'\nResponse Status: {response.status_code}')
        
        if response.status_code == 200:
            result = response.json()
            print('✅ Full confirmation successful!')
            print(f'Message: {result.get("message", "No message")}')
            print(f'Is Partial: {result.get("is_partial_confirmation", False)}')
        else:
            print(f'❌ Full confirmation failed: {response.text}')
            
    except Exception as e:
        print(f'❌ Error: {e}')

if __name__ == "__main__":
    print("🧪 Testing Partial Confirmation Functionality")
    print("="*60)
    
    # Test partial confirmation
    test_partial_confirmation()
    
    # Test full confirmation for comparison
    test_full_confirmation()
    
    print("\n" + "="*60)
    print("✅ Test completed!")
    print("\nTo use partial confirmation in Postman:")
    print("1. POST to /api/process_orders/{order_id}/validate")
    print("2. Include 'confirmed_qty' field with partial quantity")
    print("3. Example: {'status': 'Validated', 'confirmed_qty': 10}")
    print("4. Then push confirmation to SAP as usual")
