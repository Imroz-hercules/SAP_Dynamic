#!/usr/bin/env python3
"""
Script to populate the database with sample orders for testing
"""
from database import SessionLocal
from models.order_model import Order

def populate_sample_orders():
    """Add sample orders to the database"""
    
    sample_orders = [
        {
            "order_id": "PO-001",
            "material": "Flour A",
            "version": "v1.2",
            "batch": "B-101",
            "quantity": 5000,
            "status": "Pending",
            "description": "Premium wheat flour for bread production"
        },
        {
            "order_id": "PO-002",
            "material": "Bran B",
            "version": "v1.0",
            "batch": "B-102",
            "quantity": 3200,
            "status": "Validated",
            "description": "Wheat bran for fiber enrichment"
        },
        {
            "order_id": "PO-003",
            "material": "Semolina",
            "version": "v2.1",
            "batch": "B-103",
            "quantity": 2100,
            "status": "Rejected",
            "description": "Durum wheat semolina for pasta"
        },
        {
            "order_id": "PO-004",
            "material": "Flour B",
            "version": "v1.3",
            "batch": "B-104",
            "quantity": 4500,
            "status": "Pending",
            "description": "All-purpose flour for general baking"
        },
        {
            "order_id": "PO-005",
            "material": "Bran C",
            "version": "v1.2",
            "batch": "B-105",
            "quantity": 1800,
            "status": "Validated",
            "description": "Oat bran for health products"
        },
        {
            "order_id": "PO-006",
            "material": "Flour C",
            "version": "v2.0",
            "batch": "B-106",
            "quantity": 3900,
            "status": "Rejected",
            "description": "Cake flour for confectionery"
        },
        {
            "order_id": "PO-007",
            "material": "Semolina",
            "version": "v2.2",
            "batch": "B-107",
            "quantity": 2500,
            "status": "Pending",
            "description": "Fine semolina for premium pasta"
        },
        {
            "order_id": "PO-008",
            "material": "Flour D",
            "version": "v1.1",
            "batch": "B-108",
            "quantity": 4100,
            "status": "Validated",
            "description": "Whole wheat flour for health bread"
        },
        {
            "order_id": "PO-009",
            "material": "Bran D",
            "version": "v1.0",
            "batch": "B-109",
            "quantity": 1700,
            "status": "Rejected",
            "description": "Rice bran for gluten-free products"
        },
        {
            "order_id": "PO-010",
            "material": "Flour E",
            "version": "v1.4",
            "batch": "B-110",
            "quantity": 5200,
            "status": "Pending",
            "description": "Rye flour for traditional bread"
        }
    ]
    
    db = SessionLocal()
    try:
        # Check if orders already exist
        existing_count = db.query(Order).count()
        if existing_count > 0:
            print(f"Database already contains {existing_count} orders. Skipping population.")
            return
        
        # Add sample orders
        for order_data in sample_orders:
            # Fix field name mapping
            order = Order(
                po_number=order_data["order_id"],
                material=order_data["material"],
                version=order_data["version"],
                batch=order_data["batch"],
                quantity=order_data["quantity"],
                status=order_data["status"],
                description=order_data["description"]
            )
            db.add(order)
        
        db.commit()
        print(f"Successfully added {len(sample_orders)} sample orders to the database.")
        
    except Exception as e:
        db.rollback()
        print(f"Error populating orders: {e}")
    finally:
        db.close()

if __name__ == "__main__":
    populate_sample_orders()
