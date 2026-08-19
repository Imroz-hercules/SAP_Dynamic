#!/usr/bin/env python3
# check_null_packing.py

import pyodbc

# Database connection string - using Windows Authentication
connection_string = 'DRIVER={ODBC Driver 17 for SQL Server};SERVER=WIN-PGGO8DO6T0D;DATABASE=HerculesV2;Trusted_Connection=yes'

try:
    # Connect to database
    conn = pyodbc.connect(connection_string)
    cursor = conn.cursor()
    
    # Check for NULL values in packing columns
    query = """
    SELECT TOP 10 
        ASMReporting_5ID,
        PL601_TOT, PL602_TOT, PL603_TOT,
        CASE WHEN PL601_TOT IS NULL THEN 'NULL' ELSE 'NOT NULL' END as PL601_STATUS,
        CASE WHEN PL602_TOT IS NULL THEN 'NULL' ELSE 'NOT NULL' END as PL602_STATUS,
        CASE WHEN PL603_TOT IS NULL THEN 'NULL' ELSE 'NOT NULL' END as PL603_STATUS
    FROM [HerculesV2].[dbo].[ASMReporting_5]
    WHERE PL601_TOT IS NULL OR PL602_TOT IS NULL OR PL603_TOT IS NULL
    ORDER BY ASMReporting_5ID DESC
    """
    
    cursor.execute(query)
    rows = cursor.fetchall()
    
    print('Rows with NULL packing data (latest 10):')
    print('ID | PL601_TOT | PL602_TOT | PL603_TOT | PL601_STATUS | PL602_STATUS | PL603_STATUS')
    print('-' * 90)
    
    for row in rows:
        print(f'{row[0]} | {row[1]} | {row[2]} | {row[3]} | {row[4]} | {row[5]} | {row[6]}')
    
    # Check the most recent row specifically
    cursor.execute("""
        SELECT TOP 1 
            ASMReporting_5ID,
            PL601_TOT, PL602_TOT, PL603_TOT,
            CASE WHEN PL601_TOT IS NULL THEN 'NULL' ELSE 'NOT NULL' END as PL601_STATUS,
            CASE WHEN PL602_TOT IS NULL THEN 'NULL' ELSE 'NOT NULL' END as PL602_STATUS,
            CASE WHEN PL603_TOT IS NULL THEN 'NULL' ELSE 'NOT NULL' END as PL603_STATUS
        FROM [HerculesV2].[dbo].[ASMReporting_5]
        ORDER BY ASMReporting_5ID DESC
    """)
    
    latest_row = cursor.fetchone()
    print(f'\nMOST RECENT ROW:')
    print(f'ID: {latest_row[0]}')
    print(f'PL601_TOT: {latest_row[1]} ({latest_row[4]})')
    print(f'PL602_TOT: {latest_row[2]} ({latest_row[5]})')
    print(f'PL603_TOT: {latest_row[3]} ({latest_row[6]})')
    
    conn.close()
    
except Exception as e:
    print(f"Error: {e}")

