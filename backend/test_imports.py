#!/usr/bin/env python3
"""
Test script to verify all imports work correctly
"""

print("Testing imports...")

try:
    from services.auto_validator import _convert_to_tons
    print("✅ _convert_to_tons import successful")
except ImportError as e:
    print(f"❌ _convert_to_tons import failed: {e}")

try:
    from routes.sap_sync import sap_sync_bp
    print("✅ sap_sync_bp import successful")
except ImportError as e:
    print(f"❌ sap_sync_bp import failed: {e}")

try:
    from routes.order_validation import orders_bp
    print("✅ orders_bp import successful")
except ImportError as e:
    print(f"❌ orders_bp import failed: {e}")

print("Import test completed!")
