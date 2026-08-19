#!/usr/bin/env python3
"""
KPI Service for KPI data synchronization
"""

import requests
import logging
from typing import Dict, Any

logger = logging.getLogger(__name__)

class KPIService:
    """Service for synchronizing KPI data with SAP"""
    
    def __init__(self):
        self.sap_base_url = "http://localhost:5000"  # Your SAP API base URL
        
    def send_all_kpis_to_sap(self) -> Dict[str, Any]:
        """Send all KPIs (milling and packing) to SAP"""
        try:
            # Call the existing KPI sync endpoint
            response = requests.post(
                f"{self.sap_base_url}/api/kpi/send-all-to-sap",
                timeout=30
            )
            
            if response.status_code == 200:
                data = response.json()
                kpis_sent = 0
                total_records = 0
                successful_records = 0
                failed_records = 0
                
                # Count KPIs sent based on new response format
                if data.get('success') == True:
                    # Check results for milling and packing
                    results = data.get('results', {})
                    milling_success = results.get('milling', {}).get('success', False)
                    packing_success = results.get('packing', {}).get('success', False)
                    
                    if milling_success and packing_success:
                        kpis_sent = 2  # Both milling and packing KPIs sent
                        total_records = 2
                        successful_records = 2
                        failed_records = 0
                    elif milling_success or packing_success:
                        kpis_sent = 1  # At least one KPI sent
                        total_records = 2
                        successful_records = 1
                        failed_records = 1
                    else:
                        kpis_sent = 0  # No KPIs sent
                        total_records = 2
                        successful_records = 0
                        failed_records = 2
                
                return {
                    'success': data.get('success', False),
                    'kpis_sent': kpis_sent,
                    'total_records': total_records,
                    'successful_records': successful_records,
                    'failed_records': failed_records,
                    'message': data.get('message', f"KPI sync completed - {kpis_sent} sets sent")
                }
            else:
                return {
                    'success': False,
                    'kpis_sent': 0,
                    'total_records': 0,
                    'successful_records': 0,
                    'failed_records': 0,
                    'message': f"KPI sync failed with status {response.status_code}"
                }
                
        except requests.exceptions.RequestException as e:
            logger.error(f"Network error during KPI sync: {e}")
            return {
                'success': False,
                'kpis_sent': 0,
                'total_records': 0,
                'successful_records': 0,
                'failed_records': 0,
                'message': f"Network error: {str(e)}"
            }
        except Exception as e:
            logger.error(f"Unexpected error during KPI sync: {e}")
            return {
                'success': False,
                'kpis_sent': 0,
                'total_records': 0,
                'successful_records': 0,
                'failed_records': 0,
                'message': f"Unexpected error: {str(e)}"
            }
