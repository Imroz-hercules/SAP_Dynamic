# SAP Confirmation Service

This document describes the new SAP Confirmation Service implementation that handles both online and offline confirmation APIs.

## Overview

The SAP Confirmation Service replaces the previous confirmation system and implements the actual SAP APIs for order confirmation:

- **Online Confirmation**: For auto-validated orders
- **Offline Confirmation**: For manually validated orders

## API Endpoints

### Online Confirmation
- **URL**: `https://vhmioqs4ci.sap.mc3.com.sa:44300/zmi_conf_online/CONF?sap-client=200`
- **Method**: POST
- **Authentication**: Basic Auth (Username: 99999, Password: P@ssw0rdP@ssw0rd)
- **CSRF Token**: Required (fetched via GET request with `x-csrf-token: fetch` header)
- **Protocol**: HTTPS (SAP forces all Python/API requests to use HTTPS)

### Offline Confirmation
- **URL**: `https://vhmioqs4ci.sap.mc3.com.sa:44300/zmi_conf_offlin/CONFOFF?sap-client=200`
- **Method**: POST
- **Authentication**: Basic Auth (Username: 99999, Password: P@ssw0rdP@ssw0rd)
- **CSRF Token**: Required (fetched via GET request with `x-csrf-token: fetch` header)
- **Protocol**: HTTPS (SAP forces all Python/API requests to use HTTPS)

## Request Format

### Online Confirmation Payload
```json
[
    {
        "process_order": "000013006742",
        "material": "000000000001400001",
        "version": "BKL1",
        "material_desc": "MMC BAKERIES FLOUR 80% - 45 KG",
        "total_qty": "1000.000",
        "confirmed_weight": "30",
        "uom": "BAG",
        "plant": "3130",
        "created_on": "20250928",
        "confirmed_at": "091100",
        "batch": "B-20250928-01",
        "status": "Confirmed",
        "final_confirmation": "",
        "shift": "A"
    }
]
```

### Offline Confirmation Payload
```json
[
    {
        "process_order": "000023002180",
        "material": "000000000001400001",
        "version": "BKL1",
        "material_desc": "MMC BAKERIES FLOUR 80% - 45 KG",
        "total_qty": "1000.000",
        "confirmed_weight": "5",
        "uom": "BAG",
        "plant": "3130",
        "created_on": "20250928",
        "confirmed_at": "091100",
        "batch": "B-20250928-01",
        "status": "Confirmed",
        "final_confirmation": "",
        "shift": "A",
        "CONFIRMED_TEXT": "Test Text",
        "scrap": "1"
    }
]
```

## Implementation Details

### File Structure
- `backend/services/sap_confirmation.py` - Main confirmation service
- `backend/routes/process_orders.py` - Updated API endpoint
- `backend/test_sap_confirmation.py` - Test script

### Key Features

1. **CSRF Token Handling**: Automatically fetches and uses CSRF tokens for each request
2. **Data Formatting**: 
   - Process order numbers are zero-padded to 12 characters
   - Material codes are zero-padded to 18 characters
   - Dates are formatted as YYYYMMDD
   - Times are formatted as HHMMSS
3. **Shift Mapping**: Converts numeric shift values to letter codes (A, B, C)
4. **Error Handling**: Comprehensive error handling with detailed logging
5. **Retry Logic**: Built-in retry strategy for network requests

### Usage

#### In Python Code
```python
from services.sap_confirmation import confirm_orders_batch

# For auto-validated orders (online confirmation)
result = confirm_orders_batch(orders_data, "auto")

# For manually validated orders (offline confirmation)
result = confirm_orders_batch(orders_data, "manual")
```

#### Via API Endpoint
```bash
POST /api/process_orders/push-confirmation
Content-Type: application/json

{
    "order_ids": [1, 2, 3]
}
```

## Response Format

```json
{
    "message": "Push confirmation completed for 3 orders (2 auto, 1 manual)",
    "successful_count": 3,
    "failed_count": 0,
    "auto_orders_count": 2,
    "manual_orders_count": 1,
    "results": [
        {
            "process_order": "13006742",
            "status": "success",
            "confirmation_type": "online",
            "sap_response": {...}
        }
    ]
}
```

## Testing

Run the test script to verify the implementation:

```bash
cd backend
python test_sap_confirmation.py
```

## Configuration

The service uses the following configuration:
- **Base URL**: `http://vhmioqs4ci.sap.mc3.com.sa:8000`
- **Username**: `99999`
- **Password**: `P@ssw0rdP@ssw0rd`
- **Client**: `200`
- **Timeout**: 30 seconds
- **Max Retries**: 3

## Error Handling

The service handles various error scenarios:
- Network connectivity issues
- Authentication failures
- CSRF token retrieval failures
- SAP API errors
- Data formatting errors

All errors are logged with detailed information for debugging.

## Migration Notes

This implementation replaces the previous `services/sap_confirm.py` service. The new service:
- Uses actual SAP APIs instead of stub responses
- Handles CSRF tokens properly
- Separates auto and manual confirmations
- Provides better error handling and logging
- Formats data according to SAP requirements
