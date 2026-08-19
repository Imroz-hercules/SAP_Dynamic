# seed_dev.py
from database import SessionLocal
from models.order_model import Order

db = SessionLocal()

# make one pending order you can validate
o = Order(
    material="Demo Mix",
    version="v1.0",
    batch="B-DEV-001",
    quantity=0,
    status="Pending",
    po_number="PO-DEV-001",   # use any PO id your SAPStub knows, adjust if needed
)

db.add(o)
db.commit()
db.refresh(o)
print("Seeded order id:", o.id)
db.close()
