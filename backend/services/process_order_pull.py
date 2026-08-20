# services/process_order_pull.py
import logging
from sqlalchemy import text
from database import postgres_engine
from services.sap_real_client import SAPRealClient
from datetime import datetime

log = logging.getLogger(__name__)

# Initialize SAP client
sap = SAPRealClient()

# Import classification function
try:
    from routes.order_validation import classify_order
    CLASSIFICATION_AVAILABLE = True
except ImportError:
    log.warning("Classification function not available - orders will not be auto-classified")
    CLASSIFICATION_AVAILABLE = False

UPSERT_SQL = text("""
  INSERT INTO process_orders
    (order_id, material, version, batch, quantity, unit,
     status, priority, plant, confirmed_qty, material_desc, 
     sap_created_on, created_at, updated_at, order_type, packing_line, bag_size)
  VALUES
    (:po_number, :material, :version, :batch, :quantity, :unit,
     :status, :priority, :plant, :confirmed_qty, :material_desc,
     :sap_created_on, :created_at, NOW(), :order_type, :packing_line, :bag_size)
  ON CONFLICT (order_id) DO UPDATE SET
     material      = EXCLUDED.material,
     version       = EXCLUDED.version,
     batch         = EXCLUDED.batch,
     quantity      = EXCLUDED.quantity,
     unit          = EXCLUDED.unit,
     status        = CASE 
                       WHEN process_orders.status IN ('InProgress', 'Validated', 'Rejected') 
                       THEN process_orders.status 
                       ELSE EXCLUDED.status 
                     END,
     priority      = EXCLUDED.priority,
     plant         = EXCLUDED.plant,
     confirmed_qty = EXCLUDED.confirmed_qty,
     material_desc = EXCLUDED.material_desc,
     sap_created_on = EXCLUDED.sap_created_on,
     order_type    = COALESCE(process_orders.order_type, EXCLUDED.order_type),
     packing_line  = COALESCE(process_orders.packing_line, EXCLUDED.packing_line),
     bag_size      = COALESCE(process_orders.bag_size, EXCLUDED.bag_size),
     created_at    = COALESCE(process_orders.created_at, EXCLUDED.created_at),
     updated_at    = NOW();
""")

def pull_from_sap_once() -> int:
    """
    Fetch open POs from SAP and upsert into Postgres. 
    Returns count of orders processed.
    
    This function:
    1. Connects to SAP API
    2. Fetches process orders
    3. Transforms data to our format
    4. Upserts into PostgreSQL database
    5. Preserves existing status for orders in progress
    """
    try:
        log.info("Starting SAP process orders pull...")
        
        # Fetch orders from SAP
        pos = sap.get_process_orders()
        if not isinstance(pos, list):
            raise RuntimeError("Unexpected SAP response for process orders")

        if not pos:
            log.info("No process orders returned from SAP")
            return 0

        log.info(f"Retrieved {len(pos)} orders from SAP")

        # Process and store orders
        processed_count = 0
        classified_count = 0
        with postgres_engine.connect() as conn:
            for po in pos:
                try:
                    # Parse created_at datetime
                    created_at = None
                    if po.get("created_at"):
                        try:
                            created_at = datetime.fromisoformat(po["created_at"].replace('Z', '+00:00'))
                        except ValueError:
                            log.warning(f"Invalid created_at format: {po.get('created_at')}")
                            created_at = datetime.now()
                    else:
                        created_at = datetime.now()

                    # Auto-classify order if classification is available
                    order_type = None
                    packing_line = None
                    bag_size = None
                    
                    if CLASSIFICATION_AVAILABLE:
                        try:
                            # Create a mock order object for classification
                            class MockOrder:
                                def __init__(self, po_data):
                                    self.order_id = po_data.get("po_number")
                                    self.material = po_data.get("material")
                                    self.version = po_data.get("version")
                                    self.unit = po_data.get("unit", "KG")
                                    self.quantity = po_data.get("quantity")
                            
                            mock_order = MockOrder(po)
                            classification = classify_order(mock_order)
                            order_type = classification.get("order_type")

                            # ✅ A1: these were read off the TOP level of the
                            # classification dict, where classify_order has never
                            # put them — so both were always None and both columns
                            # have been NULL for every order ever pulled. They live
                            # in packing_info, and only for PACKING orders.
                            packing_info = classification.get("packing_info") or {}
                            packing_line = packing_info.get("packing_line")
                            bag_size = packing_info.get("bag_size")

                            if order_type:
                                classified_count += 1
                                log.info(f"Auto-classified order {po.get('po_number')} as {order_type}")
                            
                        except Exception as e:
                            log.warning(f"Failed to classify order {po.get('po_number')}: {e}")

                    # Execute upsert
                    result = conn.execute(UPSERT_SQL, {
                        "po_number": po.get("po_number"),
                        "material": po.get("material"),
                        "version": po.get("version"),
                        "batch": po.get("batch"),
                        "quantity": po.get("quantity"),
                        "unit": po.get("unit", "KG"),
                        "status": po.get("status", "Open"),
                        "priority": po.get("priority", 0),
                        "plant": po.get("plant"),
                        "confirmed_qty": po.get("confirmed_qty"),
                        "material_desc": po.get("material_desc"),
                        "sap_created_on": created_at,
                        "created_at": created_at,
                        "order_type": order_type,
                        "packing_line": packing_line,
                        "bag_size": bag_size,
                    })
                    processed_count += 1
                    
                except Exception as e:
                    log.error(f"Failed to process order {po.get('po_number', 'unknown')}: {e}")
                    continue
            
            conn.commit()
            log.info(f"Successfully processed {processed_count} orders from SAP, {classified_count} auto-classified")
            
        return processed_count
        
    except Exception as e:
        log.error(f"SAP pull failed: {e}")
        raise Exception(f"Failed to pull orders from SAP: {str(e)}")

def test_sap_connection() -> bool:
    """
    Test connection to SAP API.
    
    Returns:
        True if connection is successful, False otherwise
    """
    try:
        return sap.test_connection()
    except Exception as e:
        log.error(f"SAP connection test failed: {e}")
        return False
