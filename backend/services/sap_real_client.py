# services/sap_real_client.py
import os
import requests
import logging
from typing import List, Dict, Optional
from datetime import datetime
from requests.auth import HTTPBasicAuth
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry

# Import configuration
try:
    from config.sap_config import SAP_CONFIG, get_sap_url, get_sap_auth
except ImportError:
    # A8: this fallback carried the production host, username and password as
    # literal defaults - a second copy of the credentials, reached only if
    # config.sap_config fails to import. It now goes through runtime_config
    # like everything else, so there is one source and no literals here.
    from services import runtime_config as _rc

    SAP_CONFIG = {
        "base_url": _rc.sap_base_url(),
        "endpoint": _rc.sap_endpoint("orders"),
        "username": _rc.sap_username(),
        "password": _rc.sap_password(),
        "client": _rc.sap_client(),
        "timeout": _rc.sap_timeout(),
        "max_retries": int(os.getenv("SAP_MAX_RETRIES", "3")),
    }

    def get_sap_url():
        return f"{_rc.sap_base_url()}{_rc.sap_endpoint('orders')}"

    def get_sap_auth():
        return _rc.sap_auth()

log = logging.getLogger(__name__)

class SAPRealClient:
    """
    Real SAP client to fetch process orders from the provided SAP API endpoint.
    """
    
    def __init__(self):
        # A8: SAP_CONFIG is now a live view over runtime_config, so reading it
        # here resolves current values rather than import-time ones. Kept as
        # attributes because the rest of this class uses them that way; a
        # long-lived instance should be re-created after a settings change.
        self.base_url = SAP_CONFIG['base_url']
        self.endpoint = SAP_CONFIG['endpoint']
        self.username, self.password = get_sap_auth()
        self.client = SAP_CONFIG['client']
        self.timeout = SAP_CONFIG['timeout']
        
        # Setup session with retry strategy
        self.session = requests.Session()
        retry_strategy = Retry(
            total=SAP_CONFIG['max_retries'],
            backoff_factor=1,
            status_forcelist=[429, 500, 502, 503, 504],
        )
        adapter = HTTPAdapter(max_retries=retry_strategy)
        self.session.mount("http://", adapter)
        self.session.mount("https://", adapter)
        
        # Set basic auth
        self.session.auth = HTTPBasicAuth(self.username, self.password)
        
        # Set headers
        self.session.headers.update({
            'Content-Type': 'application/json',
            'Accept': 'application/json',
            'User-Agent': 'Hercules-SFMS/1.0'
        })

    def get_process_orders(self, client: str = None) -> List[Dict]:
        """
        Fetch process orders from SAP API.
        
        Args:
            client: SAP client code (default: "200")
            
        Returns:
            List of process orders in the format expected by the application
            
        Raises:
            Exception: If API call fails or returns invalid data
        """
        try:
            if client is None:
                client = self.client
            url = f"{self.base_url}{self.endpoint}"
            params = {"client": client}
            
            log.info(f"Fetching process orders from SAP API: {url}")
            
            response = self.session.get(url, params=params, timeout=self.timeout)
            response.raise_for_status()
            
            # Parse JSON response
            data = response.json()
            
            if not isinstance(data, list):
                raise ValueError(f"Expected array response, got: {type(data)}")
            
            log.info(f"Successfully fetched {len(data)} process orders from SAP")
            
            # Transform SAP data to our internal format
            transformed_orders = []
            for order in data:
                try:
                    transformed_order = self._transform_sap_order(order)
                    transformed_orders.append(transformed_order)
                except Exception as e:
                    log.error(f"Failed to transform order {order.get('PROCESS_ORDER', 'unknown')}: {e}")
                    continue
            
            return transformed_orders
            
        except requests.exceptions.RequestException as e:
            log.error(f"SAP API request failed: {e}")
            raise Exception(f"Failed to connect to SAP API: {str(e)}")
        except ValueError as e:
            log.error(f"SAP API returned invalid data: {e}")
            raise Exception(f"Invalid response from SAP API: {str(e)}")
        except Exception as e:
            log.error(f"Unexpected error fetching from SAP: {e}")
            raise Exception(f"Unexpected error: {str(e)}")

    def _transform_sap_order(self, sap_order: Dict) -> Dict:
        """
        Transform SAP order format to our internal format.
        
        SAP Format:
        {
            "PROCESS_ORDER": "000013006740",
            "MATERIAL": "000000000001400001", 
            "TOTAL_QTY": 100.000,
            "UOM": "BAG",
            "PRIORITY_ID": "1",
            "CONFIRMED_QTY": 0,
            "PLANT": "3130",
            "CREATED_ON": "2025-09-04",
            "VERSION": "BKL1",
            "MATERIAL_DESC": "MMC BAKERIES FLOUR 80% - 45 KG"
        }
        
        Returns:
            Transformed order in our internal format
        """
        # Parse CREATED_ON date (YYYYMMDD format)
        created_on = None
        if sap_order.get("CREATED_ON"):
            try:
                # Handle both YYYYMMDD and YYYY-MM-DD formats
                date_str = sap_order["CREATED_ON"]
                if len(date_str) == 8 and date_str.isdigit():
                    # YYYYMMDD format
                    created_on = datetime.strptime(date_str, "%Y%m%d")
                else:
                    # YYYY-MM-DD format
                    created_on = datetime.strptime(date_str, "%Y-%m-%d")
            except ValueError as e:
                log.warning(f"Invalid date format for CREATED_ON: {sap_order.get('CREATED_ON')}")
                created_on = datetime.now()
        
        # Generate batch number if not provided
        batch = f"BATCH-{sap_order.get('PROCESS_ORDER', 'UNKNOWN')}-{datetime.now().strftime('%Y%m%d')}"
        
        return {
            "po_number": sap_order.get("PROCESS_ORDER", "").strip(),
            "material": sap_order.get("MATERIAL", "").strip(),
            "version": sap_order.get("VERSION", "v1.0").strip(),
            "batch": batch,
            "quantity": float(sap_order.get("TOTAL_QTY", 0)),
            "unit": sap_order.get("UOM", "KG").strip(),
            "status": "Open",  # Default status for new orders from SAP (sync may set CNF from STATUS)
            "priority": int(sap_order.get("PRIORITY_ID", "0")),
            "plant": sap_order.get("PLANT", "").strip(),
            "confirmed_qty": float(sap_order.get("CONFIRMED_QTY", 0)),
            "material_desc": sap_order.get("MATERIAL_DESC", "").strip(),
            "created_at": created_on.isoformat() if created_on else datetime.now().isoformat(),
            "STATUS": (sap_order.get("STATUS") or "").strip(),  # SAP status (e.g. CNF); sync stores in status column
        }

    def test_connection(self) -> bool:
        """
        Test connection to SAP API.
        
        Returns:
            True if connection is successful, False otherwise
        """
        try:
            # Try to fetch a small number of orders to test connection
            orders = self.get_process_orders()
            log.info(f"SAP connection test successful. Retrieved {len(orders)} orders.")
            return True
        except Exception as e:
            log.error(f"SAP connection test failed: {e}")
            return False

    def get_po(self, po_number: str) -> Dict:
        """Get specific PO details (placeholder for future implementation)."""
        # This would need to be implemented based on SAP API capabilities
        return {
            "po_number": po_number, 
            "vendor": "SAP-VENDOR", 
            "currency": "SAR",
            "TOTAL_QTY": 160.0,
            "UOM": "TON",
            "MATERIAL_DESC": "Gluten-Free Flour - Grade A",
            "VERSION": "BKF3",
            "CREATED_ON": "20240903"  # Format: YYYYMMDD
        }

    def get_po_items(self, po_number: str) -> List[Dict]:
        """Get PO items (placeholder for future implementation)."""
        # This would need to be implemented based on SAP API capabilities
        return [
            {"material_code": "SAP-MATERIAL", "ordered_qty": 0, "uom": "KG"},
        ]

    def confirm_order(
        self,
        po_number: str,
        status: str,
        confirmation_time: str,
        remarks: str | None = None,
        payload: Dict | None = None
    ) -> Dict:
        """Confirm order (placeholder for future implementation)."""
        # This would need to be implemented based on SAP API capabilities
        return {
            "ok": True,
            "echo": {
                "po_number": po_number,
                "status": status,
                "confirmation_time": confirmation_time,
                "remarks": remarks,
                "payload": payload or {},
            }
        }
