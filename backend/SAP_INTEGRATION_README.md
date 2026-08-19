# SAP Process Orders Integration

This document describes the SAP integration for pulling process orders into the Hercules SFMS system.

## Overview

The system automatically pulls process orders from SAP every 3 hours and also allows manual synchronization through the UI. The integration includes:

- **Automatic Pulling**: Scheduled job runs every 3 hours
- **Manual Sync**: Users can trigger sync via the "Sync" button
- **Connection Testing**: Users can test SAP connection via the "Test SAP" button
- **Data Mapping**: SAP data is transformed to match the internal database schema
- **Error Handling**: Comprehensive error handling and logging

## SAP API Details

- **Endpoint**: `http://vhmioqs4ci.sap.mc3.com.sa:8000/zmi_get_orders/GETORD`
- **Authentication**: Basic Auth
- **Username**: `99999`
- **Password**: `P@ssw0rdP@ssw0rd`
- **Client**: `200`

## SAP Data Format

The SAP API returns an array of process orders with the following structure:

```json
[
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
]
```

## Database Schema

The `process_orders` table stores the transformed data with the following key fields:

- `order_id`: PROCESS_ORDER from SAP
- `material`: MATERIAL from SAP
- `version`: VERSION from SAP
- `quantity`: TOTAL_QTY from SAP
- `unit`: UOM from SAP
- `priority`: PRIORITY_ID from SAP
- `plant`: PLANT from SAP
- `confirmed_qty`: CONFIRMED_QTY from SAP
- `material_desc`: MATERIAL_DESC from SAP
- `sap_created_on`: CREATED_ON from SAP (parsed as datetime)
- `status`: Default "Open" for new orders
- `batch`: Auto-generated batch number

## Configuration

SAP settings can be configured via environment variables:

```bash
# SAP API Configuration
SAP_BASE_URL=http://vhmioqs4ci.sap.mc3.com.sa:8000
SAP_USERNAME=99999
SAP_PASSWORD=P@ssw0rdP@ssw0rd
SAP_CLIENT=200
SAP_TIMEOUT=30
SAP_MAX_RETRIES=3

# Pull Settings
SAP_PULL_INTERVAL_HOURS=3
SAP_AUTO_PULL_ENABLED=true
```

## API Endpoints

### Manual Sync
- **POST** `/api/process_orders/pull`
- Triggers manual synchronization with SAP
- Returns count of orders processed

### Test Connection
- **GET** `/api/process_orders/test-sap`
- Tests SAP API connection
- Returns connection status

### List Orders
- **GET** `/api/process_orders`
- Lists process orders with optional status filtering
- **GET** `/api/process_orders/queue`
- Lists orders in execution queue (Open/Pending status)

## Data Flow

1. **Scheduled Job**: Runs every 3 hours via `app_scheduler.py`
2. **SAP Client**: `SAPRealClient` fetches data from SAP API
3. **Data Transformation**: SAP format is converted to internal format
4. **Database Storage**: Orders are upserted into PostgreSQL
5. **UI Display**: Frontend displays orders with real-time updates

## Error Handling

- **Connection Errors**: Retry logic with exponential backoff
- **Data Validation**: Invalid orders are logged and skipped
- **Status Preservation**: Orders in progress are not overwritten
- **Logging**: Comprehensive logging for debugging

## Testing

Run the test script to verify SAP connection:

```bash
cd backend
python test_sap_connection.py
```

This will:
1. Test SAP API connection
2. Fetch sample orders
3. Test the pull service
4. Display results and any errors

## Monitoring

- Check application logs for SAP pull status
- Monitor the `/api/process_orders/test-sap` endpoint
- Review database for new orders after scheduled pulls
- Use the UI sync button for manual testing

## Troubleshooting

### Common Issues

1. **VPN Connection**: Ensure VPN is connected to access SAP API
2. **Authentication**: Verify username/password are correct
3. **Network**: Check firewall and network connectivity
4. **Data Format**: Verify SAP API returns expected JSON format

### Debug Steps

1. Test SAP connection via UI button
2. Check application logs for errors
3. Run the test script manually
4. Verify database connectivity
5. Check scheduler is running

## Security Notes

- SAP credentials are stored in environment variables
- API calls use HTTPS where possible
- Database connections are secured
- Logs do not contain sensitive data

## Future Enhancements

- Add order confirmation back to SAP
- Implement order status updates
- Add more detailed error reporting
- Support for multiple SAP clients
- Real-time order notifications
