#!/usr/bin/env python3
# check_packing_data.py

import pyodbc
import os

# Database connection string - using Windows Authentication
connection_string = 'DRIVER={ODBC Driver 17 for SQL Server};SERVER=WIN-PGGO8DO6T0D;DATABASE=HerculesV2;Trusted_Connection=yes'

try:
    # Connect to database
    conn = pyodbc.connect(connection_string)
    cursor = conn.cursor()
    
    # Query to check packing data
    query = """
    SELECT TOP 5 
        PL601_TOT, PL602_TOT, PL603_TOT,
        CASE WHEN PL601_TOT IS NULL THEN 'NULL' ELSE 'NOT NULL' END as PL601_STATUS,
        CASE WHEN PL602_TOT IS NULL THEN 'NULL' ELSE 'NOT NULL' END as PL602_STATUS,
        CASE WHEN PL603_TOT IS NULL THEN 'NULL' ELSE 'NOT NULL' END as PL603_STATUS
    FROM [HerculesV2].[dbo].[ASMReporting_5]
    ORDER BY ASMReporting_5ID DESC
    """
    
    cursor.execute(query)
    rows = cursor.fetchall()
    
    print('Latest 5 rows from ASMReporting_5:')
    print('PL601_TOT | PL602_TOT | PL603_TOT | PL601_STATUS | PL602_STATUS | PL603_STATUS')
    print('-' * 80)
    
    for row in rows:
        print(f'{row[0]} | {row[1]} | {row[2]} | {row[3]} | {row[4]} | {row[5]}')
    
    # Also check if there are any non-NULL values
    cursor.execute("""
        SELECT 
            COUNT(*) as total_rows,
            COUNT(PL601_TOT) as non_null_pl601,
            COUNT(PL602_TOT) as non_null_pl602,
            COUNT(PL603_TOT) as non_null_pl603
        FROM [HerculesV2].[dbo].[ASMReporting_5]
    """)
    
    stats = cursor.fetchone()
    print(f'\nDatabase Statistics:')
    print(f'Total rows: {stats[0]}')
    print(f'PL601_TOT non-NULL: {stats[1]}')
    print(f'PL602_TOT non-NULL: {stats[2]}')
    print(f'PL603_TOT non-NULL: {stats[3]}')
    
    conn.close()
    
except Exception as e:
    print(f"Error: {e}")
