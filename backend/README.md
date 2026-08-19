# Hercules KPI Backend

This backend provides KPI calculations for the Hercules SFMS system, connecting to SQL Server database and providing REST API endpoints.

## Setup Instructions

### 1. Install Dependencies
```bash
pip install -r requirements.txt
```

### 2. Database Configuration
Make sure your SQL Server database is running and accessible. The connection string is configured in `database.py`.

### 3. Insert Sample Data (Optional)
If you want to test with sample data:
```bash
python insert_sample_data.py
```

### 4. Test Database Connection
```bash
python test_connection.py
```

### 5. Run the Backend Server
```bash
python app.py
```

The server will start on `http://localhost:5000`

## API Endpoints

### GET /api/kpi
Returns calculated KPI data from the database.

**Response Format:**
```json
{
  "milling_kpis": {
    "Mill Throughput (%)": 85.71,
    "Mill Time Efficiency (%)": 77.08,
    "Total Utilization (%)": 66.07,
    "Milling Gain": 96.43,
    "Screening Ratios": 60.71,
    "Water Consumption (m³)": 11.1,
    "Extraction Rates (%)": 76.67,
    "Milling Loss (%)": 23.33,
    "Net Hours (hrs)": 18.5,
    "Downtime (hrs)": 1.5
  },
  "packing_kpis": {
    "Packing Line Capacity (bags/hr)": 40.0,
    "Daily Packing Output (bags)": 6000.0,
    "Net Hours (hrs)": 1.0,
    "Downtime (hrs)": 15.0,
    "Machine Utilization (%)": 6.25
  }
}
```

## Database Schema

The `kpicalculations` table contains the following fields:
- `id`: Primary key
- `WG202`: Actual output
- `WG201`, `WG101`: Input values
- `WG301`, `WG302`: Flour and bran outputs
- `WG501`, `WG502`, `WG503`: Screenings
- `WG202_Total_Running_Time`: Net running hours
- `WG202_Stop_Start`: Downtime
- `Daily_Hours`: Total available hours
- `DM101`-`DM203`: Water consumption values
- `PL601`: Packing output
- `timestamp`: Record timestamp

## KPI Calculations

The backend calculates various KPIs including:
- Mill throughput and efficiency
- Water consumption
- Extraction rates
- Packing line performance
- Machine utilization

## Frontend Integration

The frontend connects to this backend via the `/api/kpi` endpoint and displays the calculated KPIs in real-time with automatic refresh every 30 seconds. 