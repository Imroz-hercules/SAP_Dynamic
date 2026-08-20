# # backend/routes/sap_sync.py
# from flask import Blueprint, jsonify
# from sqlalchemy.orm import sessionmaker
# from database import postgres_engine
# from models.process_order_pg import ProcessOrderPG as ProcessOrder
# from services.auto_validator import _convert_to_tons
# from services.sap_real_client import SAPRealClient

# # DB session
# PostgresSessionLocal = sessionmaker(
#     bind=postgres_engine, autoflush=False, autocommit=False, future=True
# )

# def _db_session():
#     return PostgresSessionLocal()

# sap_sync_bp = Blueprint("sap_sync", __name__, url_prefix="/api/sap-sync")


# @sap_sync_bp.route("/seed-orders", methods=["POST"])
# def seed_orders():
#     """
#     REAL SAP INTEGRATION with Fallback:
#     Fetch process orders from real SAP API and insert into process_orders table.
#     Falls back to enhanced demo data if SAP API is not accessible.
#     """
#     try:
#         # Try to fetch from real SAP API first
#         print("🔄 Attempting to fetch orders from real SAP API...")
#         sap_orders = []
#         sap_error = None
        
#         try:
#             # Initialize SAP client
#             sap_client = SAPRealClient()
#             sap_orders = sap_client.get_process_orders()
            
#             if sap_orders and len(sap_orders) > 0:
#                 print(f"✅ Successfully retrieved {len(sap_orders)} orders from SAP API")
#             else:
#                 print("⚠️ SAP API returned no orders, falling back to real SAP format data...")
#                 raise Exception("No orders returned from SAP API")
            
#         except Exception as e:
#             sap_error = str(e)
#             print(f"⚠️ SAP API not accessible: {e}")
#             print("🔄 Attempting direct API call as fallback...")
            
#             # Try direct API call as fallback
#             try:
#                 import requests
#                 from requests.auth import HTTPBasicAuth
                
#                 url = "https://vhmioqs4ci.sap.mc3.com.sa:44300/zmi_get_orders/GETORD"
#                 params = {"client": "250"}
                
#                 response = requests.get(
#                     url,
#                     params=params,
#                     auth=HTTPBasicAuth("99999", "P@ssw0rdP@ssw0rd"),
#                     timeout=30,
#                     headers={
#                         'Accept': 'application/json',
#                         'User-Agent': 'Hercules-SFMS/1.0'
#                     },
#                     verify=False  # Disable SSL verification for SAP API
#                 )
                
#                 if response.status_code == 200:
#                     raw_data = response.json()
#                     print(f"✅ Direct API call successful, retrieved {len(raw_data)} orders")
                    
#                     # Transform raw SAP data to our format
#                     sap_orders = []
#                     for item in raw_data:
#                         transformed = {
#                             "po_number": item.get("PROCESS_ORDER", "").strip(),
#                             "material": item.get("MATERIAL", "").strip(),
#                             "version": item.get("VERSION", "v1.0").strip(),
#                             "batch": f"BATCH-{item.get('PROCESS_ORDER', 'UNKNOWN')}-{item.get('CREATED_ON', '20250922')}",
#                             "quantity": float(item.get("TOTAL_QTY", 0)),
#                             "unit": item.get("UOM", "KG").strip(),
#                             "status": "Pending",
#                             "priority": int(item.get("PRIORITY_ID", "0")),
#                             "plant": item.get("PLANT", "").strip(),
#                             "material_desc": item.get("MATERIAL_DESC", "").strip(),
#                             "created_at": item.get("CREATED_ON", "2025-09-22")
#                         }
#                         sap_orders.append(transformed)
                    
#                     sap_error = None  # Clear error since direct call worked
                    
#                 else:
#                     raise Exception(f"Direct API call failed with status {response.status_code}: {response.text}")
                    
#             except Exception as direct_error:
#                 print(f"⚠️ Direct API call also failed: {direct_error}")
#                 print("🔄 Using real SAP data format as fallback...")
                
#                 # Real SAP data format based on the API client response
#                 # This matches the exact format from your working API client
#                 sap_orders = [
#                     {
#                         "PROCESS_ORDER": "000013006740",
#                         "MATERIAL": "000000000001400001",
#                         "TOTAL_QTY": 100.000,
#                         "UOM": "BAG",
#                         "PRIORITY_ID": "1",
#                         "CONFIRMED_QTY": 0,
#                         "PLANT": "3130",
#                         "CREATED_ON": "2025-09-04"
#                     },
#                     {
#                         "PROCESS_ORDER": "000013006741",
#                         "MATERIAL": "000000000001400002",
#                         "TOTAL_QTY": 50.000,
#                         "UOM": "TO",
#                         "PRIORITY_ID": "2",
#                         "CONFIRMED_QTY": 0,
#                         "PLANT": "3130",
#                         "CREATED_ON": "2025-09-04"
#                     },
#                     {
#                         "PROCESS_ORDER": "000013006742",
#                         "MATERIAL": "000000000001400003",
#                         "TOTAL_QTY": 75.000,
#                         "UOM": "BAG",
#                         "PRIORITY_ID": "3",
#                         "CONFIRMED_QTY": 0,
#                         "PLANT": "3130",
#                         "CREATED_ON": "2025-09-04"
#                     },
#                     {
#                         "PROCESS_ORDER": "000013006743",
#                         "MATERIAL": "000000000001400004",
#                         "TOTAL_QTY": 120.000,
#                         "UOM": "BAG",
#                         "PRIORITY_ID": "4",
#                         "CONFIRMED_QTY": 0,
#                         "PLANT": "3130",
#                         "CREATED_ON": "2025-09-04"
#                     },
#                     {
#                         "PROCESS_ORDER": "000013006744",
#                         "MATERIAL": "000000000001400005",
#                         "TOTAL_QTY": 80.000,
#                         "UOM": "TO",
#                         "PRIORITY_ID": "5",
#                         "CONFIRMED_QTY": 0,
#                         "PLANT": "3130",
#                         "CREATED_ON": "2025-09-04"
#                     },
#                     {
#                         "PROCESS_ORDER": "000013006745",
#                         "MATERIAL": "000000000001400006",
#                         "TOTAL_QTY": 90.000,
#                         "UOM": "BAG",
#                         "PRIORITY_ID": "6",
#                         "CONFIRMED_QTY": 0,
#                         "PLANT": "3130",
#                         "CREATED_ON": "2025-09-04"
#                     },
#                     {
#                         "PROCESS_ORDER": "000013006746",
#                         "MATERIAL": "000000000001400007",
#                         "TOTAL_QTY": 60.000,
#                         "UOM": "TO",
#                         "PRIORITY_ID": "7",
#                         "CONFIRMED_QTY": 0,
#                         "PLANT": "3130",
#                         "CREATED_ON": "2025-09-04"
#                     },
#                     {
#                         "PROCESS_ORDER": "000013006747",
#                         "MATERIAL": "000000000001400008",
#                         "TOTAL_QTY": 110.000,
#                         "UOM": "BAG",
#                         "PRIORITY_ID": "8",
#                         "CONFIRMED_QTY": 0,
#                         "PLANT": "3130",
#                         "CREATED_ON": "2025-09-04"
#                     }
#                 ]
        
#         if not sap_orders:
#             return jsonify({
#                 "ok": False,
#                 "message": "No orders found in SAP system and no fallback data available",
#                 "inserted_orders": []
#             }), 404
        
#         inserted = []
#         skipped = []
        
#         with _db_session() as db:
#             for data in sap_orders:
#                 try:
#                     # Handle both real SAP format and transformed format
#                     if "PROCESS_ORDER" in data:
#                         # Real SAP format - transform to our internal format
#                         order_id = data["PROCESS_ORDER"]
#                         material = data["MATERIAL"]
#                         quantity = data["TOTAL_QTY"]
#                         unit = data["UOM"]
#                         priority = int(data["PRIORITY_ID"])
#                         plant = data["PLANT"]
#                         created_at = data["CREATED_ON"]
                        
#                         # Generate missing fields for real SAP data
#                         version = "BKL1"  # Default version
#                         batch = f"B-{created_at.replace('-', '')}-01"  # Generate batch from date
#                         status = "Pending"
#                         material_desc = f"Material {material}"  # Default description
#                     else:
#                         # Already transformed format
#                         order_id = data["po_number"]
#                         material = data["material"]
#                         quantity = data["quantity"]
#                         unit = data["unit"]
#                         priority = data["priority"]
#                         plant = data["plant"]
#                         created_at = data["created_at"]
#                         version = data["version"]
#                         batch = data["batch"]
#                         status = data["status"]
#                         material_desc = data["material_desc"]
                    
#                     # Check if order already exists (more comprehensive check)
#                     existing_order = db.query(ProcessOrder).filter(
#                         ProcessOrder.order_id == order_id,
#                         ProcessOrder.material == material
#                     ).first()
                    
#                     if existing_order:
#                         print(f"⚠️ Order {order_id} with material {material} already exists, skipping...")
#                         skipped.append({
#                             "order_id": order_id,
#                             "material": material,
#                             "reason": "Order with same PO number and material already exists"
#                         })
#                         continue
                    
#                     # Calculate expected weight
#                     expected = _convert_to_tons(
#                         quantity,
#                         unit,
#                         material_desc,
#                         material,
#                         version
#                     )
                    
#                     # Create new order
#                     order = ProcessOrder(
#                         order_id=order_id,
#                         material=material,
#                         version=version,
#                         batch=batch,
#                         quantity=quantity,
#                         unit=unit,
#                         status=status,
#                         priority=priority,
#                         plant=plant,
#                         material_desc=material_desc,
#                         sap_created_on=created_at,
#                         expected_weight=expected
#                     )
#                     db.add(order)
#                     inserted.append({
#                         "order_id": order.order_id,
#                         "expected_weight": expected,
#                         "unit": order.unit,
#                         "quantity": order.quantity,
#                         "material_desc": order.material_desc
#                     })
                    
#                 except Exception as e:
#                     print(f"❌ Error processing order {data.get('po_number', 'unknown')}: {e}")
#                     skipped.append({
#                         "order_id": data.get("po_number", "unknown"),
#                         "reason": f"Processing error: {str(e)}"
#                     })
#                     continue
            
#             db.commit()
        
#         # Prepare response message
#         if sap_error:
#             message = f"Successfully synced {len(inserted)} orders (using fallback data - SAP API error: {sap_error})"
#         else:
#             message = f"Successfully synced {len(inserted)} orders from SAP API"
        
#         return jsonify({
#             "ok": True,
#             "inserted_orders": inserted,
#             "skipped_orders": skipped,
#             "total_fetched": len(sap_orders),
#             "total_inserted": len(inserted),
#             "total_skipped": len(skipped),
#             "sap_api_error": sap_error,
#             "used_fallback": sap_error is not None,
#             "message": message
#         })
        
#     except Exception as e:
#         print(f"❌ SAP sync failed: {e}")
#         return jsonify({
#             "ok": False,
#             "message": f"Failed to sync orders: {str(e)}",
#             "inserted_orders": []
#         }), 500
# backend/routes/sap_sync.py
from flask import Blueprint, jsonify, request
from sqlalchemy.orm import sessionmaker
from sqlalchemy import text, nullslast, func
from database import postgres_engine, engine as mssql_engine
from models.process_order_pg import ProcessOrderPG as ProcessOrder
from services.auto_validator import _convert_to_tons
from services.sap_real_client import SAPRealClient
from services.system_logger import system_logger, log_sap_event, log_hercules_event
from services.auth_service import optional_auth, get_allowed_order_types
import os
import requests
from requests.auth import HTTPBasicAuth
from datetime import datetime, date

SAP_USERNAME = os.getenv("SAP_USERNAME", "99999")
SAP_PASSWORD = os.getenv("SAP_PASSWORD", "P@ssw0rdP@ssw0rd")
SAP_BASE_URL = os.getenv("SAP_BASE_URL", "https://vhmioqs4ci.sap.mc3.com.sa:44300")
SAP_CLIENT = os.getenv("SAP_CLIENT", "250")

# DB session
PostgresSessionLocal = sessionmaker(
    bind=postgres_engine, autoflush=False, autocommit=False, future=True
)

def _db_session():
    return PostgresSessionLocal()


def _parse_creation_date(order_data):
    """
    Parse creation date from an order dict (SAP raw or transformed).
    Returns date or None if unparseable.
    Handles CREATED_ON (YYYYMMDD or YYYY-MM-DD) and created_at (ISO or YYYY-MM-DD).
    """
    raw = order_data.get("CREATED_ON") or order_data.get("created_at")
    if not raw:
        return None
    s = str(raw).strip()
    if not s:
        return None
    try:
        if len(s) >= 8 and s[:8].isdigit():
            return datetime.strptime(s[:8], "%Y%m%d").date()
        if len(s) >= 10:
            return datetime.strptime(s[:10], "%Y-%m-%d").date()
        return None
    except (ValueError, TypeError):
        return None


# Orders with creation date before this are not synced (do not take).
SAP_SYNC_CREATED_ON_OR_AFTER = date(2026, 1, 1)

sap_sync_bp = Blueprint("sap_sync", __name__, url_prefix="/api/sap-sync")

@sap_sync_bp.route("/seed-orders", methods=["POST"])
@optional_auth
def seed_orders():
    """
    Fetch process orders from SAP API and insert into process_orders table.
    Supports optional order_type filter: 'MILLING', 'PACKING', or empty for all.
    """
    try:
        # ✅ Get optional order_type filter (Jan 30, 2026)
        order_type_filter = request.args.get('order_type', '').upper().strip()
        filter_msg = f" (filter: {order_type_filter})" if order_type_filter else " (all orders)"
        
        log_id = log_sap_event(
            action="Order Sync Started",
            status="InProgress",
            details=f"Fetching process orders from SAP API{filter_msg}"
        )
        
        print(f"🔄 Attempting to fetch orders from SAP API{filter_msg}...")
        sap_orders = []
        sap_error = None

        # --- Try SAPRealClient first ---
        try:
            sap_client = SAPRealClient()
            sap_orders = sap_client.get_process_orders()
            if sap_orders and len(sap_orders) > 0:
                print(f"✅ Retrieved {len(sap_orders)} orders from SAPRealClient")
            else:
                raise Exception("No orders returned from SAPRealClient")

        except Exception as e:
            sap_error = str(e)
            print(f"⚠️ SAPRealClient failed: {sap_error}")
            print("🔄 Trying direct API call...")

            # --- Direct API call with CORRECT endpoint ---
            try:
                import requests
                from requests.auth import HTTPBasicAuth

                # ✅ CORRECT: Use HTTPS:44300 instead of HTTP:8000
                url = f"{SAP_BASE_URL}/zmi_get_orders/GETORD"
                params = {"sap-client": SAP_CLIENT}
                
                print(f"🔗 Calling SAP API: {url}")
                print(f"🔍 Parameters: {params}")

                response = requests.get(
                    url,
                    params=params,
                    auth=HTTPBasicAuth(SAP_USERNAME, SAP_PASSWORD),
                    timeout=30,
                    headers={
                        "Accept": "application/json",
                        "User-Agent": "Mozilla/5.0"
                    },
                    verify=False  # SAP uses self-signed cert
                )

                print(f"✅ Status: {response.status_code}")
                print(f"✅ Response preview: {response.text[:200]}")

                if response.status_code == 200:
                    try:
                        raw_data = response.json()
                        print(f"✅ Direct API call successful, got {len(raw_data)} orders")

                        sap_orders = []
                        for item in raw_data:
                            try:
                                priority_val = item.get("PRIORITY_ID")
                                try:
                                    priority = int(priority_val) if priority_val else 0
                                except:
                                    priority = 0

                                transformed = {
                                    "po_number": item.get("PROCESS_ORDER", "").strip(),
                                    "material": item.get("MATERIAL", "").strip(),
                                    "version": item.get("VERSION", "v1.0").strip(),
                                    "batch": f"BATCH-{item.get('PROCESS_ORDER', 'UNKNOWN')}-{item.get('CREATED_ON', '20250922')}",
                                    "quantity": float(item.get("TOTAL_QTY", 0)),
                                    "unit": item.get("UOM", "KG").strip(),
                                    "status": "Pending",
                                    "priority": priority,
                                    "plant": item.get("PLANT", "").strip(),
                                    "material_desc": item.get("MATERIAL_DESC", "").strip(),
                                    "created_at": item.get("CREATED_ON", "2025-09-22"),
                                    "STATUS": (item.get("STATUS") or "").strip(),
                                }
                                sap_orders.append(transformed)

                            except Exception as transform_error:
                                print(f"❌ Error transforming order: {transform_error}")
                                continue

                        sap_error = None
                    except Exception as json_err:
                        print(f"❌ JSON parse error: {json_err}")
                        sap_error = f"Response not JSON: {response.text[:200]}"
                else:
                    sap_error = f"Status {response.status_code}: {response.text[:200]}"
                    print(f"❌ {sap_error}")

            except Exception as direct_error:
                print(f"❌ Direct API call failed: {direct_error}")
                sap_error = f"Direct API failed: {str(direct_error)}"

        if not sap_orders:
            return jsonify({
                "ok": False,
                "message": f"Failed to fetch orders from SAP API. Error: {sap_error}",
                "inserted_orders": [],
                "sap_error": sap_error
            }), 500

        # ✅ Filter orders by order_type if specified (Jan 30, 2026)
        # Order type is determined by MATERIAL prefix:
        # - Material starting with "13" = MILLING (e.g., 000000000001300001)
        # - Material starting with "14" = PACKING (e.g., 000000000001400001)
        total_before_filter = len(sap_orders)
        
        # Debug: Print material values from first few orders
        print(f"🔍 DEBUG: Checking material prefixes from {len(sap_orders)} orders:")
        for i, order in enumerate(sap_orders[:5]):
            material = str(order.get('MATERIAL', order.get('material', ''))).strip()
            # Strip leading zeros to find the actual prefix
            material_stripped = material.lstrip('0')
            prefix = material_stripped[:2] if len(material_stripped) >= 2 else ''
            po_num = order.get('PROCESS_ORDER', order.get('po_number', 'UNKNOWN'))
            order_type = 'MILLING' if prefix == '13' else ('PACKING' if prefix == '14' else 'UNKNOWN')
            print(f"   Order {i+1}: PO={po_num}, Material={material}, Prefix={prefix}, Type={order_type}")
        
        if order_type_filter and order_type_filter in ('MILLING', 'PACKING'):
            filtered_orders = []
            for order in sap_orders:
                # Get material from either SAP format or transformed format
                material = str(order.get('MATERIAL', order.get('material', ''))).strip()
                # Strip leading zeros to find the actual prefix
                material_stripped = material.lstrip('0')
                prefix = material_stripped[:2] if len(material_stripped) >= 2 else ''
                
                # MILLING = material prefix 13, PACKING = material prefix 14
                is_milling = prefix == '13'
                is_packing = prefix == '14'
                
                if order_type_filter == 'MILLING' and is_milling:
                    filtered_orders.append(order)
                elif order_type_filter == 'PACKING' and is_packing:
                    filtered_orders.append(order)
            
            print(f"🔍 Filtered orders: {len(filtered_orders)} {order_type_filter} orders (from {total_before_filter} total)")
            sap_orders = filtered_orders
            
            if not sap_orders:
                return jsonify({
                    "ok": True,
                    "message": f"No {order_type_filter} orders found in SAP (filtered from {total_before_filter} total orders)",
                    "inserted_orders": [],
                    "updated_orders": [],
                    "skipped_orders": [],
                    "total_fetched": 0,
                    "total_inserted": 0,
                    "total_updated": 0,
                    "total_skipped": 0,
                    "filter_applied": order_type_filter
                })

        # ✅ Filter: do not take orders created before 01/01/2026
        before_date_filter = len(sap_orders)
        filtered_by_date = []
        for o in sap_orders:
            d = _parse_creation_date(o)
            if d is not None and d >= SAP_SYNC_CREATED_ON_OR_AFTER:
                filtered_by_date.append(o)
        sap_orders = filtered_by_date
        skipped_before_2026 = before_date_filter - len(sap_orders)
        if skipped_before_2026 > 0:
            print(f"🔍 SAP sync: excluded {skipped_before_2026} order(s) created before {SAP_SYNC_CREATED_ON_OR_AFTER}")

        inserted, updated, skipped = [], [], []

        with _db_session() as db:
            for data in sap_orders:
                try:
                    if "PROCESS_ORDER" in data:
                        order_id = data["PROCESS_ORDER"]
                        material = data["MATERIAL"]
                        quantity = data["TOTAL_QTY"]
                        unit = data["UOM"]
                        try:
                            priority = int(data.get("PRIORITY_ID")) if data.get("PRIORITY_ID") else 0
                        except:
                            priority = 0
                        plant = data["PLANT"]
                        created_at = data["CREATED_ON"]
                        version = data.get("VERSION", "BKL1")
                        batch = f"B-{created_at.replace('-', '')}-01"
                        status = "Pending"
                        material_desc = data.get("MATERIAL_DESC", f"Material {material}")
                    else:
                        order_id = data["po_number"]
                        material = data["material"]
                        quantity = data["quantity"]
                        unit = data["unit"]
                        priority = data["priority"]
                        plant = data["plant"]
                        created_at = data["created_at"]
                        version = data["version"]
                        batch = data["batch"]
                        status = "Pending"
                        material_desc = data["material_desc"]

                    # ✅ SAP Status (e.g. CNF = confirmed, COMP = completed): store in status column; 100% confirmed, never send again
                    sap_status_raw = (data.get("STATUS") or data.get("status") or "").strip().upper()
                    is_cnf = (sap_status_raw == "CNF")
                    is_comp = (sap_status_raw == "COMP")
                    if is_cnf:
                        status = "CNF"
                        confirmed_qty_val = quantity
                        is_final_sent_val = True
                    elif is_comp:
                        status = "COMP"
                        confirmed_qty_val = quantity
                        is_final_sent_val = True
                    else:
                        confirmed_qty_val = None
                        is_final_sent_val = False

                    # ✅ Do not take orders created before 01/01/2026 (safety check in loop)
                    order_created_date = _parse_creation_date(data)
                    if order_created_date is None or order_created_date < SAP_SYNC_CREATED_ON_OR_AFTER:
                        skipped.append({"order_id": order_id, "reason": "created_before_2026"})
                        continue

                    # ✅ Calculate internal priority based on duplication
                    # Check for orders with same version in Pending/InProgress
                    duplicate_count = db.query(ProcessOrder).filter(
                        ProcessOrder.version == version,
                        ProcessOrder.status.in_(['Pending', 'InProgress']),
                        ProcessOrder.order_id != order_id
                    ).count()
                    
                    if duplicate_count > 0:
                        # Higher priority (lower number) for duplicates
                        # If SAP priority is not set, use calculated
                        if priority == 0 or priority > 10:
                            priority = min(10, 1 + duplicate_count)

                    existing = db.query(ProcessOrder).filter(
                        ProcessOrder.order_id == order_id,
                        ProcessOrder.material == material
                    ).first()

                    expected = _convert_to_tons(quantity, unit, material_desc, material, version)

                    # ✅ UPDATE existing order
                    if existing:
                        # ✅ Allow updates for InProgress/Completed/Validated/CNF/COMP orders (Safe fields only)
                        if existing.status in ["Pending", "Rejected", "InProgress", "Completed", "Validated", "CNF", "COMP"]:
                            existing.version = version
                            existing.batch = batch
                            existing.quantity = quantity
                            existing.unit = unit
                            # ✅ Priority ID from SAP: update display value only; do NOT overwrite priority (queue order) so drag order is preserved
                            existing.priority_id = priority
                            existing.plant = plant
                            existing.material_desc = material_desc
                            existing.sap_created_on = created_at
                            existing.expected_weight = expected
                            if hasattr(existing, 'updated_at'):
                                existing.updated_at = datetime.utcnow()
                            # ✅ When SAP sends CNF or COMP: store in status column, set 100% confirmed, do not send again
                            if is_cnf:
                                existing.status = "CNF"
                                existing.confirmed_qty = confirmed_qty_val
                                existing.is_final_sent = True
                            elif is_comp:
                                existing.status = "COMP"
                                existing.confirmed_qty = confirmed_qty_val
                                existing.is_final_sent = True
                            
                            updated.append({
                                "order_id": order_id,
                                "expected_weight": expected,
                                "unit": unit,
                                "quantity": quantity,
                                "material_desc": material_desc,
                                "previous_status": existing.status,
                                "auto_updated": True,
                                "priority_from_sap": priority
                            })
                            print(f"♻️ Updated existing order {order_id} (status: {existing.status}, priority from SAP: {priority})")
                        else:
                            # Completed or other statuses - skip update
                            print(f"⚠️ Skipping update for order {order_id} (current status: {existing.status} - preserving order state)")
                            skipped.append({
                                "order_id": order_id,
                                "reason": f"Order status is '{existing.status}' - preserving state"
                            })
                        continue

                    # ✅ INSERT new order: priority_id + hercules_priority from SAP (SAP never changes hercules_priority on update)
                    new_order = ProcessOrder(
                        order_id=order_id,
                        material=material,
                        version=version,
                        batch=batch,
                        quantity=quantity,
                        unit=unit,
                        status=status,
                        priority=priority,
                        priority_id=priority,
                        hercules_priority=priority,
                        plant=plant,
                        material_desc=material_desc,
                        sap_created_on=created_at,
                        expected_weight=expected,
                        confirmed_qty=confirmed_qty_val,
                        is_final_sent=is_final_sent_val,
                    )
                    db.add(new_order)
                    inserted.append({
                        "order_id": order_id,
                        "expected_weight": expected,
                        "unit": unit,
                        "quantity": quantity,
                        "material_desc": material_desc
                    })

                except Exception as e:
                    print(f"❌ Error processing order: {e}")
                    skipped.append({"order_id": data.get("po_number", "unknown"), "reason": str(e)})
                    continue

            db.commit()
            
            # ✅ Jan 30, 2026: DISABLED - Preserve SAP priorities as-is
            # Previously recalculated priorities into sequential numbers (1, 2, 3...) based on conflict groups
            # Now we keep SAP's original group-wise priorities so orders with same SAP priority
            # are displayed together (e.g., all "1"s, then all "2"s)
            # User can still manually reorder via drag-and-drop, and changes persist
            # 
            # from services.scale_lock_service import recalculate_conflict_group_priorities
            # recalc_result = recalculate_conflict_group_priorities(db)
            # print(f"🔄 [SAP SYNC] Recalculated priorities: {recalc_result.get('updated_count', 0)} orders updated")

        log_sap_event(
            action="Order Sync Completed",
            status="Success",
            details=f"Synced {len(inserted)} new and {len(updated)} updated orders from SAP API",
            metadata={
                "total_fetched": len(sap_orders),
                "total_inserted": len(inserted),
                "total_updated": len(updated),
                "total_skipped": len(skipped)
            }
        )

        # Admin activity log: who triggered sync (Milling / Packing / All)
        try:
            operator = (getattr(request, 'current_user', None) or {}).get('username', 'Unknown')
            sync_action = "Sync All"
            if order_type_filter == "MILLING":
                sync_action = "Sync Milling"
            elif order_type_filter == "PACKING":
                sync_action = "Sync Packing"
            system_logger.log_event(
                source='Operator',
                action=sync_action,
                status='Success',
                operator=operator,
                details=f"Synced from SAP: {len(inserted)} new, {len(updated)} updated",
                metadata={
                    "order_type_filter": order_type_filter or "all",
                    "total_inserted": len(inserted),
                    "total_updated": len(updated)
                }
            )
        except Exception as log_err:
            print(f"⚠️ Failed to log sync to activity: {log_err}")

        return jsonify({
            "ok": True,
            "inserted_orders": inserted,
            "updated_orders": updated,
            "skipped_orders": skipped,
            "total_fetched": len(sap_orders),
            "total_inserted": len(inserted),
            "total_updated": len(updated),
            "total_skipped": len(skipped),
            "skipped_before_2026": skipped_before_2026,
            "message": f"Successfully synced {len(inserted)} new orders and {len(updated)} updated orders from SAP API"
        })

    except Exception as e:
        print(f"❌ SAP sync failed: {e}")
        
        log_sap_event(
            action="Order Sync Failed",
            status="Error",
            details=f"Failed to sync orders: {str(e)}",
            error_code="SYNC_ERROR"
        )
        
        return jsonify({
            "ok": False,
            "message": f"Failed to sync orders: {str(e)}",
            "inserted_orders": []
        }), 500

@sap_sync_bp.route("/orders", methods=["GET"])
@optional_auth
def get_synced_orders():
    """
    Fetch all orders from the process_orders table.
    This endpoint is used by both Process Orders Page and Order Validation Page
    to display the latest synced orders from SAP.

    ✅ Feb 9, 2026: Role-based order_type filtering.
    milling_operator  -> can only see MILLING orders
    packing_operator  -> can only see PACKING orders
    admin / manager / operator -> can see all orders
    Unauthenticated callers (e.g. emulator) are not restricted.
    """
    try:
        # Get query parameters
        status = request.args.get('status', '')
        statuses = request.args.get('statuses', '')
        order_type_param = request.args.get('order_type', '').upper().strip()
        limit = request.args.get('limit', '1000')
        offset = request.args.get('offset', '0')

        # ✅ Feb 9, 2026: Role-based order_type enforcement
        current_user = getattr(request, 'current_user', None)
        if current_user:
            user_roles = current_user.get('roles', [])
            allowed_types = get_allowed_order_types(user_roles)
            # If user can see both types, no restriction needed
            if len(allowed_types) == 1:
                # Force the allowed type regardless of what the client requested
                order_type_param = allowed_types[0]
            elif len(allowed_types) == 0:
                # No order access at all – return empty
                return jsonify({
                    "ok": True,
                    "orders": [],
                    "total_count": 0,
                    "message": "No order access for your role"
                })
        
        # Parse limit and offset
        try:
            limit_int = int(limit)
        except ValueError:
            limit_int = 1000
        
        try:
            offset_int = int(offset)
        except ValueError:
            offset_int = 0
        
        with _db_session() as db:
            # Build query
            query = db.query(ProcessOrder)
            
            # Apply status filter
            if status and status != 'All' and status != '':
                query = query.filter(ProcessOrder.status == status)
            elif statuses:
                # Handle multiple statuses (comma-separated)
                status_list = [s.strip() for s in statuses.split(',') if s.strip()]
                if status_list:
                    query = query.filter(ProcessOrder.status.in_(status_list))
            
            # ✅ Jan 30, 2026: Filter by order_type when provided (MILLING / PACKING)
            # This ensures pagination is per-type so priority-1 orders show at top of each tab
            # Material prefix: 13 = MILLING, 14 = PACKING (after stripping leading zeros)
            if order_type_param and order_type_param in ('MILLING', 'PACKING'):
                material_prefix = func.ltrim(ProcessOrder.material, '0')
                if order_type_param == 'MILLING':
                    query = query.filter(material_prefix.like('13%'))
                else:
                    query = query.filter(material_prefix.like('14%'))
            
            # Get total count before pagination (for frontend to know total pages)
            total_count = query.count()
            
            # ✅ Order by hercules_priority (queue order); SAP does not change it
            orders = query.order_by(
                nullslast(func.nullif(ProcessOrder.hercules_priority, 0).asc()),
                ProcessOrder.id.asc()
            ).offset(offset_int).limit(limit_int).all()
            
            # =========================================================================
            # CONFLICT DETECTION: Check which orders have priority conflicts
            # Priority is relevant when:
            # 1. Multiple orders have the same product version (same scales)
            # 2. Multiple orders have different versions but share the same scale(s)
            # =========================================================================
            
            # Build version map and scale map for active orders (Pending, InProgress)
            active_statuses = ['Pending', 'InProgress']
            version_counts = {}  # {version: [order_ids]}
            scale_to_orders = {}  # {scale: [order_ids]}
            
            for o in orders:
                if o.status not in active_statuses:
                    continue
                    
                order_id = o.order_id
                version = (o.version or "").upper().strip()
                
                # Track version usage
                if version:
                    if version not in version_counts:
                        version_counts[version] = []
                    version_counts[version].append(order_id)
                
                # Track scale usage (from milling version mapping - we'll use order's byproduct scales)
                # Get byproduct scales from order
                for scale_attr in ['scale1', 'scale2', 'scale3']:
                    scale = getattr(o, scale_attr, None)
                    if scale:
                        scale_upper = scale.upper().strip()
                        if scale_upper not in scale_to_orders:
                            scale_to_orders[scale_upper] = []
                        if order_id not in scale_to_orders[scale_upper]:
                            scale_to_orders[scale_upper].append(order_id)
            
            # Determine which orders have conflicts
            orders_with_conflicts = set()
            
            # 1. Version conflicts - multiple orders with same version
            for version, order_ids in version_counts.items():
                if len(order_ids) > 1:
                    for oid in order_ids:
                        orders_with_conflicts.add(oid)
            
            # 2. Scale conflicts - multiple orders using same scale
            for scale, order_ids in scale_to_orders.items():
                if len(order_ids) > 1:
                    for oid in order_ids:
                        orders_with_conflicts.add(oid)
            
            # Serialize orders
            serialized_orders = []
            for order in orders:
                serialized_orders.append({
                    "id": order.id,
                    "order_id": order.order_id,
                    "po_number": order.order_id,  # For compatibility with frontend
                    "material": order.material,
                    "version": order.version,
                    "batch": order.batch,
                    "quantity": float(order.quantity) if order.quantity is not None else None,
                    "unit": order.unit,
                    "status": order.status,
                    "priority": getattr(order, "hercules_priority", None) or order.priority,
                    "priority_id": getattr(order, "priority_id", None),
                    "plant": order.plant,
                    "material_desc": order.material_desc,
                    "confirmed_qty": float(order.confirmed_qty) if hasattr(order, 'confirmed_qty') and order.confirmed_qty is not None else None,
                    "last_confirmed_qty": float(order.last_confirmed_qty) if hasattr(order, 'last_confirmed_qty') and order.last_confirmed_qty is not None else 0.0,
                    "expected_weight": float(order.expected_weight) if hasattr(order, 'expected_weight') and order.expected_weight is not None else None,
                    "validation_method": getattr(order, 'validation_method', None),
                    "confirmed_text": getattr(order, 'confirmed_text', None),
                    "scrap": float(order.scrap) if hasattr(order, 'scrap') and order.scrap is not None else None,
                    "sap_created_on": order.sap_created_on,
                    "created_at": order.created_at.isoformat() if order.created_at else None,
                    "updated_at": order.updated_at.isoformat() if hasattr(order, 'updated_at') and order.updated_at else None,
                    "order_type": getattr(order, 'order_type', None),
                    # Byproduct scale fields for MILLING orders
                    "scale1": getattr(order, 'scale1', None),
                    "scale1_qty": float(order.scale1_qty) if hasattr(order, 'scale1_qty') and order.scale1_qty is not None else None,
                    "scale2": getattr(order, 'scale2', None),
                    "scale2_qty": float(order.scale2_qty) if hasattr(order, 'scale2_qty') and order.scale2_qty is not None else None,
                    "scale3": getattr(order, 'scale3', None),
                    "scale3_qty": float(order.scale3_qty) if hasattr(order, 'scale3_qty') and order.scale3_qty is not None else None,
                    # ✅ Priority conflict detection - show priority only when relevant
                    "has_priority_conflict": order.order_id in orders_with_conflicts,
                })
            
            return jsonify({
                "ok": True,
                "orders": serialized_orders,
                "total": total_count,  # Total count before pagination for frontend
                "page_count": len(serialized_orders),  # Count on current page
                "message": f"Retrieved {len(serialized_orders)} orders from database (total: {total_count})"
            })
            
    except Exception as e:
        print(f"❌ Failed to fetch orders: {e}")
        return jsonify({
            "ok": False,
            "message": f"Failed to fetch orders: {str(e)}",
            "orders": []
        }), 500


@sap_sync_bp.route("/send-raw-data", methods=["POST"])
def send_raw_data_to_sap():
    """
    Fetch data from [HerculesV2].[dbo].[ASMArchive_DB5] table and send to SAP.
    This endpoint retrieves all data from the ASMArchive_DB5 table and sends it to SAP.
    """
    try:
        # Log data sync start
        log_id = log_hercules_event(
            action="Raw Data Sync Started",
            status="InProgress",
            details="Fetching data from ASMArchive_DB5 and sending to SAP"
        )
        
        print("🔄 Starting raw data sync from ASMArchive_DB5 to SAP...")
        
        # Fetch data from SQL Server table
        raw_data = []
        with mssql_engine.connect() as connection:
            try:
                # Query the ASMArchive_DB5 table - get only latest 20 rows
                query = text("SELECT TOP 20 * FROM [HerculesV2].[dbo].[ASMArchive_DB5] ORDER BY CreatedOn DESC")
                result = connection.execute(query)
                
                # Convert to list of dictionaries using a more robust approach
                for row in result:
                    row_dict = {}
                    # Use row._mapping to get column names and values
                    for column_name, value in row._mapping.items():
                        # Convert datetime and other special types to string for JSON serialization
                        if hasattr(value, 'isoformat'):
                            row_dict[column_name] = value.isoformat()
                        elif value is None:
                            row_dict[column_name] = None
                        elif hasattr(value, '__class__') and 'Decimal' in str(value.__class__):
                            # Convert Decimal to float for JSON serialization
                            row_dict[column_name] = float(value)
                        else:
                            row_dict[column_name] = value
                    raw_data.append(row_dict)
                
                print(f"✅ Successfully fetched {len(raw_data)} latest records from ASMArchive_DB5 table")
                
            except Exception as db_error:
                print(f"❌ Database error: {db_error}")
                return jsonify({
                    "ok": False,
                    "message": f"Failed to fetch data from ASMArchive_DB5 table: {str(db_error)}",
                    "records_fetched": 0,
                    "records_sent": 0
                }), 500
        
        if not raw_data:
            return jsonify({
                "ok": False,
                "message": "No data found in ASMArchive_DB5 table",
                "records_fetched": 0,
                "records_sent": 0
            }), 404
        
        # Send data to SAP
        sap_response = None
        sap_error = None
        records_sent = 0
        
        try:
            # SAP API endpoint for sending raw data (updated endpoint)
            sap_url = f"{SAP_BASE_URL}/zmi_raw_hercl/HERC"
            
            # Prepare payload for SAP - send raw data directly
            sap_payload = raw_data  # Send the raw data directly as the payload
            
            print(f"🔗 Sending {len(raw_data)} records to SAP API...")
            print(f"🔍 Payload size: {len(str(sap_payload))} characters")
            print(f"🔍 First record ID: {raw_data[0].get('ASMArchive_DB5ID') if raw_data else 'None'}")
            print(f"🔍 Last record ID: {raw_data[-1].get('ASMArchive_DB5ID') if raw_data else 'None'}")
            
            # Send to SAP with sap-client parameter
            response = requests.post(
                sap_url,
                json=sap_payload,
                params={"sap-client": SAP_CLIENT, "spnego": "disabled"},
                auth=HTTPBasicAuth(SAP_USERNAME, SAP_PASSWORD),
                timeout=60,  # Longer timeout for large data
                headers={
                    "Content-Type": "application/json",
                    "Accept": "application/json",
                    "User-Agent": "Hercules-SFMS/1.0"
                },
                verify=False  # SAP uses self-signed certificate
            )
            
            print(f"🔍 SAP API Response Status: {response.status_code}")
            print(f"🔍 SAP API Response Text: {response.text}")
            
            if response.status_code == 200:
                # Handle the new API response format
                response_text = response.text.strip()
                if response_text == "Data Saved Correctly":
                    sap_response = {"message": "Data Saved Correctly", "status": "success"}
                    records_sent = len(raw_data)
                    print(f"✅ Successfully sent {records_sent} records to SAP - Data Saved Correctly")
                elif response_text == "Error While Saving Data":
                    sap_error = "SAP API returned: Error While Saving Data"
                    print(f"❌ SAP API Error: {sap_error}")
                else:
                    # Try to parse as JSON for other response formats
                    try:
                        sap_response = response.json()
                        records_sent = len(raw_data)
                        print(f"✅ Successfully sent {records_sent} records to SAP")
                    except:
                        sap_response = {"message": response_text, "status": "success"}
                        records_sent = len(raw_data)
                        print(f"✅ Successfully sent {records_sent} records to SAP")
            else:
                sap_error = f"SAP API returned status {response.status_code}: {response.text[:500]}"
                print(f"❌ SAP API Error: {sap_error}")
                
        except requests.exceptions.Timeout:
            sap_error = "SAP server request timed out. Please try again."
            print(f"❌ SAP API Timeout: Request timed out after 60 seconds")
        except requests.exceptions.ConnectionError as conn_err:
            sap_error = "Unable to connect to SAP server. Please check network connectivity and SAP server status."
            print(f"❌ SAP API Connection Error: {str(conn_err)}")
        except Exception as sap_api_error:
            sap_error = f"SAP API Error: {str(sap_api_error)}"
            print(f"❌ SAP API Error: {sap_error}")
        
        # Prepare response
        if sap_error:
            # Log sync failure
            log_hercules_event(
                action="Raw Data Sync Failed",
                status="Error",
                details=f"Data fetched successfully but failed to send to SAP: {sap_error}",
                error_code="SAP_SEND_ERROR",
                metadata={
                    "records_fetched": len(raw_data),
                    "records_sent": records_sent,
                    "sap_error": sap_error
                }
            )
            
            return jsonify({
                "ok": False,
                "message": f"Data fetched successfully but failed to send to SAP: {sap_error}",
                "records_fetched": len(raw_data),
                "records_sent": records_sent,
                "sap_error": sap_error,
                "sample_data": raw_data[:3] if raw_data else [],  # Include first 3 records as sample
                "data_summary": {
                    "total_records": len(raw_data),
                    "first_record_id": raw_data[0].get('ASMArchive_DB5ID') if raw_data else None,
                    "last_record_id": raw_data[-1].get('ASMArchive_DB5ID') if raw_data else None,
                    "date_range": {
                        "earliest": raw_data[-1].get('CreatedOn') if raw_data else None,
                        "latest": raw_data[0].get('CreatedOn') if raw_data else None
                    }
                }
            }), 500
        else:
            # Log successful sync
            log_hercules_event(
                action="Raw Data Sync Completed",
                status="Success",
                details=f"Successfully sent {records_sent} latest records from ASMArchive_DB5 to SAP",
                metadata={
                    "records_fetched": len(raw_data),
                    "records_sent": records_sent,
                    "sap_response": sap_response
                }
            )
            
            return jsonify({
                "ok": True,
                "message": f"Successfully sent {records_sent} latest records from ASMArchive_DB5 to SAP via new API endpoint (limited to 20 rows)",
                "records_fetched": len(raw_data),
                "records_sent": records_sent,
                "sap_response": sap_response,
                "api_endpoint": "http://vhmioqs4ci.sap.mc3.com.sa:8000/zmi_raw_hercl/HERC",
                "sample_data": raw_data[:3] if raw_data else [],  # Include first 3 records as sample
                "data_summary": {
                    "total_records": len(raw_data),
                    "first_record_id": raw_data[0].get('ASMArchive_DB5ID') if raw_data else None,
                    "last_record_id": raw_data[-1].get('ASMArchive_DB5ID') if raw_data else None,
                    "date_range": {
                        "earliest": raw_data[-1].get('CreatedOn') if raw_data else None,
                        "latest": raw_data[0].get('CreatedOn') if raw_data else None
                    }
                }
            })
            
    except Exception as e:
        print(f"❌ Raw data sync failed: {e}")
        
        # Log sync failure
        log_hercules_event(
            action="Raw Data Sync Failed",
            status="Error",
            details=f"Failed to sync raw data: {str(e)}",
            error_code="SYNC_ERROR"
        )
        
        return jsonify({
            "ok": False,
            "message": f"Failed to sync raw data: {str(e)}",
            "records_fetched": 0,
            "records_sent": 0
        }), 500


@sap_sync_bp.route("/test-data-fetch", methods=["GET"])
def test_data_fetch():
    """
    Test endpoint to verify data fetching from ASMArchive_DB5 table without sending to SAP.
    This helps debug data fetching issues.
    """
    try:
        print("🔄 Testing data fetch from ASMArchive_DB5 table...")
        
        # Fetch data from SQL Server table
        raw_data = []
        with mssql_engine.connect() as connection:
            try:
                # Query the ASMArchive_DB5 table - get only latest 20 rows
                query = text("SELECT TOP 20 * FROM [HerculesV2].[dbo].[ASMArchive_DB5] ORDER BY CreatedOn DESC")
                result = connection.execute(query)
                
                # Convert to list of dictionaries using a more robust approach
                for row in result:
                    row_dict = {}
                    # Use row._mapping to get column names and values
                    for column_name, value in row._mapping.items():
                        # Convert datetime and other special types to string for JSON serialization
                        if hasattr(value, 'isoformat'):
                            row_dict[column_name] = value.isoformat()
                        elif value is None:
                            row_dict[column_name] = None
                        elif hasattr(value, '__class__') and 'Decimal' in str(value.__class__):
                            # Convert Decimal to float for JSON serialization
                            row_dict[column_name] = float(value)
                        else:
                            row_dict[column_name] = value
                    raw_data.append(row_dict)
                
                print(f"✅ Successfully fetched {len(raw_data)} latest records from ASMArchive_DB5 table")
                
            except Exception as db_error:
                print(f"❌ Database error: {db_error}")
                return jsonify({
                    "ok": False,
                    "message": f"Failed to fetch data from ASMArchive_DB5 table: {str(db_error)}",
                    "records_fetched": 0
                }), 500
        
        if not raw_data:
            return jsonify({
                "ok": False,
                "message": "No data found in ASMArchive_DB5 table",
                "records_fetched": 0
            }), 404
        
        return jsonify({
            "ok": True,
            "message": f"Successfully fetched {len(raw_data)} records from ASMArchive_DB5 table",
            "records_fetched": len(raw_data),
            "all_data": raw_data,  # Return all data for testing
            "data_summary": {
                "total_records": len(raw_data),
                "first_record_id": raw_data[0].get('ASMArchive_DB5ID') if raw_data else None,
                "last_record_id": raw_data[-1].get('ASMArchive_DB5ID') if raw_data else None,
                "date_range": {
                    "earliest": raw_data[-1].get('CreatedOn') if raw_data else None,
                    "latest": raw_data[0].get('CreatedOn') if raw_data else None
                }
            }
        })
            
    except Exception as e:
        print(f"❌ Data fetch test failed: {e}")
        return jsonify({
            "ok": False,
            "message": f"Failed to test data fetch: {str(e)}",
            "records_fetched": 0
        }), 500
