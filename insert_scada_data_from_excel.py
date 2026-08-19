# insert_scada_data_from_excel.py
"""
Script to read SCADA data from Excel file (Book1.xlsx) and insert into SQL Server database.
This script reads the Excel file and inserts data into [HerculesV2].[dbo].[ASMArchive_DB5] table.
"""

import pandas as pd
import uuid
from datetime import datetime, timezone
from sqlalchemy import text
import sys
import os

# Add backend directory to path to import database
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'backend'))
from database import engine

def generate_guid():
    """Generate a new GUID in the format used by SQL Server"""
    return str(uuid.uuid4()).upper()

def get_previous_record_guid(conn):
    """Get the GUID of the most recent record to use as PreviousRecordGUID"""
    try:
        query = text("""
            SELECT TOP 1 GUID 
            FROM [HerculesV2].[dbo].[ASMArchive_DB5] 
            ORDER BY ASMArchive_DB5ID DESC
        """)
        result = conn.execute(query).fetchone()
        if result and result[0]:
            return result[0]
    except Exception as e:
        print(f"⚠️  Could not fetch previous GUID: {e}")
    return None

def normalize_column_name(col_name):
    """Normalize Excel column names to match database column names"""
    if pd.isna(col_name):
        return None
    
    col_str = str(col_name).strip().upper()
    
    # Common mappings
    mappings = {
        'WG101_LO': ['WG101_LO', 'WG101 LO', 'WG101LO'],
        'WG101_HI': ['WG101_HI', 'WG101 HI', 'WG101HI'],
        'WG101_Product': ['WG101_PRODUCT', 'WG101 PRODUCT', 'WG101PRODUCT', 'WG101_Product'],
        'WG101_Destination': ['WG101_DESTINATION', 'WG101 DESTINATION', 'WG101DESTINATION', 'WG101_Destination'],
        # Add more mappings as needed
    }
    
    # Check direct match first
    if col_str in [k.upper() for k in mappings.keys()]:
        return col_str
    
    # Check in mappings
    for db_col, variations in mappings.items():
        if col_str in [v.upper() for v in variations]:
            return db_col.upper()
    
    # Return as-is if no mapping found
    return col_str

def safe_get_value(row, col_name, default=None):
    """Safely get value from DataFrame row, handling NaN and None"""
    try:
        if col_name in row.index:
            value = row[col_name]
            if pd.isna(value):
                return default
            return value
        return default
    except:
        return default

def insert_scada_data_from_excel(excel_file_path='Book1.xlsx'):
    """
    Read Excel file and insert data into ASMArchive_DB5 table
    
    Args:
        excel_file_path: Path to the Excel file (default: Book1.xlsx)
    """
    
    print(f"📖 Reading Excel file: {excel_file_path}")
    
    try:
        # Read Excel file
        df = pd.read_excel(excel_file_path)
        print(f"✅ Successfully read {len(df)} rows from Excel file")
        print(f"📋 Columns found: {list(df.columns)}")
        
    except FileNotFoundError:
        print(f"❌ Error: File '{excel_file_path}' not found!")
        print(f"   Please make sure the file exists in the current directory: {os.getcwd()}")
        return False
    except Exception as e:
        print(f"❌ Error reading Excel file: {e}")
        return False
    
    if df.empty:
        print("⚠️  Excel file is empty!")
        return False
    
    # Connect to database
    print("\n🔌 Connecting to database...")
    try:
        with engine.connect() as conn:
            trans = conn.begin()
            
            try:
                inserted_count = 0
                previous_guid = get_previous_record_guid(conn)
                
                print(f"\n📝 Starting data insertion...")
                print(f"   Previous Record GUID: {previous_guid or 'None (first record)'}")
                
                # Process each row
                for idx, row in df.iterrows():
                    try:
                        # Generate new GUIDs
                        new_guid = generate_guid()
                        prev_guid = previous_guid if previous_guid else 'C45D43FF-2554-4F5D-90B6-FA6FF309CA71'
                        
                        # Prepare INSERT statement with all columns
                        insert_sql = text("""
                            INSERT INTO [HerculesV2].[dbo].[ASMArchive_DB5] (
                                PreviousRecordGUID,
                                GUID,
                                CreatedOn,
                                WG101_LO, WG101_HI, WG101_Product, WG101_Destination,
                                WG201_LO, WG201_HI, WG201_Product, WG201_Destination,
                                WG202_LO, WG202_HI, WG202_Product,
                                WG301_LO, WG301_HI,
                                WG302_LO, WG302_HI,
                                WG501_LO, WG501_HI, WG501_Product, WG501_Destination,
                                WG502_LO, WG502_HI, WG502_Product, WG502_Destination,
                                WG503_LO, WG503_HI, WG503_Product,
                                DM101, DM102, DM201, DM202, DM203,
                                SL601_COUNTER, SL601_DAMAGED, SL601_Product, SL601_SIZE,
                                SL602_COUNTER, SL602_DAMAGED, SL602_PRODUCT, SL602_SIZE,
                                SL603_COUNTER, SL603_DAMAGED, SL603_Product, SL603_SIZE,
                                SL606_COUNTER, SL606_DAMAGED, SL606_Product, SL606_SIZE,
                                SL607_COUNTER, SL607_DAMAGED, SL607_PRODUCT, SL607_SIZE,
                                Dummy,
                                PL601_TOT, PL602_TOT, PL603_TOT,
                                SL607_TOT,
                                Dummy2,
                                SL606_TOT,
                                Dummy3
                            )
                            VALUES (
                                :prev_guid, :new_guid, SYSDATETIMEOFFSET(),
                                :wg101_lo, :wg101_hi, :wg101_product, :wg101_dest,
                                :wg201_lo, :wg201_hi, :wg201_product, :wg201_dest,
                                :wg202_lo, :wg202_hi, :wg202_product,
                                :wg301_lo, :wg301_hi,
                                :wg302_lo, :wg302_hi,
                                :wg501_lo, :wg501_hi, :wg501_product, :wg501_dest,
                                :wg502_lo, :wg502_hi, :wg502_product, :wg502_dest,
                                :wg503_lo, :wg503_hi, :wg503_product,
                                :dm101, :dm102, :dm201, :dm202, :dm203,
                                :sl601_counter, :sl601_damaged, :sl601_product, :sl601_size,
                                :sl602_counter, :sl602_damaged, :sl602_product, :sl602_size,
                                :sl603_counter, :sl603_damaged, :sl603_product, :sl603_size,
                                :sl606_counter, :sl606_damaged, :sl606_product, :sl606_size,
                                :sl607_counter, :sl607_damaged, :sl607_product, :sl607_size,
                                :dummy,
                                :pl601_tot, :pl602_tot, :pl603_tot,
                                :sl607_tot,
                                :dummy2,
                                :sl606_tot,
                                :dummy3
                            )
                        """)
                        
                        # Extract values from Excel row (try multiple column name formats)
                        params = {
                            'prev_guid': prev_guid,
                            'new_guid': new_guid,
                            
                            # WG101 columns
                            'wg101_lo': safe_get_value(row, 'WG101_LO', 0),
                            'wg101_hi': safe_get_value(row, 'WG101_HI', 0),
                            'wg101_product': safe_get_value(row, 'WG101_Product', ''),
                            'wg101_dest': safe_get_value(row, 'WG101_Destination', 0),
                            
                            # WG201 columns
                            'wg201_lo': safe_get_value(row, 'WG201_LO', 0),
                            'wg201_hi': safe_get_value(row, 'WG201_HI', 0),
                            'wg201_product': safe_get_value(row, 'WG201_Product', ''),
                            'wg201_dest': safe_get_value(row, 'WG201_Destination', 0),
                            
                            # WG202 columns
                            'wg202_lo': safe_get_value(row, 'WG202_LO', 0),
                            'wg202_hi': safe_get_value(row, 'WG202_HI', 0),
                            'wg202_product': safe_get_value(row, 'WG202_Product', ''),
                            
                            # WG301 columns
                            'wg301_lo': safe_get_value(row, 'WG301_LO', 0),
                            'wg301_hi': safe_get_value(row, 'WG301_HI', 0),
                            
                            # WG302 columns
                            'wg302_lo': safe_get_value(row, 'WG302_LO', 0),
                            'wg302_hi': safe_get_value(row, 'WG302_HI', 0),
                            
                            # WG501 columns
                            'wg501_lo': safe_get_value(row, 'WG501_LO', 0),
                            'wg501_hi': safe_get_value(row, 'WG501_HI', 0),
                            'wg501_product': safe_get_value(row, 'WG501_Product', ''),
                            'wg501_dest': safe_get_value(row, 'WG501_Destination', 0),
                            
                            # WG502 columns
                            'wg502_lo': safe_get_value(row, 'WG502_LO', 0),
                            'wg502_hi': safe_get_value(row, 'WG502_HI', 0),
                            'wg502_product': safe_get_value(row, 'WG502_Product', ''),
                            'wg502_dest': safe_get_value(row, 'WG502_Destination', 0),
                            
                            # WG503 columns
                            'wg503_lo': safe_get_value(row, 'WG503_LO', 0),
                            'wg503_hi': safe_get_value(row, 'WG503_HI', 0),
                            'wg503_product': safe_get_value(row, 'WG503_Product', ''),
                            
                            # DM columns (water meters)
                            'dm101': safe_get_value(row, 'DM101', 0.0),
                            'dm102': safe_get_value(row, 'DM102', 0.0),
                            'dm201': safe_get_value(row, 'DM201', 0.0),
                            'dm202': safe_get_value(row, 'DM202', 0.0),
                            'dm203': safe_get_value(row, 'DM203', 0.0),
                            
                            # SL601 columns
                            'sl601_counter': safe_get_value(row, 'SL601_COUNTER', 0),
                            'sl601_damaged': safe_get_value(row, 'SL601_DAMAGED', 0),
                            'sl601_product': safe_get_value(row, 'SL601_Product', ''),
                            'sl601_size': safe_get_value(row, 'SL601_SIZE', 0),
                            
                            # SL602 columns
                            'sl602_counter': safe_get_value(row, 'SL602_COUNTER', 0),
                            'sl602_damaged': safe_get_value(row, 'SL602_DAMAGED', 0),
                            'sl602_product': safe_get_value(row, 'SL602_PRODUCT', ''),
                            'sl602_size': safe_get_value(row, 'SL602_SIZE', 0),
                            
                            # SL603 columns
                            'sl603_counter': safe_get_value(row, 'SL603_COUNTER', 0),
                            'sl603_damaged': safe_get_value(row, 'SL603_DAMAGED', 0),
                            'sl603_product': safe_get_value(row, 'SL603_Product', ''),
                            'sl603_size': safe_get_value(row, 'SL603_SIZE', 0),
                            
                            # SL606 columns
                            'sl606_counter': safe_get_value(row, 'SL606_COUNTER', 0),
                            'sl606_damaged': safe_get_value(row, 'SL606_DAMAGED', 0),
                            'sl606_product': safe_get_value(row, 'SL606_Product', ''),
                            'sl606_size': safe_get_value(row, 'SL606_SIZE', 0),
                            
                            # SL607 columns
                            'sl607_counter': safe_get_value(row, 'SL607_COUNTER', 0),
                            'sl607_damaged': safe_get_value(row, 'SL607_DAMAGED', 0),
                            'sl607_product': safe_get_value(row, 'SL607_PRODUCT', ''),
                            'sl607_size': safe_get_value(row, 'SL607_SIZE', 0),
                            
                            # Dummy columns
                            'dummy': safe_get_value(row, 'Dummy', 0),
                            'dummy2': safe_get_value(row, 'Dummy2', 0),
                            'dummy3': safe_get_value(row, 'Dummy3', 0),
                            
                            # PL and SL TOT columns
                            'pl601_tot': safe_get_value(row, 'PL601_TOT', 0),
                            'pl602_tot': safe_get_value(row, 'PL602_TOT', 0),
                            'pl603_tot': safe_get_value(row, 'PL603_TOT', 0),
                            'sl607_tot': safe_get_value(row, 'SL607_TOT', 0),
                            'sl606_tot': safe_get_value(row, 'SL606_TOT', 0),
                        }
                        
                        # Convert numeric values
                        numeric_cols = [
                            'wg101_lo', 'wg101_hi', 'wg101_dest',
                            'wg201_lo', 'wg201_hi', 'wg201_dest',
                            'wg202_lo', 'wg202_hi',
                            'wg301_lo', 'wg301_hi',
                            'wg302_lo', 'wg302_hi',
                            'wg501_lo', 'wg501_hi', 'wg501_dest',
                            'wg502_lo', 'wg502_hi', 'wg502_dest',
                            'wg503_lo', 'wg503_hi',
                            'dm101', 'dm102', 'dm201', 'dm202', 'dm203',
                            'sl601_counter', 'sl601_damaged', 'sl601_size',
                            'sl602_counter', 'sl602_damaged', 'sl602_size',
                            'sl603_counter', 'sl603_damaged', 'sl603_size',
                            'sl606_counter', 'sl606_damaged', 'sl606_size',
                            'sl607_counter', 'sl607_damaged', 'sl607_size',
                            'dummy', 'dummy2', 'dummy3',
                            'pl601_tot', 'pl602_tot', 'pl603_tot',
                            'sl607_tot', 'sl606_tot'
                        ]
                        
                        for col in numeric_cols:
                            if col in params:
                                try:
                                    val = params[col]
                                    if val is None or (isinstance(val, float) and pd.isna(val)):
                                        params[col] = 0
                                    else:
                                        params[col] = float(val) if val != '' else 0
                                except (ValueError, TypeError):
                                    params[col] = 0
                        
                        # Execute INSERT
                        conn.execute(insert_sql, params)
                        inserted_count += 1
                        
                        # Update previous_guid for next iteration
                        previous_guid = new_guid
                        
                        if (idx + 1) % 10 == 0:
                            print(f"   ✅ Inserted {idx + 1}/{len(df)} rows...")
                    
                    except Exception as e:
                        print(f"   ❌ Error inserting row {idx + 1}: {e}")
                        print(f"      Row data: {row.to_dict()}")
                        continue
                
                # Commit transaction
                trans.commit()
                print(f"\n✅ Successfully inserted {inserted_count} out of {len(df)} rows!")
                return True
                
            except Exception as e:
                trans.rollback()
                print(f"\n❌ Error during insertion: {e}")
                import traceback
                traceback.print_exc()
                return False
                
    except Exception as e:
        print(f"❌ Database connection error: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    print("=" * 60)
    print("📊 SCADA Data Import from Excel")
    print("=" * 60)
    
    # Check if Excel file exists
    excel_file = 'Book1.xlsx'
    if not os.path.exists(excel_file):
        print(f"\n⚠️  Excel file '{excel_file}' not found in current directory!")
        print(f"   Current directory: {os.getcwd()}")
        print(f"\n   Please ensure '{excel_file}' is in the same directory as this script.")
        sys.exit(1)
    
    # Run the import
    success = insert_scada_data_from_excel(excel_file)
    
    if success:
        print("\n🎉 Data import completed successfully!")
    else:
        print("\n⚠️  Data import completed with errors. Please check the output above.")
        sys.exit(1)

