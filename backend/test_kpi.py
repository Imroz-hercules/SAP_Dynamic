#!/usr/bin/env python3
# test_kpi.py - Test KPI calculation with actual database data

import pyodbc
from routes.kpi_routes import calc_kpis_from_row
import json

def test_kpi_calculation():
    """Test KPI calculation with actual data from the database"""
    
    # SQL Server connection string
    connection_string = (
        "DRIVER={ODBC Driver 17 for SQL Server};"
        "SERVER=WIN-PGGO8DO6T0D;"
        "DATABASE=HerculesV2;"
        "Trusted_Connection=yes;"
    )
    
    try:
        print("Testing KPI calculation with real data...")
        conn = pyodbc.connect(connection_string)
        cursor = conn.cursor()
        
        # Get the latest data from the database
        cursor.execute("""
            SELECT TOP 1 
                WG201, WG501, WG502, WG503, 
                PL601_TOT, 
                DM101, DM102, DM201, DM202, DM203,
                WG101, WG202, WG301, WG302
            FROM [HerculesV2].[dbo].[ASMReporting_5] 
            ORDER BY ASMReporting_5ID DESC
        """)
        
        row = cursor.fetchone()
        if row:
            print("✓ Data fetched from database")
            
            # Get column names
            column_names = [column[0] for column in cursor.description]
            
            # Create a dictionary of the data
            sample_data = dict(zip(column_names, row))
            
            print("\nRaw data from database:")
            for field, value in sample_data.items():
                print(f"  {field}: {value}")
            
            # Test the KPI calculation function
            print("\nTesting KPI calculation...")
            kpi_result = calc_kpis_from_row(sample_data)
            
            print("\nKPI Calculation Result:")
            print(json.dumps(kpi_result, indent=2))
            
        else:
            print("⚠ No data found in table")
            
        conn.close()
        print("✓ Database connection closed")
        
    except Exception as e:
        print(f"✗ Test failed: {e}")
        return False
    
    return True

if __name__ == "__main__":
    test_kpi_calculation()
