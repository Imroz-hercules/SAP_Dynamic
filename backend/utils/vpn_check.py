import requests
import logging
from typing import Dict, Any, Optional

logger = logging.getLogger(__name__)

# Constants
SAP_ENDPOINT = "https://vhmioqs4ci.sap.mc3.com.sa:44300"

def check_vpn_connection() -> Dict[str, Any]:
    """
    Check if VPN connection to SAP is available.
    Directly monitors real SAP endpoint connectivity.
    Returns connected=True if VPN is working, False if not.
    
    Returns:
        {
            "connected": bool,
            "message": str,
            "error": Optional[str]
        }
    """
    logger.info("🔍 Checking VPN connection to real SAP endpoint...")

    try:
        # Try to reach the SAP server root or a lightweight endpoint
        # We use a short timeout (5 seconds) to avoid hanging
        # Using verify=False because of self-signed certs often used in internal networks
        import urllib3
        urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)
        
        response = requests.get(
            SAP_ENDPOINT, 
            timeout=5, 
            verify=False
        )
        
        # Any response code indicates network connectivity, even 401 or 404
        # We just want to know if the server is reachable
        return {
            "connected": True,
            "message": "VPN connected",
            "error": None
        }
        
    except requests.exceptions.ConnectionError as e:
        logger.warning(f"VPN Check Failed: Connection Error - {str(e)}")
        return {
            "connected": False,
            "message": "VPN disconnected",
            "error": "Connection refused or unreachable"
        }
    except requests.exceptions.Timeout as e:
        logger.warning(f"VPN Check Failed: Timeout - {str(e)}")
        return {
            "connected": False,
            "message": "VPN disconnected",
            "error": "Connection timed out"
        }
    except requests.exceptions.RequestException as e:
        logger.warning(f"VPN Check Failed: Request Exception - {str(e)}")
        return {
            "connected": False,
            "message": "VPN disconnected",
            "error": str(e)
        }
    except Exception as e:
        logger.error(f"VPN Check Error: {str(e)}")
        return {
            "connected": False,
            "message": "VPN check error",
            "error": str(e)
        }

