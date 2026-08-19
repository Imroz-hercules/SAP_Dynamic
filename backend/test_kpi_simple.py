#!/usr/bin/env python3
# test_kpi_simple.py - Simple test of KPI calculation logic

import pyodbc
from datetime import datetime
import json

def safe(v, default=0.0):
    try:
        if v is None:
            return default
        return float(v)
    except Exception:
        return default

def test_kpi_calculation_simple():
    """Test KPI calculation logic with actual data from the database"""
    
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
            
            # Test the validation logic
            print("\nTesting validation logic...")
            
            # Extract values
            WG201 = safe(sample_data.get("WG201"))
            WG501 = safe(sample_data.get("WG501"))
            WG502 = safe(sample_data.get("WG502"))
            WG503 = safe(sample_data.get("WG503"))
            PL601 = safe(sample_data.get("PL601_TOT"))
            daily_hrs = 24.0  # Default value
            
            print(f"  WG201: {WG201}")
            print(f"  WG501: {WG501}")
            print(f"  WG502: {WG502}")
            print(f"  WG503: {WG503}")
            print(f"  PL601: {PL601}")
            print(f"  daily_hrs: {daily_hrs}")
            
            # Test validation
            has_milling_data = (
                WG201 > 0.001 and  # Must have some input wheat (at least 0.001 ton)
                (WG501 > 0 or WG502 > 0 or WG503 > 0) and  # Must have some flour/bran output
                daily_hrs > 0  # Must have daily hours
            )
            
            has_packing_data = (
                PL601 > 0 and  # Must have some packing output
                daily_hrs > 0  # Must have daily hours
            )
            
            has_valid_data = has_milling_data or has_packing_data
            
            print(f"\nValidation results:")
            print(f"  WG201 > 0.001: {WG201 > 0.001}")
            print(f"  flour_output > 0: {(WG501 > 0 or WG502 > 0 or WG503 > 0)}")
            print(f"  daily_hrs > 0: {daily_hrs > 0}")
            print(f"  PL601 > 0: {PL601 > 0}")
            print(f"  has_milling_data: {has_milling_data}")
            print(f"  has_packing_data: {has_packing_data}")
            print(f"  has_valid_data: {has_valid_data}")
            
            if has_valid_data:
                print("\n✓ Data validation passed - would calculate KPIs")
                
                # Test some calculations
                if has_milling_data:
                    print("\nMilling calculations:")
                    
                    # Milling Gain (%)
                    total_output = WG501 + WG502 + WG503 + WG301 + WG302
                    milling_gain = (total_output / WG201 * 100.0) if WG201 > 0 else 0.0
                    print(f"  Milling Gain: {milling_gain:.2f}%")
                    
                    # Water Consumption (m³)
                    total_water = DM101 + DM102 + DM201 + DM202 + DM203
                    print(f"  Water Consumption: {total_water:.2f} m³")
                    
                    # Flour Extraction (%)
                    total_flour = WG501 + WG502
                    flour_extraction = (total_flour / WG201 * 100.0) if WG201 > 0 else 0.0
                    print(f"  Flour Extraction: {flour_extraction:.2f}%")
                
                if has_packing_data:
                    print("\nPacking calculations:")
                    print(f"  Daily Packing Output: {PL601:.0f} bags")
            else:
                print("\n✗ Data validation failed - would return zeros")
            
        else:
            print("⚠ No data found in table")
            
        conn.close()
        print("✓ Database connection closed")
        
    except Exception as e:
        print(f"✗ Test failed: {e}")
        return False
    
    return True

if __name__ == "__main__":
    test_kpi_calculation_simple()
