#!/usr/bin/env python3
"""
SAP Sync Service for raw data synchronization
"""

import os
import requests
import logging
from typing import Dict, Any

logger = logging.getLogger(__name__)

def _backend_port():
    """Port the Flask app runs on (must match app.py / PORT / FLASK_RUN_PORT)."""
    return os.environ.get("BACKEND_PORT", os.environ.get("PORT", os.environ.get("FLASK_RUN_PORT", "5000")))


class SAPSyncService:
    """Service for synchronizing raw data with SAP"""
    
    def __init__(self):
        # This service calls the app's OWN API, not SAP. The port was hardcoded
        # to 5000, so the scheduled sync failed silently on any other port.
        # services/process_order_service.py already had this helper.
        self.sap_base_url = f"http://127.0.0.1:{_backend_port()}"
        
    def send_raw_data_to_sap(self) -> Dict[str, Any]:
        """Send raw data from ASMReporting_5 to SAP"""
        try:
            # Call the existing SAP sync endpoint
            response = requests.post(
                f"{self.sap_base_url}/api/sap-sync/send-raw-data",
                timeout=30
            )
            
            if response.status_code == 200:
                data = response.json()
                records_sent = data.get('records_sent', 0)
                success = data.get('ok', False) or data.get('success', False)
                
                return {
                    'success': success,
                    'records_sent': records_sent,
                    'message': data.get('message', f"Raw data sync completed - {records_sent} records sent")
                }
            else:
                return {
                    'success': False,
                    'records_sent': 0,
                    'message': f"SAP sync failed with status {response.status_code}"
                }
                
        except requests.exceptions.RequestException as e:
            logger.error(f"Network error during SAP sync: {e}")
            return {
                'success': False,
                'records_sent': 0,
                'message': f"Network error: {str(e)}"
            }
        except Exception as e:
            logger.error(f"Unexpected error during SAP sync: {e}")
            return {
                'success': False,
                'records_sent': 0,
                'message': f"Unexpected error: {str(e)}"
            }
