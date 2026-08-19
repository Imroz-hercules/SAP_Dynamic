# backend/services/process_order_sync.py
from database import engine as mssql_engine, postgres_engine
from sqlalchemy import text
from datetime import datetime

def fetch_process_orders_from_mssql():
    """Fetch process orders from SQL Server"""
    try:
        # SQL query to fetch process orders from SQL Server
        # You can replace this with your actual table name and columns
        query = """
        SELECT 
            ROW_NUMBER() OVER (ORDER BY (SELECT NULL)) as id,
            COALESCE(OrderID, 'ORD-' + CAST(ROW_NUMBER() OVER (ORDER BY (SELECT NULL)) AS VARCHAR(10))) as order_id,
            COALESCE(Material, 'Material-' + CAST(ROW_NUMBER() OVER (ORDER BY (SELECT NULL)) AS VARCHAR(10))) as material,
            COALESCE(Version, 'v1.0') as version,
            COALESCE(Batch, 'BATCH-' + CAST(ROW_NUMBER() OVER (ORDER BY (SELECT NULL)) AS VARCHAR(10))) as batch,
            COALESCE(Quantity, 0.0) as quantity,
            COALESCE(Status, 'Pending') as status,
            COALESCE(CreatedDate, GETDATE()) as date
        FROM (
            -- Sample data - replace with your actual SQL Server table
            SELECT 
                'PO-001' as OrderID, 'Wheat Flour' as Material, 'v1.0' as Version, 'BATCH-001' as Batch, 1000.0 as Quantity, 'Pending' as Status, DATEADD(day, -1, GETDATE()) as CreatedDate
            UNION ALL
            SELECT 'PO-002', 'Rice Flour', 'v1.0', 'BATCH-002', 1500.0, 'Validated', DATEADD(day, -2, GETDATE())
            UNION ALL
            SELECT 'PO-003', 'Corn Flour', 'v1.0', 'BATCH-003', 800.0, 'Rejected', DATEADD(day, -3, GETDATE())
            UNION ALL
            SELECT 'PO-004', 'Barley Flour', 'v1.0', 'BATCH-004', 1200.0, 'Pending', DATEADD(day, -4, GETDATE())
            UNION ALL
            SELECT 'PO-005', 'Oat Flour', 'v1.0', 'BATCH-005', 900.0, 'Validated', DATEADD(day, -5, GETDATE())
        ) AS SampleData
        ORDER BY date DESC
        """
        
        with mssql_engine.connect() as conn:
            result = conn.execute(text(query))
            rows = result.mappings().all()
            return [dict(row) for row in rows]
            
    except Exception as e:
        print(f"Error fetching from SQL Server: {e}")
        return []

def store_process_orders_to_postgres(orders_data):
    """Store process orders data to PostgreSQL"""
    try:
        # Create the process_orders table if it doesn't exist
        create_table_sql = """
        CREATE TABLE IF NOT EXISTS process_orders (
            id SERIAL PRIMARY KEY,
            order_id VARCHAR(50) NOT NULL,
            material VARCHAR(100) NOT NULL,
            version VARCHAR(20) NOT NULL DEFAULT 'v1.0',
            batch VARCHAR(50) NOT NULL,
            quantity FLOAT NOT NULL DEFAULT 0.0,
            status VARCHAR(20) NOT NULL DEFAULT 'Pending',
            date TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT CURRENT_TIMESTAMP,
            created_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT CURRENT_TIMESTAMP
        )
        """
        
        with postgres_engine.begin() as pg:
            # Create table
            pg.execute(text(create_table_sql))
            
            # Clear existing data (optional - remove if you want to keep historical data)
            pg.execute(text("DELETE FROM process_orders"))
            
            # Insert new data
            for order in orders_data:
                insert_sql = """
                INSERT INTO process_orders (order_id, material, version, batch, quantity, status, date, created_at)
                VALUES (:order_id, :material, :version, :batch, :quantity, :status, :date, :created_at)
                """
                pg.execute(text(insert_sql), {
                    'order_id': order['order_id'],
                    'material': order['material'],
                    'version': order['version'],
                    'batch': order['batch'],
                    'quantity': order['quantity'],
                    'status': order['status'],
                    'date': order['date'],
                    'created_at': datetime.now()
                })
        
        print(f"Successfully stored {len(orders_data)} process orders to PostgreSQL")
        return True
        
    except Exception as e:
        print(f"Error storing to PostgreSQL: {e}")
        return False

def sync_process_orders():
    """Main function to sync process orders from SQL Server to PostgreSQL"""
    print("Starting process orders sync...")
    
    # Fetch data from SQL Server
    orders_data = fetch_process_orders_from_mssql()
    
    if not orders_data:
        print("No data fetched from SQL Server")
        return False
    
    # Store data to PostgreSQL
    success = store_process_orders_to_postgres(orders_data)
    
    if success:
        print(f"Successfully synced {len(orders_data)} process orders")
    else:
        print("Failed to sync process orders")
    
    return success
