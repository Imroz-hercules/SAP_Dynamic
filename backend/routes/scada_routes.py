# # routes/scada_routes.py
# from flask import Blueprint, jsonify, request
# from sqlalchemy import text
# from database import engine as mssql_engine
# import logging

# scada_bp = Blueprint("scada", __name__, url_prefix="/api")

# logger = logging.getLogger(__name__)

# # CORS preflight handler
# @scada_bp.route("/scada/readings", methods=["OPTIONS"])
# def handle_scada_options():
#     """Handle CORS preflight requests"""
#     return '', 200, {
#         'Access-Control-Allow-Origin': 'http://localhost:5173',
#         'Access-Control-Allow-Methods': 'GET, POST, PUT, DELETE, OPTIONS',
#         'Access-Control-Allow-Headers': 'Content-Type, Authorization, ngrok-skip-browser-warning',
#         'Access-Control-Allow-Credentials': 'true'
#     }

# @scada_bp.route("/scada/readings", methods=["GET"])
# def get_scada_readings():
#     """
#     Fetch latest SCADA readings from ASMReporting_5 table with calculated values
#     based on the signal mappings provided by the user.
#     """
#     try:
#         # Add CORS headers for frontend requests
#         response_headers = {
#             'Access-Control-Allow-Origin': 'http://localhost:5173',
#             'Access-Control-Allow-Methods': 'GET, POST, PUT, DELETE, OPTIONS',
#             'Access-Control-Allow-Headers': 'Content-Type, Authorization, ngrok-skip-browser-warning',
#             'Access-Control-Allow-Credentials': 'true'
#         }
#         # SQL query to get the latest row from ASMReporting_5
#         sql = text("""
#             SELECT TOP 1 
#                 WG201, WG202, WG101, WG301, WG302,
#                 WG501, WG502, WG503,
#                 DM101, DM102, DM201, DM202, DM203,
#                 PL601_TOT, PL602_TOT, PL603_TOT,
#                 CreatedOn
#             FROM [HerculesV2].[dbo].[ASMReporting_5]
#             ORDER BY ASMReporting_5ID DESC
#         """)
        
#         with mssql_engine.connect() as conn:
#             row = conn.execute(sql).mappings().first()
            
#             if not row:
#                 return jsonify({
#                     "error": "No SCADA data found",
#                     "timestamp": None
#                 }), 404, response_headers
            
#             # Convert row to dict and ensure all values are floats
#             data = dict(row)
#             for key in data:
#                 if key != 'CreatedOn':
#                     try:
#                         data[key] = float(data[key]) if data[key] is not None else 0.0
#                     except (ValueError, TypeError):
#                         data[key] = 0.0
            
#             # Log the raw data for debugging
#             logger.info(f"Raw database row: {data}")
            
#             # Calculate the derived values based on user's requirements
#             scada_readings = {
#                 # Direct mappings
#                 "cleaningScale": data.get("WG201", 0.0),
#                 "totalRunningTime": data.get("WG202", 0.0),
#                 "dryWheatScale": data.get("WG101", 0.0),
#                 "totalScreening": data.get("WG301", 0.0),
#                 "totalFlour": data.get("WG302", 0.0),
                
#                 # Calculated values
#                 "flour": data.get("WG501", 0.0) + data.get("WG502", 0.0),  # WG501 + WG502 = Flour
#                 "totalBran": data.get("WG503", 0.0),  # WG503 = Bran
#                 "totalWheat": (data.get("WG501", 0.0) + data.get("WG502", 0.0) + data.get("WG503", 0.0)),  # WG501+WG502+WG503 = TOTAL WHEAT
                
#                 # Water calculations
#                 "totalPreCleaningWater": data.get("DM101", 0.0) + data.get("DM102", 0.0),  # DM101 + DM102
#                 "waterCleanWheat": data.get("DM201", 0.0) + data.get("DM202", 0.0) + data.get("DM203", 0.0),  # DM201+DM202+DM203
#                 "totalWaterUsed": (data.get("DM101", 0.0) + data.get("DM102", 0.0) + 
#                                  data.get("DM201", 0.0) + data.get("DM202", 0.0) + data.get("DM203", 0.0)),  # DM101+DM102+DM201+DM202+DM203
                
#                 # Packing inputs from SQL Server
#                 "actualPackingOutput": data.get("PL601_TOT", 0.0),
#                 "packingStdCapacity": data.get("PL602_TOT", 0.0),
#                 "packingGoodOutput": data.get("PL603_TOT", 0.0),
#                 "packingTotalOutput": data.get("PL601_TOT", 0.0),  # Using PL601_TOT as total output
#                 "packingPlannedOutput": data.get("PL602_TOT", 0.0),  # Using PL602_TOT as planned output
#                 "packingNetHours": 0.0,  # Placeholder - can be calculated if needed
#                 "packingTotalHours": 0.0,  # Placeholder - can be calculated if needed
                
#                 # Add NULL status for debugging
#                 "packingDataStatus": {
#                     "PL601_TOT_NULL": data.get("PL601_TOT") is None,
#                     "PL602_TOT_NULL": data.get("PL602_TOT") is None,
#                     "PL603_TOT_NULL": data.get("PL603_TOT") is None,
#                 },
                
#                 # Raw signal values for debugging
#                 "rawSignals": {
#                     "WG201": data.get("WG201", 0.0),
#                     "WG202": data.get("WG202", 0.0),
#                     "WG101": data.get("WG101", 0.0),
#                     "WG301": data.get("WG301", 0.0),
#                     "WG302": data.get("WG302", 0.0),
#                     "WG501": data.get("WG501", 0.0),
#                     "WG502": data.get("WG502", 0.0),
#                     "WG503": data.get("WG503", 0.0),
#                     "DM101": data.get("DM101", 0.0),
#                     "DM102": data.get("DM102", 0.0),
#                     "DM201": data.get("DM201", 0.0),
#                     "DM202": data.get("DM202", 0.0),
#                     "DM203": data.get("DM203", 0.0),
#                     "PL601_TOT": data.get("PL601_TOT", 0.0),
#                     "PL602_TOT": data.get("PL602_TOT", 0.0),
#                     "PL603_TOT": data.get("PL603_TOT", 0.0),
#                 },
                
#                 # Metadata
#                 "lastUpdated": data.get("CreatedOn").isoformat() if data.get("CreatedOn") else None,
#                 "dataSource": "ASMReporting_5"
#             }
            
#             logger.info(f"SCADA readings fetched successfully: {scada_readings}")
#             return jsonify(scada_readings), 200, response_headers
            
#     except Exception as e:
#         logger.error(f"Error fetching SCADA readings: {e}")
#         return jsonify({
#             "error": f"Error fetching SCADA data: {str(e)}",
#             "timestamp": None
#         }), 500, response_headers

# @scada_bp.route("/scada/live-monitoring", methods=["OPTIONS"])
# def handle_live_monitoring_options():
#     """Handle CORS preflight requests for live monitoring"""
#     return '', 200, {
#         'Access-Control-Allow-Origin': 'http://localhost:5173',
#         'Access-Control-Allow-Methods': 'GET, POST, PUT, DELETE, OPTIONS',
#         'Access-Control-Allow-Headers': 'Content-Type, Authorization, ngrok-skip-browser-warning',
#         'Access-Control-Allow-Credentials': 'true'
#     }

# @scada_bp.route("/scada/live-monitoring", methods=["GET"])
# def get_live_monitoring_records():
#     """
#     Fetch latest 20 SCADA records from ASMReporting_5 table for live monitoring.
#     Returns all raw signals: WG201, WG202, WG101, WG301, WG302, WG501, WG502, WG503,
#     DM101, DM102, DM201, DM202, DM203, PL601_TOT, PL602_TOT, PL603_TOT
#     """
#     try:
#         # Add CORS headers for frontend requests
#         response_headers = {
#             'Access-Control-Allow-Origin': 'http://localhost:5173',
#             'Access-Control-Allow-Methods': 'GET, POST, PUT, DELETE, OPTIONS',
#             'Access-Control-Allow-Headers': 'Content-Type, Authorization, ngrok-skip-browser-warning',
#             'Access-Control-Allow-Credentials': 'true'
#         }
        
#         # Get limit from query parameter, default to 20
#         limit = request.args.get('limit', '20')
#         try:
#             limit_int = int(limit)
#             if limit_int < 1 or limit_int > 100:
#                 limit_int = 20  # Default to 20 if invalid
#         except ValueError:
#             limit_int = 20
        
#         # SQL query to get the latest rows from ASMReporting_5
#         # Order by CreatedOn DESC to ensure we get the most recent records first
#         sql = text(f"""
#             SELECT TOP {limit_int}
#                 WG201, WG202, WG101, WG301, WG302,
#                 WG501, WG502, WG503,
#                 DM101, DM102, DM201, DM202, DM203,
#                 PL601_TOT, PL602_TOT, PL603_TOT,
#                 CreatedOn
#             FROM [HerculesV2].[dbo].[ASMReporting_5]
#             ORDER BY CreatedOn DESC, ASMReporting_5ID DESC
#         """)
        
#         with mssql_engine.connect() as conn:
#             rows = conn.execute(sql).mappings().all()
            
#             if not rows:
#                 return jsonify({
#                     "error": "No SCADA data found",
#                     "records": [],
#                     "count": 0
#                 }), 404, response_headers
            
#             # Process all rows
#             records = []
#             for row in rows:
#                 data = dict(row)
#                 # Convert all values to floats except CreatedOn
#                 for key in data:
#                     if key != 'CreatedOn':
#                         try:
#                             data[key] = float(data[key]) if data[key] is not None else 0.0
#                         except (ValueError, TypeError):
#                             data[key] = 0.0
                
#                 record = {
#                     "timestamp": data.get("CreatedOn").isoformat() if data.get("CreatedOn") else None,
#                     "rawSignals": {
#                         "WG201": data.get("WG201", 0.0),
#                         "WG202": data.get("WG202", 0.0),
#                         "WG101": data.get("WG101", 0.0),
#                         "WG301": data.get("WG301", 0.0),
#                         "WG302": data.get("WG302", 0.0),
#                         "WG501": data.get("WG501", 0.0),
#                         "WG502": data.get("WG502", 0.0),
#                         "WG503": data.get("WG503", 0.0),
#                         "DM101": data.get("DM101", 0.0),
#                         "DM102": data.get("DM102", 0.0),
#                         "DM201": data.get("DM201", 0.0),
#                         "DM202": data.get("DM202", 0.0),
#                         "DM203": data.get("DM203", 0.0),
#                         "PL601_TOT": data.get("PL601_TOT", 0.0),
#                         "PL602_TOT": data.get("PL602_TOT", 0.0),
#                         "PL603_TOT": data.get("PL603_TOT", 0.0),
#                     }
#                 }
#                 records.append(record)
            
#             logger.info(f"Live monitoring records fetched: {len(records)} records")
#             return jsonify({
#                 "records": records,
#                 "count": len(records),
#                 "dataSource": "ASMReporting_5"
#             }), 200, response_headers
            
#     except Exception as e:
#         logger.error(f"Error fetching live monitoring records: {e}")
#         return jsonify({
#             "error": f"Error fetching SCADA data: {str(e)}",
#             "records": [],
#             "count": 0
#         }), 500, response_headers# routes/scada_routes.py
from flask import Blueprint, jsonify, request
from sqlalchemy import text
from database import engine as mssql_engine, PostgresSessionLocal
from models.process_order_pg import ProcessOrderPG
import logging

scada_bp = Blueprint("scada", __name__, url_prefix="/api")

logger = logging.getLogger(__name__)

# Helper function to get allowed CORS origin from request
def get_cors_origin():
    """Returns the request origin for CORS headers"""
    return request.headers.get('Origin', 'http://localhost:5173')

# GLOBAL OFFSET FOR ZERO RESET
SCADA_RESET_BASE = {}

# Track auto-reset events for palletizers (tag -> reset_timestamp)
# This allows order_validation to detect and update baselines accordingly
PALLETIZER_AUTO_RESET_EVENTS = {}


def _registry_scale_groups():
    """
    Active tag groups from scada_tags (B1). Falls back to the historical lists
    if the registry cannot be read.
    """
    try:
        from services.scada_tag_registry import hi_lo_tags, tags_for_category
        wg = hi_lo_tags(active_only=True)
        pl_sl = [
            t for t in tags_for_category("PACKING", active_only=True)
            if "DAMAGED" not in t
        ]
        dm = tags_for_category("WATER", active_only=True)
        if wg or pl_sl or dm:
            return wg, pl_sl, dm
    except Exception as exc:
        logger.debug("SCADA registry unavailable for scale groups: %s", exc)
    return (
        ["WG101", "WG201", "WG202", "WG301", "WG302", "WG501", "WG502", "WG503"],
        ["PL601_TOT", "PL602_TOT", "PL603_TOT", "SL606_TOT", "SL607_TOT"],
        ["DM101", "DM102", "DM201", "DM202", "DM203"],
    )


# ============================================================
# RESET API — makes system treat current SCADA values as ZERO
# ============================================================
@scada_bp.route("/scada/reset", methods=["POST"])
def reset_scada_to_zero():
    """
    Reset SCADA baseline safely – only numeric columns included.
    Supports resetting specific scales with optional custom values via 'scale_resets' parameter.
    If 'scale_resets' is provided, it expects a list of objects: { "tag": "WG...", "custom_current_value": 123.45 }
    If 'scale_tags' is provided (legacy), resets those scales to 0.
    """
    global SCADA_RESET_BASE

    try:
        # ✅ Get request data
        request_data = request.get_json() or {}
        scale_resets = request_data.get('scale_resets', [])
        scale_tags_legacy = request_data.get('scale_tags', [])
        
        # ✅ Helper function to concatenate HI and LO values as strings
        def concat_hi_lo(hi_val, lo_val):
            """Concatenate HI and LO values as strings, then convert to float"""
            try:
                hi_str = str(int(hi_val)) if hi_val is not None else "0"
                lo_str = str(int(lo_val)) if lo_val is not None else "0"
                combined_str = hi_str + lo_str
                return float(combined_str)
            except:
                return 0.0
        
        # ✅ WG / PL-SL / DM groups from scada_tags registry (B1)
        wg_scales_with_hi_lo, pl_sl_scales, dm_scales = _registry_scale_groups()
        
        # ✅ CHECK DEMO MODE - Read from emulator instead of MSSQL
        from database import get_demo_mode
        use_emulator = get_demo_mode()
        row = None
        emulator_data = None
        
        if use_emulator:
            try:
                from services.embedded_emulator import get_emulator
                emulator = get_emulator()
                emulator_data = emulator.get_latest()
                raw_scales = emulator_data.get("raw_scales", {})
                scales = emulator_data.get("scales", {})
                
                # Build a row-like dict from emulator data for compatibility
                row = {}
                # WG scales: get HI and LO values
                for tag in wg_scales_with_hi_lo:
                    hi_key = f"{tag}_HI"
                    lo_key = f"{tag}_LO"
                    row[hi_key] = raw_scales.get(hi_key, 0)
                    row[lo_key] = raw_scales.get(lo_key, 0)
                # DM scales
                for dm in dm_scales:
                    row[dm] = raw_scales.get(dm, 0)
                # PL/SL scales
                for pl in pl_sl_scales:
                    row[pl] = raw_scales.get(pl, 0)
                
                logger.info(f"[RESET] Using embedded emulator data for reset baseline")
            except Exception as e:
                logger.error(f"[RESET] Failed to get emulator data: {e}, falling back to MSSQL")
                use_emulator = False
        
        # Fallback to MSSQL if not using emulator or emulator failed
        if not use_emulator or row is None:
            sql = text("""
                SELECT TOP 1 *
                FROM [HerculesV2].[dbo].[ASMArchive_DB5]
                ORDER BY ASMArchive_DB5ID DESC
            """)

            with mssql_engine.connect() as conn:
                row = conn.execute(sql).mappings().first()
            
            if row:
                row = dict(row)  # Convert to dict for consistent access

        if not row:
            return jsonify({"success": False, "message": "No SCADA data found"}), 404

        new_base = {}
        SCALE_TAG_PREFIXES = ("WG", "DM", "PL", "SL")
        
        # ✅ Track post-reset values for updating order baselines
        # post_reset_values[tag] = the value that will be displayed AFTER reset
        post_reset_values = {}
        
        # ✅ Handle new format: scale_resets
        if scale_resets and isinstance(scale_resets, list):
            for item in scale_resets:
                tag = item.get('tag')
                custom_val = item.get('custom_current_value')
                
                if not tag or not tag.startswith(SCALE_TAG_PREFIXES):
                    continue
                
                try:
                    # ✅ WG scales: Use HI+LO concatenation
                    if tag in wg_scales_with_hi_lo:
                        hi_col = f"{tag}_HI"
                        lo_col = f"{tag}_LO"
                        if hi_col in row and lo_col in row:
                            total = concat_hi_lo(row[hi_col], row[lo_col])
                        elif hi_col in row:
                            total = float(row[hi_col] or 0)
                        else:
                            logger.warning(f"⚠️ WG scale {tag} columns not found")
                            continue
                    # ✅ PL/SL scales: Direct column access
                    elif tag in pl_sl_scales:
                        if tag in row:
                            total = float(row[tag] or 0)
                        else:
                            logger.warning(f"⚠️ PL/SL scale {tag} not found in row")
                            continue
                    # ✅ DM scales: Direct column access
                    elif tag.startswith("DM"):
                        if tag in row:
                            total = float(row[tag] or 0)
                        else:
                            logger.warning(f"⚠️ DM scale {tag} not found in row")
                            continue
                    else:
                        logger.warning(f"⚠️ Unknown scale type: {tag}")
                        continue
                    
                    if custom_val is not None:
                        # Calculate offset so that (total - offset) = custom_val
                        offset = total - float(custom_val)
                        new_base[tag] = offset
                        post_reset_values[tag] = float(custom_val)  # ✅ Store the actual post-reset value
                        logger.info(f"✅ Resetting scale {tag} to custom value: {custom_val} (Total: {total}, Offset: {offset})")
                    else:
                        # Reset to 0
                        new_base[tag] = total
                        post_reset_values[tag] = 0.0  # ✅ Post-reset value is 0
                        logger.info(f"✅ Resetting scale {tag} to 0 (Offset: {total})")
                except (ValueError, TypeError) as e:
                    logger.warning(f"⚠️ Skipping invalid value for {tag}: {e}")

        # ✅ Handle legacy format: scale_tags (simple list of tags to reset to 0)
        elif scale_tags_legacy and isinstance(scale_tags_legacy, list):
            for tag in scale_tags_legacy:
                if not tag.startswith(SCALE_TAG_PREFIXES):
                    continue
                try:
                    # ✅ WG scales: Use HI+LO concatenation
                    if tag in wg_scales_with_hi_lo:
                        hi_col = f"{tag}_HI"
                        lo_col = f"{tag}_LO"
                        if hi_col in row and lo_col in row:
                            total = concat_hi_lo(row[hi_col], row[lo_col])
                            new_base[tag] = total
                            post_reset_values[tag] = 0.0  # ✅ Legacy always resets to 0
                            logger.info(f"✅ Resetting scale {tag} to 0 (Legacy, HI+LO)")
                    # ✅ PL/SL scales: Direct column access
                    elif tag in pl_sl_scales and tag in row:
                        new_base[tag] = float(row[tag] or 0)
                        post_reset_values[tag] = 0.0  # ✅ Legacy always resets to 0
                        logger.info(f"✅ Resetting scale {tag} to 0 (Legacy)")
                    # ✅ DM scales: Direct column access
                    elif tag.startswith("DM") and tag in row:
                        new_base[tag] = float(row[tag] or 0)
                        post_reset_values[tag] = 0.0  # ✅ Legacy always resets to 0
                        logger.info(f"✅ Resetting scale {tag} to 0 (Legacy)")
                except (ValueError, TypeError):
                    pass
                        
        # ✅ If neither provided but endpoint called, reset all scales
        elif not request_data:
            # Reset WG scales with HI+LO concatenation
            for tag in wg_scales_with_hi_lo:
                hi_col = f"{tag}_HI"
                lo_col = f"{tag}_LO"
                if hi_col in row and lo_col in row:
                    try:
                        new_base[tag] = concat_hi_lo(row[hi_col], row[lo_col])
                        post_reset_values[tag] = 0.0  # ✅ Reset all always resets to 0
                    except:
                        pass
            # Reset DM columns directly
            for k, v in row.items():
                if k.startswith("DM"):
                    try:
                        new_base[k] = float(v or 0)
                        post_reset_values[k] = 0.0  # ✅ Reset all always resets to 0
                    except:
                        pass
            # Reset PL/SL scales
            for tag in pl_sl_scales:
                if tag in row:
                    try:
                        new_base[tag] = float(row[tag] or 0)
                        post_reset_values[tag] = 0.0  # ✅ Reset all always resets to 0
                    except:
                        pass

        # ✅ Update global offset map
        for tag, value in new_base.items():
            SCADA_RESET_BASE[tag] = value
        
        logger.info(f"🔥 SCADA_RESET_BASE updated: {len(new_base)} scales modified")

        # ✅ CRITICAL: Also update order baselines in PostgreSQL for active orders
        # This ensures delta calculation is correct after reset
        orders_updated = 0
        try:
            pg_session = PostgresSessionLocal()
            
            # Import classification function to determine which equipment each order uses
            from routes.order_validation import classify_order
            
            # Find active orders (InProgress, Validated) that use the reset scales
            active_orders = pg_session.query(ProcessOrderPG).filter(
                ProcessOrderPG.status.in_(['InProgress', 'Validated'])
            ).all()
            
            for order in active_orders:
                order_updated = False
                
                # ✅ Get the equipment this order uses via classification
                try:
                    classification = classify_order(order)
                    order_equipment = [eq.upper() for eq in classification.get("equipment", [])]
                except Exception as class_err:
                    logger.warning(f"⚠️ Could not classify order {order.order_id}: {class_err}")
                    order_equipment = []
                
                # Also get scale1/scale2/scale3 for PL/SL scales (PACKING)
                scale1 = str(getattr(order, 'scale1', '') or '').upper()
                scale2 = str(getattr(order, 'scale2', '') or '').upper()
                scale3 = str(getattr(order, 'scale3', '') or '').upper()
                
                for tag in new_base.keys():
                    tag_upper = tag.upper()
                    tag_lower = tag.lower()
                    baseline_attr = f"baseline_{tag_lower}"
                    
                    # ✅ Get the actual post-reset value (e.g., 10 if user entered custom value 10)
                    post_reset_val = post_reset_values.get(tag, 0.0)
                    
                    # ✅ For PL/SL scales: Update scale1_qty/scale2_qty/scale3_qty
                    if tag_upper.startswith("PL") or tag_upper.startswith("SL"):
                        if tag_upper == scale1:
                            setattr(order, 'scale1_qty', post_reset_val)
                            order_updated = True
                            logger.info(f"✅ Set scale1_qty={post_reset_val} for order {order.order_id} (scale: {tag})")
                        elif tag_upper == scale2:
                            setattr(order, 'scale2_qty', post_reset_val)
                            order_updated = True
                            logger.info(f"✅ Set scale2_qty={post_reset_val} for order {order.order_id} (scale: {tag})")
                        elif tag_upper == scale3:
                            setattr(order, 'scale3_qty', post_reset_val)
                            order_updated = True
                            logger.info(f"✅ Set scale3_qty={post_reset_val} for order {order.order_id} (scale: {tag})")
                    
                    # ✅ For WG/DM scales: Update baseline_{tag} if order uses this equipment
                    elif tag_upper in order_equipment:
                        if hasattr(order, baseline_attr):
                            setattr(order, baseline_attr, post_reset_val)
                            order_updated = True
                            logger.info(f"✅ Set {baseline_attr}={post_reset_val} for order {order.order_id} (equipment match)")
                
                if order_updated:
                    orders_updated += 1
            
            pg_session.commit()
            logger.info(f"✅ Updated baselines for {orders_updated} active orders")
            
        except Exception as db_error:
            logger.error(f"⚠️ Error updating order baselines: {db_error}")
            if pg_session:
                pg_session.rollback()
        finally:
            if pg_session:
                pg_session.close()

        return jsonify({
            "success": True,
            "message": f"SCADA Reset Successful for {len(new_base)} scale(s), {orders_updated} orders updated",
            "reset_scales": list(new_base.keys()),
            "baseline_keys": list(SCADA_RESET_BASE.keys()),
            "orders_updated": orders_updated
        }), 200

    except Exception as e:
        logger.error(f"Error in reset_scada_to_zero: {e}")
        return jsonify({"success": False, "message": str(e)}), 500


@scada_bp.route("/scada/scales/status", methods=["GET"])
def get_scales_status():
    """
    Get detailed status of available scales: Tag, Total (Raw), Current (Calculated), Reset Base.
    Used for the reset modal.
    """
    try:
        # ✅ Check demo mode first - use embedded emulator if enabled
        from database import get_demo_mode
        if get_demo_mode():
            from services.embedded_emulator import get_emulator
            emulator = get_emulator()
            emulator_status = emulator.get_scales_status()
            
            # Build scales status from emulator data
            scales_status = []
            combined = emulator_status.get("combined", {})
            
            for tag, total in combined.items():
                reset_base = SCADA_RESET_BASE.get(tag, 0.0)
                current = max(0.0, float(total) - reset_base)
                scales_status.append({
                    "tag": tag,
                    "total": float(total),
                    "current": current,
                    "reset_base": reset_base,
                    "custom_offset": 0.0
                })
            
            # Sort by tag
            scales_status.sort(key=lambda x: x["tag"])
            
            return jsonify({
                "success": True,
                "scales": scales_status,
                "count": len(scales_status),
                "source": "embedded_emulator"
            }), 200
        
        # ✅ Production mode - use MSSQL
        sql = text("""
            SELECT TOP 1 *
            FROM [HerculesV2].[dbo].[ASMArchive_DB5]
            ORDER BY ASMArchive_DB5ID DESC
        """)

        with mssql_engine.connect() as conn:
            row = conn.execute(sql).mappings().first()

        if not row:
            return jsonify({"success": False, "message": "No SCADA data found", "scales": []}), 404

        SCALE_TAG_PREFIXES = ("WG", "DM", "PL", "SL")
        
        # ✅ Helper function to concatenate HI and LO values as strings
        # Zero-pad LO to 6 digits to ensure consistent concatenation
        def concat_hi_lo(hi_val, lo_val):
            """Concatenate HI and LO values as strings, then convert to float"""
            try:
                hi_str = str(int(hi_val)) if hi_val is not None else "0"
                lo_str = str(int(lo_val)).zfill(6) if lo_val is not None else "000000"
                combined_str = hi_str + lo_str
                return float(combined_str)
            except:
                return 0.0
        
        # ✅ WG / PL-SL groups from scada_tags registry (B1)
        wg_scales_with_hi_lo, pl_sl_scales, _dm_scales = _registry_scale_groups()
        
        scales_status = []
        
        # ✅ Process WG columns with HI+LO concatenation
        for tag in wg_scales_with_hi_lo:
            hi_col = f"{tag}_HI"
            lo_col = f"{tag}_LO"
            if hi_col in row and lo_col in row:
                try:
                    total = concat_hi_lo(row[hi_col], row[lo_col])
                    reset_base = SCADA_RESET_BASE.get(tag, 0.0)
                    current = max(0.0, total - reset_base)
                    
                    scales_status.append({
                        "tag": tag,
                        "total": total,
                        "current": current,
                        "reset_base": reset_base,
                        "custom_offset": 0.0
                    })
                except (ValueError, TypeError):
                    pass
        
        # ✅ Process DM columns (direct values)
        for k, v in row.items():
            if k.startswith("DM"):
                try:
                    total = float(v or 0)
                    reset_base = SCADA_RESET_BASE.get(k, 0.0)
                    current = max(0.0, total - reset_base)
                    
                    scales_status.append({
                        "tag": k,
                        "total": total,
                        "current": current,
                        "reset_base": reset_base,
                        "custom_offset": 0.0
                    })
                except (ValueError, TypeError):
                    pass
        
        # ✅ Process PL and SL columns (direct values)
        for tag in pl_sl_scales:
            if tag in row:
                try:
                    total = float(row[tag] or 0)
                    reset_base = SCADA_RESET_BASE.get(tag, 0.0)
                    current = max(0.0, total - reset_base)
                    
                    scales_status.append({
                        "tag": tag,
                        "total": total,
                        "current": current,
                        "reset_base": reset_base,
                        "custom_offset": 0.0
                    })
                except (ValueError, TypeError):
                    pass

        # Sort by tag
        scales_status.sort(key=lambda x: x["tag"])

        return jsonify({
            "success": True,
            "scales": scales_status,
            "count": len(scales_status)
        }), 200

    except Exception as e:
        logger.error(f"Error getting scales status: {e}")
        return jsonify({"success": False, "message": str(e), "scales": []}), 500



# ============================================================
# CORS HANDLER
# ============================================================
@scada_bp.route("/scada/readings", methods=["OPTIONS"])
def handle_scada_options():
    headers = {
        'Access-Control-Allow-Origin': get_cors_origin(),
        'Access-Control-Allow-Methods': 'GET, POST, PUT, DELETE, OPTIONS',
        'Access-Control-Allow-Headers': 'Content-Type, Authorization, ngrok-skip-browser-warning',
        'Access-Control-Allow-Credentials': 'true'
    }
    return '', 200, headers


# ============================================================
# MAIN SCADA READINGS API (NOW ZERO-BASED AFTER RESET)
# ============================================================
@scada_bp.route("/scada/readings", methods=["GET"])
def get_scada_readings():
    try:
        response_headers = {
            'Access-Control-Allow-Origin': get_cors_origin(),
            'Access-Control-Allow-Methods': 'GET, POST, PUT, DELETE, OPTIONS',
            'Access-Control-Allow-Headers': 'Content-Type, Authorization, ngrok-skip-browser-warning',
            'Access-Control-Allow-Credentials': 'true'
        }

        # ✅ CHECK DEMO MODE - Use embedded emulator
        from database import get_demo_mode
        
        if get_demo_mode():
            try:
                from services.embedded_emulator import get_emulator
                emulator = get_emulator()
                emulator_data = emulator.get_latest()
                scales = emulator_data.get("scales", {})
                
                # Helper to get combined HI+LO or direct value
                def get_scale_value(tag):
                    v = scales.get(tag)
                    if v is not None:
                        return float(v)
                    # Try HI/LO combination
                    hi_val = scales.get(f"{tag}_HI")
                    lo_val = scales.get(f"{tag}_LO")
                    if hi_val is not None and lo_val is not None:
                        try:
                            return float(str(int(hi_val)) + str(int(lo_val)))
                        except:
                            pass
                    return 0.0
                
                # Build response from emulator data
                scada_readings = {
                    "cleaningScale": get_scale_value("WG201"),
                    "totalRunningTime": get_scale_value("WG202"),
                    "dryWheatScale": get_scale_value("WG101"),
                    "totalScreening": get_scale_value("WG301"),
                    "totalFlour": get_scale_value("WG302"),
                    "flour": get_scale_value("WG501") + get_scale_value("WG502"),
                    "totalBran": get_scale_value("WG503"),
                    "totalWheat": get_scale_value("WG501") + get_scale_value("WG502") + get_scale_value("WG503"),
                    "totalPreCleaningWater": float(scales.get("DM101", 0)) + float(scales.get("DM102", 0)),
                    "waterCleanWheat": float(scales.get("DM201", 0)) + float(scales.get("DM202", 0)) + float(scales.get("DM203", 0)),
                    "totalWaterUsed": float(scales.get("DM101", 0)) + float(scales.get("DM102", 0)) + float(scales.get("DM201", 0)) + float(scales.get("DM202", 0)) + float(scales.get("DM203", 0)),
                    "actualPackingOutput": float(scales.get("PL601_TOT", 0)),
                    "packingStdCapacity": float(scales.get("PL602_TOT", 0)),
                    "packingGoodOutput": float(scales.get("PL603_TOT", 0)),
                    "packingTotalOutput": float(scales.get("PL601_TOT", 0)),
                    "packingPlannedOutput": float(scales.get("PL602_TOT", 0)),
                    "packingNetHours": 0.0,
                    "packingTotalHours": 0.0,
                    "rawSignals": scales,
                    "lastUpdated": emulator_data.get("timestamp"),
                    "dataSource": "SCADA_EMULATOR"
                }
                logger.info(f"✅ [EMULATOR] SCADA readings from emulator: WG201={scada_readings['cleaningScale']}")
                return jsonify(scada_readings), 200, response_headers
            except Exception as e:
                logger.error(f"[EMULATOR] Error fetching from emulator: {e}, falling back to MSSQL")

        # Fetch from MSSQL database (production mode or emulator fallback)
        sql = text("""
            SELECT TOP 1 
                WG101_LO, WG101_HI, WG101_Product, WG101_Destination,
                WG201_LO, WG201_HI, WG201_Product, WG201_Destination,
                WG202_LO, WG202_HI, WG202_Product,
                WG301_LO, WG301_HI,
                WG302_LO, WG302_HI,
                WG501_LO, WG501_HI, WG501_Product, WG501_Destination,
                WG502_LO, WG502_HI, WG502_Product, WG502_Destination,
                WG503_LO, WG503_HI, WG503_Product,
                DM101, DM102, DM201, DM202, DM203,
                PL601_TOT, PL602_TOT, PL603_TOT,
                SL607_TOT, SL606_TOT,
                CreatedOn
            FROM [HerculesV2].[dbo].[ASMArchive_DB5]
            ORDER BY ASMArchive_DB5ID DESC
        """)

        with mssql_engine.connect() as conn:
            row = conn.execute(sql).mappings().first()

        if not row:
            return jsonify({"error": "No SCADA data found", "timestamp": None}), 404, response_headers

        # Convert row to dictionary and cast floats
        data = dict(row)
        for key in data:
            if key != 'CreatedOn':
                try:
                    data[key] = float(data[key]) if data[key] is not None else 0.0
                except:
                    data[key] = 0.0

        # =======================================================
        # APPLY ZERO RESET OFFSET
        # =======================================================
        global SCADA_RESET_BASE
        
        # ✅ Helper function to concatenate HI and LO values as strings
        def concat_hi_lo(hi_val, lo_val):
            """Concatenate HI and LO values as strings, then convert to float"""
            try:
                hi_str = str(int(hi_val)) if hi_val is not None else "0"
                lo_str = str(int(lo_val)) if lo_val is not None else "0"
                combined_str = hi_str + lo_str
                return float(combined_str)
            except:
                return 0.0
        
        # ✅ WG / PL-SL groups from scada_tags registry (B1)
        wg_scales_with_hi_lo, pl_sl_scales, _dm_scales = _registry_scale_groups()
        
        # ✅ Calculate adjusted WG values (concatenated HI+LO minus offset)
        adjusted_wg_values = {}
        for tag in wg_scales_with_hi_lo:
            hi_col = f"{tag}_HI"
            lo_col = f"{tag}_LO"
            if hi_col in data and lo_col in data:
                concatenated = concat_hi_lo(data[hi_col], data[lo_col])
                offset = SCADA_RESET_BASE.get(tag, 0.0)
                adjusted = max(0.0, concatenated - offset)
                adjusted_wg_values[tag] = adjusted
        
        # ✅ Apply reset offset to DM columns (direct values)
        if SCADA_RESET_BASE:
            for tag, offset in SCADA_RESET_BASE.items():
                if tag.startswith("DM") and tag in data:
                    try:
                        data[tag] = max(0.0, data[tag] - offset)
                    except:
                        pass
                # ✅ Apply reset offset to PL/SL columns
                elif tag in pl_sl_scales and tag in data:
                    try:
                        data[tag] = max(0.0, data[tag] - offset)
                    except:
                        pass

        logger.info(f"Adjusted SCADA row after reset: WG adjusted={adjusted_wg_values}")

        # =======================================================
        # BUILD FINAL SCADA PAYLOAD
        # ✅ Map new columns to old field names for backward compatibility
        # =======================================================
        scada_readings = {
            # ✅ Use adjusted concatenated HI+LO values (with reset offset applied)
            "cleaningScale": adjusted_wg_values.get("WG201", 0.0),
            "totalRunningTime": adjusted_wg_values.get("WG202", 0.0),
            "dryWheatScale": adjusted_wg_values.get("WG101", 0.0),
            "totalScreening": adjusted_wg_values.get("WG301", 0.0),
            "totalFlour": adjusted_wg_values.get("WG302", 0.0),

            # Calculated values - using adjusted concatenated values
            "flour": adjusted_wg_values.get("WG501", 0.0) + adjusted_wg_values.get("WG502", 0.0),
            "totalBran": adjusted_wg_values.get("WG503", 0.0),
            "totalWheat": (
                adjusted_wg_values.get("WG501", 0.0)
                + adjusted_wg_values.get("WG502", 0.0)
                + adjusted_wg_values.get("WG503", 0.0)
            ),

            # Water usage - DM columns remain the same
            "totalPreCleaningWater": data.get("DM101", 0.0) + data.get("DM102", 0.0),
            "waterCleanWheat": data.get("DM201", 0.0) + data.get("DM202", 0.0) + data.get("DM203", 0.0),
            "totalWaterUsed": (
                data.get("DM101", 0.0)
                + data.get("DM102", 0.0)
                + data.get("DM201", 0.0)
                + data.get("DM202", 0.0)
                + data.get("DM203", 0.0)
            ),

            # Packing values - remain the same
            "actualPackingOutput": data.get("PL601_TOT", 0.0),
            "packingStdCapacity": data.get("PL602_TOT", 0.0),
            "packingGoodOutput": data.get("PL603_TOT", 0.0),
            "packingTotalOutput": data.get("PL601_TOT", 0.0),
            "packingPlannedOutput": data.get("PL602_TOT", 0.0),

            "packingNetHours": 0.0,
            "packingTotalHours": 0.0,

            # Debug: raw signals - include all new columns
            "rawSignals": data,

            "lastUpdated": data.get("CreatedOn").isoformat() if data.get("CreatedOn") else None,
            "dataSource": "ASMArchive_DB5"
        }

        return jsonify(scada_readings), 200, response_headers

    except Exception as e:
        logger.error(f"Error fetching SCADA readings: {e}")
        return jsonify({"error": f"Error fetching SCADA data: {str(e)}", "timestamp": None}), 500, response_headers


# ============================================================
# LIVE MONITORING API (unchanged)
# ============================================================
@scada_bp.route("/scada/live-monitoring", methods=["OPTIONS"])
def handle_live_monitoring_options():
    headers = {
        'Access-Control-Allow-Origin': get_cors_origin(),
        'Access-Control-Allow-Methods': 'GET, POST, PUT, DELETE, OPTIONS',
        'Access-Control-Allow-Headers': 'Content-Type, Authorization, ngrok-skip-browser-warning',
        'Access-Control-Allow-Credentials': 'true'
    }
    return '', 200, headers


@scada_bp.route("/scada/live-monitoring", methods=["GET"])
def get_live_monitoring_records():
    try:
        response_headers = {
            'Access-Control-Allow-Origin': get_cors_origin(),
            'Access-Control-Allow-Methods': 'GET, POST, PUT, DELETE, OPTIONS',
            'Access-Control-Allow-Headers': 'Content-Type, Authorization, ngrok-skip-browser-warning',
            'Access-Control-Allow-Credentials': 'true'
        }

        limit = request.args.get('limit', '20')
        try:
            limit_int = int(limit)
            if limit_int < 1 or limit_int > 100:
                limit_int = 20
        except:
            limit_int = 20

        # ✅ CHECK DEMO MODE FIRST - Use embedded emulator
        from database import get_demo_mode
        from datetime import datetime
        
        if get_demo_mode():
            try:
                from services.embedded_emulator import get_emulator
                emulator = get_emulator()
                emulator_data = emulator.get_latest()
                raw_scales = emulator_data.get("raw_scales", {})
                scales = emulator_data.get("scales", {})
                
                # Helper to get combined HI+LO or direct value
                def get_scale_value(tag):
                    # Try direct key first from scales dict
                    v = scales.get(tag)
                    if v is not None:
                        return float(v)
                    # Try HI/LO combination from raw_scales
                    hi_val = raw_scales.get(f"{tag}_HI")
                    lo_val = raw_scales.get(f"{tag}_LO")
                    if hi_val is not None and lo_val is not None:
                        try:
                            return float(str(int(hi_val)) + str(int(lo_val)))
                        except:
                            pass
                    return 0.0
                
                # Build single record from emulator (live data)
                rawSignals = {
                    # Main WG columns (concatenated HI+LO values)
                    'WG101': get_scale_value("WG101"),
                    'WG201': get_scale_value("WG201"),
                    'WG202': get_scale_value("WG202"),
                    'WG301': get_scale_value("WG301"),
                    'WG302': get_scale_value("WG302"),
                    'WG501': get_scale_value("WG501"),
                    'WG502': get_scale_value("WG502"),
                    'WG503': get_scale_value("WG503"),
                    # DM columns (single values)
                    'DM101': float(raw_scales.get("DM101", 0) or 0),
                    'DM102': float(raw_scales.get("DM102", 0) or 0),
                    'DM201': float(raw_scales.get("DM201", 0) or 0),
                    'DM202': float(raw_scales.get("DM202", 0) or 0),
                    'DM203': float(raw_scales.get("DM203", 0) or 0),
                    # PL and SL columns
                    'PL601_TOT': float(raw_scales.get("PL601_TOT", 0) or 0),
                    'PL602_TOT': float(raw_scales.get("PL602_TOT", 0) or 0),
                    'PL603_TOT': float(raw_scales.get("PL603_TOT", 0) or 0),
                    'SL606_TOT': float(raw_scales.get("SL606_TOT", 0) or 0),
                    'SL607_TOT': float(raw_scales.get("SL607_TOT", 0) or 0),
                    # HI/LO columns (separate values for display)
                    'WG101_LO': float(raw_scales.get('WG101_LO', 0) or 0),
                    'WG101_HI': float(raw_scales.get('WG101_HI', 0) or 0),
                    'WG201_LO': float(raw_scales.get('WG201_LO', 0) or 0),
                    'WG201_HI': float(raw_scales.get('WG201_HI', 0) or 0),
                    'WG202_LO': float(raw_scales.get('WG202_LO', 0) or 0),
                    'WG202_HI': float(raw_scales.get('WG202_HI', 0) or 0),
                    'WG301_LO': float(raw_scales.get('WG301_LO', 0) or 0),
                    'WG301_HI': float(raw_scales.get('WG301_HI', 0) or 0),
                    'WG302_LO': float(raw_scales.get('WG302_LO', 0) or 0),
                    'WG302_HI': float(raw_scales.get('WG302_HI', 0) or 0),
                    'WG501_LO': float(raw_scales.get('WG501_LO', 0) or 0),
                    'WG501_HI': float(raw_scales.get('WG501_HI', 0) or 0),
                    'WG502_LO': float(raw_scales.get('WG502_LO', 0) or 0),
                    'WG502_HI': float(raw_scales.get('WG502_HI', 0) or 0),
                    'WG503_LO': float(raw_scales.get('WG503_LO', 0) or 0),
                    'WG503_HI': float(raw_scales.get('WG503_HI', 0) or 0),
                }
                
                # ✅ APPLY SCADA_RESET_BASE OFFSETS - Subtract baseline from raw values
                # This makes the reset functionality work properly in demo mode
                scales_to_adjust = [
                    'WG101', 'WG201', 'WG202', 'WG301', 'WG302', 'WG501', 'WG502', 'WG503',
                    'DM101', 'DM102', 'DM201', 'DM202', 'DM203',
                    'PL601_TOT', 'PL602_TOT', 'PL603_TOT', 'SL606_TOT', 'SL607_TOT'
                ]
                
                for tag in scales_to_adjust:
                    if tag in rawSignals and tag in SCADA_RESET_BASE:
                        offset = SCADA_RESET_BASE[tag]
                        raw_val = rawSignals[tag]
                        rawSignals[tag] = max(0.0, raw_val - offset)
                        logger.debug(f"[LIVE] Applied offset to {tag}: {raw_val} - {offset} = {rawSignals[tag]}")
                
                records = [{
                    "timestamp": emulator_data.get("timestamp") or datetime.now().isoformat(),
                    "rawSignals": rawSignals
                }]
                
                logger.info(f"[EMULATOR] Live monitoring from embedded emulator: {len(records)} record(s), offsets applied: {len(SCADA_RESET_BASE)}")
                return jsonify({"records": records, "count": len(records), "dataSource": "embedded_emulator"}), 200, response_headers
            except Exception as e:
                logger.error(f"[EMULATOR] Error fetching from embedded emulator: {e}, falling back to MSSQL")

        # Fetch from MSSQL database (production mode or emulator fallback)
        sql = text(f"""
            SELECT TOP {limit_int}
                WG101_LO, WG101_HI, WG101_Product, WG101_Destination,
                WG201_LO, WG201_HI, WG201_Product, WG201_Destination,
                WG202_LO, WG202_HI, WG202_Product,
                WG301_LO, WG301_HI,
                WG302_LO, WG302_HI,
                WG501_LO, WG501_HI, WG501_Product, WG501_Destination,
                WG502_LO, WG502_HI, WG502_Product, WG502_Destination,
                WG503_LO, WG503_HI, WG503_Product,
                DM101, DM102, DM201, DM202, DM203,
                PL601_TOT, PL602_TOT, PL603_TOT,
                SL607_TOT, SL606_TOT,
                CreatedOn
            FROM [HerculesV2].[dbo].[ASMArchive_DB5]
            ORDER BY CreatedOn DESC, ASMArchive_DB5ID DESC
        """)

        with mssql_engine.connect() as conn:
            rows = conn.execute(sql).mappings().all()

        if not rows:
            return jsonify({"error": "No SCADA data found", "records": [], "count": 0}), 404, response_headers

        records = []
        for row in rows:
            data = dict(row)
            # Exclude non-numeric columns from float conversion
            exclude_keys = ['CreatedOn', 'WG101_Product', 'WG101_Destination', 'WG201_Product', 'WG201_Destination', 
                           'WG202_Product', 'WG501_Product', 'WG501_Destination', 'WG502_Product', 
                           'WG502_Destination', 'WG503_Product']
            for key in data:
                if key not in exclude_keys:
                    try:
                        data[key] = float(data[key]) if data[key] is not None else 0.0
                    except:
                        data[key] = 0.0

            # ✅ Calculate concatenated WG values (HI + LO as string concatenation)
            # Helper function to concatenate HI and LO
            def concat_hi_lo(hi_val, lo_val):
                """Concatenate HI and LO values as strings, then convert to float"""
                try:
                    hi_str = str(int(hi_val)) if hi_val is not None else "0"
                    lo_str = str(int(lo_val)) if lo_val is not None else "0"
                    combined_str = hi_str + lo_str
                    return float(combined_str)
                except:
                    return 0.0
            
            # ✅ Map new column names with concatenated WG values
            # Also include HI/LO columns for display
            rawSignals = {
                # Main WG columns (concatenated HI+LO values)
                'WG101': concat_hi_lo(data.get('WG101_HI', 0.0), data.get('WG101_LO', 0.0)),
                'WG201': concat_hi_lo(data.get('WG201_HI', 0.0), data.get('WG201_LO', 0.0)),
                'WG202': concat_hi_lo(data.get('WG202_HI', 0.0), data.get('WG202_LO', 0.0)),
                'WG301': concat_hi_lo(data.get('WG301_HI', 0.0), data.get('WG301_LO', 0.0)),
                'WG302': concat_hi_lo(data.get('WG302_HI', 0.0), data.get('WG302_LO', 0.0)),
                'WG501': concat_hi_lo(data.get('WG501_HI', 0.0), data.get('WG501_LO', 0.0)),
                'WG502': concat_hi_lo(data.get('WG502_HI', 0.0), data.get('WG502_LO', 0.0)),
                'WG503': concat_hi_lo(data.get('WG503_HI', 0.0), data.get('WG503_LO', 0.0)),
                # DM and PL columns (single values)
                'DM101': data.get('DM101', 0.0),
                'DM102': data.get('DM102', 0.0),
                'DM201': data.get('DM201', 0.0),
                'DM202': data.get('DM202', 0.0),
                'DM203': data.get('DM203', 0.0),
                'PL601_TOT': data.get('PL601_TOT', 0.0),
                'PL602_TOT': data.get('PL602_TOT', 0.0),
                'PL603_TOT': data.get('PL603_TOT', 0.0),
                'SL606_TOT': data.get('SL606_TOT', 0.0),
                'SL607_TOT': data.get('SL607_TOT', 0.0),
                # HI/LO columns (separate values for display)
                'WG101_LO': data.get('WG101_LO', 0.0),
                'WG101_HI': data.get('WG101_HI', 0.0),
                'WG201_LO': data.get('WG201_LO', 0.0),
                'WG201_HI': data.get('WG201_HI', 0.0),
                'WG202_LO': data.get('WG202_LO', 0.0),
                'WG202_HI': data.get('WG202_HI', 0.0),
                'WG301_LO': data.get('WG301_LO', 0.0),
                'WG301_HI': data.get('WG301_HI', 0.0),
                'WG302_LO': data.get('WG302_LO', 0.0),
                'WG302_HI': data.get('WG302_HI', 0.0),
                'WG501_LO': data.get('WG501_LO', 0.0),
                'WG501_HI': data.get('WG501_HI', 0.0),
                'WG502_LO': data.get('WG502_LO', 0.0),
                'WG502_HI': data.get('WG502_HI', 0.0),
                'WG503_LO': data.get('WG503_LO', 0.0),
                'WG503_HI': data.get('WG503_HI', 0.0),
            }

            records.append({
                "timestamp": data.get("CreatedOn").isoformat() if data.get("CreatedOn") else None,
                "rawSignals": rawSignals
            })
        
        # ✅ Records are already ordered by CreatedOn DESC from SQL, so most recent is first
        # No need to reverse - SQL ORDER BY CreatedOn DESC, ASMArchive_DB5ID DESC ensures correct order

        return jsonify({"records": records, "count": len(records), "dataSource": "ASMArchive_DB5"}), 200, response_headers

    except Exception as e:
        logger.error(f"Error fetching live monitoring records: {e}")
        return jsonify({"error": f"Error fetching SCADA data: {str(e)}", "records": [], "count": 0}), 500, response_headers


# ============================================================
# SCADA HISTORY API - Real historical data for dashboard charts
# ============================================================
@scada_bp.route("/scada/history", methods=["GET"])
def get_scada_history():
    """
    Fetch historical SCADA data aggregated by hour for dashboard charts.
    Returns real data from ASMArchive_DB5 for the last 24 hours.
    In demo mode, returns data from PostgreSQL scada_aggregate_values table.
    """
    try:
        response_headers = {
            'Access-Control-Allow-Origin': get_cors_origin(),
            'Access-Control-Allow-Methods': 'GET, OPTIONS',
            'Access-Control-Allow-Headers': 'Content-Type, Authorization, ngrok-skip-browser-warning',
            'Access-Control-Allow-Credentials': 'true'
        }

        # ✅ CHECK DEMO MODE FIRST - Return data from PostgreSQL
        from database import get_demo_mode, postgres_engine
        from datetime import datetime, timedelta
        
        if get_demo_mode() and postgres_engine is not None:
            try:
                # Query PostgreSQL for historical data
                pg_sql = text("""
                    SELECT 
                        EXTRACT(HOUR FROM created_at) as hour,
                        AVG(VALUE_WG201) as avg_cleaning_scale,
                        AVG(VALUE_WG101) as avg_dry_wheat,
                        AVG(VALUE_WG301) as avg_screening,
                        AVG(VALUE_WG302) as avg_flour,
                        AVG(VALUE_WG501) as avg_wg501,
                        AVG(VALUE_WG502) as avg_wg502,
                        AVG(VALUE_WG503) as avg_bran,
                        SUM(VALUE_DM101) as total_dm101,
                        SUM(VALUE_DM102) as total_dm102,
                        SUM(VALUE_DM201) as total_dm201,
                        SUM(VALUE_DM202) as total_dm202,
                        SUM(VALUE_DM203) as total_dm203,
                        MAX(VALUE_PL601_TOT) as max_pl601,
                        COUNT(*) as reading_count
                    FROM scada_aggregate_values
                    WHERE created_at >= NOW() - INTERVAL '24 hours'
                    GROUP BY EXTRACT(HOUR FROM created_at)
                    ORDER BY hour
                """)
                
                with postgres_engine.connect() as pg_conn:
                    rows = pg_conn.execute(pg_sql).mappings().all()
                
                hourly_data = []
                for row in rows:
                    hour = int(row['hour']) if row['hour'] is not None else 0
                    water_pre_cleaning = (float(row['total_dm101'] or 0) + float(row['total_dm102'] or 0))
                    water_clean_wheat = (float(row['total_dm201'] or 0) + float(row['total_dm202'] or 0) + float(row['total_dm203'] or 0))
                    total_water = water_pre_cleaning + water_clean_wheat
                    flour_total = float(row['avg_wg501'] or 0) + float(row['avg_wg502'] or 0)
                    bran_total = float(row['avg_bran'] or 0)
                    
                    hourly_data.append({
                        "hour": f"{hour:02d}:00",
                        "hour_num": hour,
                        "cleaning_scale": round(float(row['avg_cleaning_scale'] or 0), 2),
                        "dry_wheat": round(float(row['avg_dry_wheat'] or 0), 2),
                        "screening": round(float(row['avg_screening'] or 0), 2),
                        "flour": round(flour_total, 2),
                        "bran": round(bran_total, 2),
                        "water_pre_cleaning": round(water_pre_cleaning, 2),
                        "water_clean_wheat": round(water_clean_wheat, 2),
                        "total_water": round(total_water, 2),
                        "packing_output": 0.0,  # Not available in PostgreSQL table
                        "reading_count": int(row['reading_count'] or 0)
                    })
                
                logger.info(f"✅ [EMULATOR] SCADA history from PostgreSQL: {len(hourly_data)} hours")
                return jsonify({
                    "hourly_data": hourly_data,
                    "count": len(hourly_data),
                    "dataSource": "PostgreSQL_emulator"
                }), 200, response_headers
            except Exception as pg_e:
                logger.warning(f"[EMULATOR] PostgreSQL history query failed: {pg_e}, falling back to MSSQL")

        # Get hourly aggregated data for the last 24 hours
        sql = text("""
            SELECT 
                DATEPART(HOUR, CreatedOn) as hour,
                AVG(CAST(WG201_HI AS FLOAT)) as avg_cleaning_scale,
                AVG(CAST(WG101_HI AS FLOAT)) as avg_dry_wheat,
                AVG(CAST(WG301_HI AS FLOAT)) as avg_screening,
                AVG(CAST(WG302_HI AS FLOAT)) as avg_flour,
                AVG(CAST(WG501_HI AS FLOAT)) as avg_wg501,
                AVG(CAST(WG502_HI AS FLOAT)) as avg_wg502,
                AVG(CAST(WG503_HI AS FLOAT)) as avg_bran,
                SUM(CAST(DM101 AS FLOAT)) as total_dm101,
                SUM(CAST(DM102 AS FLOAT)) as total_dm102,
                SUM(CAST(DM201 AS FLOAT)) as total_dm201,
                SUM(CAST(DM202 AS FLOAT)) as total_dm202,
                SUM(CAST(DM203 AS FLOAT)) as total_dm203,
                MAX(CAST(PL601_TOT AS FLOAT)) as max_pl601,
                MAX(CAST(PL602_TOT AS FLOAT)) as max_pl602,
                MAX(CAST(PL603_TOT AS FLOAT)) as max_pl603,
                COUNT(*) as reading_count
            FROM [HerculesV2].[dbo].[ASMArchive_DB5]
            WHERE CreatedOn >= DATEADD(HOUR, -24, GETDATE())
            GROUP BY DATEPART(HOUR, CreatedOn)
            ORDER BY hour
        """)

        with mssql_engine.connect() as conn:
            rows = conn.execute(sql).mappings().all()

        # Build hourly data for charts
        hourly_data = []
        for row in rows:
            hour = int(row['hour']) if row['hour'] is not None else 0
            
            # Calculate water consumption for this hour
            water_pre_cleaning = (float(row['total_dm101'] or 0) + float(row['total_dm102'] or 0))
            water_clean_wheat = (float(row['total_dm201'] or 0) + float(row['total_dm202'] or 0) + float(row['total_dm203'] or 0))
            total_water = water_pre_cleaning + water_clean_wheat
            
            # Calculate flour production
            flour_total = float(row['avg_wg501'] or 0) + float(row['avg_wg502'] or 0)
            bran_total = float(row['avg_bran'] or 0)
            
            hourly_data.append({
                "hour": f"{hour:02d}:00",
                "hour_num": hour,
                "cleaning_scale": round(float(row['avg_cleaning_scale'] or 0), 2),
                "dry_wheat": round(float(row['avg_dry_wheat'] or 0), 2),
                "screening": round(float(row['avg_screening'] or 0), 2),
                "flour": round(flour_total, 2),
                "bran": round(bran_total, 2),
                "water_pre_cleaning": round(water_pre_cleaning, 2),
                "water_clean_wheat": round(water_clean_wheat, 2),
                "total_water": round(total_water, 2),
                "packing_output": round(float(row['max_pl601'] or 0), 2),
                "reading_count": int(row['reading_count'] or 0)
            })

        # Get latest values for current stats
        latest_sql = text("""
            SELECT TOP 1
                WG201_HI, WG101_HI, WG301_HI, WG302_HI,
                WG501_HI, WG502_HI, WG503_HI,
                DM101, DM102, DM201, DM202, DM203,
                PL601_TOT, PL602_TOT, PL603_TOT,
                SL601_COUNTER, SL602_COUNTER, SL603_COUNTER,
                SL606_COUNTER, SL607_COUNTER,
                CreatedOn
            FROM [HerculesV2].[dbo].[ASMArchive_DB5]
            ORDER BY ASMArchive_DB5ID DESC
        """)
        
        with mssql_engine.connect() as conn:
            latest = conn.execute(latest_sql).mappings().first()

        current_stats = {}
        if latest:
            current_stats = {
                "cleaning_scale": float(latest['WG201_HI'] or 0),
                "dry_wheat": float(latest['WG101_HI'] or 0),
                "screening": float(latest['WG301_HI'] or 0),
                "total_flour": float(latest['WG302_HI'] or 0),
                "flour": float(latest['WG501_HI'] or 0) + float(latest['WG502_HI'] or 0),
                "bran": float(latest['WG503_HI'] or 0),
                "water_pre_cleaning": float(latest['DM101'] or 0) + float(latest['DM102'] or 0),
                "water_clean_wheat": float(latest['DM201'] or 0) + float(latest['DM202'] or 0) + float(latest['DM203'] or 0),
                "total_water": (float(latest['DM101'] or 0) + float(latest['DM102'] or 0) + 
                               float(latest['DM201'] or 0) + float(latest['DM202'] or 0) + float(latest['DM203'] or 0)),
                "packing_pl601": float(latest['PL601_TOT'] or 0),
                "packing_pl602": float(latest['PL602_TOT'] or 0),
                "packing_pl603": float(latest['PL603_TOT'] or 0),
                "bags_sl601": int(latest['SL601_COUNTER'] or 0),
                "bags_sl602": int(latest['SL602_COUNTER'] or 0),
                "bags_sl603": int(latest['SL603_COUNTER'] or 0),
                "bags_sl606": int(latest['SL606_COUNTER'] or 0),
                "bags_sl607": int(latest['SL607_COUNTER'] or 0),
                "last_updated": latest['CreatedOn'].isoformat() if latest['CreatedOn'] else None
            }

        return jsonify({
            "success": True,
            "hourly_data": hourly_data,
            "current_stats": current_stats,
            "data_source": "ASMArchive_DB5"
        }), 200, response_headers

    except Exception as e:
        logger.error(f"Error fetching SCADA history: {e}")
        return jsonify({
            "success": False,
            "error": str(e),
            "hourly_data": [],
            "current_stats": {}
        }), 500


@scada_bp.route("/scada/history", methods=["OPTIONS"])
def handle_scada_history_options():
    headers = {
        'Access-Control-Allow-Origin': get_cors_origin(),
        'Access-Control-Allow-Methods': 'GET, OPTIONS',
        'Access-Control-Allow-Headers': 'Content-Type, Authorization, ngrok-skip-browser-warning',
        'Access-Control-Allow-Credentials': 'true'
    }
    return '', 200, headers
