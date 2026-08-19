# Reports Backend Setup

This document explains how to set up the backend for the Reports functionality.

## Overview

The Reports system includes:
- **Shift Reports**: Production order data with timestamps
- **Daily Summary**: Aggregated daily production metrics
- **API Routes**: RESTful endpoints for data management
- **Database Models**: PostgreSQL tables for data storage

## Database Setup

### 1. Create Tables

Run the following command to create the necessary database tables:

```bash
cd Backend
python create_reports_tables.py
```

This script will:
- Create `shift_reports` table
- Create `daily_summaries` table
- Seed sample data for testing
- Display table structures

### 2. Database Schema

#### Shift Reports Table
```sql
CREATE TABLE shift_reports (
    id SERIAL PRIMARY KEY,
    po_number VARCHAR(64) NOT NULL,
    material VARCHAR(128) NOT NULL,
    version VARCHAR(32) NOT NULL DEFAULT 'v1.0',
    planned_quantity NUMERIC(18,3) NOT NULL DEFAULT 0,
    actual_quantity NUMERIC(18,3) NOT NULL DEFAULT 0,
    unit VARCHAR(16) NOT NULL DEFAULT 'T',
    flour_extraction_percent NUMERIC(5,2) NOT NULL DEFAULT 0,
    utilization_percent NUMERIC(5,2) NOT NULL DEFAULT 0,
    loss_percent NUMERIC(5,2) NOT NULL DEFAULT 0,
    status VARCHAR(32) NOT NULL DEFAULT 'Pending',
    timestamp TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT NOW(),
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);
```

#### Daily Summary Table
```sql
CREATE TABLE daily_summaries (
    id SERIAL PRIMARY KEY,
    report_date TIMESTAMP WITH TIME ZONE NOT NULL,
    total_wheat NUMERIC(18,3) NOT NULL DEFAULT 0,
    total_flour NUMERIC(18,3) NOT NULL DEFAULT 0,
    total_bran NUMERIC(18,3) NOT NULL DEFAULT 0,
    total_water NUMERIC(18,3) NOT NULL DEFAULT 0,
    total_packing NUMERIC(18,3) NOT NULL DEFAULT 0,
    efficiency_percent NUMERIC(5,2) NOT NULL DEFAULT 0,
    wheat_unit VARCHAR(16) NOT NULL DEFAULT 'T',
    flour_unit VARCHAR(16) NOT NULL DEFAULT 'T',
    bran_unit VARCHAR(16) NOT NULL DEFAULT 'T',
    water_unit VARCHAR(16) NOT NULL DEFAULT 'm³',
    packing_unit VARCHAR(16) NOT NULL DEFAULT 'Bags',
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);
```

## API Endpoints

### Shift Reports
- `GET /api/reports/shift-reports` - Get all shift reports
- `POST /api/reports/shift-reports` - Create new shift report

### Daily Summary
- `GET /api/reports/daily-summary` - Get daily summary
- `POST /api/reports/daily-summary` - Create/update daily summary

### Export & Integration
- `POST /api/reports/export-pdf` - Export reports to PDF
- `POST /api/reports/send-to-sap` - Send reports to SAP
- `GET /api/reports/stats` - Get reports statistics

## Frontend Integration

The frontend has been updated to:
- Fetch data from the new API endpoints
- Display real-time data instead of mock data
- Include timestamp column in shift reports table
- Show loading states and error handling
- Provide refresh functionality

## Sample Data

The setup script includes sample data:
- 4 shift reports with different materials and statuses
- 1 daily summary with aggregated metrics
- Realistic production data for testing

## Usage

1. **Start the backend server**:
   ```bash
   cd Backend
   python app.py
   ```

2. **Access the reports page** in your frontend application

3. **View real data** from the database instead of mock data

4. **Use the refresh button** to reload data from the API

## Features Added

### Backend
- ✅ PostgreSQL models for shift reports and daily summaries
- ✅ RESTful API routes with proper error handling
- ✅ Database migration script with sample data
- ✅ Integration with existing Flask app structure

### Frontend
- ✅ Real-time data fetching from API
- ✅ Timestamp column in shift reports table
- ✅ Loading states and error handling
- ✅ Refresh functionality
- ✅ TypeScript type definitions
- ✅ Professional styling maintained

## Troubleshooting

### Database Connection Issues
- Ensure PostgreSQL is running on localhost:5432
- Verify database credentials in `database.py`
- Check if the `sap` database exists

### API Issues
- Verify the backend server is running on port 5000
- Check CORS settings if frontend can't connect
- Review server logs for error messages

### Frontend Issues
- Check browser console for API errors
- Verify the API endpoints are accessible
- Ensure proper TypeScript compilation
