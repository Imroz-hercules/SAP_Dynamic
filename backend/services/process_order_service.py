#!/usr/bin/env python3
"""
Process Order Service for process order synchronization
"""

import os
import requests
import logging
from typing import Dict, Any

logger = logging.getLogger(__name__)

def _backend_port():
    """Port the Flask app runs on (must match app.py / PORT / FLASK_RUN_PORT)."""
    return os.environ.get("BACKEND_PORT", os.environ.get("PORT", os.environ.get("FLASK_RUN_PORT", "5000")))

class ProcessOrderService:
    """Service for synchronizing process orders with SAP"""
    
    def __init__(self):
        port = _backend_port()
        self.sap_base_url = f"http://127.0.0.1:{port}"
        
    def sync_process_orders_from_sap(self) -> Dict[str, Any]:
        """Sync process orders from SAP using the real SAP sync endpoint"""
        try:
            # Call the real SAP sync endpoint that the button uses
            response = requests.post(
                f"{self.sap_base_url}/api/sap-sync/seed-orders",
                headers={'Content-Type': 'application/json'},
                timeout=60  # Longer timeout for SAP API calls
            )
            
            if response.status_code == 200:
                data = response.json()
                if data.get('ok', False):
                    orders_synced = data.get('total_inserted', 0)
                    return {
                        'success': True,
                        'orders_synced': orders_synced,
                        'message': f"Successfully synced {orders_synced} process orders from SAP",
                        'details': {
                            'inserted_orders': data.get('inserted_orders', []),
                            'skipped_orders': data.get('skipped_orders', []),
                            'total_fetched': data.get('total_fetched', 0),
                            'used_fallback': data.get('used_fallback', False),
                            'sap_api_error': data.get('sap_api_error')
                        }
                    }
                else:
                    return {
                        'success': False,
                        'orders_synced': 0,
                        'message': data.get('message', 'SAP sync failed'),
                        'details': {
                            'sap_error': data.get('sap_error'),
                            'used_fallback': data.get('used_fallback', False)
                        }
                    }
            else:
                error_data = response.json() if response.headers.get('content-type', '').startswith('application/json') else {}
                return {
                    'success': False,
                    'orders_synced': 0,
                    'message': f"SAP sync failed with status {response.status_code}",
                    'details': error_data
                }
                
        except requests.exceptions.RequestException as e:
            logger.error(f"Network error during SAP process order sync: {e}")
            return {
                'success': False,
                'orders_synced': 0,
                'message': f"Network error: {str(e)}"
            }
        except Exception as e:
            logger.error(f"Unexpected error during SAP process order sync: {e}")
            return {
                'success': False,
                'orders_synced': 0,
                'message': f"Unexpected error: {str(e)}"
            }
