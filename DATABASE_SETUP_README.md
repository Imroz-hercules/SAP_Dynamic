# Hercules KPI Database Setup Guide

## Overview
The Hercules KPI application requires two databases:
- **MSSQL Server**: For KPI data, materials, and order validation
- **PostgreSQL**: For SCADA data, process orders, and user management

## Installation Process

### 1. Database Configuration Page
During installation, you'll see a "Database Configuration" page where you can:

#### MSSQL Database Configuration
- **Server**: Your MSSQL server name (e.g., `localhost`, `server-name`, `server-name\instance`)
- **Database**: Database name (default: `HerculesKPI`)
- **Username**: MSSQL username (default: `sa`)
- **Password**: MSSQL password

#### PostgreSQL Database Configuration
- **Host**: PostgreSQL server host (default: `localhost`)
- **Port**: PostgreSQL port (default: `5432`)
- **Database**: Database name (default: `hercules_kpi`)
- **Username**: PostgreSQL username (default: `postgres`)
- **Password**: PostgreSQL password

### 2. Automatic Database Setup
The installer will automatically:
- ✅ Test database connections
- ✅ Create required tables in both databases
- ✅ Set up proper permissions
- ✅ Save configuration for the application

## Database Requirements

### MSSQL Server
- **Version**: SQL Server 2016 or later
- **Required Tables**:
  - KPI data tables
  - Material mapping tables
  - Order validation tables
  - Process order tables

### PostgreSQL
- **Version**: PostgreSQL 10 or later
- **Required Tables**:
  - SCADA data tables
  - Process order tables
  - User roles and permissions
  - Sync interval settings

## Manual Database Setup (If Needed)

If the automatic setup fails, you can manually run the database setup:

```bash
cd "C:\Program Files\HerculesKPI"
python database_setup.py
```

## Configuration File

The database configuration is saved to:
```
C:\Program Files\HerculesKPI\backend\database_config.json
```

Example configuration:
```json
{
  "mssql": {
    "server": "localhost",
    "database": "HerculesKPI",
    "username": "sa",
    "password": "your_password"
  },
  "postgresql": {
    "host": "localhost",
    "port": "5432",
    "database": "hercules_kpi",
    "username": "postgres",
    "password": "your_password"
  }
}
```

## Troubleshooting

### Connection Issues
1. **Check database services are running**
2. **Verify firewall settings**
3. **Confirm username/password**
4. **Check network connectivity**

### Permission Issues
1. **Ensure user has CREATE TABLE permissions**
2. **Check database ownership**
3. **Verify SQL Server authentication mode**

### Table Creation Issues
1. **Check database exists**
2. **Verify user permissions**
3. **Check for naming conflicts**

## Support

If you encounter issues during database setup:
1. Check the setup log in the installer
2. Review the database configuration
3. Ensure all prerequisites are met
4. Contact your database administrator

## Security Notes

- Database passwords are stored in plain text in the configuration file
- Ensure proper file permissions on the configuration file
- Consider using Windows Authentication for MSSQL when possible
- Use strong passwords for database accounts
