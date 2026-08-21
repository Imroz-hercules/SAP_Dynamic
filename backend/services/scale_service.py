# # services/scale_service.py
# import logging
# import time
# from sqlalchemy import text
# from database import engine as mssql_engine  # ✅ Use MS SQL Server for SCADA data
# from typing import Optional, Dict, List
# from datetime import datetime, timedelta, timezone
# from dateutil import parser

# log = logging.getLogger(__name__)

# # --------------------------------------------------
# # SCADA Field Mappings
# # --------------------------------------------------

# # Milling streams (cumulative TON counters)
# MILLING_FIELDS = [
#     "WG501",  # Bakery Flour stream (F1)
#     "WG502",  # Cake Flour / IWW stream (F2)
#     "WG503",  # Bran stream (F3)
# ]

# # Packing palletizer bag counters (cumulative BAG counters)
# PACKING_FIELDS = [
#     "SL601_COUNTER",  # Palletizer 1 - 45 KG bags
#     "SL602_COUNTER",  # Palletizer 2 - 45 KG bags
#     "SL603_COUNTER",  # Palletizer 3 - 40 KG BRAN bags
#     "SL606_COUNTER",  # Palletizer 6 - 01 KG mini bags
#     "SL607_COUNTER",  # Palletizer 7 - 10 KG bags
# ]

# # Input/process monitoring fields
# INPUT_FIELDS = [
#     "WG101",  # Wheat input - Silo 1
#     "WG201",  # Wheat input - Silo 2
#     "WG202",  # Wheat input - Active scale
#     "WG301",  # Wheat input - Silo 3
#     "WG302",  # Wheat input - Silo 4
# ]

# # Water dosing meters
# WATER_FIELDS = [
#     "DM101",  # Water meter 1
#     "DM102",  # Water meter 2
#     "DM201",  # Water meter 3
#     "DM202",  # Water meter 4
#     "DM203",  # Water meter 5
# ]

# # Damaged bag counters (for quality tracking)
# DAMAGED_FIELDS = [
#     "SL601_DAMAGED",
#     "SL602_DAMAGED",
#     "SL603_DAMAGED",
#     "SL606_DAMAGED",
#     "SL607_DAMAGED",
# ]

# # Build comprehensive allowed fields list
# ALLOWED_SCADA_FIELDS = (
#     MILLING_FIELDS + 
#     PACKING_FIELDS + 
#     INPUT_FIELDS + 
#     WATER_FIELDS + 
#     DAMAGED_FIELDS
# )

# # --------------------------------------------------
# # Safe Attribute Access Helpers
# # --------------------------------------------------
# def get_attr_safe(obj, attr_name: str, default=None):
#     """
#     Safely get a dynamic attribute (like baseline_dm201).
#     Returns default if not present or None.
#     """
#     try:
#         if hasattr(obj, attr_name):
#             value = getattr(obj, attr_name)
#             return value if value is not None else default
#         return default
#     except Exception:
#         return default


# def set_attr_safe(obj, attr_name: str, value):
#     """
#     Safely set a dynamic attribute on an ORM model.
#     Silently ignores if the attribute doesn't exist.
#     """
#     try:
#         if hasattr(obj, attr_name):
#             setattr(obj, attr_name, value)
#     except Exception as e:
#         log.warning(f"Failed to set {attr_name} on {obj}: {e}")

# # --------------------------------------------------
# # Helper
# # --------------------------------------------------
# def _fetch_one(query: str, params: dict = None):
#     """Run a query safely and fetch one row."""
#     try:
#         with mssql_engine.connect() as conn:
#             result = conn.execute(text(query), params or {})
#             return result.fetchone()
#     except Exception as e:
#         log.error(f"Database query error: {e}")
#         import traceback
#         traceback.print_exc()
#         return None

# # --------------------------------------------------
# # SCADA Cache Management
# # --------------------------------------------------
# # Global cache to track last read time per tag (for debugging)
# _scada_read_timestamps = {}

# def clear_scada_cache():
#     """
#     Clear SCADA cache and force fresh reads.
#     This ensures we get the latest values from the database, not stale cached values.
#     """
#     global _scada_read_timestamps
#     _scada_read_timestamps = {}
#     print("🔄 SCADA cache cleared - forcing fresh database reads")
    
#     # Force database connection pool to refresh by creating a new connection
#     try:
#         # Close any stale connections in the pool
#         mssql_engine.dispose()
#         print("✅ Database connection pool refreshed")
#     except Exception as e:
#         print(f"⚠️ Could not refresh connection pool: {e}")

# def force_fresh_scada_read(field_name: str) -> Optional[float]:
#     """
#     Force a fresh SCADA read by ensuring we use a new database connection.
#     This bypasses any connection-level caching.
#     """
#     try:
#         # Create a fresh connection to bypass any caching
#         with mssql_engine.connect() as conn:
#             query = f"""
#                 SELECT TOP 1 [{field_name}], CreatedOn
#                 FROM [dbo].[ASMArchive_DB5]
#                 WHERE [{field_name}] IS NOT NULL
#                 ORDER BY ASMArchive_DB5ID DESC
#             """
#             result = conn.execute(text(query))
#             row = result.fetchone()
            
#             if row and row[0] is not None:
#                 value = float(row[0])
#                 _scada_read_timestamps[field_name] = datetime.now()
#                 return value
#         return None
#     except Exception as e:
#         log.error(f"Error in force_fresh_scada_read for {field_name}: {e}")
#         return None

# # --------------------------------------------------
# # Core SCADA Reading Functions
# # --------------------------------------------------
# def get_scada_reading(field_name: str) -> Optional[float]:
#     """
#     Get the latest reading for any SCADA field.
    
#     Args:
#         field_name: SCADA tag name (e.g., "WG501", "SL607_COUNTER")
    
#     Returns:
#         Latest cumulative value as float, or None if not available
#     """
#     try:
#         if field_name not in ALLOWED_SCADA_FIELDS:
#             log.warning(f"Field '{field_name}' not in allowed SCADA fields list")
#             return None
        
#         # ✅ FIXED: Order by ASMArchive_DB5ID DESC to get last inserted row
#         query = f"""
#             SELECT TOP 1 [{field_name}], CreatedOn
#             FROM [dbo].[ASMArchive_DB5]
#             WHERE [{field_name}] IS NOT NULL
#             ORDER BY ASMArchive_DB5ID DESC
#         """
        
#         row = _fetch_one(query)
        
#         if row and row[0] is not None:
#             value = row[0]
            
#             try:
#                 return float(value)
#             except (ValueError, TypeError) as e:
#                 log.error(f"Cannot convert {field_name} value '{value}' to float: {e}")
#                 return None
        
#         log.debug(f"No data available for SCADA field '{field_name}'")
#         return None
        
#     except Exception as e:
#         log.error(f"Error fetching SCADA field '{field_name}': {e}")
#         import traceback
#         traceback.print_exc()
#         return None

# def get_scada_reading_with_timestamp(field_name: str) -> Optional[tuple]:
#     """
#     Get the latest reading for any SCADA field with its timestamp.
    
#     Args:
#         field_name: SCADA tag name
    
#     Returns:
#         (value, timestamp) tuple, or None if not available
#     """
#     try:
#         if field_name not in ALLOWED_SCADA_FIELDS:
#             log.warning(f"Field '{field_name}' not in allowed list")
#             return None
        
#         # ✅ FIXED: Order by ASMArchive_DB5ID DESC to get last inserted row
#         query = f"""
#             SELECT TOP 1 [{field_name}], CreatedOn
#             FROM [dbo].[ASMArchive_DB5]
#             WHERE [{field_name}] IS NOT NULL
#             ORDER BY ASMArchive_DB5ID DESC
#         """
        
#         row = _fetch_one(query)
        
#         if row and row[0] is not None:
#             value = float(row[0])
#             timestamp = str(row[1])
#             return (value, timestamp)
        
#         return None
        
#     except Exception as e:
#         log.error(f"Error fetching SCADA field '{field_name}' with timestamp: {e}")
#         import traceback
#         traceback.print_exc()
#         return None
# def get_multiple_scada_readings(field_names: List[str], force_fresh: bool = False) -> Dict[str, Dict[str, float]]:
#     """
#     Get latest readings for multiple SCADA fields together.
#     Returns structure:
#       { tag: {"current": <float>, "delta": <float>} }
#     Handles DM scales (water meters) with last-two-readings method.
    
#     Args:
#         force_fresh: If True, forces fresh database connection to bypass any caching
#     """
#     results = {}
#     valid_fields = [f for f in field_names if f in ALLOWED_SCADA_FIELDS]

#     if not valid_fields:
#         log.warning(f"No valid SCADA fields: {field_names}")
#         return results

#     try:
#         # ✅ CRITICAL: If force_fresh, use new connection for each read
#         if force_fresh:
#             print(f"🔄 Forcing fresh SCADA reads for: {valid_fields}")
#             # Small delay to ensure database has latest values
#             time.sleep(0.2)
        
#         for f in valid_fields:
#             # ✅ Handle DM (water) meters
#             if f.startswith("DM"):
#                 query = f"""
#                     SELECT TOP 2 [{f}], CreatedOn
#                     FROM [dbo].[ASMArchive_DB5]
#                     WHERE [{f}] IS NOT NULL
#                     ORDER BY ASMArchive_DB5ID DESC
#                 """
#                 # ✅ CRITICAL: Use fresh connection if force_fresh is True
#                 if force_fresh:
#                     with mssql_engine.connect() as conn:
#                         rows = conn.execute(text(query)).fetchall()
#                 else:
#                     with mssql_engine.connect() as conn:
#                         rows = conn.execute(text(query)).fetchall()

#                 if rows:
#                     latest = float(rows[0][0] or 0)
#                     prev = float(rows[1][0]) if len(rows) > 1 and rows[1][0] is not None else latest
#                     delta = max(0.0, latest - prev)
#                     results[f] = {"current": latest, "delta": delta}
#                     print(f"🧮 DM {f}: latest={latest}, prev={prev}, Δ={delta}")
#                 else:
#                     results[f] = {"current": 0.0, "delta": 0.0}
#             else:
#                 # ✅ Normal tags (WG, SL, etc.)
#                 # ✅ CRITICAL: Use fresh connection if force_fresh is True
#                 if force_fresh:
#                     query = f"""
#                         SELECT TOP 1 [{f}], CreatedOn
#                         FROM [dbo].[ASMArchive_DB5]
#                         WHERE [{f}] IS NOT NULL
#                         ORDER BY ASMArchive_DB5ID DESC
#                     """
#                     with mssql_engine.connect() as conn:
#                         result = conn.execute(text(query))
#                         row = result.fetchone()
#                     val = float(row[0]) if row and row[0] is not None else 0.0
#                 else:
#                     query = f"""
#                         SELECT TOP 1 [{f}], CreatedOn
#                         FROM [dbo].[ASMArchive_DB5]
#                         WHERE [{f}] IS NOT NULL
#                         ORDER BY ASMArchive_DB5ID DESC
#                     """
#                     row = _fetch_one(query)
#                     val = float(row[0]) if row and row[0] is not None else 0.0
#                 results[f] = {"current": val, "delta": 0.0}  # delta handled later

#         print(f"✅ SCADA readings fetched (with delta info): {results}")
#         return results

#     except Exception as e:
#         log.error(f"Error fetching multiple SCADA readings: {e}")
#         import traceback
#         traceback.print_exc()
#         return {f: {"current": 0.0, "delta": 0.0} for f in valid_fields}


# # --------------------------------------------------
# # Validation Helper Functions
# # --------------------------------------------------
# def capture_baseline_readings(equipment: List[str], force_fresh: bool = True) -> Dict[str, float]:
#     """
#     Capture baseline readings when an order STARTS.
    
#     For cumulative counters (DM, SL): Uses most recent NON-NULL value
#     For regular scales (WG): Uses last inserted row value
    
#     Args:
#         equipment: List of SCADA tags to capture
#         force_fresh: If True, forces fresh database reads (default: True for baselines)
    
#     Returns:
#         Dict of baseline readings (all values, including 0.0 if that's the actual SCADA value)
    
#     Example:
#         baselines = capture_baseline_readings(["SL607_COUNTER", "DM201"])
#         # Returns: {"SL607_COUNTER": 10.0, "DM201": 30.0}  <- Actual SCADA values
#     """
#     print(f"🔍 DEBUG - Capturing baselines for: {equipment} (force_fresh={force_fresh})")
    
#     # ✅ CRITICAL: Always force fresh reads for baseline capture
#     readings = get_multiple_scada_readings(equipment, force_fresh=force_fresh)
#     print(f"🔍 DEBUG - Raw readings from SCADA: {readings}")
    
#     # ✅ CRITICAL: For DM scales (cumulative counters), we MUST capture the actual current SCADA value
#     # Even if it's 0.0, that's the actual baseline (not a missing value)
#     # For other scales, None means missing, but for DM scales, we need to find the most recent value
#     valid_baselines = {}
#     for tag in equipment:
#         value = None
        
#         # First, try to get value from readings dict
#         if tag in readings:
#             reading_data = readings[tag]
#             # Handle both dict format {"current": value, "delta": value} and direct value
#             if isinstance(reading_data, dict):
#                 value = reading_data.get("current")
#             else:
#                 value = reading_data
            
#             if value is not None:
#                 valid_baselines[tag] = float(value)
#                 print(f"✅ Captured baseline for {tag} from readings: {value}")
#             else:
#                 print(f"⚠️ {tag} returned None from readings dict")
#         else:
#             print(f"⚠️ {tag} not found in readings dict")
        
#         # If value is still None, try individual query (especially important for DM/SL scales)
#         if value is None:
#             if tag.startswith("DM") or tag.startswith("SL"):
#                 # ✅ CRITICAL: For cumulative counters, we MUST find the actual current value
#                 print(f"🔍 {tag} is a cumulative counter - querying for most recent non-NULL value...")
#                 individual_value = get_scada_reading(tag)
#                 if individual_value is not None:
#                     valid_baselines[tag] = float(individual_value)
#                     print(f"✅ Found {tag} = {individual_value} via individual query (this is the actual baseline!)")
#                 else:
#                     # If SCADA truly has no data, set to 0.0
#                     valid_baselines[tag] = 0.0
#                     print(f"⚠️ {tag} has no SCADA data in database, setting baseline to 0.0")
#             else:
#                 # For non-cumulative scales, None means no reading available
#                 valid_baselines[tag] = 0.0
#                 print(f"⚠️ {tag} has no SCADA data, setting baseline to 0.0")
    
#     if len(valid_baselines) < len(equipment):
#         missing = set(equipment) - set(valid_baselines.keys())
#         log.warning(f"Could not capture baselines for: {missing}")
    
#     print(f"🔍 DEBUG - Final captured baselines: {valid_baselines}")
#     return valid_baselines

# def calculate_deltas(equipment: List[str], baselines: Dict[str, float], order=None, db=None) -> Dict[str, Dict[str, float]]:
#     """
#     Smart delta calculator with persistence.
#     Tracks previous SCADA readings in DB fields per tag (last_scada_value_<tag>).
#     """
#     print(f"🔍 DEBUG - calculate_deltas called")
#     print(f"   Equipment: {equipment}")
#     print(f"   Baselines: {baselines}")

#     current_readings = get_multiple_scada_readings(equipment)
#     print(f"🔍 DEBUG - Current readings from SCADA: {current_readings}")

#     deltas = {}

#     for tag in equipment:
#         baseline = baselines.get(tag, 0.0)
#         reading = current_readings.get(tag)
        
#         # Handle both dict format {"current": value, "delta": value} and direct value
#         if isinstance(reading, dict):
#             current = reading.get("current", 0.0)
#             scada_delta = reading.get("delta", 0.0)  # ✅ Delta already calculated by get_multiple_scada_readings()
#         else:
#             current = reading if reading is not None else 0.0
#             scada_delta = 0.0
        
#         if current is None or current == 0.0:
#             log.warning(f"No current reading available for {tag}, using baseline")
#             current = baseline
        
#         # --- Persisted last reading field (using JSON column) ---
#         last_scada_values = get_attr_safe(order, "last_scada_values", {}) or {}
#         if not isinstance(last_scada_values, dict):
#             last_scada_values = {}
#         tag_key = tag.lower()
#         last_val = float(last_scada_values.get(tag_key, 0.0) or 0.0)

#         # --- Compute delta ---
#         if tag.startswith("DM"):  # DM = cumulative counter (difference between readings)
#             # ✅ FIX: For DM meters, calculate delta from baseline (like WG scales)
#             # This gives: delta = current - baseline (e.g., 150 - 130 = 20)
#             # The SCADA delta (from last 2 rows) is only used for internal tracking
#             delta = max(0.0, current - baseline)
#             print(f"🔍 DEBUG - {tag}: DM delta from baseline: current={current} - baseline={baseline} = {delta}")
#         else:  # WG and other scales
#             delta = max(0.0, current - baseline)

#         # --- Update last value (so next call knows previous reading) ---
#         if order:
#             # Update the JSON dict
#             last_scada_values[tag_key] = float(current)
#             set_attr_safe(order, "last_scada_values", last_scada_values)

#         deltas[tag] = {
#             "baseline": baseline,
#             "current": current,
#             "delta": round(delta, 3)
#         }

#         print(f"🔍 DEBUG - {tag}: baseline={baseline}, last={last_val}, current={current}, delta={delta}")

#     # ✅ Persist updated last_scada_value_* fields
#     if db and order:
#         try:
#             # Mark the JSON field as modified so SQLAlchemy tracks the change
#             from sqlalchemy.orm.attributes import flag_modified
#             flag_modified(order, "last_scada_values")
            
#             # Add order to session if not already tracked
#             db.add(order)
#             # Commit the transaction
#             db.commit()
#             print(f"✅ Persisted last_scada_values to database: {get_attr_safe(order, 'last_scada_values', {})}")
#         except Exception as e:
#             log.warning(f"Failed to persist last_scada_values: {e}")
#             import traceback
#             traceback.print_exc()
#             if db:
#                 try:
#                     db.rollback()
#                 except:
#                     pass

#     print(f"✅ Computed deltas (persistent): {deltas}")
#     return deltas

# # --------------------------------------------------
# # Legacy Functions (MS SQL Server syntax)
# # --------------------------------------------------
# def get_current_scale_value() -> Optional[float]:
#     """Legacy function: Fetch latest WG202 reading (wheat input scale)."""
#     return get_scada_reading("WG202")

# def get_current_scale_value_with_timestamp() -> Optional[tuple]:
#     """Legacy function: Fetch WG202 with timestamp."""
#     return get_scada_reading_with_timestamp("WG202")

# def get_order_end_time(start_time: str) -> Optional[str]:
#     """Legacy function: Find last timestamp where WG202 > 0."""
#     try:
#         query = """
#             SELECT MAX(CreatedOn) AS end_time
#             FROM [dbo].[ASMArchive_DB5]
#             WHERE CreatedOn >= :start_time
#               AND WG202 IS NOT NULL
#               AND WG202 > 0
#         """
#         row = _fetch_one(query, {"start_time": start_time})
#         return str(row[0]) if row and row[0] else None
#     except Exception as e:
#         log.error(f"Error fetching order end_time: {e}")
#         return None

# def get_wg202_for_order(start_time: str, end_time: str) -> Optional[Dict[str, float]]:
#     """Legacy function: Calculate WG202 delta for time window."""
#     try:
#         query = """
#             SELECT MIN(WG202) AS start_val,
#                    MAX(WG202) AS end_val
#             FROM [dbo].[ASMArchive_DB5]
#             WHERE CreatedOn BETWEEN :start_time AND :end_time
#               AND WG202 IS NOT NULL
#               AND WG202 > 0
#         """
#         row = _fetch_one(query, {"start_time": start_time, "end_time": end_time})

#         if row and row[0] is not None and row[1] is not None:
#             start_val, end_val = float(row[0]), float(row[1])
#             return {
#                 "start": start_val,
#                 "end": end_val,
#                 "actual_tons": max(0.0, end_val - start_val)
#             }
#         return None
#     except Exception as e:
#         log.error(f"Error calculating WG202 aggregation: {e}")
#         return None

# def get_outputs_for_order(start_time: str, end_time: str) -> Optional[Dict[str, float]]:
#     """Legacy function: Calculate flour/bran outputs for time window."""
#     try:
#         query = """
#             SELECT 
#                 MIN(WG501) AS s1, MAX(WG501) AS e1,
#                 MIN(WG502) AS s2, MAX(WG502) AS e2,
#                 MIN(WG503) AS s3, MAX(WG503) AS e3
#             FROM [dbo].[ASMArchive_DB5]
#             WHERE CreatedOn BETWEEN :start_time AND :end_time
#         """
#         row = _fetch_one(query, {"start_time": start_time, "end_time": end_time})

#         if row:
#             s1, e1, s2, e2, s3, e3 = [float(x or 0) for x in row]
#             flour_tons = max(0.0, (e1 - s1) + (e2 - s2))
#             bran_tons = max(0.0, e3 - s3)
#             return {"flour_tons": flour_tons, "bran_tons": bran_tons}
#         return None
#     except Exception as e:
#         log.error(f"Error calculating outputs aggregation: {e}")
#         return None

# def wait_until_match(expected_tons: float, baseline: float,
#                      tolerance_pct: float = 5.0, timeout: int = 300) -> Dict[str, any]:
#     """Legacy function: Poll WG202 until it matches expected production."""
#     tolerance_amount = expected_tons * (tolerance_pct / 100.0)
#     log.info(f"[WAIT] Expecting {expected_tons} tons ±{tolerance_amount}, baseline={baseline}")

#     elapsed = 0
#     actual = 0.0
#     while elapsed < timeout:
#         current_val = get_current_scale_value() or baseline
#         actual = max(0.0, current_val - baseline)
#         diff = actual - expected_tons

#         if abs(diff) <= tolerance_amount or actual >= expected_tons:
#             log.info(f"[MATCH] expected={expected_tons}, actual={actual}, diff={diff}")
#             return {
#                 "matched": True,
#                 "expected_tons": expected_tons,
#                 "actual_tons": actual,
#                 "tolerance": tolerance_pct,
#                 "elapsed_sec": elapsed
#             }

#         log.debug(f"[WAIT] Still waiting... expected={expected_tons}, actual={actual}, diff={diff}")
#         time.sleep(5)
#         elapsed += 5

#     log.warning(f"[TIMEOUT] Did not reach expected tons within {timeout}s")
#     return {
#         "matched": False,
#         "expected_tons": expected_tons,
#         "actual_tons": actual,
#         "tolerance": tolerance_pct,
#         "reason": "TIMEOUT",
#         "elapsed_sec": elapsed
#     }

# def get_nearest_start_time(sap_date: str) -> Optional[str]:
#     """Legacy function: Get nearest SCADA timestamp for SAP date."""
#     try:
#         query = """
#             SELECT TOP 1 CreatedOn
#             FROM [dbo].[ASMArchive_DB5]
#             WHERE CreatedOn >= :sap_date
#             ORDER BY CreatedOn ASC
#         """
#         row = _fetch_one(query, {"sap_date": sap_date})
#         return str(row[0]) if row and row[0] else None
#     except Exception as e:
#         log.error(f"Error fetching nearest start_time: {e}")
#         return None

# def get_order_window(sap_date: str) -> Optional[Dict[str, str]]:
#     """Legacy function: Resolve SAP date into SCADA time window."""
#     try:
#         dt = parser.isoparse(str(sap_date))
#         start_dt_utc = dt.astimezone(timezone.utc).replace(tzinfo=None)

#         start_time = get_nearest_start_time(start_dt_utc.strftime("%Y-%m-%d %H:%M:%S"))
#         if not start_time:
#             log.warning(f"No SCADA start found for {sap_date}, using fallback {start_dt_utc}")
#             start_time = start_dt_utc.strftime("%Y-%m-%d %H:%M:%S")

#         end_time = get_order_end_time(start_time)
#         if not end_time:
#             fallback_end = start_dt_utc + timedelta(days=1)
#             log.warning(f"No SCADA end found for {sap_date}, using fallback {fallback_end}")
#             end_time = fallback_end.strftime("%Y-%m-%d %H:%M:%S")

#         return {"start": start_time, "end": end_time}
#     except Exception as e:
#         log.error(f"Error resolving order window for {sap_date}: {e}")
#         return None

# # --------------------------------------------------
# # Utility Functions
# # --------------------------------------------------
# def get_scada_field_type(field_name: str) -> Optional[str]:
#     """
#     Get the type/category of a SCADA field.
    
#     Returns:
#         "MILLING", "PACKING", "INPUT", "WATER", "DAMAGED", or None
#     """
#     if field_name in MILLING_FIELDS:
#         return "MILLING"
#     elif field_name in PACKING_FIELDS:
#         return "PACKING"
#     elif field_name in INPUT_FIELDS:
#         return "INPUT"
#     elif field_name in WATER_FIELDS:
#         return "WATER"
#     elif field_name in DAMAGED_FIELDS:
#         return "DAMAGED"
#     else:
#         return None

# def get_all_available_fields() -> List[str]:
#     """Get list of all SCADA fields that can be queried."""
#     return ALLOWED_SCADA_FIELDS.copy()
# services/scale_service.py
import logging
import time
from sqlalchemy import text
from database import engine as mssql_engine  # ✅ Use MS SQL Server for SCADA data (production mode)
from typing import Optional, Dict, List, Any
from datetime import datetime, timedelta, timezone
from dateutil import parser

log = logging.getLogger(__name__)

# --------------------------------------------------
# SCADA Emulator HTTP Client
# --------------------------------------------------
# Cache for emulator data to avoid excessive HTTP calls
_emulator_cache: Dict[str, Any] = {"data": None, "timestamp": None}
_EMULATOR_CACHE_TTL = 1.0  # seconds

def _fetch_from_emulator() -> Optional[Dict[str, float]]:
    """
    Fetch SCADA data from embedded emulator (when demo mode is enabled).
    Returns dict of {tag: value} or None on error.
    Uses caching to avoid excessive calls.
    
    ✅ FIXED (Jan 26, 2026): Now uses embedded emulator directly instead of HTTP calls.
    """
    import time as _time
    global _emulator_cache
    
    # Check cache
    if _emulator_cache["data"] is not None and _emulator_cache["timestamp"] is not None:
        age = _time.time() - _emulator_cache["timestamp"]
        if age < _EMULATOR_CACHE_TTL:
            return _emulator_cache["data"]
    
    try:
        # ✅ CRITICAL FIX: Use embedded emulator directly (no HTTP call)
        from services.embedded_emulator import get_emulator
        emulator = get_emulator()
        emulator_data = emulator.get_latest()
        scales = emulator_data.get("scales", {})
        
        # Update cache
        _emulator_cache["data"] = scales
        _emulator_cache["timestamp"] = _time.time()
        log.debug(f"✅ [EMULATOR] Fetched from embedded emulator: {len(scales)} scales")
        return scales
    except Exception as e:
        log.error(f"Embedded emulator fetch error: {e}")
        return None

def clear_emulator_cache():
    """Clear the emulator data cache."""
    global _emulator_cache
    _emulator_cache = {"data": None, "timestamp": None}

# --------------------------------------------------
# SCADA Field Mappings (Workstream B — driven by scada_tags)
# --------------------------------------------------
# Mutable lists so scada_tag_registry.refresh_consumer_lists() can update them
# in place. CONTRACTS.md freezes MILLING_FIELDS / INPUT_FIELDS as importable
# lists — callers that imported the name keep working after a registry refresh.

# Milling streams (cumulative TON counters)
MILLING_FIELDS = [
    "WG501",  # Bakery Flour stream (F1)
    "WG502",  # Cake Flour / IWW stream (F2)
    "WG503",  # Bran stream (F3)
]

# Packing palletizer bag counters (cumulative BAG counters)
PACKING_FIELDS = [
    "PL601_TOT",  # Palletizer 1 - 45 KG bags
    "PL602_TOT",  # Palletizer 2 - 45 KG bags
    "PL603_TOT",  # Palletizer 3 - 40 KG BRAN bags
    "SL606_TOT",  # Palletizer 6 - 1 KG mini bags
    "SL607_TOT",  # Palletizer 7 - 10 KG bags
]

# Input/process monitoring fields
INPUT_FIELDS = [
    "WG101",  # Wheat input - Silo 1
    "WG201",  # Wheat input - Silo 2
    "WG202",  # Wheat input - Active scale
    "WG301",  # Wheat input - Silo 3
    "WG302",  # Wheat input - Silo 4
]

# Water dosing meters
WATER_FIELDS = [
    "DM101",  # Water meter 1
    "DM102",  # Water meter 2
    "DM201",  # Water meter 3
    "DM202",  # Water meter 4
    "DM203",  # Water meter 5
]

# Damaged bag counters (for quality tracking)
DAMAGED_FIELDS = [
    "SL601_DAMAGED",
    "SL602_DAMAGED",
    "SL603_DAMAGED",
    "SL606_DAMAGED",
    "SL607_DAMAGED",
]

# Build comprehensive allowed fields list (list, not tuple — mutated by registry)
ALLOWED_SCADA_FIELDS = (
    MILLING_FIELDS +
    PACKING_FIELDS +
    INPUT_FIELDS +
    WATER_FIELDS +
    DAMAGED_FIELDS
)
# Rebind as a fresh list so refresh can .clear()/.extend() without touching the
# category lists' identities incorrectly when ALLOWED was a sum of lists.
ALLOWED_SCADA_FIELDS = list(ALLOWED_SCADA_FIELDS)

try:
    from services.scada_tag_registry import refresh_consumer_lists as _refresh_scada_lists
    _refresh_scada_lists()
except Exception as _scada_reg_exc:
    print(f"[DEBUG] scada_tag_registry refresh deferred: {_scada_reg_exc}")

# --------------------------------------------------
# GLOBAL RESET (Option C)
# - Prefer SCADA_RESET_BASE from routes.scada_routes if available
# - Otherwise use internal LOCAL_SCADA_RESET_BASE
# - Values in these dicts are numeric offsets (the SCADA value at reset)
# --------------------------------------------------

LOCAL_SCADA_RESET_BASE: Dict[str, float] = {}

# DEBUG: Print file location
print("[DEBUG] scale_service.py LOADED FROM FILE:", __file__)

try:
    # Try to import SCADA_RESET_BASE from routes.scada_routes (if present)
    # using import inside try to avoid hard circular import errors at startup.
    from routes.scada_routes import SCADA_RESET_BASE as EXTERNAL_SCADA_RESET_BASE  # type: ignore
    # EXTERNAL_SCADA_RESET_BASE may be mutated by scada_routes.reset API
    SCADA_RESET_SOURCE = "external"
    print("[DEBUG] RESET BASE IMPORTED (external):", EXTERNAL_SCADA_RESET_BASE)
except Exception as e:
    EXTERNAL_SCADA_RESET_BASE = None
    SCADA_RESET_SOURCE = "local"
    print(f"[DEBUG] RESET BASE IMPORT FAILED: {e} - Using local reset base")

def _get_reset_base() -> Dict[str, float]:
    """
    Return the active reset base dictionary.
    Prefer external SCADA_RESET_BASE if available (Option C).
    """
    if EXTERNAL_SCADA_RESET_BASE and isinstance(EXTERNAL_SCADA_RESET_BASE, dict):
        # ✅ DEBUG: Log when reset base is accessed (only first few times to avoid spam)
        if not hasattr(_get_reset_base, '_debug_count'):
            _get_reset_base._debug_count = 0
        _get_reset_base._debug_count += 1
        if _get_reset_base._debug_count <= 3:
            log.info(f"[DEBUG] _get_reset_base() returning EXTERNAL: {len(EXTERNAL_SCADA_RESET_BASE)} keys, id={id(EXTERNAL_SCADA_RESET_BASE)}")
        return EXTERNAL_SCADA_RESET_BASE
    if not hasattr(_get_reset_base, '_debug_count'):
        _get_reset_base._debug_count = 0
    _get_reset_base._debug_count += 1
    if _get_reset_base._debug_count <= 3:
        log.info(f"[DEBUG] _get_reset_base() returning LOCAL: {len(LOCAL_SCADA_RESET_BASE)} keys")
    return LOCAL_SCADA_RESET_BASE

def get_reset_base_debug() -> Dict[str, Any]:
    """Debug function to check reset base status."""
    return {
        "source": SCADA_RESET_SOURCE,
        "external": EXTERNAL_SCADA_RESET_BASE,
        "local": LOCAL_SCADA_RESET_BASE,
        "active": _get_reset_base()
    }

def set_local_reset_base(baseline: Dict[str, float]):
    """
    Utility to set the local reset baseline programmatically.
    Not required if you use /api/scada/reset which sets routes.scada_routes.SCADA_RESET_BASE.
    """
    global LOCAL_SCADA_RESET_BASE
    LOCAL_SCADA_RESET_BASE = {k: float(v) for k, v in (baseline or {}).items()}

def clear_local_reset_base():
    global LOCAL_SCADA_RESET_BASE
    LOCAL_SCADA_RESET_BASE = {}

# --------------------------------------------------
# Safe Attribute Access Helpers
# --------------------------------------------------
def get_attr_safe(obj, attr_name: str, default=None):
    """
    Safely get a dynamic attribute (like baseline_dm201).
    Returns default if not present or None.
    """
    try:
        if hasattr(obj, attr_name):
            value = getattr(obj, attr_name)
            return value if value is not None else default
        return default
    except Exception:
        return default


def set_attr_safe(obj, attr_name: str, value):
    """
    Safely set a dynamic attribute on an ORM model.
    Silently ignores if the attribute doesn't exist.
    """
    try:
        if hasattr(obj, attr_name):
            setattr(obj, attr_name, value)
    except Exception as e:
        log.warning(f"Failed to set {attr_name} on {obj}: {e}")

# --------------------------------------------------
# Helper
# --------------------------------------------------
def _fetch_one(query: str, params: dict = None):
    """Run a query safely and fetch one row."""
    try:
        with mssql_engine.connect() as conn:
            result = conn.execute(text(query), params or {})
            return result.fetchone()
    except Exception as e:
        log.error(f"Database query error: {e}")
        import traceback
        traceback.print_exc()
        return None

# --------------------------------------------------
# DM: SUM of 30-second readings only. No accumulation, no other logic.
# --------------------------------------------------
def sum_dm_readings(dm_tag: str, start_time: datetime, end_time: datetime = None) -> float:
    """
    Sum 30-second DM readings in [start_time, end_time]. Nothing else.

    PLC writes DM (e.g. DM101, DM201) every 30 seconds to ASMArchive_DB5.
    Each row = one 30-sec reading. We SUM those rows. No accumulation, no delta-from-two-rows.

    Args:
        dm_tag: e.g. DM101, DM102, DM201, DM202, DM203
        start_time: window start
        end_time: window end (default: now)

    Returns:
        SUM([dm_tag]) over rows with CreatedOn in [start_time, end_time]
    """
    if end_time is None:
        end_time = datetime.now()
    
    if not dm_tag.startswith("DM"):
        log.warning(f"sum_dm_readings called with non-DM tag: {dm_tag}")
        return 0.0
    
    try:
        # Use demo mode if enabled - fetch from embedded emulator
        from database import get_demo_mode
        if get_demo_mode():
            # In demo mode, get DM reading from embedded emulator
            scales = _fetch_from_emulator()
            if scales and dm_tag in scales:
                dm_value = float(scales[dm_tag])
                log.debug(f"Demo mode: sum_dm_readings returning {dm_value} for {dm_tag} from emulator")
                return dm_value
            log.debug(f"Demo mode: sum_dm_readings returning 0.0 for {dm_tag} (not in emulator)")
            return 0.0
        
        # ✅ FIX: Remove timezone info to avoid MSSQL issues
        if hasattr(start_time, 'replace') and start_time.tzinfo is not None:
            start_time = start_time.replace(tzinfo=None)
        if hasattr(end_time, 'replace') and end_time.tzinfo is not None:
            end_time = end_time.replace(tzinfo=None)

        if start_time > end_time:
            print(f"💧 {dm_tag}: start_time > end_time, return 0")
            return 0.0

        # SUM of 30-sec DM rows in [start_time, end_time] only. Nothing else.
        query = f"""
            SELECT COALESCE(SUM([{dm_tag}]), 0.0) as total_water,
                   COUNT(*) as row_count
            FROM [HerculesV2].[dbo].[ASMArchive_DB5]
            WHERE [{dm_tag}] IS NOT NULL
              AND CAST(CreatedOn AS datetime2) >= :start_time
              AND CAST(CreatedOn AS datetime2) <= :end_time
        """
        print(f"💧 {dm_tag}: SUM of 30-sec rows from {start_time} to {end_time}")

        with mssql_engine.connect() as conn:
            result = conn.execute(text(query), {"start_time": start_time, "end_time": end_time})
            row = result.fetchone()

        if row:
            total = float(row[0] or 0.0)
            row_count = int(row[1] or 0)
            print(f"💧 {dm_tag}: SUM={total:.2f} ({row_count} rows)")
            return total
        print(f"💧 {dm_tag}: no rows, 0")
        return 0.0
                
    except Exception as e:
        log.error(f"Error summing DM readings for {dm_tag}: {e}")
        import traceback
        traceback.print_exc()
        return 0.0


def sum_dm_readings_for_order(dm_tag: str, order) -> float:
    """
    Pick start_time from order, then SUM 30-sec DM rows in [start, now]. Nothing else.
    
    ✅ DEMO MODE FIX (Jan 26, 2026):
    In production, DM values are 30-sec delta readings that we SUM.
    In demo mode, the emulator has DM as a mini-totalizer, so we calculate:
    delta = current_dm - baseline_dm (captured at order start)
    """
    if order is None:
        print(f"⚠️ sum_dm_readings_for_order: order is None for {dm_tag}")
        return 0.0
    
    # ✅ DEMO MODE: Calculate delta from baseline (not sum of readings)
    # In demo mode, DM acts like a mini-totalizer that we calculate delta for
    from database import get_demo_mode
    if get_demo_mode():
        # Get current DM value from emulator
        scales = _fetch_from_emulator()
        if not scales or dm_tag not in scales:
            print(f"💧 {dm_tag}: Demo mode - not found in emulator, returning 0.0")
            return 0.0
        
        current_dm = float(scales[dm_tag])
        
        # Get baseline captured at order start
        baseline_key = f"baseline_{dm_tag.lower()}"
        baseline_dm = float(get_attr_safe(order, baseline_key, 0.0) or 0.0)
        
        # Calculate delta (total water used since order start)
        delta = max(0.0, current_dm - baseline_dm)
        print(f"💧 {dm_tag}: Demo mode - current={current_dm:.2f}, baseline={baseline_dm:.2f}, delta={delta:.2f}")
        return delta
    
    # ✅ PRODUCTION MODE: SUM all 30-sec readings since order start
    # Try multiple timestamp sources in priority order
    start_time = None
    source = "none"
    
    # 1. Try shift_start_time (most accurate for shift-based tracking)
    start_time = get_attr_safe(order, "shift_start_time")
    if start_time:
        source = "shift_start_time"
    
    # 2. Fallback to created_at (when order was created/started in system)
    if start_time is None:
        start_time = get_attr_safe(order, "created_at")
        if start_time:
            source = "created_at"
    
    # 3. Fallback to date field
    if start_time is None:
        start_time = get_attr_safe(order, "date")
        if start_time:
            source = "date"
    
    # 4. Last resort: use 8 hours ago
    if start_time is None:
        start_time = datetime.now() - timedelta(hours=8)
        source = "fallback_8h"
        print(f"⚠️ {dm_tag}: No timestamp on order, using 8 hours ago")
    
    # ✅ FIX: Handle string timestamps (convert to datetime)
    if isinstance(start_time, str):
        try:
            start_time = parser.parse(start_time)
        except Exception as e:
            print(f"⚠️ {dm_tag}: Failed to parse start_time string: {start_time}, error: {e}")
            start_time = datetime.now() - timedelta(hours=8)
    
    print(f"💧 {dm_tag}: Summing from {start_time} (source: {source})")
    result = sum_dm_readings(dm_tag, start_time)
    print(f"💧 {dm_tag}: SUM result = {result:.2f}")
    return result


# --------------------------------------------------
# SCADA Cache Management
# --------------------------------------------------
# Global cache to track last read time per tag (for debugging)
_scada_read_timestamps = {}

def clear_scada_cache():
    """
    Clear SCADA cache and force fresh reads.
    This ensures we get the latest values from the database, not stale cached values.
    """
    global _scada_read_timestamps
    _scada_read_timestamps = {}
    print("🔄 SCADA cache cleared - forcing fresh database reads")

    # Force database connection pool to refresh by creating a new connection
    try:
        # Close any stale connections in the pool
        mssql_engine.dispose()
        print("✅ Database connection pool refreshed")
    except Exception as e:
        print(f"⚠️ Could not refresh connection pool: {e}")

def force_fresh_scada_read(field_name: str) -> Optional[float]:
    """
    Force a fresh SCADA read by ensuring we use a new database connection.
    This bypasses any connection-level caching.
    """
    try:
        # Create a fresh connection to bypass any caching
        with mssql_engine.connect() as conn:
            query = f"""
                SELECT TOP 1 [{field_name}], CreatedOn
                FROM [dbo].[ASMArchive_DB5]
                WHERE [{field_name}] IS NOT NULL
                ORDER BY ASMArchive_DB5ID DESC
            """
            result = conn.execute(text(query))
            row = result.fetchone()

            if row and row[0] is not None:
                value = float(row[0])
                _scada_read_timestamps[field_name] = datetime.now()
                return value
        return None
    except Exception as e:
        log.error(f"Error in force_fresh_scada_read for {field_name}: {e}")
        return None

# --------------------------------------------------
# RESET OFFSET APPLIER
# --------------------------------------------------
def apply_reset_offset(value: float, tag: str, apply_reset: bool = True) -> float:
    """
    Adjust a numeric SCADA reading using the active reset baseline.

    Args:
        value: numeric raw SCADA value
        tag: SCADA tag (e.g., "WG501")
        apply_reset: if False, return raw value (used for baseline capture)

    Returns:
        Adjusted value (value - reset_baseline[tag]) clamped to >= 0.0
    """
    try:
        # ✅ AUTO-NORMALIZE packing counters at registry rollover_max (B2)
        # Apply modulo before manual reset offset so both mechanisms can work together
        if tag in PACKING_FIELDS and value is not None:
            try:
                from services.scada_tag_registry import get_rollover_max
                palletizer_max = get_rollover_max(tag, default=100000.0)
            except Exception:
                palletizer_max = 100000.0
            if palletizer_max and palletizer_max > 0:
                raw_value = float(value)
                if raw_value >= palletizer_max:
                    normalized = raw_value % palletizer_max
                    if not hasattr(apply_reset_offset, '_palletizer_normalized'):
                        apply_reset_offset._palletizer_normalized = set()
                    if tag not in apply_reset_offset._palletizer_normalized:
                        apply_reset_offset._palletizer_normalized.add(tag)
                        log.info(
                            f"🔄 [{tag}] Auto-normalized palletizer: raw={raw_value:.2f} → "
                            f"normalized={normalized:.2f} (modulo {palletizer_max})"
                        )
                    value = normalized
        
        if not apply_reset:
            return float(value if value is not None else 0.0)
        if tag is None:
            return float(value if value is not None else 0.0)
        reset_base = _get_reset_base()
        if reset_base and tag in reset_base:
            try:
                reset_value = float(reset_base.get(tag, 0.0))
                adjusted = float(value if value is not None else 0.0) - reset_value
                if adjusted < 0:
                    return 0.0
                # ✅ DEBUG: Log first few resets to verify it's working
                if not hasattr(apply_reset_offset, '_debug_count'):
                    apply_reset_offset._debug_count = {}
                if tag not in apply_reset_offset._debug_count:
                    apply_reset_offset._debug_count[tag] = 0
                apply_reset_offset._debug_count[tag] += 1
                if apply_reset_offset._debug_count[tag] <= 2:
                    log.info(f"[DEBUG] apply_reset_offset({tag}): raw={value:.2f}, reset={reset_value:.2f}, adjusted={adjusted:.2f}")
                return adjusted
            except Exception as e:
                log.warning(f"Error applying reset offset for {tag}: {e}")
                return float(value if value is not None else 0.0)
        # ✅ DEBUG: Log when reset base doesn't have the tag
        if reset_base and tag not in reset_base:
            if not hasattr(apply_reset_offset, '_missing_tags'):
                apply_reset_offset._missing_tags = set()
            if tag not in apply_reset_offset._missing_tags:
                apply_reset_offset._missing_tags.add(tag)
                log.warning(f"[DEBUG] apply_reset_offset({tag}): Tag not in reset_base. Reset base has {len(reset_base)} keys: {list(reset_base.keys())[:10]}")
        return float(value if value is not None else 0.0)
    except Exception as e:
        log.error(f"Exception in apply_reset_offset({tag}): {e}")
        try:
            return float(value if value is not None else 0.0)
        except:
            return 0.0

# --------------------------------------------------
# Core SCADA Reading Functions
# --------------------------------------------------
def get_scada_reading(field_name: str, apply_reset: bool = True) -> Optional[float]:
    """
    Get the latest reading for any SCADA field.

    Args:
        field_name: SCADA tag name (e.g., "WG501", "SL607_COUNTER")
        apply_reset: If True (default) apply reset offset so consumers see zero-based values.
                     If False, return raw SCADA database value (used by baseline capture).

    Returns:
        Latest cumulative value as float (possibly adjusted), or None if not available
    """
    try:
        if field_name not in ALLOWED_SCADA_FIELDS:
            log.warning(f"Field '{field_name}' not in allowed SCADA fields list")
            return None

        # ✅ CHECK DEMO MODE FIRST - Use embedded emulator
        from database import get_demo_mode
        if get_demo_mode():
            scales = _fetch_from_emulator()
            if scales and field_name in scales:
                numeric = float(scales[field_name])
                return apply_reset_offset(numeric, field_name, apply_reset=apply_reset)
            log.debug(f"No data from emulator for field '{field_name}'")
            return None

        # ✅ CRITICAL FIX: For WG scales (MILLING), concatenate HI + LO values
        # DM scales don't need this - they have single columns
        if field_name.startswith("WG") and field_name in MILLING_FIELDS + INPUT_FIELDS:
            # Read both HI and LO columns and concatenate as strings
            # Zero-pad LO to 6 digits to ensure consistent concatenation
            query = f"""
                SELECT TOP 1 
                    CAST([{field_name}_HI] AS VARCHAR) + RIGHT('000000' + CAST([{field_name}_LO] AS VARCHAR), 6) AS combined_value,
                    CreatedOn
                FROM [dbo].[ASMArchive_DB5]
                WHERE [{field_name}_HI] IS NOT NULL 
                  AND [{field_name}_LO] IS NOT NULL
                ORDER BY ASMArchive_DB5ID DESC
            """
            
            row = _fetch_one(query)
            
            if row and row[0] is not None:
                try:
                    # Combined value is already a string concatenation from SQL
                    combined_str = str(row[0]).strip()
                    numeric = float(combined_str)
                    log.debug(f"🔍 WG scale {field_name}: HI+LO concatenated = {combined_str} -> {numeric}")
                except (ValueError, TypeError) as e:
                    log.error(f"Cannot convert {field_name} concatenated value '{row[0]}' to float: {e}")
                    return None
                # Apply reset offset (unless explicitly disabled)
                adjusted = apply_reset_offset(numeric, field_name, apply_reset=apply_reset)
                return adjusted
            
            log.debug(f"No HI/LO data available for WG scale '{field_name}'")
            return None

        # ✅ MSSQL MODE: Normal fields (DM, PL, SL, etc.) - single column
        query = f"""
            SELECT TOP 1 [{field_name}], CreatedOn
            FROM [dbo].[ASMArchive_DB5]
            WHERE [{field_name}] IS NOT NULL
            ORDER BY ASMArchive_DB5ID DESC
        """

        row = _fetch_one(query)

        if row and row[0] is not None:
            value = row[0]
            try:
                numeric = float(value)
            except (ValueError, TypeError) as e:
                log.error(f"Cannot convert {field_name} value '{value}' to float: {e}")
                return None
            # Apply reset offset (unless explicitly disabled)
            adjusted = apply_reset_offset(numeric, field_name, apply_reset=apply_reset)
            return adjusted

        log.debug(f"No data available for SCADA field '{field_name}'")
        return None

    except Exception as e:
        log.error(f"Error fetching SCADA field '{field_name}': {e}")
        import traceback
        traceback.print_exc()
        return None

def get_scada_reading_with_timestamp(field_name: str, apply_reset: bool = True) -> Optional[tuple]:
    """
    Get the latest reading for any SCADA field with its timestamp.

    Args:
        field_name: SCADA tag name
        apply_reset: If True apply reset offset to the returned numeric value.

    Returns:
        (value, timestamp) tuple, or None if not available
    """
    try:
        if field_name not in ALLOWED_SCADA_FIELDS:
            log.warning(f"Field '{field_name}' not in allowed list")
            return None

        # ✅ CRITICAL FIX: For WG scales (MILLING), concatenate HI + LO values
        # Zero-pad LO to 6 digits to ensure consistent concatenation
        if field_name.startswith("WG") and field_name in MILLING_FIELDS + INPUT_FIELDS:
            query = f"""
                SELECT TOP 1 
                    CAST([{field_name}_HI] AS VARCHAR) + RIGHT('000000' + CAST([{field_name}_LO] AS VARCHAR), 6) AS combined_value,
                    CreatedOn
                FROM [dbo].[ASMArchive_DB5]
                WHERE [{field_name}_HI] IS NOT NULL 
                  AND [{field_name}_LO] IS NOT NULL
                ORDER BY ASMArchive_DB5ID DESC
            """
            
            row = _fetch_one(query)
            
            if row and row[0] is not None:
                try:
                    combined_str = str(row[0]).strip()
                    numeric = float(combined_str)
                    log.debug(f"🔍 WG scale {field_name}: HI+LO concatenated = {combined_str} -> {numeric}")
                except (ValueError, TypeError) as e:
                    log.error(f"Cannot convert {field_name} concatenated value '{row[0]}' to float: {e}")
                    return None
                value = apply_reset_offset(numeric, field_name, apply_reset=apply_reset)
                timestamp = str(row[1])
                return (value, timestamp)
            
            return None

        # Normal fields (DM, PL, SL, etc.) - single column
        query = f"""
            SELECT TOP 1 [{field_name}], CreatedOn
            FROM [dbo].[ASMArchive_DB5]
            WHERE [{field_name}] IS NOT NULL
            ORDER BY ASMArchive_DB5ID DESC
        """

        row = _fetch_one(query)

        if row and row[0] is not None:
            raw_val = row[0]
            try:
                numeric = float(raw_val)
            except (ValueError, TypeError) as e:
                log.error(f"Cannot convert {field_name} value '{raw_val}' to float: {e}")
                return None
            value = apply_reset_offset(numeric, field_name, apply_reset=apply_reset)
            timestamp = str(row[1])
            return (value, timestamp)

        return None

    except Exception as e:
        log.error(f"Error fetching SCADA field '{field_name}' with timestamp: {e}")
        import traceback
        traceback.print_exc()
        return None

def get_multiple_scada_readings(field_names: List[str], force_fresh: bool = False, apply_reset: bool = True) -> Dict[str, Dict[str, float]]:
    """
    Get latest readings for multiple SCADA fields together.
    Returns structure:
      { tag: {"current": <float>, "delta": <float>} }
    Handles DM scales (water meters) with last-two-readings method.

    Args:
        force_fresh: If True, forces fresh database connection to bypass any caching
        apply_reset: If True (default) apply reset offset to 'current' values (use True for KPIs/validation).
                     Set to False when capturing actual baselines.
    """
    results = {}
    valid_fields = [f for f in field_names if f in ALLOWED_SCADA_FIELDS]

    if not valid_fields:
        log.warning(f"No valid SCADA fields: {field_names}")
        return results

    try:
        # ✅ CHECK DEMO MODE FIRST - Use embedded emulator
        from database import get_demo_mode
        if get_demo_mode():
            if force_fresh:
                clear_emulator_cache()  # Force fresh fetch from emulator
            scales = _fetch_from_emulator()
            if scales:
                for f in valid_fields:
                    if f in scales:
                        val_raw = float(scales[f])
                        val = apply_reset_offset(val_raw, f, apply_reset=apply_reset)
                        results[f] = {"current": val, "delta": 0.0}
                    else:
                        results[f] = {"current": 0.0, "delta": 0.0}
                print(f"✅ SCADA readings from EMBEDDED EMULATOR: {results}")
                return results
            else:
                log.warning("Embedded emulator returned no data")
                return {f: {"current": 0.0, "delta": 0.0} for f in valid_fields}

        # ✅ MSSQL MODE
        # If force_fresh, short delay to ensure DB has latest values
        if force_fresh:
            print(f"🔄 Forcing fresh SCADA reads for: {valid_fields}")
            time.sleep(0.2)

        for f in valid_fields:
            # Handle DM (water) meters - use last two rows to compute delta
            if f.startswith("DM"):
                query = f"""
                    SELECT TOP 2 [{f}], CreatedOn
                    FROM [dbo].[ASMArchive_DB5]
                    WHERE [{f}] IS NOT NULL
                    ORDER BY ASMArchive_DB5ID DESC
                """
                if force_fresh:
                    with mssql_engine.connect() as conn:
                        rows = conn.execute(text(query)).fetchall()
                else:
                    with mssql_engine.connect() as conn:
                        rows = conn.execute(text(query)).fetchall()

                if rows:
                    latest_raw = float(rows[0][0] or 0.0)
                    prev_raw = float(rows[1][0]) if len(rows) > 1 and rows[1][0] is not None else latest_raw

                    # Apply reset offset (only to 'current' and for delta calc if apply_reset True)
                    latest = apply_reset_offset(latest_raw, f, apply_reset=apply_reset)
                    prev = apply_reset_offset(prev_raw, f, apply_reset=apply_reset)

                    # Delta is difference between latest and previous (already adjusted if apply_reset==True)
                    delta = max(0.0, latest - prev)
                    results[f] = {"current": latest, "delta": delta}
                    print(f"🧮 DM {f}: raw_latest={latest_raw}, raw_prev={prev_raw}, latest_adj={latest}, prev_adj={prev}, Δ={delta}")
                else:
                    results[f] = {"current": 0.0, "delta": 0.0}
            elif f.startswith("WG") and f in MILLING_FIELDS + INPUT_FIELDS:
                # ✅ CRITICAL FIX: For WG scales (MILLING), concatenate HI + LO values
                # Zero-pad LO to 6 digits to ensure consistent concatenation
                query = f"""
                    SELECT TOP 1 
                        CAST([{f}_HI] AS VARCHAR) + RIGHT('000000' + CAST([{f}_LO] AS VARCHAR), 6) AS combined_value,
                        CreatedOn
                    FROM [dbo].[ASMArchive_DB5]
                    WHERE [{f}_HI] IS NOT NULL 
                      AND [{f}_LO] IS NOT NULL
                    ORDER BY ASMArchive_DB5ID DESC
                """
                
                if force_fresh:
                    with mssql_engine.connect() as conn:
                        result = conn.execute(text(query))
                        row = result.fetchone()
                else:
                    row = _fetch_one(query)

                if row and row[0] is not None:
                    try:
                        # Combined value is already a string concatenation from SQL
                        combined_str = str(row[0]).strip()
                        val_raw = float(combined_str)
                        log.debug(f"🔍 WG scale {f}: HI+LO concatenated = {combined_str} -> {val_raw}")
                    except (ValueError, TypeError) as e:
                        log.error(f"Cannot convert {f} concatenated value '{row[0]}' to float: {e}")
                        val_raw = 0.0
                else:
                    val_raw = 0.0
                
                val = apply_reset_offset(val_raw, f, apply_reset=apply_reset)
                # delta will be computed by calculate_deltas (which uses baseline)
                results[f] = {"current": val, "delta": 0.0}
            else:
                # Normal tags (PL, SL, etc.) - single column
                query = f"""
                    SELECT TOP 1 [{f}], CreatedOn
                    FROM [dbo].[ASMArchive_DB5]
                    WHERE [{f}] IS NOT NULL
                    ORDER BY ASMArchive_DB5ID DESC
                """
                if force_fresh:
                    with mssql_engine.connect() as conn:
                        result = conn.execute(text(query))
                        row = result.fetchone()
                else:
                    row = _fetch_one(query)

                val_raw = float(row[0]) if row and row[0] is not None else 0.0
                val = apply_reset_offset(val_raw, f, apply_reset=apply_reset)
                # delta will be computed by calculate_deltas (which uses baseline)
                results[f] = {"current": val, "delta": 0.0}
        print(f"✅ SCADA readings fetched (with delta info): {results}")
        return results

    except Exception as e:
        log.error(f"Error fetching multiple SCADA readings: {e}")
        import traceback
        traceback.print_exc()
        return {f: {"current": 0.0, "delta": 0.0} for f in valid_fields}

# --------------------------------------------------
# Validation Helper Functions
# --------------------------------------------------
def capture_baseline_readings(equipment: List[str], force_fresh: bool = True) -> Dict[str, float]:
    """
    Capture baseline readings when an order STARTS.

    For cumulative counters (DM, SL): Uses most recent NON-NULL value
    For regular scales (WG): Uses last inserted row value

    Args:
        equipment: List of SCADA tags to capture
        force_fresh: If True, forces fresh database reads (default: True for baselines)

    Returns:
        Dict of baseline readings (RESET-ADJUSTED values, so they start from 0.0 after reset)

    ✅ CRITICAL FIX: Baselines are now captured as RESET-ADJUSTED values.
    This ensures:
    - After reset, baseline = 0.0 (not raw SCADA value)
    - Delta = current (reset-adjusted) - baseline (reset-adjusted) = correct production
    - Example: If reset at 1367.10, then baseline = 0.0, current = 1000.0, delta = 1000.0 ✓
    """
    print(f"🔍 DEBUG - Capturing baselines for: {equipment} (force_fresh={force_fresh})")

    # ✅ CRITICAL: Apply reset offset when capturing baselines
    # This ensures baselines are reset-adjusted (0.0 after reset), not raw SCADA values
    readings = get_multiple_scada_readings(equipment, force_fresh=force_fresh, apply_reset=True)
    print(f"🔍 DEBUG - Reset-adjusted readings from SCADA (for baseline capture): {readings}")

    valid_baselines = {}
    for tag in equipment:
        value = None

        # First, try to get value from readings dict
        if tag in readings:
            reading_data = readings[tag]
            if isinstance(reading_data, dict):
                value = reading_data.get("current")
            else:
                value = reading_data

            if value is not None:
                valid_baselines[tag] = float(value)
                print(f"✅ Captured baseline for {tag} from readings: {value}")
            else:
                print(f"⚠️ {tag} returned None from readings dict")
        else:
            print(f"⚠️ {tag} not found in readings dict")

        # If value is still None, try individual query (especially for DM/SL scales)
        if value is None:
            if tag.startswith("DM") or tag.startswith("SL"):
                print(f"🔍 {tag} is a cumulative counter - querying for most recent non-NULL value...")
                # ✅ CRITICAL: Apply reset offset here too (apply_reset=True)
                individual_value = get_scada_reading(tag, apply_reset=True)
                if individual_value is not None:
                    valid_baselines[tag] = float(individual_value)
                    print(f"✅ Found {tag} = {individual_value} via individual query (RESET-ADJUSTED baseline!)")
                else:
                    valid_baselines[tag] = 0.0
                    print(f"⚠️ {tag} has no SCADA data in database, setting baseline to 0.0")
            else:
                valid_baselines[tag] = 0.0
                print(f"⚠️ {tag} has no SCADA data, setting baseline to 0.0")

    if len(valid_baselines) < len(equipment):
        missing = set(equipment) - set(valid_baselines.keys())
        log.warning(f"Could not capture baselines for: {missing}")

    print(f"🔍 DEBUG - Final captured baselines: {valid_baselines}")
    return valid_baselines

def calculate_deltas(equipment: List[str], baselines: Dict[str, float], order=None, db=None) -> Dict[str, Dict[str, float]]:
    """
    Smart delta calculator with persistence.
    Tracks previous SCADA readings in DB fields per tag (last_scada_value_<tag>).
    """
    print(f"🔍 DEBUG - calculate_deltas called")
    print(f"   Equipment: {equipment}")
    print(f"   Baselines: {baselines}")

    # By default, use reset-adjusted current readings (apply_reset=True)
    current_readings = get_multiple_scada_readings(equipment)
    print(f"🔍 DEBUG - Current readings from SCADA (adjusted): {current_readings}")

    deltas = {}

    for tag in equipment:
        baseline = baselines.get(tag, 0.0)
        reading = current_readings.get(tag)

        # Handle both dict format {"current": value, "delta": value} and direct value
        if isinstance(reading, dict):
            current = reading.get("current", 0.0)
            scada_delta = reading.get("delta", 0.0)  # DM delta already calculated if applicable
        else:
            current = reading if reading is not None else 0.0
            scada_delta = 0.0

        if current is None or current == 0.0:
            log.warning(f"No current reading available for {tag}, using baseline")
            current = baseline

        # --- Persisted last reading field (using JSON column) ---
        last_scada_values = get_attr_safe(order, "last_scada_values", {}) or {}
        if not isinstance(last_scada_values, dict):
            last_scada_values = {}
        tag_key = tag.lower()
        last_val = float(last_scada_values.get(tag_key, 0.0) or 0.0)

        # --- Compute delta ---
        # Track whether baseline was updated (for returning correct value to UI)
        baseline_updated_to = None
        
        if tag.startswith("DM"):
            # DM = 30-sec averages: SUM all readings in order window (match KPI). Do NOT use accumulation.
            # Accumulation misses readings between 60s polls; sum_dm_readings_for_order sums from DB.
            delta = sum_dm_readings_for_order(tag, order)
        else:  # WG and other scales (totalizers - use delta)
            raw_delta = current - baseline
            
            # ✅ B2: packing rollover from scada_tags.rollover_max (was hardcoded 100000)
            is_palletizer = tag in PACKING_FIELDS

            if raw_delta < 0 and is_palletizer:
                try:
                    from services.scada_tag_registry import get_rollover_max
                    palletizer_max = get_rollover_max(tag, default=100000.0) or 100000.0
                except Exception:
                    palletizer_max = 100000.0
                delta = current + (palletizer_max - baseline)
                print(
                    f"🔄 [{tag}] Palletizer rollover (max={palletizer_max}): "
                    f"baseline={baseline}, current={current}, delta={delta}"
                )
                # Do not update baseline after rollover — formula stays valid as
                # the counter climbs past the wrap point.
            else:
                # Normal case - clamp negative deltas to 0 (for WG scales or normal palletizer operation)
                delta = max(0.0, raw_delta)

        # --- Update last value (so next call knows previous reading) ---
        if order:
            last_scada_values[tag_key] = float(current)
            set_attr_safe(order, "last_scada_values", last_scada_values)

        # ✅ Return updated baseline if rollover occurred, so UI shows correct value
        display_baseline = baseline_updated_to if baseline_updated_to is not None else baseline
        
        # Flag whether rollover happened - callers can use this to decide how to handle the delta
        rollover_detected = baseline_updated_to is not None
        
        deltas[tag] = {
            "baseline": display_baseline,
            "current": current,
            "delta": round(delta, 3),
            "rollover": rollover_detected
        }

        print(f"🔍 DEBUG - {tag}: baseline={baseline}, last={last_val}, current={current}, delta={delta}")

    # Persist updated last_scada_values to DB if requested
    if db and order:
        try:
            from sqlalchemy.orm.attributes import flag_modified
            flag_modified(order, "last_scada_values")
            db.add(order)
            db.commit()
            print(f"✅ Persisted last_scada_values to database: {get_attr_safe(order, 'last_scada_values', {})}")
        except Exception as e:
            log.warning(f"Failed to persist last_scada_values: {e}")
            import traceback
            traceback.print_exc()
            if db:
                try:
                    db.rollback()
                except:
                    pass

    print(f"✅ Computed deltas (persistent): {deltas}")
    return deltas

def get_wg_scale_hi_lo(field_name: str, apply_reset: bool = True) -> Optional[Dict[str, float]]:
    """
    Get HI and LO values separately for WG scales (MILLING).
    
    Args:
        field_name: SCADA tag name (e.g., "WG501", "WG502")
        apply_reset: If True apply reset offset to combined value.
    
    Returns:
        Dict with "hi", "lo", and "combined" keys, or None if not available
    """
    try:
        log.debug(f"🔍 get_wg_scale_hi_lo called for: {field_name}")
        
        if field_name not in ALLOWED_SCADA_FIELDS:
            log.warning(f"Field '{field_name}' not in ALLOWED_SCADA_FIELDS")
            return None
        
        is_wg = field_name.startswith("WG")
        in_milling = field_name in MILLING_FIELDS
        in_input = field_name in INPUT_FIELDS
        
        log.debug(f"🔍 {field_name}: is_wg={is_wg}, in_milling={in_milling}, in_input={in_input}")
        
        if not (is_wg and (in_milling or in_input)):
            log.debug(f"Field '{field_name}' is not a WG scale in MILLING_FIELDS or INPUT_FIELDS")
            return None
        
        # ✅ CHECK DEMO MODE FIRST - Use embedded emulator
        from database import get_demo_mode
        if get_demo_mode():
            # Fetch raw scales from embedded emulator (contains HI/LO separately)
            try:
                from services.embedded_emulator import get_emulator
                emulator = get_emulator()
                data = emulator.get_latest()
                raw_scales = data.get("raw_scales", {})
                log.debug(f"🔍 [EMULATOR] Raw scales keys: {list(raw_scales.keys())[:20]}")
                
                # Get HI and LO from emulator (they're stored as field_name_HI and field_name_LO)
                hi_key = f"{field_name}_HI"
                lo_key = f"{field_name}_LO"
                
                if hi_key in raw_scales and lo_key in raw_scales:
                    hi_raw = float(raw_scales[hi_key])
                    lo_raw = float(raw_scales[lo_key])
                    
                    # Concatenate to get combined value
                    hi_str = str(hi_raw)
                    lo_str = str(lo_raw)
                    combined_str = hi_str + lo_str
                    
                    try:
                        combined_raw = float(combined_str)
                    except ValueError:
                        # Fallback to addition if concatenation fails
                        combined_raw = hi_raw + lo_raw
                    
                    # Apply reset offset to combined value only
                    combined_adjusted = apply_reset_offset(combined_raw, field_name, apply_reset=apply_reset)
                    
                    result = {
                        "hi": hi_raw,
                        "lo": lo_raw,
                        "combined": combined_adjusted
                    }
                    log.debug(f"✅ [EMULATOR] {field_name}: HI={hi_raw}, LO={lo_raw}, Combined={combined_adjusted}")
                    return result
                else:
                    log.warning(f"[EMULATOR] HI/LO keys not found: {hi_key}, {lo_key} in raw_scales. Available keys: {list(raw_scales.keys())[:20]}")
                    return None
            except Exception as e:
                log.error(f"[EMULATOR] Error fetching HI/LO from embedded emulator: {e}")
                return None
        
        # ✅ MSSQL MODE: Read HI and LO separately
        # Zero-pad LO to 6 digits to ensure consistent concatenation
        query = f"""
            SELECT TOP 1 
                [{field_name}_HI],
                [{field_name}_LO],
                CAST([{field_name}_HI] AS VARCHAR) + RIGHT('000000' + CAST([{field_name}_LO] AS VARCHAR), 6) AS combined_value,
                CreatedOn
            FROM [dbo].[ASMArchive_DB5]
            WHERE [{field_name}_HI] IS NOT NULL 
              AND [{field_name}_LO] IS NOT NULL
            ORDER BY ASMArchive_DB5ID DESC
        """
        
        log.debug(f"🔍 Executing query for {field_name}_HI and {field_name}_LO")
        row = _fetch_one(query)
        
        if row and row[0] is not None and row[1] is not None:
            try:
                hi_raw = float(row[0])
                lo_raw = float(row[1])
                combined_str = str(row[2]).strip()
                combined_raw = float(combined_str)
                
                log.debug(f"✅ {field_name}: HI={hi_raw}, LO={lo_raw}, Combined={combined_raw}")
                
                # Apply reset offset to combined value only (for consistency)
                # HI and LO are shown as raw values for display
                combined_adjusted = apply_reset_offset(combined_raw, field_name, apply_reset=apply_reset)
                
                result = {
                    "hi": hi_raw,
                    "lo": lo_raw,
                    "combined": combined_adjusted
                }
                log.debug(f"✅ Returning HI/LO data for {field_name}: {result}")
                return result
            except (ValueError, TypeError) as e:
                log.error(f"Cannot convert {field_name} HI/LO values: {e}, row={row}")
                return None
        else:
            log.warning(f"No HI/LO data found for {field_name}, row={row}")
        
        return None
    
    except Exception as e:
        log.error(f"Error fetching WG scale HI/LO for '{field_name}': {e}")
        import traceback
        traceback.print_exc()
        return None

# --------------------------------------------------
# Legacy Functions (MS SQL Server syntax)
# --------------------------------------------------
def get_current_scale_value() -> Optional[float]:
    """Legacy function: Fetch latest WG202 reading (wheat input scale)."""
    return get_scada_reading("WG202")

def get_current_scale_value_with_timestamp() -> Optional[tuple]:
    """Legacy function: Fetch WG202 with timestamp."""
    return get_scada_reading_with_timestamp("WG202")

def get_order_end_time(start_time: str) -> Optional[str]:
    """Legacy function: Find last timestamp where WG202 > 0."""
    try:
        query = """
            SELECT MAX(CreatedOn) AS end_time
            FROM [dbo].[ASMArchive_DB5]
            WHERE CreatedOn >= :start_time
              AND WG202 IS NOT NULL
              AND WG202 > 0
        """
        row = _fetch_one(query, {"start_time": start_time})
        return str(row[0]) if row and row[0] else None
    except Exception as e:
        log.error(f"Error fetching order end_time: {e}")
        return None

def get_wg202_for_order(start_time: str, end_time: str) -> Optional[Dict[str, float]]:
    """Legacy function: Calculate WG202 delta for time window."""
    try:
        query = """
            SELECT MIN(WG202) AS start_val,
                   MAX(WG202) AS end_val
            FROM [dbo].[ASMArchive_DB5]
            WHERE CreatedOn BETWEEN :start_time AND :end_time
              AND WG202 IS NOT NULL
              AND WG202 > 0
        """
        row = _fetch_one(query, {"start_time": start_time, "end_time": end_time})

        if row and row[0] is not None and row[1] is not None:
            start_val, end_val = float(row[0]), float(row[1])
            return {
                "start": start_val,
                "end": end_val,
                "actual_tons": max(0.0, end_val - start_val)
            }
        return None
    except Exception as e:
        log.error(f"Error calculating WG202 aggregation: {e}")
        return None

def get_outputs_for_order(start_time: str, end_time: str) -> Optional[Dict[str, float]]:
    """Legacy function: Calculate flour/bran outputs for time window."""
    try:
        query = """
            SELECT 
                MIN(WG501) AS s1, MAX(WG501) AS e1,
                MIN(WG502) AS s2, MAX(WG502) AS e2,
                MIN(WG503) AS s3, MAX(WG503) AS e3
            FROM [dbo].[ASMArchive_DB5]
            WHERE CreatedOn BETWEEN :start_time AND :end_time
        """
        row = _fetch_one(query, {"start_time": start_time, "end_time": end_time})

        if row:
            s1, e1, s2, e2, s3, e3 = [float(x or 0) for x in row]
            flour_tons = max(0.0, (e1 - s1) + (e2 - s2))
            bran_tons = max(0.0, e3 - s3)
            return {"flour_tons": flour_tons, "bran_tons": bran_tons}
        return None
    except Exception as e:
        log.error(f"Error calculating outputs aggregation: {e}")
        return None

def wait_until_match(expected_tons: float, baseline: float,
                     tolerance_pct: float = 5.0, timeout: int = 300) -> Dict[str, any]:
    """Legacy function: Poll WG202 until it matches expected production."""
    tolerance_amount = expected_tons * (tolerance_pct / 100.0)
    log.info(f"[WAIT] Expecting {expected_tons} tons ±{tolerance_amount}, baseline={baseline}")

    elapsed = 0
    actual = 0.0
    while elapsed < timeout:
        current_val = get_current_scale_value() or baseline
        actual = max(0.0, current_val - baseline)
        diff = actual - expected_tons

        if abs(diff) <= tolerance_amount or actual >= expected_tons:
            log.info(f"[MATCH] expected={expected_tons}, actual={actual}, diff={diff}")
            return {
                "matched": True,
                "expected_tons": expected_tons,
                "actual_tons": actual,
                "tolerance": tolerance_pct,
                "elapsed_sec": elapsed
            }

        log.debug(f"[WAIT] Still waiting... expected={expected_tons}, actual={actual}, diff={diff}")
        time.sleep(5)
        elapsed += 5

    log.warning(f"[TIMEOUT] Did not reach expected tons within {timeout}s")
    return {
        "matched": False,
        "expected_tons": expected_tons,
        "actual_tons": actual,
        "tolerance": tolerance_pct,
        "reason": "TIMEOUT",
        "elapsed_sec": elapsed
    }

def get_nearest_start_time(sap_date: str) -> Optional[str]:
    """Legacy function: Get nearest SCADA timestamp for SAP date."""
    try:
        query = """
            SELECT TOP 1 CreatedOn
            FROM [dbo].[ASMArchive_DB5]
            WHERE CreatedOn >= :sap_date
            ORDER BY CreatedOn ASC
        """
        row = _fetch_one(query, {"sap_date": sap_date})
        return str(row[0]) if row and row[0] else None
    except Exception as e:
        log.error(f"Error fetching nearest start_time for {sap_date}: {e}")
        return None

def get_order_window(sap_date: str) -> Optional[Dict[str, str]]:
    """Legacy function: Resolve SAP date into SCADA time window."""
    try:
        dt = parser.isoparse(str(sap_date))
        start_dt_utc = dt.astimezone(timezone.utc).replace(tzinfo=None)

        start_time = get_nearest_start_time(start_dt_utc.strftime("%Y-%m-%d %H:%M:%S"))
        if not start_time:
            log.warning(f"No SCADA start found for {sap_date}, using fallback {start_dt_utc}")
            start_time = start_dt_utc.strftime("%Y-%m-%d %H:%M:%S")

        end_time = get_order_end_time(start_time)
        if not end_time:
            fallback_end = start_dt_utc + timedelta(days=1)
            log.warning(f"No SCADA end found for {sap_date}, using fallback {fallback_end}")
            end_time = fallback_end.strftime("%Y-%m-%d %H:%M:%S")

        return {"start": start_time, "end": end_time}
    except Exception as e:
        log.error(f"Error resolving order window for {sap_date}: {e}")
        return None

# --------------------------------------------------
# Utility Functions
# --------------------------------------------------
def get_scada_field_type(field_name: str) -> Optional[str]:
    """
    Get the type/category of a SCADA field.

    Returns:
        "MILLING", "PACKING", "INPUT", "WATER", "DAMAGED", or None
    """
    if field_name in MILLING_FIELDS:
        return "MILLING"
    elif field_name in PACKING_FIELDS:
        return "PACKING"
    elif field_name in INPUT_FIELDS:
        return "INPUT"
    elif field_name in WATER_FIELDS:
        return "WATER"
    elif field_name in DAMAGED_FIELDS:
        return "DAMAGED"
    else:
        return None

def get_all_available_fields() -> List[str]:
    """Get list of all SCADA fields that can be queried."""
    return ALLOWED_SCADA_FIELDS.copy()
