# services/sap_confirmation.py
import os
import requests
import logging
import csv
import json
from io import StringIO
from typing import List, Dict, Any, Optional
from datetime import datetime
from requests.auth import HTTPBasicAuth
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry
from services.system_logger import system_logger, log_sap_event, log_hercules_event
from services.error_logger import log_order_error
from database import PostgresSessionLocal
from sqlalchemy import text, func
from utils.shifts import get_current_shift
from utils.sap_logger import log_sap_request, log_sap_response  # New Logger

log = logging.getLogger(__name__)

class SAPConfirmationService:
    """
    SAP Confirmation Service for online and offline confirmation APIs.
    Handles CSRF token retrieval and confirmation submission.
    """
    
    def __init__(self):
        # A8: read through runtime_config rather than os.getenv, so a change on
        # the Engineering page reaches this instance. Note that
        # sap_confirmation.py:2481 keeps a module-level singleton, which froze
        # these at import - the properties below make that harmless by
        # re-resolving on each access.
        from services import runtime_config as _rc

        self._rc = _rc
        self.timeout = _rc.sap_timeout()
        
        # Setup session with retry strategy
        self.session = requests.Session()
        retry_strategy = Retry(
            total=3,
            backoff_factor=1,
            status_forcelist=[429, 500, 502, 503, 504],
        )
        adapter = HTTPAdapter(max_retries=retry_strategy)
        self.session.mount("http://", adapter)
        self.session.mount("https://", adapter)
        
        # Try different authentication methods
        self.session.auth = HTTPBasicAuth(self.username, self.password)
        
        # Add headers for better SAP compatibility
        self.session.headers.update({
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36',
            'Accept': 'application/json, text/html, */*',
            'Accept-Language': 'en-US,en;q=0.9',
            'Accept-Encoding': 'gzip, deflate',
            'Connection': 'keep-alive',
            'Cache-Control': 'no-cache'
        })
        
        # Log initial mode (will be read from database via property)
        initial_mode = self.mock_mode
        if initial_mode:
            log.info("🔧 MOCK MODE ENABLED - Using demo SAP server at http://localhost:6000/mock")
            log.info("✅ VPN checks will be skipped - orders will be sent directly to demo server")
        else:
            log.info("🔧 PRODUCTION MODE - Using real SAP server")
            log.info("⚠️ VPN checks will be performed - orders will be sent to real SAP or stored offline")
    
    # A8: these were instance attributes captured in __init__. As properties
    # they resolve at the moment of use, so the module-level singleton created
    # at the bottom of this file no longer pins them to import-time values.
    @property
    def base_url(self) -> str:
        return self._rc.sap_production_url()

    @property
    def mock_base_url(self) -> str:
        return self._rc.sap_mock_url()

    @property
    def username(self) -> str:
        return self._rc.sap_username()

    @property
    def password(self) -> str:
        return self._rc.sap_password()

    @property
    def client(self) -> str:
        return self._rc.sap_client()

    @property
    def mock_mode(self) -> bool:
        """
        Get mock SAP mode from database settings.
        Returns True if mock SAP is enabled, False for real SAP.
        This property reads from the database each time it's accessed,
        so changes in the Admin settings page take effect immediately.
        """
        try:
            from models.system_settings import is_mock_sap_enabled
            mode = is_mock_sap_enabled()
            log.debug(f"🔍 Mock SAP mode from database: {mode}")
            return mode
        except Exception as e:
            log.warning(f"⚠️ Could not read mock SAP mode from database: {e}, defaulting to True (mock mode)")
            return True  # Default to mock mode for safety
    
    def _get_url(self, endpoint: str) -> str:
        """
        Get the full URL for an endpoint, choosing between mock and production.
        
        Args:
            endpoint: The endpoint path (e.g., '/zmi_conf_online/CONF')
            
        Returns:
            Full URL string
        """
        if self.mock_mode:
            # Mock server endpoints match real SAP paths (with /mock prefix)
            return f"{self.mock_base_url}{endpoint}"
        else:
            # Production SAP URL with client parameter
            return f"{self.base_url}{endpoint}?sap-client={self.client}"
    
    def _get_csrf_token(self, endpoint: str) -> Optional[str]:
        """
        Get CSRF token from SAP endpoint using HTTPS port 44300.
        In mock mode, returns a dummy token without making a request.
        
        Args:
            endpoint: The endpoint to get token from (e.g., '/zmi_conf_online/CONF')
            
        Returns:
            CSRF token string or None if failed
        """
        # ✅ MOCK MODE: Return dummy token without making request
        if self.mock_mode:
            log.info(f"🔧 MOCK MODE: Returning dummy CSRF token for {endpoint}")
            return "demo-token"
        
        import urllib3
        urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)
        
        try:
            url = self._get_url(endpoint)
            headers = {
                'x-csrf-token': 'fetch',
                'Accept': 'application/json',
                'User-Agent': 'Python-Requests/2.31.0',
                'Connection': 'keep-alive'
            }
            
            log.info(f"Getting CSRF token from: {url}")
            response = self.session.get(
                url, 
                headers=headers, 
                timeout=self.timeout,
                verify=False  # Ignore SSL certificate errors
            )
            
            # Log detailed response information for debugging
            log.info(f"Response status: {response.status_code}")
            log.info(f"Response headers: {dict(response.headers)}")
            
            # Check for authentication issues
            if response.status_code == 401:
                log.error("SAP authentication failed - 401 Unauthorized")
                log.error(f"Response: {response.text[:200]}")
                return None
            
            if response.status_code not in [200, 201]:
                log.error(f"Failed to fetch CSRF token. Status: {response.status_code}")
                log.error(f"Response: {response.text[:200]}")
                return None
            
            # Extract CSRF token from response headers (try multiple header names)
            csrf_token = (
                response.headers.get('x-csrf-token') or 
                response.headers.get('X-CSRF-Token') or
                response.headers.get('X-Csrf-Token')
            )
            
            if csrf_token:
                log.info(f"Successfully retrieved CSRF token: {csrf_token[:30]}...")
                return csrf_token
            else:
                log.error("CSRF token not found in response headers")
                log.error(f"Available headers: {list(response.headers.keys())}")
                return None
                
        except requests.exceptions.ConnectionError as e:
            log.error(f"Connection error to SAP server: {e}")
            log.error(f"SAP server URL: {self.base_url}")
            return None
        except requests.exceptions.Timeout as e:
            log.error(f"Timeout connecting to SAP server: {e}")
            return None
        except requests.exceptions.HTTPError as e:
            log.error(f"HTTP error from SAP server: {e}")
            log.error(f"Response status: {e.response.status_code if hasattr(e, 'response') else 'Unknown'}")
            if hasattr(e, 'response') and e.response.status_code == 401:
                log.error("SAP server requires different authentication method (SPNego)")
            return None
        except requests.exceptions.RequestException as e:
            log.error(f"Failed to get CSRF token: {e}")
            return None
    
    def _format_date_time(self, dt: datetime | str) -> tuple[str, str]:
        """
        Format datetime to SAP required format.
        
        Args:
            dt: datetime object or string (ISO format or other common formats)
            
        Returns:
            Tuple of (date_string, time_string) in YYYYMMDD and HHMMSS format
        """
        # Handle string input (from database)
        if isinstance(dt, str):
            try:
                # Remove timezone info if present (Z or +00:00)
                dt_clean = dt.replace('Z', '').split('+')[0] if '+' in dt else dt.replace('Z', '')
                # Try ISO format first
                try:
                    dt = datetime.fromisoformat(dt_clean)
                except ValueError:
                    # Try common formats
                    parsed = False
                    for fmt in ['%Y-%m-%d %H:%M:%S.%f', '%Y-%m-%d %H:%M:%S', '%Y-%m-%dT%H:%M:%S.%f', '%Y-%m-%dT%H:%M:%S', '%Y-%m-%d']:
                        try:
                            dt = datetime.strptime(dt_clean, fmt)
                            parsed = True
                            break
                        except ValueError:
                            continue
                    
                    if not parsed:
                        # If all parsing fails, try dateutil (if available)
                        try:
                            from dateutil import parser
                            dt = parser.parse(dt)
                        except (ImportError, ValueError):
                            # Last resort: use current time
                            log.warning(f"⚠️ Could not parse datetime string '{dt}', using current time")
                            dt = datetime.now()
            except Exception as e:
                log.warning(f"⚠️ Error parsing datetime '{dt}': {e}, using current time")
                dt = datetime.now()
        
        # Ensure dt is a datetime object
        if not isinstance(dt, datetime):
            log.warning(f"⚠️ Invalid datetime type: {type(dt)}, using current time")
            dt = datetime.now()
        
        date_str = dt.strftime("%Y%m%d")
        time_str = dt.strftime("%H%M%S")
        return date_str, time_str
    
    def _format_process_order(self, po_number: str) -> str:
        """
        Format process order number to 12 characters as required by SAP system.
        
        Args:
            po_number: Process order number (can be any format)
            
        Returns:
            Formatted process order number (12 chars, zero-padded)
            
        Example:
            "12002902" → "000012002902"
            "000012002902" → "000012002902"
        """
        # Handle None values
        if po_number is None:
            return "0000000000"
        
        # Remove any whitespace
        po = str(po_number).strip()
        
        # Handle empty string
        if not po:
            return "0000000000"
        
        # Remove leading zeros, then pad to 12 digits
        po = po.lstrip('0') or '0'  # Handle all-zero case
        
        # Pad with leading zeros to 12 characters (SAP system)
        return po.zfill(12)
    
    def _format_material(self, material: str) -> str:
        """
        Format material code to 18 characters as required by SAP.
        
        Args:
            material: Material code
            
        Returns:
            Formatted material code (18 chars, zero-padded)
        """
        return material.zfill(18)
    
    
    def _convert_to_json_format(self, orders_data: List[Dict[str, Any]], confirmation_type: str = "online") -> List[Dict[str, Any]]:
        """
        Convert orders to SAP JSON format.
        NEW LOGIC: No chunking - always send ONE payload per order with the EXACT confirmed_weight.
        """
        if not orders_data:
            return []

        json_orders: List[Dict[str, Any]] = []

        for order in orders_data:
            confirmed_weight = float(order.get('confirmed_weight') or 0)
            total_qty = float(order.get('total_qty') or 0)

            # Skip orders with 0 confirmation weight
            if confirmed_weight <= 0:
                continue

            # ✅ CRITICAL FIX: Cap confirmed_weight to never exceed total_qty (target)
            # This ensures we never send more than the target quantity to SAP
            if total_qty > 0 and confirmed_weight > total_qty:
                print(f"⚠️ Capping confirmed_weight from {confirmed_weight:.2f} to {total_qty:.2f} (target)")
                confirmed_weight = total_qty

            # Determine if final confirmation
            is_final = (total_qty > 0 and confirmed_weight >= total_qty)

            # Always build exactly one payload
            payload = self._build_single_confirmation(
                order,
                confirmed_weight,
                is_final,
                confirmation_type.lower()
            )

            json_orders.append(payload)

        return json_orders

    def _build_single_confirmation(self, order: Dict[str, Any], confirmed_weight: float, is_final: bool, confirmation_type: str) -> Dict[str, Any]:
        """
        Build a single confirmation JSON for SAP.
        """
        # Date/time
        created_date, created_time = self._format_date_time(order.get('created_at', datetime.now()))

        # Shift
        # ✅ CRITICAL: For auto shift-end confirmations, always use the shift from the order dict
        # This is the actual shift where production occurred, not the current shift
        shift_value = order.get('shift')
        
        # ✅ Validate shift value - must be A, B, or C
        if shift_value and isinstance(shift_value, str) and shift_value.strip().upper() in ("A", "B", "C"):
            shift = shift_value.strip().upper()
            log.debug(f"Using shift from order dict: {shift} (PO: {order.get('po_number', 'unknown')})")
        elif shift_value and isinstance(shift_value, (int, float)):
            # If shift is a number, convert to letter
            shift_num = int(shift_value)
            if shift_num in (1, 2, 3):
                shift = chr(64 + shift_num)  # 1->A, 2->B, 3->C
                log.debug(f"Converted shift number {shift_num} to letter: {shift} (PO: {order.get('po_number', 'unknown')})")
            else:
                # Invalid number, fall back to current shift lookup
                log.warning(f"Invalid shift number {shift_num}, falling back to current shift lookup (PO: {order.get('po_number', 'unknown')})")
                shift = None
        else:
            # Shift not provided or invalid - fall back to current shift lookup
            log.warning(f"Shift not provided in order dict, falling back to current shift lookup (PO: {order.get('po_number', 'unknown')})")
            shift = None
        
        # ✅ Fallback: Get current shift from database only if shift was not provided
        if not shift:
            plant = order.get('plant', '')
            # Determine department based on plant (3130 = MILLING, others = PACKING)
            department = "MILLING" if plant and "3130" in str(plant) else "PACKING"
            
            shift = "A"  # Default fallback
            with PostgresSessionLocal() as db:
                shift_row = get_current_shift(plant, department, db)
                if shift_row:
                    shift = shift_row.shift_code
                    log.warning(f"Using current shift from database: {shift} (PO: {order.get('po_number', 'unknown')}) - THIS MAY BE INCORRECT FOR AUTO CONFIRMATIONS")
                else:
                    # Fallback: use shift number mapping if database lookup fails
                    shift_value_priority = order.get('priority', 1)
                    try:
                        shift_num = int(shift_value_priority) if shift_value_priority is not None else 1
                    except (ValueError, TypeError):
                        shift_num = 1
                    
                    if department == "MILLING":
                        shift = chr(64 + ((shift_num - 1) % 3) + 1)  # A, B, or C
                    else:
                        shift = chr(64 + ((shift_num - 1) % 2) + 1)  # A or B
                    log.warning(f"Using fallback shift calculation: {shift} (PO: {order.get('po_number', 'unknown')})")

        # ✅ FINAL CONFIRMATION LOGIC: Correctly determine if this is the final confirmation
        # For shift-wise confirmations, we need to check cumulative totals, not just single shift weight
        db_last = float(order.get("last_confirmed_qty", 0) or 0)
        db_total = float(order.get("total_qty", 0) or 0)
        db_is_final = bool(order.get("is_final_sent", False))
        order_is_final_confirmation = bool(order.get("is_final_confirmation", False))  # ✅ From shift_auto_confirm
        
        final_flag = ""
        
        # Rule 1: Explicit flag from shift_auto_confirm (for validated orders at shift end)
        if order_is_final_confirmation:
            final_flag = "X"
            log.debug(f"Final confirmation: is_final_confirmation flag is True (validated order at shift end)")
        
        # Rule 2: This shift weight completes the total order
        # When last_confirmed_qty + confirmed_weight >= total_qty, the order is complete
        if not final_flag and db_total > 0 and (db_last + confirmed_weight >= db_total):
            final_flag = "X"
            log.debug(f"Final confirmation: Shift weight {confirmed_weight} completes order (last={db_last}, total={db_total})")
        
        # Rule 3: Database already marked as final (safety check)
        if not final_flag and db_is_final:
            final_flag = "X"
            log.debug(f"Final confirmation: Database flag is_final_sent is True")
        
        # Rule 4: Fallback to original is_final parameter (for backward compatibility)
        if not final_flag and is_final:
            final_flag = "X"
            log.debug(f"Final confirmation: is_final parameter is True")

        data: Dict[str, Any] = {
            "PROCESS_ORDER": self._format_process_order(order.get('po_number', '')),
            "MATERIAL": self._format_material(order.get('material', '')),
            "VERSION": order.get('version', ''),
            "MATERIAL_DESC": order.get('material_desc', ''),
            "TOTAL_QTY": f"{float(order.get('total_qty', 0) or 0):.3f}",
            "CONFIRMED_WEIGHT": str(int(confirmed_weight)),
            "UOM": order.get('uom', 'TO'),
            "PLANT": order.get('plant', ''),
            "CREATED_ON": created_date,
            "CONFIRMED_AT": created_time,
            "BATCH": order.get('batch', ''),
            "STATUS": "Confirmed",
            "FINAL_CONFIRMATION": final_flag,
            "SHIFT": shift,
            "SCALE1": str(order.get('scale1', '')),
            "SCALE1_QTY": str(order.get('scale1_qty', '')),
            "SCALE2": str(order.get('scale2', '')),
            "SCALE2_QTY": str(order.get('scale2_qty', '')),
            "SCALE3": str(order.get('scale3', '')),
            "SCALE3_QTY": str(order.get('scale3_qty', '')),
        }
        
        # Only include SCRAP and CONFIRMED_TEXT for offline (manual) confirmations
        # Online (automatic end-of-shift) confirmations should NOT include these fields
        if confirmation_type == "offline":
            data["CONFIRMED_TEXT"] = order.get('confirmed_text', '')
            data["SCRAP"] = str(int(float(order.get('scrap', 0) or 0)))

        return data

    def _convert_to_table_format(self, orders_data: List[Dict[str, Any]], confirmation_type: str = "online") -> str:
        """
        Convert orders data to JSON format for SAP.
        Both online and offline confirmations now use JSON format.
        
        Args:
            orders_data: List of order dictionaries
            confirmation_type: "online" or "offline" to determine field structure
            
        Returns:
            JSON string representing the orders
        """
        # For both online and offline confirmations, return JSON format
        json_data = self._convert_to_json_format(orders_data, confirmation_type)
        return json.dumps(json_data)
    
    def confirm_online(self, orders_data: List[Dict[str, Any]]) -> Dict[str, Any]:
        """
        Send online confirmation to SAP using the same authentication pattern as KPI endpoints.
        Parses SAP response to detect individual order success/failure.
        
        Args:
            orders_data: List of order dictionaries with required fields
            
        Returns:
            Dict with confirmation results including per-order status
        """
        endpoint = "/zmi_conf_online/CONF"
        
        # Log confirmation start
        log_id = log_sap_event(
            action="Online Confirmation Started",
            status="InProgress",
            details=f"Starting online confirmation for {len(orders_data)} orders",
            metadata={"order_count": len(orders_data), "endpoint": endpoint}
        )
        
        try:
            # Convert to JSON format for online confirmation
            json_data = self._convert_to_json_format(orders_data, "online")
            log.info(f"Online JSON format data prepared: {len(json.dumps(json_data))} characters")
            log.debug(f"Online JSON data preview: {json.dumps(json_data)[:200]}...")
            
            # Get URL (mock or production)
            url = self._get_url(endpoint)
            log.info(f"Sending online confirmation to: {url}")
            log.info(f"Online JSON data: {json.dumps(json_data)}")
            
            # ✅ LOG REQUEST TO DB
            db_log_id = log_sap_request(
                endpoint=url,
                method="POST",
                payload=json_data,
                po_number=orders_data[0].get('po_number') if orders_data else None,
                log_type="online_confirmation"
            )
            
            # ============================================================
            # MOCK MODE: Simple POST request without CSRF/auth
            # ============================================================
            if self.mock_mode:
                log.info("🔧 MOCK MODE: Sending simple POST to demo server...")
                try:
                    post_response = requests.post(
                        url,
                        json=json_data,
                        timeout=30
                    )
                    log.info(f"POST response status: {post_response.status_code}")
                    log.info(f"POST response: {post_response.text[:500]}")
                    
                    # ✅ LOG RESPONSE TO JSON FILE (Mock Mode) - Added Jan 28, 2026
                    try:
                        log_sap_response(
                            log_id=db_log_id,
                            response_payload={"text": post_response.text, "status_code": post_response.status_code},
                            status_code=post_response.status_code,
                            duration_ms=int(post_response.elapsed.total_seconds() * 1000) if hasattr(post_response, 'elapsed') else None
                        )
                    except Exception as log_err:
                        log.warning(f"Warning: Failed to log mock response: {log_err}")
                        
                except requests.exceptions.RequestException as mock_error:
                    # Connection error in mock mode - log and re-raise to be caught by outer handler
                    log.error(f"❌ MOCK MODE: Connection error to demo server: {mock_error}")
                    # Re-raise to be caught by outer exception handler which will log to error_log
                    raise
            else:
                # ============================================================
                # PRODUCTION MODE: STEP 1: GET request to fetch CSRF token (HTTPS)
                # ============================================================
                log.info("Step 1: Fetching CSRF token via HTTPS...")
                
                get_headers = {
                    "x-csrf-token": "fetch",
                    "Accept": "application/json",
                    "User-Agent": "Python-Requests/2.31.0",
                    "Connection": "keep-alive"
                }
                
                token_response = requests.get(
                    url,
                    headers=get_headers,
                    auth=(self.username, self.password),
                    timeout=30,
                    verify=False  # Ignore SSL certificate errors
                )
                
                log.info(f"GET response status: {token_response.status_code}")
                log.info(f"GET response headers: {dict(token_response.headers)}")
                
                # Check for authentication errors
                if token_response.status_code == 401:
                    log.error(f"❌ Authentication failed: {token_response.text[:300]}")
                    return {
                        "ok": False,
                        "error": "Authentication failed",
                        "successful_count": 0,
                        "failed_count": len(orders_data),
                        "successful_orders": [],
                        "failed_orders": [order.get('po_number') for order in orders_data]
                    }
                
                if token_response.status_code not in [200, 201]:
                    log.error(f"❌ Failed to fetch CSRF token: {token_response.status_code}")
                    return {
                        "ok": False,
                        "error": f"Failed to get CSRF token. Status: {token_response.status_code}",
                        "successful_count": 0,
                        "failed_count": len(orders_data),
                        "successful_orders": [],
                        "failed_orders": [order.get('po_number') for order in orders_data]
                    }
                
                # Extract CSRF token
                csrf_token = (
                    token_response.headers.get("x-csrf-token") or 
                    token_response.headers.get("X-CSRF-Token") or
                    token_response.headers.get("X-Csrf-Token")
                )
                
                cookies = token_response.cookies
                
                if not csrf_token:
                    log.error("❌ No CSRF token in response headers")
                    log.error(f"Available headers: {list(token_response.headers.keys())}")
                    return {
                        "ok": False,
                        "error": "CSRF token not found in response",
                        "successful_count": 0,
                        "failed_count": len(orders_data),
                        "successful_orders": [],
                        "failed_orders": [order.get('po_number') for order in orders_data]
                    }
                
                log.info(f"✅ CSRF token received: {csrf_token[:30]}...")
                log.info(f"Cookies received: {len(cookies)} cookie(s)")
                
                # ============================================================
                # STEP 2: POST request with CSRF token and data (HTTPS)
                # ============================================================
                log.info("Step 2: Sending POST request with Online Confirmation data...")
                
                post_headers = {
                    "x-csrf-token": csrf_token,
                    "Content-Type": "application/json",
                    "Accept": "application/json",
                    "User-Agent": "Python-Requests/2.31.0",
                    "Connection": "keep-alive"
                }
                
                post_response = requests.post(
                    url,
                    json=json_data,
                    headers=post_headers,
                    cookies=cookies,
                    auth=(self.username, self.password),
                    timeout=30,
                    verify=False
                )
                
                # ✅ LOG RESPONSE TO DB AND JSON FILE
                try:
                    log_sap_response(
                        log_id=db_log_id,
                        response_payload={"text": post_response.text},
                        status_code=post_response.status_code,
                        duration_ms=int(post_response.elapsed.total_seconds() * 1000)
                    )
                    log.info(f"✅ [REAL SAP] Response logged to JSON file")
                except Exception as log_err:
                    log.warning(f"⚠️ [REAL SAP] Failed to log response: {log_err}")
                
                log.info(f"POST response status: {post_response.status_code}")
                log.info(f"POST response: {post_response.text[:500]}")
            
            # ============================================================
            # STEP 3: Parse SAP response to detect individual order status
            # ============================================================
            if post_response.status_code in [200, 201]:
                try:
                    # Parse SAP response - it returns a JSON array as a string
                    sap_response_text = post_response.text.strip()
                    
                    # Check if response is a JSON array
                    if sap_response_text.startswith('[') and sap_response_text.endswith(']'):
                        log.info("📋 Parsing SAP response array...")
                        sap_orders = json.loads(sap_response_text)
                        
                        successful_orders = []
                        failed_orders = []
                        offline_stored_count = 0  # ✅ Initialize early to avoid scope issues
                        
                        # Parse each order's result
                        for sap_order in sap_orders:
                            message = sap_order.get('MESSAGE', '')
                            po_number = sap_order.get('PROCESS_ORDER', '').lstrip('0')  # Remove leading zeros
                            
                            log.info(f"Order {po_number}: {message}")
                            
                            # Check if order was actually saved successfully
                            # Success: message contains success indicators but NOT error indicators
                            success_indicators = ['saved', 'confirmations have been entered', 'confirmed', 'successfully', 'success']
                            has_success = any(indicator in message.lower() for indicator in success_indicators)
                            has_error = any(error_keyword in message.lower() for error_keyword in [
                                'already being processed',
                                'error',
                                'failed',
                                'locked',
                                'not found',
                                'invalid',
                                'reject',
                                'rejected',
                                'denied',
                                'refused',
                                'cannot',
                                'unable',
                                'warning',
                                'exception'
                            ])
                            
                            # ✅ IMPROVED LOGIC: If no success indicator OR has error indicator, treat as failed
                            if has_success and not has_error:
                                successful_orders.append(po_number)
                                log.info(f"✅ Order {po_number}: SUCCESS")
                            else:
                                # Treat as failed if error indicators present OR no success indicators
                                failed_orders.append({
                                    "po_number": po_number,
                                    "error": message.strip() if message.strip() else "SAP confirmation rejected - no success message",
                                    "material": sap_order.get('MATERIAL', ''),
                                    "batch": sap_order.get('BATCH', ''),
                                    "status": sap_order.get('STATUS', ''),
                                    "full_sap_order": sap_order  # Include full SAP response for debugging
                                })
                                log.warning(f"❌ Order {po_number}: FAILED - {message}")
                        
                        # ✅ Log failed orders to error_log table
                        # NOTE: SAP rejections go ONLY to error_log, NOT to offline_confirmations
                        # (per Dec_13_changes.md fallback strategy document)
                        for fail in failed_orders:
                            po = fail.get("po_number", "")
                            error_msg = fail.get("error", "SAP confirmation failed")
                            # Find the original order data for payload
                            original_order = next((o for o in orders_data if str(o.get("po_number", "")).lstrip("0") == str(po).lstrip("0")), None)
                            
                            # Build comprehensive payload with all relevant information
                            # ✅ CRITICAL: Include vpn_connected and http_status per fallback strategy
                            payload = {
                                "sent_payload": original_order if original_order else {},
                                "sap_reply": fail,
                                "sap_response": sap_response_text[:1000] if 'sap_response_text' in locals() else "",
                                "confirmation_type": "online",
                                "timestamp": datetime.now().isoformat(),
                                "vpn_connected": True,  # ✅ VPN was connected (request reached SAP)
                                "http_status": post_response.status_code  # ✅ HTTP request succeeded
                            }
                            
                            # Ensure PO number is properly formatted (remove leading zeros for consistency)
                            po_clean = str(po).lstrip("0") if po else ""
                            
                            log_order_error(
                                po_number=po_clean,
                                error_type="sap_failed",
                                error_message=error_msg,
                                payload=payload,
                                source="sap_online"
                            )
                            log.info(f"📌 Error logged for PO {po_clean}: {error_msg}")
                        
                        # ✅ CRITICAL: SAP rejections are logged ONLY to error_log, NOT to offline_confirmations
                        # Per Dec_13_changes.md fallback strategy:
                        # - offline_confirmations is for VPN disconnected (network issue)
                        # - error_log is for SAP rejections (SAP processed request but rejected)
                        # Users can reprocess from error_log with updated scrap/confirmed_text
                        if failed_orders:
                            log.warning(f"⚠️ {len(failed_orders)} orders rejected by SAP - logged to error_log (NOT offline_confirmations)")
                            log.info(f"📋 Failed orders (SAP rejected): {[f.get('po_number') for f in failed_orders]}")
                            log.info(f"💡 Use Error Log UI to reprocess these orders with updated scrap/confirmed_text")
                        
                        # Determine overall status
                        total_orders = len(orders_data)
                        success_count = len(successful_orders)
                        failed_count = len(failed_orders)
                        
                        if success_count == total_orders:
                            status = "Success"
                            log.info(f"✅ All {total_orders} orders confirmed successfully")
                        elif success_count > 0:
                            status = "PartialSuccess"
                            log.warning(f"⚠️ Partial success: {success_count}/{total_orders} orders confirmed")
                        else:
                            status = "Failed"
                            log.error(f"❌ All {total_orders} orders failed")
                        
                        # Log detailed results
                        log_sap_event(
                            action="Online Confirmation Completed",
                            status=status,
                            details=f"Online confirmation: {success_count} succeeded, {failed_count} failed (SAP rejected - logged to error_log)",
                            metadata={
                                "order_count": total_orders,
                                "successful_count": success_count,
                                "failed_count": failed_count,
                                "successful_orders": successful_orders,
                                "failed_orders": failed_orders,
                                "sap_response": sap_response_text[:1000]  # Limit size
                            }
                        )
                        
                        # Build response message
                        message_parts = []
                        if success_count > 0:
                            message_parts.append(f"{success_count} order(s) confirmed successfully")
                        if failed_count > 0:
                            message_parts.append(f"{failed_count} order(s) failed")
                        if offline_stored_count > 0:
                            message_parts.append(f"{offline_stored_count} order(s) saved to offline queue for manual retry")
                        
                        response_message = " | ".join(message_parts) if message_parts else "No orders processed"
                        
                        return {
                            "ok": True,
                            "message": response_message,
                            "sap_response": sap_response_text,
                            "successful_count": success_count,
                            "failed_count": failed_count,
                            "offline_stored_count": offline_stored_count,
                            "successful_orders": successful_orders,
                            "failed_orders": failed_orders
                        }
                    
                    else:
                        # Response is not a JSON array - treat as generic success/error
                        log.warning("⚠️ SAP response is not a JSON array, checking for success/error indicators...")
                        
                        # Check for error indicators in response
                        error_indicators = ['error', 'failed', 'reject', 'rejected', 'denied', 'exception', 'invalid', 'cannot', 'unable']
                        has_error_in_response = any(indicator in sap_response_text.lower() for indicator in error_indicators)
                        has_success_in_response = "Data Saved Correctly" in sap_response_text or "success" in sap_response_text.lower()
                        
                        if has_error_in_response and not has_success_in_response:
                            # Response contains errors - log all orders as failed
                            log.error(f"❌ SAP response contains error indicators: {sap_response_text[:200]}")
                            
                            failed_orders_list = []
                            for order in orders_data:
                                po = str(order.get('po_number', '')).lstrip('0')
                                failed_orders_list.append(po)
                                
                                payload = {
                                    "sent_payload": order,
                                    "sap_response": sap_response_text[:1000],
                                    "confirmation_type": "online",
                                    "timestamp": datetime.now().isoformat(),
                                    "note": "Non-array response with error indicators"
                                }
                                
                                log_order_error(
                                    po_number=po,
                                    error_type="sap_failed",
                                    error_message=f"SAP confirmation rejected: {sap_response_text[:200]}",
                                    payload=payload,
                                    source="sap_online"
                                )
                                log.info(f"📌 Error logged for PO {po}: Non-array response with errors")
                            
                            # ✅ Store all failed orders in offline_confirmations
                            offline_stored = 0
                            try:
                                from models.offline_confirmation import OfflineConfirmation
                                
                                with PostgresSessionLocal() as offline_db:
                                    for order in orders_data:
                                        try:
                                            po_num = order.get('po_number')
                                            if not po_num:
                                                continue
                                            
                                            # Check if already exists - compare in Python for reliability
                                            if not po_num:
                                                log.error(f"❌ No PO number found, skipping")
                                                continue
                                            
                                            po_num_stripped = str(po_num).lstrip('0')
                                            if not po_num_stripped or po_num_stripped == '':
                                                po_num_stripped = str(po_num)
                                            
                                            log.info(f"🔍 Checking duplicate for PO: original={po_num}, stripped={po_num_stripped}")
                                            
                                            # Get order status to determine duplicate handling
                                            from sqlalchemy import text
                                            order_status_row = offline_db.execute(text("""
                                                SELECT status FROM process_orders 
                                                WHERE LTRIM(order_id, '0') = LTRIM(:po, '0')
                                                LIMIT 1
                                            """), {"po": str(po_num)}).fetchone()
                                            
                                            order_status = (order_status_row[0] or "").upper() if order_status_row else ""
                                            
                                            # ✅ For VALIDATED orders: Skip if already in database (one validated order = one offline record)
                                            # ✅ For PARTIAL confirmations: Allow duplicates (same order can have multiple partial confirmations)
                                            if order_status == "VALIDATED":
                                                all_pending = offline_db.query(OfflineConfirmation).filter(
                                                    OfflineConfirmation.status == 'pending'
                                                ).all()
                                                
                                                log.info(f"🔍 Found {len(all_pending)} pending records in database")
                                                
                                                existing = None
                                                for pending in all_pending:
                                                    if not pending.order_id:
                                                        continue
                                                    
                                                    pending_stripped = str(pending.order_id).lstrip('0')
                                                    if not pending_stripped or pending_stripped == '':
                                                        pending_stripped = str(pending.order_id)
                                                    
                                                    # Ensure both are non-empty before comparing
                                                    if not po_num_stripped or not pending_stripped:
                                                        log.warning(f"⚠️ Empty PO number detected: new={po_num_stripped}, existing={pending_stripped}")
                                                        continue
                                                    
                                                    # Exact string comparison (case-sensitive)
                                                    is_match = (pending_stripped == po_num_stripped)
                                                    log.info(f"   Compare: '{po_num_stripped}' == '{pending_stripped}'? {is_match} (existing order_id={pending.order_id})")
                                                    
                                                    if is_match:
                                                        existing = pending
                                                        log.warning(f"⏭️ DUPLICATE: Validated order {po_num} (stripped: '{po_num_stripped}') matches existing ID {pending.id} with order_id={pending.order_id} (stripped: '{pending_stripped}')")
                                                        break
                                                
                                                if existing:
                                                    log.warning(f"⏭️ Skipping validated order {po_num} - duplicate detected")
                                                    continue
                                            else:
                                                # ✅ UPDATED: For partial confirmations, check for existing and UPDATE instead of creating duplicates
                                                existing = None
                                                for pending in all_pending:
                                                    if not pending.order_id:
                                                        continue
                                                    pending_stripped = str(pending.order_id).lstrip('0')
                                                    if not pending_stripped:
                                                        pending_stripped = str(pending.order_id)
                                                    if pending_stripped == po_num_stripped:
                                                        existing = pending
                                                        break
                                                
                                                if existing:
                                                    # ✅ UPDATE existing record - accumulate the confirmed_weight
                                                    new_weight = float(order.get('confirmed_weight', 0))
                                                    old_weight = existing.confirmed_weight or 0
                                                    accumulated_weight = old_weight + new_weight
                                                    existing.confirmed_weight = accumulated_weight
                                                    new_scrap = float(order.get('scrap', 0))
                                                    existing.scrap = (existing.scrap or 0) + new_scrap
                                                    updated_payload = json.loads(json.dumps(order, default=str))
                                                    updated_payload['confirmed_weight'] = accumulated_weight
                                                    existing.sap_payload = updated_payload
                                                    # ✅ Keep existing confirmed_text - don't overwrite user's manual notes
                                                    # existing.confirmed_text is preserved as-is
                                                    log.info(f"✅ [SAPError] UPDATED existing offline order {po_num}: {old_weight:.2f} + {new_weight:.2f} = {accumulated_weight:.2f}")
                                                    offline_stored += 1
                                                    continue  # Skip creating new record
                                            
                                            log.info(f"✅ NEW ORDER: PO {po_num} (stripped: {po_num_stripped}) - storing (status: {order_status})...")
                                            
                                            offline_record = OfflineConfirmation(
                                                order_id=str(po_num),
                                                process_order_id=order.get('process_order_id'),
                                                material=order.get('material'),
                                                version=order.get('version'),
                                                confirmed_weight=float(order.get('confirmed_weight', 0)),
                                                total_qty=float(order.get('total_qty', 0)),
                                                uom=order.get('uom', 'KG'),
                                                plant=order.get('plant'),
                                                batch=order.get('batch', ''),
                                                shift=order.get('shift'),
                                                scrap=float(order.get('scrap', 0)),
                                                confirmed_text="",  # Leave empty unless user explicitly adds text
                                                sap_payload=json.loads(json.dumps(order, default=str)),  # Serialize datetime objects
                                                validation_method='SAPError',
                                                status='pending',
                                                retry_count=0
                                            )
                                            offline_db.add(offline_record)
                                            offline_stored += 1
                                        except Exception as item_err:
                                            log.error(f"Failed to store offline: {item_err}")
                                    
                                    if offline_stored > 0:
                                        offline_db.commit()
                                        log.info(f"✅ Stored {offline_stored} orders in offline_confirmations")
                                        
                                        # ✅ Update process_orders - treat offline as confirmed
                                        try:
                                            for order in orders_data:
                                                po_num = order.get('po_number')
                                                shift = (order.get('shift') or '').upper()
                                                confirmed_weight = float(order.get('confirmed_weight', 0))
                                                is_final = order.get('is_final', False)
                                                
                                                if po_num and shift in ('A', 'B', 'C'):
                                                    shift_col = f"confirmed_shift_{shift.lower()}"
                                                    
                                                    if shift == 'A':
                                                        last_calc = f"(COALESCE(confirmed_shift_a, 0) + :w) + COALESCE(confirmed_shift_b, 0) + COALESCE(confirmed_shift_c, 0)"
                                                    elif shift == 'B':
                                                        last_calc = f"COALESCE(confirmed_shift_a, 0) + (COALESCE(confirmed_shift_b, 0) + :w) + COALESCE(confirmed_shift_c, 0)"
                                                    else:
                                                        last_calc = f"COALESCE(confirmed_shift_a, 0) + COALESCE(confirmed_shift_b, 0) + (COALESCE(confirmed_shift_c, 0) + :w)"
                                                    
                                                    # ✅ Feb 5, 2026: Set status to 'Validated' on successful SAP confirmation
                                                    # Preserve existing Validated status, upgrade Completed → Validated
                                                    offline_db.execute(text(f"""
                                                        UPDATE process_orders
                                                        SET {shift_col} = COALESCE({shift_col}, 0) + :w,
                                                            last_confirmed_qty = {last_calc},
                                                            confirmed_qty = {last_calc},
                                                            is_final_sent = CASE WHEN :is_final THEN TRUE ELSE is_final_sent END,
                                                            status = CASE 
                                                                WHEN status = 'Validated' THEN 'Validated'
                                                                WHEN status = 'Completed' AND :is_final THEN 'Validated'
                                                                WHEN status = 'Completed' THEN 'Completed'
                                                                ELSE status
                                                            END,
                                                            updated_at = NOW()
                                                        WHERE order_id = :po
                                                    """), {"w": confirmed_weight, "is_final": is_final, "po": po_num})
                                            offline_db.commit()
                                            log.info(f"✅ Updated confirmation values for {len(orders_data)} orders (offline)")
                                        except Exception as update_err:
                                            log.error(f"Failed to update process_orders: {update_err}")
                            except Exception as store_err:
                                log.error(f"Failed to store offline: {store_err}")
                            
                            log_sap_event(
                                action="Online Confirmation - Offline Stored",
                                status="OfflineQueued",
                                details=f"{offline_stored} orders confirmed offline due to SAP error",
                                metadata={
                                    "order_count": len(orders_data),
                                    "successful_count": offline_stored,
                                    "failed_count": 0,
                                    "offline_stored_count": offline_stored,
                                    "sap_response": sap_response_text[:1000]
                                }
                            )
                            
                            return {
                                "ok": True,
                                "offline_mode": True,
                                "message": f"SAP error - {offline_stored} order(s) confirmed offline (will sync to SAP later)",
                                "sap_response": sap_response_text,
                                "successful_count": offline_stored,
                                "failed_count": 0,
                                "offline_stored_count": offline_stored,
                                "successful_orders": [order.get('po_number') for order in orders_data],
                                "failed_orders": []
                            }
                        elif has_success_in_response:
                            log.info("✅ SUCCESS! Online confirmation data saved to SAP")
                            
                            # ✅ CRITICAL FIX (Jan 23, 2026): Update process_orders on ONLINE SUCCESS
                            # This was missing - database wasn't updated when SAP confirmed successfully
                            try:
                                for order in orders_data:
                                    po_num = order.get('po_number')
                                    shift = (order.get('shift') or '').upper()
                                    confirmed_weight = float(order.get('confirmed_weight', 0))
                                    is_final = order.get('is_final', False)
                                    
                                    if po_num and shift in ('A', 'B', 'C'):
                                        shift_col = f"confirmed_shift_{shift.lower()}"
                                        
                                        if shift == 'A':
                                            last_calc = f"(COALESCE(confirmed_shift_a, 0) + :w) + COALESCE(confirmed_shift_b, 0) + COALESCE(confirmed_shift_c, 0)"
                                        elif shift == 'B':
                                            last_calc = f"COALESCE(confirmed_shift_a, 0) + (COALESCE(confirmed_shift_b, 0) + :w) + COALESCE(confirmed_shift_c, 0)"
                                        else:
                                            last_calc = f"COALESCE(confirmed_shift_a, 0) + COALESCE(confirmed_shift_b, 0) + (COALESCE(confirmed_shift_c, 0) + :w)"
                                        
                                        offline_db.execute(text(f"""
                                            UPDATE process_orders
                                            SET {shift_col} = COALESCE({shift_col}, 0) + :w,
                                                last_confirmed_qty = {last_calc},
                                                confirmed_qty = {last_calc},
                                                is_final_sent = CASE WHEN :is_final THEN TRUE ELSE is_final_sent END,
                                                updated_at = NOW()
                                            WHERE order_id = :po
                                        """), {"w": confirmed_weight, "is_final": is_final, "po": po_num})
                                offline_db.commit()
                                log.info(f"✅ Updated confirmation values for {len(orders_data)} orders (online success)")
                            except Exception as update_err:
                                log.error(f"Failed to update process_orders after online success: {update_err}")
                            
                            log_sap_event(
                                action="Online Confirmation Completed",
                                status="Success",
                                details=f"Successfully sent {len(orders_data)} orders for online confirmation",
                                metadata={
                                    "order_count": len(orders_data),
                                    "successful_count": len(orders_data),
                                    "failed_count": 0,
                                    "sap_response": sap_response_text
                                }
                            )
                            
                            return {
                                "ok": True,
                                "message": f"Successfully sent {len(orders_data)} orders for online confirmation",
                                "sap_response": sap_response_text,
                                "successful_count": len(orders_data),
                                "failed_count": 0,
                                "successful_orders": [order.get('po_number') for order in orders_data],
                                "failed_orders": []
                            }
                        else:
                            # Ambiguous response - check if it looks like an error
                            log.warning("⚠️ Ambiguous SAP response - cannot determine success/failure clearly")
                            
                            # If response is short and doesn't look like success, treat as potential failure
                            if len(sap_response_text) < 50 and not has_success_in_response:
                                log.warning("⚠️ Short ambiguous response - logging as potential failure")
                                for order in orders_data:
                                    po = str(order.get('po_number', '')).lstrip('0')
                                    payload = {
                                        "sent_payload": order,
                                        "sap_response": sap_response_text,
                                        "confirmation_type": "online",
                                        "timestamp": datetime.now().isoformat(),
                                        "note": "Ambiguous response - treated as potential failure"
                                    }
                                    log_order_error(
                                        po_number=po,
                                        error_type="sap_failed",
                                        error_message=f"Ambiguous SAP response: {sap_response_text}",
                                        payload=payload,
                                        source="sap_online"
                                    )
                                
                                return {
                                    "ok": False,
                                    "message": f"Ambiguous response from SAP for {len(orders_data)} orders",
                                    "sap_response": sap_response_text,
                                    "successful_count": 0,
                                    "failed_count": len(orders_data),
                                    "successful_orders": [],
                                    "failed_orders": [str(order.get('po_number', '')).lstrip('0') for order in orders_data]
                                }
                            
                            # Default: assume success if 200/201 but can't parse clearly
                            log.info("✅ POST successful (non-standard response format)")
                            
                            # ✅ CRITICAL FIX (Jan 23, 2026): Update process_orders on NON-STANDARD SUCCESS
                            try:
                                for order in orders_data:
                                    po_num = order.get('po_number')
                                    shift = (order.get('shift') or '').upper()
                                    confirmed_weight = float(order.get('confirmed_weight', 0))
                                    is_final = order.get('is_final', False)
                                    
                                    if po_num and shift in ('A', 'B', 'C'):
                                        shift_col = f"confirmed_shift_{shift.lower()}"
                                        
                                        if shift == 'A':
                                            last_calc = f"(COALESCE(confirmed_shift_a, 0) + :w) + COALESCE(confirmed_shift_b, 0) + COALESCE(confirmed_shift_c, 0)"
                                        elif shift == 'B':
                                            last_calc = f"COALESCE(confirmed_shift_a, 0) + (COALESCE(confirmed_shift_b, 0) + :w) + COALESCE(confirmed_shift_c, 0)"
                                        else:
                                            last_calc = f"COALESCE(confirmed_shift_a, 0) + COALESCE(confirmed_shift_b, 0) + (COALESCE(confirmed_shift_c, 0) + :w)"
                                        
                                        offline_db.execute(text(f"""
                                            UPDATE process_orders
                                            SET {shift_col} = COALESCE({shift_col}, 0) + :w,
                                                last_confirmed_qty = {last_calc},
                                                confirmed_qty = {last_calc},
                                                is_final_sent = CASE WHEN :is_final THEN TRUE ELSE is_final_sent END,
                                                updated_at = NOW()
                                            WHERE order_id = :po
                                        """), {"w": confirmed_weight, "is_final": is_final, "po": po_num})
                                offline_db.commit()
                                log.info(f"✅ Updated confirmation values for {len(orders_data)} orders (non-standard success)")
                            except Exception as update_err:
                                log.error(f"Failed to update process_orders after non-standard success: {update_err}")
                            
                            log_sap_event(
                                action="Online Confirmation Completed",
                                status="Success",
                                details=f"Successfully sent {len(orders_data)} orders for online confirmation",
                                metadata={
                                    "order_count": len(orders_data),
                                    "successful_count": len(orders_data),
                                    "failed_count": 0,
                                    "sap_response": sap_response_text,
                                    "note": "Non-standard response format"
                                }
                            )
                            
                            return {
                                "ok": True,
                                "message": f"Successfully sent {len(orders_data)} orders for online confirmation",
                                "sap_response": sap_response_text,
                                "successful_count": len(orders_data),
                                "failed_count": 0,
                                "successful_orders": [order.get('po_number') for order in orders_data],
                                "failed_orders": []
                            }
                    
                except json.JSONDecodeError as e:
                    log.error(f"❌ Failed to parse SAP response JSON: {e}")
                    log.error(f"Response text: {post_response.text[:200]}")
                    
                    # Check if response contains error indicators
                    response_text = post_response.text
                    error_indicators = ['error', 'failed', 'reject', 'rejected', 'denied', 'exception', 'invalid', 'cannot', 'unable']
                    has_error_in_response = any(indicator in response_text.lower() for indicator in error_indicators)
                    
                    if has_error_in_response:
                        # Response contains errors - log all orders as failed
                        log.error(f"❌ Response contains error indicators despite JSON parse failure")
                        failed_orders_list = []
                        for order in orders_data:
                            po = str(order.get('po_number', '')).lstrip('0')
                            failed_orders_list.append(po)
                            
                            payload = {
                                "sent_payload": order,
                                "sap_response": response_text[:1000],
                                "confirmation_type": "online",
                                "timestamp": datetime.now().isoformat(),
                                "parse_error": str(e),
                                "note": "JSON parse failed but response contains error indicators"
                            }
                            
                            log_order_error(
                                po_number=po,
                                error_type="sap_failed",
                                error_message=f"SAP confirmation failed (parse error): {response_text[:200]}",
                                payload=payload,
                                source="sap_online"
                            )
                            log.info(f"📌 Error logged for PO {po}: JSON parse failed with error indicators")
                        
                        return {
                            "ok": False,
                            "message": f"Failed to parse SAP response and response contains errors",
                            "sap_response": response_text,
                            "successful_count": 0,
                            "failed_count": len(orders_data),
                            "successful_orders": [],
                            "failed_orders": failed_orders_list,
                            "parse_error": str(e)
                        }
                    else:
                        # Can't parse but no clear error indicators - treat as success but log warning
                        log.warning(f"⚠️ Could not parse SAP response but no error indicators found")
                        
                        # ✅ CRITICAL FIX (Jan 23, 2026): Update process_orders on PARSE ERROR SUCCESS
                        try:
                            for order in orders_data:
                                po_num = order.get('po_number')
                                shift = (order.get('shift') or '').upper()
                                confirmed_weight = float(order.get('confirmed_weight', 0))
                                is_final = order.get('is_final', False)
                                
                                if po_num and shift in ('A', 'B', 'C'):
                                    shift_col = f"confirmed_shift_{shift.lower()}"
                                    
                                    if shift == 'A':
                                        last_calc = f"(COALESCE(confirmed_shift_a, 0) + :w) + COALESCE(confirmed_shift_b, 0) + COALESCE(confirmed_shift_c, 0)"
                                    elif shift == 'B':
                                        last_calc = f"COALESCE(confirmed_shift_a, 0) + (COALESCE(confirmed_shift_b, 0) + :w) + COALESCE(confirmed_shift_c, 0)"
                                    else:
                                        last_calc = f"COALESCE(confirmed_shift_a, 0) + COALESCE(confirmed_shift_b, 0) + (COALESCE(confirmed_shift_c, 0) + :w)"
                                    
                                    offline_db.execute(text(f"""
                                        UPDATE process_orders
                                        SET {shift_col} = COALESCE({shift_col}, 0) + :w,
                                            last_confirmed_qty = {last_calc},
                                            confirmed_qty = {last_calc},
                                            is_final_sent = CASE WHEN :is_final THEN TRUE ELSE is_final_sent END,
                                            updated_at = NOW()
                                        WHERE order_id = :po
                                    """), {"w": confirmed_weight, "is_final": is_final, "po": po_num})
                            offline_db.commit()
                            log.info(f"✅ Updated confirmation values for {len(orders_data)} orders (parse error success)")
                        except Exception as update_err:
                            log.error(f"Failed to update process_orders after parse error success: {update_err}")
                        
                        return {
                            "ok": True,
                            "message": f"Sent {len(orders_data)} orders (couldn't parse SAP response)",
                            "sap_response": post_response.text,
                            "successful_count": len(orders_data),
                            "failed_count": 0,
                            "successful_orders": [order.get('po_number') for order in orders_data],
                            "failed_orders": [],
                            "parse_error": str(e)
                        }
            
            else:
                # HTTP error status
                log.error(f"❌ POST failed: {post_response.status_code}")
                log.error(f"Response: {post_response.text[:500]}")
                
                log_sap_event(
                    action="Online Confirmation Failed",
                    status="Error",
                    details=f"POST request failed with status {post_response.status_code}",
                    error_code="HTTP_ERROR",
                    metadata={
                        "order_count": len(orders_data),
                        "status_code": post_response.status_code,
                        "response": post_response.text[:500]
                    }
                )
                
                # ✅ Log all failed orders to error_log table
                for order in orders_data:
                    po = str(order.get('po_number', '')).lstrip('0')
                    try:
                        payload = {
                            "sent_payload": order,
                            "sap_response": post_response.text[:1000] if hasattr(post_response, 'text') else "",
                            "status_code": post_response.status_code,
                            "confirmation_type": "online",
                            "timestamp": datetime.now().isoformat()
                        }
                    except Exception as payload_err:
                        payload = {"error": f"Payload creation failed: {str(payload_err)}"}
                    
                    log_order_error(
                        po_number=po,
                        error_type="sap_failed",
                        error_message=f"POST failed with status {post_response.status_code}",
                        payload=payload,
                        source="sap_online"
                    )
                    log.info(f"📌 Error logged for PO {po}: HTTP {post_response.status_code}")
                
                # ✅ Store all failed orders in offline_confirmations
                offline_stored = 0
                try:
                    from models.offline_confirmation import OfflineConfirmation
                    
                    with PostgresSessionLocal() as offline_db:
                        for order in orders_data:
                            try:
                                po_num = order.get('po_number')
                                if not po_num:
                                    continue
                                
                                # Check if already exists - if yes, UPDATE instead of skip
                                po_num_stripped = str(po_num).lstrip('0')
                                existing = offline_db.query(OfflineConfirmation).filter(
                                    func.ltrim(OfflineConfirmation.order_id, '0') == po_num_stripped,
                                    OfflineConfirmation.status == 'pending'
                                ).first()
                                
                                if existing:
                                    # ✅ UPDATE existing record - accumulate the confirmed_weight
                                    new_weight = float(order.get('confirmed_weight', 0))
                                    old_weight = existing.confirmed_weight or 0
                                    accumulated_weight = old_weight + new_weight
                                    existing.confirmed_weight = accumulated_weight
                                    new_scrap = float(order.get('scrap', 0))
                                    existing.scrap = (existing.scrap or 0) + new_scrap
                                    updated_payload = json.loads(json.dumps(order, default=str))
                                    updated_payload['confirmed_weight'] = accumulated_weight
                                    existing.sap_payload = updated_payload
                                    # ✅ Keep existing confirmed_text - don't overwrite user's manual notes
                                    # existing.confirmed_text is preserved as-is
                                    log.info(f"✅ UPDATED existing offline order {po_num}: {old_weight:.2f} + {new_weight:.2f} = {accumulated_weight:.2f}")
                                    offline_stored += 1
                                    continue  # Skip creating new record
                                
                                # ✅ Check if order is validated - store all orders offline
                                from database import PostgresSessionLocal as StatusDB
                                with StatusDB() as status_db:
                                    from sqlalchemy import text
                                    order_status_row = status_db.execute(text("""
                                        SELECT status FROM process_orders 
                                        WHERE LTRIM(order_id, '0') = LTRIM(:po, '0')
                                        LIMIT 1
                                    """), {"po": str(po_num)}).fetchone()
                                    
                                    order_status = (order_status_row[0] or "").upper() if order_status_row else ""
                                    log.info(f"✅ Processing order {po_num} for offline storage (status: {order_status})")
                                
                                offline_record = OfflineConfirmation(
                                    order_id=str(po_num),
                                    process_order_id=order.get('process_order_id'),
                                    material=order.get('material'),
                                    version=order.get('version'),
                                    confirmed_weight=float(order.get('confirmed_weight', 0)),
                                    total_qty=float(order.get('total_qty', 0)),
                                    uom=order.get('uom', 'KG'),
                                    plant=order.get('plant'),
                                    batch=order.get('batch', ''),
                                    shift=order.get('shift'),
                                    scrap=float(order.get('scrap', 0)),
                                    confirmed_text="",  # Leave empty unless user explicitly adds text
                                    sap_payload=json.loads(json.dumps(order, default=str)),  # Serialize datetime objects
                                    validation_method='HTTPError',
                                    status='pending',
                                    retry_count=0
                                )
                                offline_db.add(offline_record)
                                offline_stored += 1
                            except Exception as item_err:
                                log.error(f"Failed to store offline: {item_err}")
                        
                        if offline_stored > 0:
                            offline_db.commit()
                            log.info(f"✅ Stored {offline_stored} orders in offline_confirmations")
                            
                            # ✅ Update process_orders - treat offline as confirmed
                            # Update confirmation values so order disappears from active list
                            try:
                                for order in orders_data:
                                    po_num = order.get('po_number')
                                    shift = (order.get('shift') or '').upper()
                                    confirmed_weight = float(order.get('confirmed_weight', 0))
                                    is_final = order.get('is_final', False)
                                    
                                    if po_num and shift in ('A', 'B', 'C'):
                                        shift_col = f"confirmed_shift_{shift.lower()}"
                                        
                                        if shift == 'A':
                                            last_calc = f"(COALESCE(confirmed_shift_a, 0) + :w) + COALESCE(confirmed_shift_b, 0) + COALESCE(confirmed_shift_c, 0)"
                                        elif shift == 'B':
                                            last_calc = f"COALESCE(confirmed_shift_a, 0) + (COALESCE(confirmed_shift_b, 0) + :w) + COALESCE(confirmed_shift_c, 0)"
                                        else:
                                            last_calc = f"COALESCE(confirmed_shift_a, 0) + COALESCE(confirmed_shift_b, 0) + (COALESCE(confirmed_shift_c, 0) + :w)"
                                        
                                        # ✅ Feb 5, 2026: Set status to 'Validated' on successful SAP confirmation
                                        # Preserve existing Validated status, upgrade Completed → Validated on final
                                        offline_db.execute(text(f"""
                                            UPDATE process_orders
                                            SET {shift_col} = COALESCE({shift_col}, 0) + :w,
                                                last_confirmed_qty = {last_calc},
                                                confirmed_qty = {last_calc},
                                                is_final_sent = CASE WHEN :is_final THEN TRUE ELSE is_final_sent END,
                                                status = CASE 
                                                    WHEN status = 'Validated' THEN 'Validated'
                                                    WHEN status = 'Completed' AND :is_final THEN 'Validated'
                                                    WHEN status = 'Completed' THEN 'Completed'
                                                    ELSE status
                                                END,
                                                updated_at = NOW()
                                            WHERE order_id = :po
                                        """), {"w": confirmed_weight, "is_final": is_final, "po": po_num})
                                offline_db.commit()
                                log.info(f"✅ Updated confirmation values for {len(orders_data)} orders (offline)")
                            except Exception as update_err:
                                log.error(f"Failed to update process_orders: {update_err}")
                except Exception as store_err:
                    log.error(f"Failed to store offline: {store_err}")
                
                return {
                    "ok": True,
                    "offline_mode": True,
                    "message": f"VPN/Network issue - {offline_stored} order(s) confirmed offline (will sync to SAP later)",
                    "sap_response": post_response.text,
                    "successful_count": offline_stored,
                    "failed_count": len(orders_data) - offline_stored,
                    "offline_stored_count": offline_stored,
                    "successful_orders": [order.get('po_number') for order in orders_data],
                    "failed_orders": []
                }
            
        except requests.exceptions.RequestException as e:
            log.error(f"❌ Online confirmation failed: {e}")
            
            # Log confirmation failure
            log_sap_event(
                action="Online Confirmation Failed",
                status="Error",
                details=f"SAP online confirmation error: {str(e)}",
                error_code="CONFIRMATION_ERROR",
                metadata={
                    "order_count": len(orders_data),
                    "successful_count": 0,
                    "failed_count": len(orders_data),
                    "error": str(e)
                }
            )
            
            # ✅ Log all failed orders to error_log table
            for order in orders_data:
                # Extract PO number with proper handling
                po_raw = order.get('po_number') or order.get('process_order') or order.get('order_id') or ''
                po = str(po_raw).lstrip('0') if po_raw else ''
                
                # If PO is still empty, try to get from order_id or other fields
                if not po:
                    po = str(order.get('id', '') or order.get('order_id', '') or 'UNKNOWN')
                
                # Serialize payload carefully
                try:
                    payload_data = {
                        "sent_payload": order,
                        "error": str(e),
                        "error_type": type(e).__name__,
                        "confirmation_type": "online",
                        "timestamp": datetime.now().isoformat(),
                        "url": url if 'url' in locals() else "unknown"
                    }
                except Exception as payload_err:
                    payload_data = {"error": f"Payload creation failed: {str(payload_err)}"}
                
                error_msg = f"SAP online confirmation error: {str(e)}"
                
                try:
                    log_order_error(
                        po_number=po if po else "UNKNOWN",
                        error_type="sap_failed",
                        error_message=error_msg,
                        payload=payload_data,
                        source="sap_online"
                    )
                    log.info(f"📌 Error logged for PO {po}: Request exception - {str(e)}")
                except Exception as log_err:
                    log.exception(f"❌ Failed to log error for order {po}: {log_err}")
                    
            # ✅✅ NEW: Store in offline_confirmations table if network/VPN error
            # This allows manual retry later from the frontend
            stored_count = 0
            try:
                # Check if it's a connection error (which implies VPN/network down)
                is_connection_error = isinstance(e, (requests.exceptions.ConnectionError, requests.exceptions.Timeout))
                
                if is_connection_error:
                    log.warning(f"⚠️ Network/VPN error detected: {type(e).__name__}. Storing {len(orders_data)} orders for offline confirmation.")
                    
                    # Import here to avoid circular imports (log is used below, so it must be defined)
                    from models.offline_confirmation import OfflineConfirmation
                    
                    with PostgresSessionLocal() as offline_db:
                        processed_po_numbers = set()  # Track PO numbers processed in this batch
                        for order in orders_data:
                            try:
                                po_num = order.get('po_number')
                                if not po_num:
                                    continue
                                    
                                # Strip leading zeros for comparison
                                po_num_stripped = str(po_num).lstrip('0')
                                if not po_num_stripped or po_num_stripped == '':
                                    po_num_stripped = str(po_num)
                                
                                log.info(f"🔍 [NetworkFailover] Checking duplicate for PO: original={po_num}, stripped={po_num_stripped}")
                                
                                # Get order status first to determine duplicate handling
                                from sqlalchemy import text
                                order_status_row = offline_db.execute(text("""
                                    SELECT status FROM process_orders 
                                    WHERE LTRIM(order_id, '0') = LTRIM(:po, '0')
                                    LIMIT 1
                                """), {"po": str(po_num)}).fetchone()
                                
                                order_status = (order_status_row[0] or "").upper() if order_status_row else ""
                                
                                # First check: Is this PO already processed in this batch?
                                if po_num_stripped in processed_po_numbers:
                                    log.warning(f"⏭️ [NetworkFailover] DUPLICATE IN BATCH: Order {po_num} (stripped: '{po_num_stripped}') already processed - skipping")
                                    continue
                                
                                # Second check: Database duplicate check
                                # ✅ For VALIDATED orders: Skip if already in database (one validated order = one offline record)
                                # ✅ For PARTIAL confirmations: Allow duplicates (same order can have multiple partial confirmations)
                                if order_status == "VALIDATED":
                                    all_pending = offline_db.query(OfflineConfirmation).filter(
                                        OfflineConfirmation.status == 'pending'
                                    ).all()
                                    
                                    existing = None
                                    for pending in all_pending:
                                        if not pending.order_id:
                                            continue
                                        
                                        pending_stripped = str(pending.order_id).lstrip('0')
                                        if not pending_stripped or pending_stripped == '':
                                            pending_stripped = str(pending.order_id)
                                        
                                        if not po_num_stripped or not pending_stripped:
                                            continue
                                        
                                        is_match = (pending_stripped == po_num_stripped)
                                        if is_match:
                                            existing = pending
                                            log.warning(f"⏭️ [NetworkFailover] DUPLICATE IN DB: Validated order {po_num} (stripped: '{po_num_stripped}') matches existing ID {pending.id}")
                                            break
                                    
                                    if existing:
                                        log.warning(f"⏭️ [NetworkFailover] Skipping validated order {po_num} - duplicate detected")
                                        continue
                                else:
                                    # ✅ UPDATED: For partial confirmations, check for existing and UPDATE instead of creating duplicates
                                    all_pending = offline_db.query(OfflineConfirmation).filter(
                                        OfflineConfirmation.status == 'pending'
                                    ).all()
                                    
                                    existing = None
                                    for pending in all_pending:
                                        if not pending.order_id:
                                            continue
                                        pending_stripped = str(pending.order_id).lstrip('0')
                                        if not pending_stripped:
                                            pending_stripped = str(pending.order_id)
                                        if pending_stripped == po_num_stripped:
                                            existing = pending
                                            break
                                    
                                    if existing:
                                        # ✅ UPDATE existing record - accumulate the confirmed_weight
                                        new_weight = float(order.get('confirmed_weight', 0))
                                        old_weight = existing.confirmed_weight or 0
                                        accumulated_weight = old_weight + new_weight
                                        existing.confirmed_weight = accumulated_weight
                                        # Also update scrap (sum it) if provided
                                        new_scrap = float(order.get('scrap', 0))
                                        existing.scrap = (existing.scrap or 0) + new_scrap
                                        # Update the SAP payload with new accumulated values
                                        updated_payload = json.loads(json.dumps(order, default=str))
                                        updated_payload['confirmed_weight'] = accumulated_weight
                                        existing.sap_payload = updated_payload
                                        # ✅ Keep existing confirmed_text - don't overwrite user's manual notes
                                        # existing.confirmed_text is preserved as-is
                                        log.info(f"✅ [NetworkFailover] UPDATED existing offline order {po_num}: {old_weight:.2f} + {new_weight:.2f} = {accumulated_weight:.2f}")
                                        processed_po_numbers.add(po_num_stripped)
                                        stored_count += 1
                                        continue  # Skip creating new record
                                
                                log.info(f"✅ [NetworkFailover] Processing order {po_num} for offline storage (status: {order_status})")
                                
                                # Mark this PO as processed in this batch
                                processed_po_numbers.add(po_num_stripped)
                                
                                log.info(f"✅ [NetworkFailover] NEW ORDER: PO {po_num} (stripped: {po_num_stripped}) - storing...")
                                
                                # Map fields from SAP payload back to DB model
                                offline_record = OfflineConfirmation(
                                    order_id=str(po_num),
                                    process_order_id=order.get('process_order_id'),
                                    material=order.get('material'),
                                    version=order.get('version'),
                                    confirmed_weight=float(order.get('confirmed_weight', 0)),
                                    total_qty=float(order.get('total_qty', 0)),
                                    uom=order.get('uom', 'KG'),
                                    plant=order.get('plant'),
                                    batch=order.get('batch', ''),
                                    shift=order.get('shift'),
                                    scrap=float(order.get('scrap', 0)),
                                    confirmed_text="",  # Leave empty unless user explicitly adds text
                                    sap_payload=json.loads(json.dumps(order, default=str)),  # Serialize datetime objects
                                    validation_method='NetworkFailover',
                                    status='pending',
                                    retry_count=0
                                )
                                offline_db.add(offline_record)
                                offline_db.flush()  # Flush so subsequent duplicate checks can see this record
                                stored_count += 1
                                log.info(f"✅ [NetworkFailover] Stored order {po_num} (flushed to session)")
                            except Exception as item_err:
                                log.error(f"Failed to store offline item {order.get('po_number')}: {item_err}")
                        
                        if stored_count > 0:
                            offline_db.commit()
                            log.info(f"✅ Successfully stored {stored_count} orders in offline_confirmations table")
                            
                            # ✅ Update process_orders - treat offline as confirmed
                            try:
                                for order in orders_data:
                                    po_num = order.get('po_number')
                                    shift = (order.get('shift') or '').upper()
                                    confirmed_weight = float(order.get('confirmed_weight', 0))
                                    is_final = order.get('is_final', False)
                                    
                                    if po_num and shift in ('A', 'B', 'C'):
                                        shift_col = f"confirmed_shift_{shift.lower()}"
                                        
                                        if shift == 'A':
                                            last_calc = f"(COALESCE(confirmed_shift_a, 0) + :w) + COALESCE(confirmed_shift_b, 0) + COALESCE(confirmed_shift_c, 0)"
                                        elif shift == 'B':
                                            last_calc = f"COALESCE(confirmed_shift_a, 0) + (COALESCE(confirmed_shift_b, 0) + :w) + COALESCE(confirmed_shift_c, 0)"
                                        else:
                                            last_calc = f"COALESCE(confirmed_shift_a, 0) + COALESCE(confirmed_shift_b, 0) + (COALESCE(confirmed_shift_c, 0) + :w)"
                                        
                                        # ✅ Feb 5, 2026: Set status to 'Validated' on successful SAP confirmation
                                        # Preserve existing Validated status, upgrade Completed → Validated on final
                                        offline_db.execute(text(f"""
                                            UPDATE process_orders
                                            SET {shift_col} = COALESCE({shift_col}, 0) + :w,
                                                last_confirmed_qty = {last_calc},
                                                confirmed_qty = {last_calc},
                                                is_final_sent = CASE WHEN :is_final THEN TRUE ELSE is_final_sent END,
                                                status = CASE 
                                                    WHEN status = 'Validated' THEN 'Validated'
                                                    WHEN status = 'Completed' AND :is_final THEN 'Validated'
                                                    WHEN status = 'Completed' THEN 'Completed'
                                                    ELSE status
                                                END,
                                                updated_at = NOW()
                                            WHERE order_id = :po
                                        """), {"w": confirmed_weight, "is_final": is_final, "po": po_num})
                                offline_db.commit()
                                log.info(f"✅ Updated confirmation values for {len(orders_data)} orders (offline)")
                            except Exception as update_err:
                                log.error(f"Failed to update process_orders: {update_err}")
            except Exception as store_err:
                log.error(f"❌ Failed to store offline confirmations after network error: {store_err}")
                import traceback
                traceback.print_exc()
            
            return {
                "ok": True,
                "offline_mode": True,
                "message": f"Network error - {stored_count} order(s) confirmed offline (will sync to SAP later)",
                "successful_count": stored_count,
                "failed_count": len(orders_data) - stored_count,
                "offline_stored_count": stored_count,
                "successful_orders": [order.get('po_number') for order in orders_data],
                "failed_orders": []
            }

    def confirm_offline(self, orders_data: List[Dict[str, Any]]) -> Dict[str, Any]:
        """
        Send offline confirmation to SAP using the same authentication pattern as KPI endpoints.
        
        Args:
            orders_data: List of order dictionaries with required fields
            
        Returns:
            Dict with confirmation results
        """
        log.info(f"🚀 confirm_offline() called with {len(orders_data)} order(s), mock_mode={self.mock_mode}")
        
        endpoint = "/zmi_conf_offlin/CONFOFF"
        
        # Log confirmation start (wrap in try/except to not block if logging fails)
        try:
            log_id = log_sap_event(
                action="Offline Confirmation Started",
                status="InProgress",
                details=f"Starting offline confirmation for {len(orders_data)} orders",
                metadata={"order_count": len(orders_data), "endpoint": endpoint}
            )
        except Exception as log_event_err:
            log.warning(f"⚠️ Failed to log SAP event: {log_event_err} - continuing anyway")
        
        try:
            # Convert to JSON format for offline confirmation
            log.info(f"🔍 Converting {len(orders_data)} order(s) to JSON format for offline confirmation...")
            json_data = self._convert_to_json_format(orders_data, "offline")
            log.info(f"✅ Offline JSON format data prepared: {len(json_data)} order(s), {len(json.dumps(json_data))} characters")
            log.info(f"🔍 JSON data preview: {json.dumps(json_data, default=str)[:500]}...")
            
            if not json_data:
                log.error(f"❌ ERROR: _convert_to_json_format returned empty list! Input had {len(orders_data)} order(s)")
                log.error(f"❌ Input orders_data: {json.dumps(orders_data, default=str)[:500]}")
                return {
                    "ok": False,
                    "error": "No orders to send after JSON conversion (possibly filtered out)",
                    "successful_count": 0,
                    "failed_count": len(orders_data),
                    "successful_orders": [],
                    "failed_orders": [order.get('po_number', '').lstrip('0') for order in orders_data]
                }
            
            # Get URL (mock or production)
            url = self._get_url(endpoint)
            log.info(f"📤 Sending offline confirmation to: {url}")
            log.info(f"📦 Full JSON data: {json.dumps(json_data, default=str)}")
            
            # ✅ LOG REQUEST TO DB (wrap in try/except to not block if logging fails)
            db_log_id = None  # Initialize to avoid undefined variable
            try:
                db_log_id = log_sap_request(
                    endpoint=url,
                    method="POST",
                    payload=json_data,
                    po_number=orders_data[0].get('po_number') if orders_data else None,
                    log_type="offline_confirmation"
                )
            except Exception as log_err:
                log.warning(f"⚠️ Failed to log SAP request to DB: {log_err} - continuing anyway")
            
            # ============================================================
            # MOCK MODE: Simple POST request without CSRF/auth
            # ============================================================
            if self.mock_mode:
                log.info("🔧 MOCK MODE: Sending simple POST to demo server...")
                log.info(f"🔧 MOCK MODE: URL = {url}")
                log.info(f"🔧 MOCK MODE: Sending {len(json_data)} order(s) for OFFLINE confirmation")
                if json_data:
                    first_order = json_data[0] if isinstance(json_data, list) else json_data
                    log.info(f"🔧 MOCK MODE: First order PO = {first_order.get('PROCESS_ORDER', first_order.get('po_number', 'N/A'))}")
                    log.info(f"🔧 MOCK MODE: Full payload keys = {list(first_order.keys()) if isinstance(first_order, dict) else 'N/A'}")
                try:
                    log.info(f"🔧 MOCK MODE: About to POST to {url} with {len(json_data) if isinstance(json_data, list) else 1} order(s)")
                    log.info(f"🔧 MOCK MODE: Full payload being sent: {json.dumps(json_data, indent=2, default=str)[:1000]}")
                    post_response = requests.post(
                        url,
                        json=json_data,
                        timeout=30
                    )
                    log.info(f"✅ MOCK MODE: POST response status: {post_response.status_code}")
                    log.info(f"✅ MOCK MODE: POST response headers: {dict(post_response.headers)}")
                    log.info(f"✅ MOCK MODE: POST response text (first 500 chars): {post_response.text[:500]}")
                    
                    # ✅ LOG RESPONSE TO JSON FILE (Mock Mode - Offline) - Added Jan 28, 2026
                    try:
                        log_sap_response(
                            log_id=db_log_id,
                            response_payload={"text": post_response.text, "status_code": post_response.status_code},
                            status_code=post_response.status_code,
                            duration_ms=int(post_response.elapsed.total_seconds() * 1000) if hasattr(post_response, 'elapsed') else None
                        )
                    except Exception as log_err:
                        log.warning(f"Warning: Failed to log mock offline response: {log_err}")
                    
                    # ✅ MOCK MODE: Return success immediately (demo server always accepts)
                    if post_response.status_code in [200, 201]:
                        log.info(f"✅ MOCK MODE: Demo server accepted confirmation - returning success")
                        successful_orders = [order.get('po_number', '').lstrip('0') for order in orders_data]
                        return {
                            "ok": True,
                            "message": f"Mock mode: Successfully sent {len(orders_data)} order(s) to demo server",
                            "sap_response": post_response.text,
                            "successful_count": len(orders_data),
                            "failed_count": 0,
                            "successful_orders": successful_orders,
                            "failed_orders": []
                        }
                    else:
                        log.warning(f"⚠️ MOCK MODE: Demo server returned status {post_response.status_code}")
                        # Still return success in mock mode (demo server might return different codes)
                        successful_orders = [order.get('po_number', '').lstrip('0') for order in orders_data]
                        return {
                            "ok": True,
                            "message": f"Mock mode: Sent {len(orders_data)} order(s) to demo server (status {post_response.status_code})",
                            "sap_response": post_response.text,
                            "successful_count": len(orders_data),
                            "failed_count": 0,
                            "successful_orders": successful_orders,
                            "failed_orders": []
                        }
                except requests.exceptions.RequestException as mock_error:
                    # Connection error in mock mode - log and re-raise to be caught by outer handler
                    log.error(f"❌ MOCK MODE: Connection error to demo server: {mock_error}")
                    log.error(f"❌ MOCK MODE: Make sure demo_sap_server.py is running on port 6000")
                    # Re-raise to be caught by outer exception handler which will log to error_log
                    raise
            else:
                # ============================================================
                # PRODUCTION MODE: STEP 1: GET request to fetch CSRF token (HTTPS)
                # ============================================================
                log.info("Step 1: Fetching CSRF token via HTTPS...")
                
                get_headers = {
                    "x-csrf-token": "fetch",
                    "Accept": "application/json",
                    "User-Agent": "Python-Requests/2.31.0",
                    "Connection": "keep-alive"
                }
                
                token_response = requests.get(
                    url,
                    headers=get_headers,
                    auth=(self.username, self.password),
                    timeout=30,
                    verify=False  # Ignore SSL certificate errors
                )
                
                log.info(f"GET response status: {token_response.status_code}")
                log.info(f"GET response headers: {dict(token_response.headers)}")
                
                # Check for errors
                if token_response.status_code == 401:
                    log.error(f"❌ Authentication failed: {token_response.text[:300]}")
                    return {
                        "ok": False,
                        "error": "Authentication failed",
                        "successful_count": 0,
                        "failed_count": len(orders_data)
                    }
                
                if token_response.status_code not in [200, 201]:
                    log.error(f"❌ Failed to fetch CSRF token: {token_response.status_code}")
                    return {
                        "ok": False,
                        "error": f"Failed to get CSRF token. Status: {token_response.status_code}",
                        "successful_count": 0,
                        "failed_count": len(orders_data)
                    }
                
                # Extract CSRF token
                csrf_token = (
                    token_response.headers.get("x-csrf-token") or 
                    token_response.headers.get("X-CSRF-Token") or
                    token_response.headers.get("X-Csrf-Token")
                )
                
                cookies = token_response.cookies
                
                if not csrf_token:
                    log.error("❌ No CSRF token in response headers")
                    log.error(f"Available headers: {list(token_response.headers.keys())}")
                    return {
                        "ok": False,
                        "error": "CSRF token not found in response",
                        "successful_count": 0,
                        "failed_count": len(orders_data)
                    }
                
                log.info(f"✅ CSRF token received: {csrf_token[:30]}...")
                log.info(f"Cookies received: {len(cookies)} cookie(s)")
                
                # ============================================================
                # STEP 2: POST request with CSRF token and data (HTTPS)
                # ============================================================
                log.info("Step 2: Sending POST request with Offline Confirmation data...")
                
                post_headers = {
                    "x-csrf-token": csrf_token,
                    "Content-Type": "application/json",
                    "Accept": "application/json",
                    "User-Agent": "Python-Requests/2.31.0",
                    "Connection": "keep-alive"
                }
                
                post_response = requests.post(
                    url,
                    json=json_data,  # Use json parameter instead of data
                    headers=post_headers,
                    cookies=cookies,
                    auth=(self.username, self.password),
                    timeout=30,
                    verify=False
                )
                
                # ✅ LOG RESPONSE TO DB AND JSON FILE
                try:
                    log_sap_response(
                        log_id=db_log_id,
                        response_payload={"text": post_response.text},
                        status_code=post_response.status_code,
                        duration_ms=int(post_response.elapsed.total_seconds() * 1000)
                    )
                    log.info(f"✅ [REAL SAP OFFLINE] Response logged to JSON file")
                except Exception as log_err:
                    log.warning(f"⚠️ [REAL SAP OFFLINE] Failed to log response: {log_err}")
                
                log.info(f"POST response status: {post_response.status_code}")
                log.info(f"POST response: {post_response.text[:500]}")
            
            # Check success
            if post_response.status_code in [200, 201]:
                # Parse SAP response to detect individual order status (similar to online confirmation)
                try:
                    sap_response_text = post_response.text.strip()
                    
                    # Check if response is a JSON array
                    if sap_response_text.startswith('[') and sap_response_text.endswith(']'):
                        log.info("📋 Parsing SAP offline response array...")
                        sap_orders = json.loads(sap_response_text)
                        
                        successful_orders = []
                        failed_orders = []
                        
                        # Parse each order's result
                        for sap_order in sap_orders:
                            message = sap_order.get('MESSAGE', '')
                            po_number = sap_order.get('PROCESS_ORDER', '').lstrip('0')  # Remove leading zeros
                            
                            log.info(f"Offline Order {po_number}: {message}")
                            
                            # Check if order was actually saved successfully
                            success_indicators = ['saved', 'confirmations have been entered', 'confirmed', 'successfully', 'success']
                            has_success = any(indicator in message.lower() for indicator in success_indicators)
                            has_error = any(error_keyword in message.lower() for error_keyword in [
                                'already being processed',
                                'error',
                                'failed',
                                'locked',
                                'not found',
                                'invalid',
                                'reject',
                                'rejected',
                                'denied',
                                'refused',
                                'cannot',
                                'unable',
                                'warning',
                                'exception'
                            ])
                            
                            # ✅ IMPROVED LOGIC: If no success indicator OR has error indicator, treat as failed
                            if has_success and not has_error:
                                successful_orders.append(po_number)
                                log.info(f"✅ Offline Order {po_number}: SUCCESS")
                            else:
                                # Treat as failed if error indicators present OR no success indicators
                                failed_orders.append({
                                    "po_number": po_number,
                                    "error": message.strip() if message.strip() else "SAP offline confirmation rejected - no success message",
                                    "material": sap_order.get('MATERIAL', ''),
                                    "batch": sap_order.get('BATCH', ''),
                                    "status": sap_order.get('STATUS', ''),
                                    "full_sap_order": sap_order  # Include full SAP response for debugging
                                })
                                log.warning(f"❌ Offline Order {po_number}: FAILED - {message}")
                        
                        # ✅ Log failed orders to error_log table
                        # NOTE: SAP rejections go ONLY to error_log, NOT to offline_confirmations
                        # Per Dec_13_changes.md fallback strategy document
                        for fail in failed_orders:
                            po = fail.get("po_number", "")
                            error_msg = fail.get("error", "SAP offline confirmation failed")
                            # Find the original order data for payload
                            original_order = next((o for o in orders_data if str(o.get("po_number", "")).lstrip("0") == str(po).lstrip("0")), None)
                            
                            # Build comprehensive payload with all relevant information
                            # ✅ CRITICAL: Include vpn_connected and http_status per fallback strategy
                            try:
                                payload = {
                                    "sent_payload": original_order if original_order else {},
                                    "sap_reply": fail,
                                    "sap_response": sap_response_text[:1000] if 'sap_response_text' in locals() else "",
                                    "confirmation_type": "offline",
                                    "timestamp": datetime.now().isoformat(),
                                    "vpn_connected": True,  # ✅ VPN was connected (request reached SAP)
                                    "http_status": post_response.status_code  # ✅ HTTP request succeeded
                                }
                            except Exception as payload_err:
                                payload = {"error": f"Payload creation failed: {str(payload_err)}"}
                            
                            # Ensure PO number is properly formatted (remove leading zeros for consistency)
                            po_clean = str(po).lstrip("0") if po else ""
                            
                            log_order_error(
                                po_number=po_clean,
                                error_type="sap_failed",
                                error_message=error_msg,
                                payload=payload,
                                source="sap_offline"
                            )
                            log.info(f"📌 Error logged for PO {po_clean}: {error_msg}")
                        
                        # ✅ CRITICAL: SAP rejections are logged ONLY to error_log, NOT to offline_confirmations
                        # Per Dec_13_changes.md fallback strategy:
                        # - offline_confirmations is for VPN disconnected (network issue)
                        # - error_log is for SAP rejections (SAP processed request but rejected)
                        # Users can reprocess from error_log with updated scrap/confirmed_text
                        if failed_orders:
                            log.warning(f"⚠️ {len(failed_orders)} orders rejected by SAP - logged to error_log (NOT offline_confirmations)")
                            log.info(f"📋 Failed orders (SAP rejected): {[f.get('po_number') for f in failed_orders]}")
                            log.info(f"💡 Use Error Log UI to reprocess these orders with updated scrap/confirmed_text")
                        
                        # Determine overall status
                        total_orders = len(orders_data)
                        success_count = len(successful_orders)
                        failed_count = len(failed_orders)
                        
                        if success_count == total_orders:
                            status = "Success"
                            log.info(f"✅ All {total_orders} offline orders confirmed successfully")
                        elif success_count > 0:
                            status = "PartialSuccess"
                            log.warning(f"⚠️ Partial offline success: {success_count}/{total_orders} orders confirmed")
                        else:
                            status = "Failed"
                            log.error(f"❌ All {total_orders} offline orders failed")
                        
                        # Log detailed results
                        log_sap_event(
                            action="Offline Confirmation Completed",
                            status=status,
                            details=f"Offline confirmation: {success_count} succeeded, {failed_count} failed",
                            metadata={
                                "order_count": total_orders,
                                "successful_count": success_count,
                                "failed_count": failed_count,
                                "successful_orders": successful_orders,
                                "failed_orders": failed_orders,
                                "sap_response": sap_response_text[:1000]  # Limit size
                            }
                        )
                        
                        return {
                            "ok": True,
                            "message": f"Offline confirmation: {success_count} succeeded, {failed_count} failed out of {total_orders}",
                            "sap_response": sap_response_text,
                            "successful_count": success_count,
                            "failed_count": failed_count,
                            "successful_orders": successful_orders,
                            "failed_orders": failed_orders
                        }
                    
                    else:
                        # Response is not a JSON array - treat as generic success/error
                        log.warning("⚠️ SAP offline response is not a JSON array, checking for success/error indicators...")
                        
                        # Check for error indicators in response
                        error_indicators = ['error', 'failed', 'reject', 'rejected', 'denied', 'exception', 'invalid', 'cannot', 'unable']
                        has_error_in_response = any(indicator in sap_response_text.lower() for indicator in error_indicators)
                        has_success_in_response = "Data Saved Correctly" in sap_response_text or "success" in sap_response_text.lower()
                        
                        if has_error_in_response and not has_success_in_response:
                            # Response contains errors - log all orders as failed
                            log.error(f"❌ SAP offline response contains error indicators: {sap_response_text[:200]}")
                            
                            failed_orders_list = []
                            for order in orders_data:
                                po = str(order.get('po_number', '')).lstrip('0')
                                failed_orders_list.append(po)
                                
                                payload = {
                                    "sent_payload": order,
                                    "sap_response": sap_response_text[:1000],
                                    "confirmation_type": "offline",
                                    "timestamp": datetime.now().isoformat(),
                                    "note": "Non-array response with error indicators"
                                }
                                
                                log_order_error(
                                    po_number=po,
                                    error_type="sap_failed",
                                    error_message=f"SAP offline confirmation rejected: {sap_response_text[:200]}",
                                    payload=payload,
                                    source="sap_offline"
                                )
                                log.info(f"📌 Error logged for PO {po}: Non-array response with errors")
                            
                            log_sap_event(
                                action="Offline Confirmation Failed",
                                status="Error",
                                details=f"All {len(orders_data)} orders failed - response contains errors",
                                metadata={
                                    "order_count": len(orders_data),
                                    "successful_count": 0,
                                    "failed_count": len(orders_data),
                                    "failed_orders": failed_orders_list,
                                    "sap_response": sap_response_text[:1000]
                                }
                            )
                            
                            return {
                                "ok": False,
                                "message": f"All {len(orders_data)} orders failed - SAP response contains errors",
                                "sap_response": sap_response_text,
                                "successful_count": 0,
                                "failed_count": len(orders_data),
                                "successful_orders": [],
                                "failed_orders": failed_orders_list
                            }
                        elif has_success_in_response:
                            log.info("✅ SUCCESS! Offline confirmation data saved to SAP")
                            
                            # Return all orders as successful since we can't parse individual results
                            successful_orders = [order.get('po_number', '').lstrip('0') for order in orders_data]
                            
                            log_sap_event(
                                action="Offline Confirmation Completed",
                                status="Success",
                                details=f"Successfully sent {len(orders_data)} orders for offline confirmation",
                                metadata={
                                    "order_count": len(orders_data),
                                    "successful_count": len(orders_data),
                                    "failed_count": 0,
                                    "successful_orders": successful_orders,
                                    "failed_orders": [],
                                    "sap_response": sap_response_text
                                }
                            )
                            
                            return {
                                "ok": True,
                                "message": f"Successfully sent {len(orders_data)} orders for offline confirmation",
                                "sap_response": sap_response_text,
                                "successful_count": len(orders_data),
                                "failed_count": 0,
                                "successful_orders": successful_orders,
                                "failed_orders": []
                            }
                        else:
                            # Ambiguous response - check if it looks like an error
                            log.warning("⚠️ Ambiguous SAP offline response - cannot determine success/failure clearly")
                            
                            # If response is short and doesn't look like success, treat as potential failure
                            if len(sap_response_text) < 50 and not has_success_in_response:
                                log.warning("⚠️ Short ambiguous response - logging as potential failure")
                                for order in orders_data:
                                    po = str(order.get('po_number', '')).lstrip('0')
                                    payload = {
                                        "sent_payload": order,
                                        "sap_response": sap_response_text,
                                        "confirmation_type": "offline",
                                        "timestamp": datetime.now().isoformat(),
                                        "note": "Ambiguous response - treated as potential failure"
                                    }
                                    log_order_error(
                                        po_number=po,
                                        error_type="sap_failed",
                                        error_message=f"Ambiguous SAP offline response: {sap_response_text}",
                                        payload=payload,
                                        source="sap_offline"
                                    )
                                
                                return {
                                    "ok": False,
                                    "message": f"Ambiguous response from SAP for {len(orders_data)} orders",
                                    "sap_response": sap_response_text,
                                    "successful_count": 0,
                                    "failed_count": len(orders_data),
                                    "successful_orders": [],
                                    "failed_orders": [str(order.get('po_number', '')).lstrip('0') for order in orders_data]
                                }
                            
                            # Default: assume success if 200/201 but can't parse clearly
                            log.info("✅ POST successful (non-standard response format)")
                            
                            # Return all orders as successful since we can't parse individual results
                            successful_orders = [order.get('po_number', '').lstrip('0') for order in orders_data]
                            
                            log_sap_event(
                                action="Offline Confirmation Completed",
                                status="Success",
                                details=f"Successfully sent {len(orders_data)} orders for offline confirmation",
                                metadata={
                                    "order_count": len(orders_data),
                                    "successful_count": len(orders_data),
                                    "failed_count": 0,
                                    "successful_orders": successful_orders,
                                    "failed_orders": [],
                                    "sap_response": sap_response_text,
                                    "note": "Non-standard response format"
                                }
                            )
                            
                            return {
                                "ok": True,
                                "message": f"Successfully sent {len(orders_data)} orders for offline confirmation",
                                "sap_response": sap_response_text,
                                "successful_count": len(orders_data),
                                "failed_count": 0,
                                "successful_orders": successful_orders,
                                "failed_orders": []
                            }
                    
                except json.JSONDecodeError as e:
                    log.error(f"❌ Failed to parse SAP offline response JSON: {e}")
                    log.error(f"Response text: {post_response.text[:200]}")
                    
                    # Check if response contains error indicators
                    response_text = post_response.text
                    error_indicators = ['error', 'failed', 'reject', 'rejected', 'denied', 'exception', 'invalid', 'cannot', 'unable']
                    has_error_in_response = any(indicator in response_text.lower() for indicator in error_indicators)
                    
                    if has_error_in_response:
                        # Response contains errors - log all orders as failed
                        log.error(f"❌ Response contains error indicators despite JSON parse failure")
                        failed_orders_list = []
                        for order in orders_data:
                            po = str(order.get('po_number', '')).lstrip('0')
                            failed_orders_list.append(po)
                            
                            payload = {
                                "sent_payload": order,
                                "sap_response": response_text[:1000],
                                "confirmation_type": "offline",
                                "timestamp": datetime.now().isoformat(),
                                "parse_error": str(e),
                                "note": "JSON parse failed but response contains error indicators"
                            }
                            
                            log_order_error(
                                po_number=po,
                                error_type="sap_failed",
                                error_message=f"SAP offline confirmation failed (parse error): {response_text[:200]}",
                                payload=payload,
                                source="sap_offline"
                            )
                            log.info(f"📌 Error logged for PO {po}: JSON parse failed with error indicators")
                        
                        return {
                            "ok": False,
                            "message": f"Failed to parse SAP response and response contains errors",
                            "sap_response": response_text,
                            "successful_count": 0,
                            "failed_count": len(orders_data),
                            "successful_orders": [],
                            "failed_orders": failed_orders_list,
                            "parse_error": str(e)
                        }
                    else:
                        # Can't parse but no clear error indicators - treat as success but log warning
                        log.warning(f"⚠️ Could not parse SAP offline response but no error indicators found")
                        successful_orders = [order.get('po_number', '').lstrip('0') for order in orders_data]
                        
                        return {
                            "ok": True,
                            "message": f"Sent {len(orders_data)} orders (couldn't parse SAP response)",
                            "sap_response": post_response.text,
                            "successful_count": len(orders_data),
                            "failed_count": 0,
                            "successful_orders": successful_orders,
                            "failed_orders": [],
                            "parse_error": str(e)
                        }
            else:
                log.error(f"❌ POST failed: {post_response.status_code}")
                
                # ✅ Log all failed orders to error_log table
                for order in orders_data:
                    po = str(order.get('po_number', '')).lstrip('0')
                    payload = {
                        "sent_payload": order,
                        "sap_response": post_response.text[:1000] if hasattr(post_response, 'text') else "",
                        "status_code": post_response.status_code,
                        "confirmation_type": "offline",
                        "timestamp": datetime.now().isoformat()
                    }
                    log_order_error(
                        po_number=po,
                        error_type="sap_failed",
                        error_message=f"POST failed with status {post_response.status_code}",
                        payload=payload,
                        source="sap_offline"
                    )
                    log.info(f"📌 Error logged for PO {po}: HTTP {post_response.status_code}")
                
                return {
                    "ok": False,
                    "error": f"POST failed with status {post_response.status_code}",
                    "successful_count": 0,
                    "failed_count": len(orders_data),
                    "successful_orders": [],
                    "failed_orders": [order.get('po_number', '').lstrip('0') for order in orders_data]
                }
            
        except requests.exceptions.RequestException as e:
            log.error(f"❌ Offline confirmation failed (RequestException): {e}")
            import traceback
            log.error(f"❌ Traceback: {traceback.format_exc()}")
            
            # Log confirmation failure
            log_sap_event(
                action="Offline Confirmation Failed",
                status="Error",
                details=f"SAP offline confirmation error: {str(e)}",
                error_code="CONFIRMATION_ERROR",
                metadata={
                    "order_count": len(orders_data),
                    "successful_count": 0,
                    "failed_count": len(orders_data),
                    "error": str(e)
                }
            )
            
            # ✅ Log all failed orders to error_log table
            for order in orders_data:
                # Extract PO number with proper handling
                po_raw = order.get('po_number') or order.get('process_order') or order.get('order_id') or ''
                po = str(po_raw).lstrip('0') if po_raw else ''
                
                # If PO is still empty, try to get from order_id or other fields
                if not po:
                    po = str(order.get('id', '') or order.get('order_id', '') or 'UNKNOWN')
                
                payload = {
                    "sent_payload": order,
                    "error": str(e),
                    "error_type": type(e).__name__,
                    "confirmation_type": "offline",
                    "timestamp": datetime.now().isoformat(),
                    "url": url if 'url' in locals() else "unknown"
                }
                
                error_msg = f"SAP offline confirmation error: {str(e)}"
                
                try:
                    log_order_error(
                        po_number=po if po else "UNKNOWN",
                        error_type="sap_failed",
                        error_message=error_msg,
                        payload=payload,
                        source="sap_offline"
                    )
                    log.info(f"📌 Error logged for PO {po}: Request exception - {str(e)}")
                except Exception as log_err:
                    log.exception(f"❌ Failed to log error for order {po}: {log_err}")
                    # Try to log with minimal info
                    try:
                        log_order_error(
                            po_number=po if po else "UNKNOWN",
                            error_type="sap_failed",
                            error_message=f"Error logging failed: {str(log_err)} | Original: {error_msg}",
                            payload={"original_error": str(e)},
                            source="sap_offline"
                        )
                    except:
                        log.error(f"❌❌ CRITICAL: Could not log error for order at all. PO: {po}, Error: {str(e)}")
            
            return {
                "ok": False,
                "error": f"SAP offline confirmation error: {str(e)}",
                "successful_count": 0,
                "failed_count": len(orders_data),
                "successful_orders": [],
                "failed_orders": [order.get('po_number', '').lstrip('0') for order in orders_data]
            }
        
        except Exception as general_error:
            # Catch any other unexpected exceptions
            log.error(f"❌❌ UNEXPECTED ERROR in confirm_offline: {general_error}")
            import traceback
            log.error(f"❌❌ Traceback: {traceback.format_exc()}")
            return {
                "ok": False,
                "error": f"Unexpected error in offline confirmation: {str(general_error)}",
                "successful_count": 0,
                "failed_count": len(orders_data),
                "successful_orders": [],
                "failed_orders": [order.get('po_number', '').lstrip('0') for order in orders_data]
            }
    

    def _fallback_confirmation(self, orders_data: List[Dict[str, Any]], confirmation_type: str) -> Dict[str, Any]:
        """
        Fallback confirmation when SAP is not available.
        This simulates successful confirmation for development/testing purposes.
        
        Args:
            orders_data: List of order dictionaries with required fields
            confirmation_type: "auto" for online confirmation, "manual" for offline confirmation
            
        Returns:
            Dict with simulated confirmation results
        """
        log.warning(f"🔧 FALLBACK MODE: SAP server not available, simulating {confirmation_type} confirmation")
        log.warning(f"📋 Processing {len(orders_data)} orders in fallback mode")
        
        # Simulate some orders succeeding and some failing for realistic testing
        successful_count = max(1, len(orders_data) - 1) if len(orders_data) > 1 else len(orders_data)
        failed_count = len(orders_data) - successful_count
        
        # Create successful and failed order lists
        successful_orders = [order.get('po_number', '').lstrip('0') for order in orders_data[:successful_count]]
        failed_orders = [order.get('po_number', '').lstrip('0') for order in orders_data[successful_count:]]
        
        return {
            "ok": True,
            "message": f"FALLBACK: Simulated {confirmation_type} confirmation for {len(orders_data)} orders",
            "sap_response": {
                "fallback_mode": True,
                "confirmation_type": confirmation_type,
                "orders_processed": len(orders_data),
                "note": "SAP server not available - using fallback confirmation"
            },
            "successful_count": successful_count,
            "failed_count": failed_count,
            "successful_orders": successful_orders,
            "failed_orders": failed_orders
        }

    def confirm_orders_batch(self, orders_data: List[Dict[str, Any]], confirmation_type: str = "auto") -> Dict[str, Any]:
        """
        Send batch confirmation to SAP (online for auto, offline for manual).
        In mock mode, sends to demo server at http://localhost:6000/mock.
        
        Args:
            orders_data: List of order dictionaries with required fields
            confirmation_type: "auto" for online confirmation, "manual" for offline confirmation
            
        Returns:
            Dict with confirmation results
        """
        # ✅ FIX: In mock mode, still call confirm_online/confirm_offline
        # They will automatically route to the demo server
        if self.mock_mode:
            log.info(f"🔧 MOCK MODE: Sending {confirmation_type} confirmation to demo server")
        
        # Try SAP confirmation (will use mock server if mock_mode is True)
        if confirmation_type.lower() == "auto":
            result = self.confirm_online(orders_data)
        else:
            result = self.confirm_offline(orders_data)
        
        # If SAP confirmation fails due to connectivity/auth issues (only in production mode), use fallback
        if not self.mock_mode and not result.get("ok", False) and "Failed to retrieve CSRF token" in result.get("error", ""):
            log.warning("🔄 SAP confirmation failed, switching to fallback mode")
            return self._fallback_confirmation(orders_data, confirmation_type)
        
        return result
    
    def push_confirmation(self, orders_data: List[Dict[str, Any]], confirmation_type: str = "online") -> Dict[str, Any]:
        """
        Alias for confirm_online/confirm_offline based on confirmation_type.
        Used by shift-based confirmation logic.
        
        Args:
            orders_data: List of order dictionaries with required fields
            confirmation_type: "online" or "offline"
            
        Returns:
            Dict with confirmation results (converted to use 'success' key for compatibility)
        """
        if confirmation_type.lower() == "online":
            result = self.confirm_online(orders_data)
        else:
            result = self.confirm_offline(orders_data)
        
        # Convert result format to use 'success' key for compatibility
        if result.get("ok", False):
            return {"success": True, **result}
        else:
            return {"success": False, "message": result.get("error", "SAP confirmation failed"), **result}


# Global instance
sap_confirmation_service = SAPConfirmationService()

# Convenience functions
def confirm_orders_online(orders_data: List[Dict[str, Any]]) -> Dict[str, Any]:
    """Send online confirmation to SAP."""
    return sap_confirmation_service.confirm_online(orders_data)

def confirm_orders_offline(orders_data: List[Dict[str, Any]]) -> Dict[str, Any]:
    """Send offline confirmation to SAP."""
    return sap_confirmation_service.confirm_offline(orders_data)

def confirm_orders_batch(orders_data: List[Dict[str, Any]], confirmation_type: str = "auto") -> Dict[str, Any]:
    """Send batch confirmation to SAP."""
    return sap_confirmation_service.confirm_orders_batch(orders_data, confirmation_type)
