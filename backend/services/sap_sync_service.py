#!/usr/bin/env python3
"""
SAP Sync Service for raw data synchronization
"""

import requests
import logging
from typing import Dict, Any

logger = logging.getLogger(__name__)

class SAPSyncService:
    """Service for synchronizing raw data with SAP"""
    
    def __init__(self):
        self.sap_base_url = "http://localhost:5000"  # Your SAP API base URL
        
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
