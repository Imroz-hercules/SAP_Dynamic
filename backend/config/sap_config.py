import os

# SAP Configuration
SAP_CONFIG = {
    "base_url": os.getenv("SAP_BASE_URL", "http://vhmioqs4ci.sap.mc3.com.sa:8000"),
    "endpoint": os.getenv("SAP_ENDPOINT", "/zmi_get_orders/GETORD"),
    "username": os.getenv("SAP_USERNAME", "99999"),
    "password": os.getenv("SAP_PASSWORD", "P@ssw0rdP@ssw0rd"),
    "client": os.getenv("SAP_CLIENT", "200"),
    "timeout": int(os.getenv("SAP_TIMEOUT", "30")),
    "max_retries": int(os.getenv("SAP_MAX_RETRIES", "3")),
    "mock_mode": os.getenv("SAP_MOCK_MODE", "true").lower() == "true",
    "fallback_mode": os.getenv("SAP_FALLBACK_MODE", "true").lower() == "true"
}

# SAP Confirmation Endpoints
SAP_CONFIRMATION_ENDPOINTS = {
    "online": "/zmi_conf_online/CONF",
    "offline": "/zmi_conf_offlin/CONFOFF"
}