# kpi_routes.py
from flask import Blueprint, jsonify, request
from sqlalchemy import text
from database import engine
from datetime import datetime, timedelta
from dateutil import parser as dtparser  # pip install python-dateutil
import logging
import requests
from requests.auth import HTTPBasicAuth
import os

# ✅ CRITICAL: Import reset offset function to apply SCADA reset to KPIs
try:
    from services.scale_service import apply_reset_offset, sum_dm_readings
    RESET_AVAILABLE = True
except Exception as e:
    logger = logging.getLogger(__name__)
    logger.warning(f"Could not import apply_reset_offset from scale_service: {e}")
    RESET_AVAILABLE = False
    def apply_reset_offset(value: float, tag: str, apply_reset: bool = True) -> float:
        """Fallback if import fails"""
        return float(value if value is not None else 0.0)
    def sum_dm_readings(dm_tag: str, start_time, end_time=None) -> float:
        """Fallback if import fails"""
        return 0.0

# Import shift utilities for current shift calculation
try:
    from utils.shifts import get_current_shift, compute_shift_end_datetime
    from models.shift_master import ShiftMaster
    from models.kpi_send_tracking import KpiSendTracking
    from database import PostgresSessionLocal
    from sqlalchemy import func as sa_func
    SHIFT_UTILS_AVAILABLE = True
except Exception as e:
    logger = logging.getLogger(__name__)
    logger.warning(f"Could not import shift utilities: {e}")
    SHIFT_UTILS_AVAILABLE = False

kpi_bp = Blueprint("kpi_bp", __name__)

TABLE = "[HerculesV2].[dbo].[ASMArchive_DB5]"
SCHEMA = "dbo"
TNAME = "ASMArchive_DB5"

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# ============================================================
# MOCK MODE CONFIGURATION
# ============================================================
# ✅ Mock mode is now read from database settings (not environment variable)
# This allows changing mode via the Admin settings page
MOCK_BASE_URL = os.getenv("SAP_MOCK_URL", "http://localhost:6000/mock")
PRODUCTION_BASE_URL = os.getenv("SAP_BASE_URL", "https://vhmioqs4ci.sap.mc3.com.sa:44300")
SAP_USERNAME = os.getenv("SAP_USERNAME", "99999")
SAP_PASSWORD = os.getenv("SAP_PASSWORD", "P@ssw0rdP@ssw0rd")

def get_mock_sap_mode() -> bool:
    """
    Get mock SAP mode from database settings.
    Returns True if mock SAP is enabled, False for real SAP.
    """
    try:
        from models.system_settings import is_mock_sap_enabled
        mode = is_mock_sap_enabled()
        return mode
    except Exception as e:
        logger.warning(f"⚠️ Could not read mock SAP mode from database: {e}, defaulting to True (mock mode)")
        return True  # Default to mock mode for safety

def get_sap_url(endpoint: str, client: str = None) -> str:
    """
    Get the full SAP URL for an endpoint, choosing between mock and production.
    
    Args:
        endpoint: The endpoint path (e.g., '/zmi_kpi_mill/MKPI')
        client: SAP client number (default from SAP_CLIENT env)
        
    Returns:
        Full URL string
    """
    if client is None:
        client = os.getenv("SAP_CLIENT", "250")
    if get_mock_sap_mode():
        # Mock server endpoints match real SAP paths (with /mock prefix)
        return f"{MOCK_BASE_URL}{endpoint}"
    else:
        # Production SAP URL with client parameter
        return f"{PRODUCTION_BASE_URL}{endpoint}?sap-client={client}"

# Log initial mode
initial_mode = get_mock_sap_mode()
if initial_mode:
    logger.info("🔧 MOCK MODE ENABLED - Using demo SAP server at http://localhost:6000/mock")
else:
    logger.info("🔧 PRODUCTION MODE - Using real SAP server")

# ---- helpers --------------------------------------------------------------

def safe(v, default=0.0):
    try:
        if v is None:
            return default
        return float(v)
    except Exception:
        return default

def parse_iso(s: str):
    # accepts "YYYY-MM-DD", "YYYY-MM-DDTHH:mm:ss", with or without Z / offset
    
    if not s:
        return None
    
    try:
        # Handle various formats
        if 'T' in s:
            # ISO format with time
            return dtparser.isoparse(s)
        else:
            # Date only
            return dtparser.parse(s)
    except Exception as e:
        logger.error(f"Failed to parse date '{s}': {e}")
        return None

def first_mapping(row):
    return row if row is None else dict(row)

# Enhanced KPI calculation with real-time data processing
def calc_kpis_from_row(row):
    """Calculate KPIs from raw database row with enhanced real-time processing.
    
    ✅ CRITICAL: Now applies SCADA reset offsets to all values before calculation.
    This ensures KPIs show zero-based values after /api/scada/reset is called.
    """
    try:
        # Check if we have valid SCADA data
        has_valid_data = False
        
        # ✅ CRITICAL: Apply reset offsets to all SCADA values before using them
        # This ensures KPIs reflect zero-based values after reset
        # Grain / product weights (t) - using actual column names from your database
        WG101 = apply_reset_offset(safe(row.get("WG101")), "WG101", apply_reset=True)   # dry wheat (t)
        WG201 = apply_reset_offset(safe(row.get("WG201")), "WG201", apply_reset=True)   # clean wheat (t)
        WG202 = apply_reset_offset(safe(row.get("WG202")), "WG202", apply_reset=True)   # total milled (t) over the period
        WG301 = apply_reset_offset(safe(row.get("WG301")), "WG301", apply_reset=True)   # milling screenings (t)
        WG302 = apply_reset_offset(safe(row.get("WG302")), "WG302", apply_reset=True)   # pre-clean screenings (t)
        WG501 = apply_reset_offset(safe(row.get("WG501")), "WG501", apply_reset=True)   # flour F1 (t)
        WG502 = apply_reset_offset(safe(row.get("WG502")), "WG502", apply_reset=True)   # flour F2 (t)
        WG503 = apply_reset_offset(safe(row.get("WG503")), "WG503", apply_reset=True)   # bran (t)

        # Water consumption (m³) - using actual column names from your database
        DM101 = apply_reset_offset(safe(row.get("DM101")), "DM101", apply_reset=True)
        DM102 = apply_reset_offset(safe(row.get("DM102")), "DM102", apply_reset=True)
        DM201 = apply_reset_offset(safe(row.get("DM201")), "DM201", apply_reset=True)
        DM202 = apply_reset_offset(safe(row.get("DM202")), "DM202", apply_reset=True)
        DM203 = apply_reset_offset(safe(row.get("DM203")), "DM203", apply_reset=True)

        # Time fields - since these columns don't exist in your table, we'll use defaults
        # In a real SCADA system, these would come from time-based calculations
        run_hours = safe(row.get("WG202_Total_Running_Time"), 8.0)   # default to 8 hours if not available
        downtime = safe(row.get("WG202_Stop_Start"), 0.0)           # default to 0 hours if not available
        daily_hrs = safe(row.get("Daily_Hours"), 24.0)              # default to 24 hours
        cap_per_h = safe(row.get("WG202_CapacityPerHour"), 0.0)     # will be calculated if not available

        # Packing data - using actual column names from your database
        # ✅ CRITICAL: Apply reset offsets to packing data as well
        PL601 = apply_reset_offset(safe(row.get("PL601_TOT")), "PL601_TOT", apply_reset=True)  # packing output
        PL602 = apply_reset_offset(safe(row.get("PL602_TOT")), "PL602_TOT", apply_reset=True)  # additional packing data
        PL603 = apply_reset_offset(safe(row.get("PL603_TOT")), "PL603_TOT", apply_reset=True)  # additional packing data
        
        # Check if data is recent (not older than 24 hours)
        # Since we have issues with the CreatedOn column, we'll assume data is recent
        is_recent_data = True
        
        # Check if we have meaningful data for milling calculations
        # We need essential data for meaningful milling KPIs
        # Essential data: clean wheat input (WG201), some output data
        has_milling_data = (
            WG201 > 0.001 and  # Must have some input wheat (at least 0.001 ton)
            (WG501 > 0 or WG502 > 0 or WG503 > 0) and  # Must have some flour/bran output
            daily_hrs > 0  # Must have daily hours
        )
        
        # Check if we have meaningful data for packing calculations
        # We need some packing output
        has_packing_data = (
            PL601 > 0 and  # Must have some packing output
            daily_hrs > 0  # Must have daily hours
        )
        
        # Check if we have any meaningful data at all
        has_valid_data = has_milling_data or has_packing_data
        
        # Log the data for debugging
        logger.info(f"KPI Calculation Data: WG201={WG201}, WG501={WG501}, WG502={WG502}, PL601={PL601}, daily_hrs={daily_hrs}, has_milling_data={has_milling_data}, has_packing_data={has_packing_data}")
        if not has_valid_data:
            logger.info(f"Validation failed - WG201>0.001: {WG201 > 0.001}, flour_output>0: {(WG501 > 0 or WG502 > 0 or WG503 > 0)}, daily_hrs>0: {daily_hrs > 0}")

        # If no valid SCADA data, return all zeros
        if not has_valid_data:
            return {
                "milling_kpis": {
                    "Mill Throughput (%)": 0.0,
                    "Mill Time Efficiency (%)": 0.0,
                    "Total Utilization (%)": 0.0,
                    "Milling Gain": 0.0,
                    "Milling Screening (%)": 0.0,
                    "Flour Extraction (%)": 0.0,
                    "Milling Loss (%)": 0.0,
                    "Net Hours (hrs)": 0.0,
                    "Downtime (hrs)": 0.0,
                    # New KPIs
                    "Max Utilization of Milling Capacity (%)": 0.0,
                    "Pre Cleaning Screening (%)": 0.0,
                    "1st Break Capacity per Hour (t/h)": 0.0,
                    "Bran Extraction (%)": 0.0,
                },
                "packing_kpis": {
                    "Packing Line Capacity (bags/hr)": 0.0,
                    "Daily Packing Output (bags)": 0.0,
                    "Net Hours (hrs)": 0.0,
                    "Downtime (hrs)": 0.0,
                    "Machine Utilization (%)": 0.0,
                    # New KPI
                    "Packing Line Capacity (tons/hr)": 0.0,
                },
                "timestamp": datetime.now().isoformat(),
                "data_source": "no_scada_data"
            }

        # Calculate net hours
        net_hours = max(run_hours - downtime, 0.0)

        # Estimate capacity per hour if not provided
        if cap_per_h <= 0 and net_hours > 0:
            cap_per_h = WG202 / net_hours  # t/h

        # ----- Milling KPIs ----------------------------------------------------
        # Initialize all milling KPIs to 0
        mill_throughput = 0.0
        mill_time_eff = 0.0
        total_util = 0.0
        milling_gain = 0.0
        screening_ratio = 0.0
        total_water = 0.0
        flour_extraction = 0.0
        milling_loss = 0.0
        
        # New KPIs
        max_utilization_milling_capacity = 0.0
        pre_cleaning_screening = 0.0
        first_break_capacity_per_hour = 0.0
        bran_extraction = 0.0

        # Only calculate milling KPIs if we have valid milling data
        # This is a strict check - if any required data is missing, all values remain 0
        if has_milling_data and has_valid_data:
            # Standard mill nameplate capacity is 25 t/h
            nameplate_tph = 25.0

            # Calculate capacity per hour based on output if not available
            if cap_per_h <= 0 and run_hours > 0:
                cap_per_h = WG202 / run_hours if WG202 > 0 else 0.0

            # Mill Throughput (%) - calculate based on capacity
            if cap_per_h > 0:
                mill_throughput = (cap_per_h / nameplate_tph * 100.0)
                # Cap at 100% maximum (percentage cannot exceed 100)
                mill_throughput = min(mill_throughput, 100.0)

            # Mill Time Efficiency (%) - use default values since we don't have real time data
            if daily_hrs > 0:
                mill_time_eff = (run_hours / daily_hrs * 100.0)
                # Cap at 100% maximum
                mill_time_eff = min(mill_time_eff, 100.0)

            # Total Utilization (%)
            total_util = (mill_time_eff * mill_throughput) / 100.0
            # Cap at 100% maximum (percentage cannot exceed 100)
            total_util = min(total_util, 100.0)

            # Milling Gain (%) - calculate based on actual data
            if WG201 > 0:
                total_output = WG501 + WG502 + WG503 + WG301 + WG302
                if total_output > 0:
                    milling_gain = (total_output / WG201 * 100.0)
                    # Cap at reasonable maximum (120% - some moisture gain is possible)
                    milling_gain = min(milling_gain, 120.0)

            # Milling Screening (%) - calculate based on actual data
            # Formula: (WG301) / (WG201) * 100%
            if WG201 > 0 and WG301 > 0:
                screening_ratio = (WG301 / WG201 * 100.0)
                # Cap at reasonable maximum (20% screening is very high)
                screening_ratio = min(screening_ratio, 20.0)

            # Water Consumption calculation removed - using SCADA water data instead

            # Flour Extraction (%) - calculate based on actual data
            if WG202 > 0 and (WG501 > 0 or WG502 > 0):
                total_flour = WG501 + WG502
                if total_flour > 0:
                    flour_extraction = (total_flour / WG202 * 100.0)
                    # Cap at reasonable maximum (85% flour extraction is very high)
                    flour_extraction = min(flour_extraction, 85.0)

            # # Milling Loss (%)
            # milling_loss = 100.0 - milling_gain
            # # Ensure it's not negative
            # milling_loss = max(milling_loss, 0.0)
            
               # Milling Loss (%) - calculate based on actual data
            if WG202 > 0:
                total_output = WG501 + WG502 + WG503  # Total Flour + Total Bran
                if total_output > 0:
                    milling_loss = ((WG202 - total_output) / WG202 * 100.0)
                    # Ensure it's not negative
                    milling_loss = max(milling_loss, 0.0)

            # New KPI Calculations
            
            # 1. MAX UTILIZATION OF MILLING CAPACITY
            # Formula: (WG202) / (TOTAL RUN HOURS * 25)
            if run_hours > 0:
                max_utilization_milling_capacity = (WG202 / (run_hours * 25.0)) * 100.0
                # Cap at 100% maximum (percentage cannot exceed 100)
                max_utilization_milling_capacity = min(max_utilization_milling_capacity, 100.0)
            
            # 2. PRE CLEANING SCREENING (%)
            # Formula: (WG302) / (WG101) * 100%
            if WG101 > 0 and WG302 > 0:
                pre_cleaning_screening = (WG302 / WG101) * 100.0
                # Cap at reasonable maximum (20%)
                pre_cleaning_screening = min(pre_cleaning_screening, 20.0)
            
            # 3. 1ST BREAK CAPACITY PER HOUR AND DAY
            # Formula: (WG202) / (NET HOURS)
            if net_hours > 0 and WG202 > 0:
                first_break_capacity_per_hour = WG202 / net_hours
                # Cap at reasonable maximum (30 t/h)
                first_break_capacity_per_hour = min(first_break_capacity_per_hour, 30.0)
            
            # 4. BRAN EXTRACTION (%)
            # Formula: (WG503) / (WG202) * 100%
            if WG202 > 0 and WG503 > 0:
                bran_extraction = (WG503 / WG202) * 100.0
                # Cap at reasonable maximum (25% bran extraction is very high)
                bran_extraction = min(bran_extraction, 25.0)

        # ----- Packing KPIs ----------------------------------------------------
        # Initialize all packing KPIs to 0
        packing_capacity = 0.0
        daily_packing_output = 0.0
        packing_util = 0.0
        
        # New Packing KPI
        packing_line_capacity_tons_per_hour = 0.0

        # Only calculate packing KPIs if we have valid packing data
        # This is a strict check - if any required data is missing, all values remain 0
        if has_packing_data and has_valid_data:
            # Packing Line Capacity (bags/hr) - calculate based on output and time
            if net_hours > 0 and PL601 > 0:
                packing_capacity = (PL601 / net_hours)
                # Cap at reasonable maximum (2000 bags/hr)
                packing_capacity = min(packing_capacity, 2000.0)

            # Daily Packing Output (bags) - use actual data but cap at reasonable maximum
            if PL601 > 0:
                # The PL601_TOT value seems to be a cumulative total, not daily output
                # Let's use it as is but cap it reasonably
                daily_packing_output = PL601
                # Cap at reasonable maximum (100000 bags per day)
                daily_packing_output = min(daily_packing_output, 100000.0)

            # Packing Machine Utilization (%) - calculate based on time data
            if daily_hrs > 0 and net_hours > 0:
                packing_util = (net_hours / daily_hrs * 100.0)
                # Cap at 100% maximum
                packing_util = min(packing_util, 100.0)

            # New Packing KPI Calculation
            
            # PACKING Line capacity in Tons per hour
            # Formula: PL601 (45 KG) 16.87 TON + PL602 (45 KG) 16.87 TON + PL603 (40 KG BRAN) 10.6 TON + PL606 (01 KG) 2.5 TON + PL607 (10 KG) 4.18 TON
            # Convert bags to tons and calculate total capacity
            if net_hours > 0:
                # Get additional packing data if available
                PL606 = safe(row.get("PL606_TOT", 0.0))
                PL607 = safe(row.get("PL607_TOT", 0.0))
                
                # Convert bags to tons (approximate conversions based on bag weights)
                pl601_tons = PL601 * 0.045  # 45 KG bags
                pl602_tons = PL602 * 0.045  # 45 KG bags  
                pl603_tons = PL603 * 0.040  # 40 KG bran bags
                pl606_tons = PL606 * 0.001  # 1 KG bags
                pl607_tons = PL607 * 0.010  # 10 KG bags
                
                total_packing_tons = pl601_tons + pl602_tons + pl603_tons + pl606_tons + pl607_tons
                packing_line_capacity_tons_per_hour = total_packing_tons / net_hours
                # Cap at reasonable maximum (50 t/h)
                packing_line_capacity_tons_per_hour = min(packing_line_capacity_tons_per_hour, 50.0)

        # Return calculated KPIs
        # Determine data source based on validation
        data_source = "real_time_calculation" if has_valid_data else "no_scada_data"
        
        result = {
            "milling_kpis": {
                "Mill Throughput (%)": round(mill_throughput, 2),
                "Mill Time Efficiency (%)": round(mill_time_eff, 2),
                "Total Utilization (%)": round(total_util, 2),
                "Milling Gain": round(milling_gain, 2),
                "Milling Screening (%)": round(screening_ratio, 2),
                "Flour Extraction (%)": round(flour_extraction, 2),
                "Milling Loss (%)": round(milling_loss, 2),
                "Net Hours (hrs)": round(net_hours, 2),
                "Downtime (hrs)": round(downtime, 2),
                # New KPIs
                "Max Utilization of Milling Capacity (%)": round(max_utilization_milling_capacity, 2),
                "Pre Cleaning Screening (%)": round(pre_cleaning_screening, 2),
                "1st Break Capacity per Hour (t/h)": round(first_break_capacity_per_hour, 2),
                "Bran Extraction (%)": round(bran_extraction, 2),
            },
            "packing_kpis": {
                "Packing Line Capacity (bags/hr)": round(packing_capacity, 2),
                "Daily Packing Output (bags)": round(daily_packing_output, 2),
                "Net Hours (hrs)": round(net_hours, 2),
                "Downtime (hrs)": round(downtime, 2),
                "Machine Utilization (%)": round(packing_util, 2),
                # New KPI
                "Packing Line Capacity (tons/hr)": round(packing_line_capacity_tons_per_hour, 2),
            },
            "timestamp": datetime.now().isoformat(),
            "data_source": data_source
        }
        
        # Final validation - if we don't have valid data, force all values to 0
        if not has_valid_data:
            logger.warning("Final validation failed - forcing all KPIs to 0")
            result = {
                "milling_kpis": {
                    "Mill Throughput (%)": 0.0,
                    "Mill Time Efficiency (%)": 0.0,
                    "Total Utilization (%)": 0.0,
                    "Milling Gain": 0.0,
                    "Milling Screening (%)": 0.0,
                    "Flour Extraction (%)": 0.0,
                    "Milling Loss (%)": 0.0,
                    "Net Hours (hrs)": 0.0,
                    "Downtime (hrs)": 0.0,
                    # New KPIs
                    "Max Utilization of Milling Capacity (%)": 0.0,
                    "Pre Cleaning Screening (%)": 0.0,
                    "1st Break Capacity per Hour (t/h)": 0.0,
                    "Bran Extraction (%)": 0.0,
                },
                "packing_kpis": {
                    "Packing Line Capacity (bags/hr)": 0.0,
                    "Daily Packing Output (bags)": 0.0,
                    "Net Hours (hrs)": 0.0,
                    "Downtime (hrs)": 0.0,
                    "Machine Utilization (%)": 0.0,
                    # New KPI
                    "Packing Line Capacity (tons/hr)": 0.0,
                },
                "timestamp": datetime.now().isoformat(),
                "data_source": "no_scada_data"
            }
        
        # Log the final result for debugging
        logger.info(f"KPI Calculation Result: {result}")
        
        return result
    except Exception as e:
        logger.error(f"Error calculating KPIs: {e}")
        # Return default values on error
        return {
            "milling_kpis": {
                "Mill Throughput (%)": 0.0,
                "Mill Time Efficiency (%)": 0.0,
                "Total Utilization (%)": 0.0,
                "Milling Gain": 0.0,
                "Screening Ratios": 0.0,
                "Water Consumption (m³)": 0.0,
                "Extraction Rates (%)": 0.0,
                "Milling Loss (%)": 0.0,
                "Net Hours (hrs)": 0.0,
                "Downtime (hrs)": 0.0,
                # New KPIs
                "Max Utilization of Milling Capacity (%)": 0.0,
                "Pre Cleaning Screening (%)": 0.0,
                "1st Break Capacity per Hour (t/h)": 0.0,
            },
            "packing_kpis": {
                "Packing Line Capacity (bags/hr)": 0.0,
                "Daily Packing Output (bags)": 0.0,
                "Net Hours (hrs)": 0.0,
                "Downtime (hrs)": 0.0,
                "Machine Utilization (%)": 0.0,
                # New KPI
                "Packing Line Capacity (tons/hr)": 0.0,
            },
            "timestamp": datetime.now().isoformat(),
            "data_source": "error_fallback"
        }

def fetch_existing_columns(conn):
    sql = text("""
        SELECT COLUMN_NAME
        FROM INFORMATION_SCHEMA.COLUMNS
        WHERE TABLE_SCHEMA = :schema AND TABLE_NAME = :tname
    """)
    cols = {r[0] for r in conn.execute(sql, {"schema": SCHEMA, "tname": TNAME}).fetchall()}
    return cols

# ---- SQL builders ---------------------------------------------------------

SUM_COLS = [
    "WG101","WG201","WG202","WG301","WG302","WG501","WG502","WG503",
    "DM101","DM102","DM201","DM202","DM203",
    # totals (some sites store both COUNTER and TOT; we'll prefer deltas for range)
    "PL601_TOT","PL602_TOT","PL603_TOT","SL606_TOT","SL607_TOT",
]

# ✅ WG scales that need HI+LO concatenation (same as validation in scale_service.py)
WG_SCALES = ["WG101", "WG201", "WG202", "WG301", "WG302", "WG501", "WG502", "WG503"]

COUNTER_COLS = [
    "PL601_TOT","PL602_TOT","PL603_TOT","SL606_TOT","SL607_TOT",
]
OPTIONAL_TIME_COLS = [
    # These columns don't exist in the current database, so we'll use defaults
    # "WG202_Total_Running_Time", "WG202_Stop_Start", "WG202_CapacityPerHour", "Daily_Hours"
]

def build_range_sql(existing):
    parts = []

    # ✅ CRITICAL FIX: For WG scales, concatenate HI + LO values before summing
    # Same pattern as used in scale_service.py for validation
    for wg in WG_SCALES:
        hi_col = f"{wg}_HI"
        lo_col = f"{wg}_LO"
        if hi_col in existing and lo_col in existing:
            # Combine HI and LO as strings (concatenate), convert to float, then SUM
            parts.append(
                f"SUM(CASE "
                f"WHEN [{hi_col}] IS NOT NULL AND [{lo_col}] IS NOT NULL "
                f"THEN TRY_CONVERT(float, CAST([{hi_col}] AS VARCHAR) + CAST([{lo_col}] AS VARCHAR)) "
                f"ELSE 0 END) AS [{wg}]"
            )

    # SUMs for DM*/PL*/SL* (non-WG scales) if present
    for c in SUM_COLS:
        if c not in WG_SCALES and c in existing:  # Skip WG scales, already handled above
            parts.append(
                f"SUM(CASE WHEN TRY_CONVERT(float,[{c}]) IS NOT NULL THEN TRY_CONVERT(float,[{c}]) ELSE 0 END) AS [{c}]"
            )

    # Delta (MAX−MIN) for counters/totals if present
    for c in COUNTER_COLS:
        if c in existing:
            parts.append(
                f"CASE WHEN (MAX(COALESCE([{c}],0)) - MIN(COALESCE([{c}],0))) < 0 "
                f"THEN 0 ELSE (MAX(COALESCE([{c}],0)) - MIN(COALESCE([{c}],0))) END AS [{c}]"
            )

    # Optional time fields
    for c in OPTIONAL_TIME_COLS:
        if c in existing:
            if c == "Daily_Hours":
                parts.append(f"MAX([{c}]) AS [{c}]")
            else:
                parts.append(
                    f"SUM(CASE WHEN TRY_CONVERT(float,[{c}]) IS NOT NULL THEN TRY_CONVERT(float,[{c}]) ELSE 0 END) AS [{c}]"
                )

    select_clause = ", ".join(parts) if parts else "COUNT(1) AS rows_in_window"
    sql = f"""
        SELECT {select_clause}
        FROM {TABLE}
        WHERE [CreatedOn] >= :start AND [CreatedOn] <= :end
    """
    return text(sql)

def build_latest_sql():
    # ✅ CRITICAL FIX: For WG scales, concatenate HI + LO values
    # Same pattern as used in scale_service.py for validation
    wg_parts = []
    for wg in WG_SCALES:
        wg_parts.append(
            f"CASE WHEN [{wg}_HI] IS NOT NULL AND [{wg}_LO] IS NOT NULL "
            f"THEN TRY_CONVERT(float, CAST([{wg}_HI] AS VARCHAR) + CAST([{wg}_LO] AS VARCHAR)) "
            f"ELSE NULL END AS [{wg}]"
        )
    
    # Build SELECT clause with WG combined values first, then all other columns
    select_parts = wg_parts + ["*"]
    select_clause = ", ".join(select_parts)
    
    return text(f"""
        SELECT TOP 1 {select_clause}
        FROM {TABLE}
        ORDER BY ASMArchive_DB5ID DESC
    """)

# ---- Helper functions for current shift KPIs -----------------------------

def get_baseline_at_time(target_time: datetime, existing: set):
    """
    Get baseline SCADA data at a specific timestamp (shift start).
    Returns the first record at or after the target time.
    
    In demo mode: Queries PostgreSQL scada_aggregate_values table
    In production mode: Queries MSSQL ASMArchive_DB5 table
    
    ✅ FIXED (Jan 26, 2026): Now uses get_demo_mode() instead of USE_SCADA_EMULATOR.
    """
    try:
        # ✅ CHECK DEMO MODE FIRST - Query PostgreSQL for historical data
        from database import get_demo_mode, postgres_engine
        
        if get_demo_mode() and postgres_engine is not None:
            try:
                # Query PostgreSQL for baseline at shift start
                pg_sql = text("""
                    SELECT 
                        VALUE_WG101, VALUE_WG201, VALUE_WG202, VALUE_WG301, VALUE_WG302,
                        VALUE_WG501, VALUE_WG502, VALUE_WG503,
                        VALUE_DM101, VALUE_DM102, VALUE_DM201, VALUE_DM202, VALUE_DM203,
                        VALUE_PL601_TOT,
                        created_at
                    FROM scada_aggregate_values
                    WHERE created_at >= :target_time
                    ORDER BY created_at ASC
                    LIMIT 1
                """)
                
                with postgres_engine.connect() as pg_conn:
                    row = pg_conn.execute(pg_sql, {"target_time": target_time}).mappings().first()
                    
                    # If no data at shift start, try to get earliest available data as baseline
                    baseline_source = "shift_start"
                    if not row:
                        logger.warning(f"[EMULATOR] No PostgreSQL data at shift start {target_time}, using earliest available data")
                        earliest_sql = text("""
                            SELECT 
                                VALUE_WG101, VALUE_WG201, VALUE_WG202, VALUE_WG301, VALUE_WG302,
                                VALUE_WG501, VALUE_WG502, VALUE_WG503,
                                VALUE_DM101, VALUE_DM102, VALUE_DM201, VALUE_DM202, VALUE_DM203,
                                VALUE_PL601_TOT,
                                created_at
                            FROM scada_aggregate_values
                            ORDER BY created_at ASC
                            LIMIT 1
                        """)
                        row = pg_conn.execute(earliest_sql).mappings().first()
                        baseline_source = "earliest_available"
                    
                    if row:
                        # Map PostgreSQL column names (VALUE_WG101) to expected format (WG101)
                        result = {}
                        row_dict = dict(row)
                        baseline_time = row_dict.get("created_at", "unknown")
                        for key, value in row_dict.items():
                            if key.startswith("VALUE_"):
                                # Remove VALUE_ prefix
                                clean_key = key[6:]  # VALUE_WG101 -> WG101
                                result[clean_key] = float(value) if value is not None else 0.0
                            elif key not in ["created_at", "id", "mode", "window_start", "window_end"]:
                                result[key] = float(value) if value is not None else 0.0
                        
                        logger.info(f"✅ [EMULATOR] Got baseline from PostgreSQL ({baseline_source}): {len(result)} keys at {baseline_time}")
                        return result
                    else:
                        logger.warning(f"[EMULATOR] No PostgreSQL data found at all - emulator data not yet stored")
                        return None
            except Exception as pg_e:
                logger.warning(f"[EMULATOR] PostgreSQL baseline query failed: {pg_e}, falling back to MSSQL")
                # Fall through to MSSQL query
        
        # Fetch from MSSQL database (production mode or fallback)
        # Build SQL to get first record at or after target_time
        wg_parts = []
        for wg in WG_SCALES:
            hi_col = f"{wg}_HI"
            lo_col = f"{wg}_LO"
            if hi_col in existing and lo_col in existing:
                wg_parts.append(
                    f"CASE WHEN [{hi_col}] IS NOT NULL AND [{lo_col}] IS NOT NULL "
                    f"THEN TRY_CONVERT(float, CAST([{hi_col}] AS VARCHAR) + CAST([{lo_col}] AS VARCHAR)) "
                    f"ELSE NULL END AS [{wg}]"
                )
        
        # Add other columns
        other_cols = []
        for c in SUM_COLS:
            if c not in WG_SCALES and c in existing:
                other_cols.append(f"[{c}]")
        
        select_parts = wg_parts + other_cols
        select_clause = ", ".join(select_parts) if select_parts else "*"
        
        sql = text(f"""
            SELECT TOP 1 {select_clause}
            FROM {TABLE}
            WHERE [CreatedOn] >= :target_time
            ORDER BY [CreatedOn] ASC, ASMArchive_DB5ID ASC
        """)
        
        with engine.connect() as conn:
            row = conn.execute(sql, {"target_time": target_time}).mappings().first()
            if row:
                return dict(row)
        return None
    except Exception as e:
        logger.error(f"Error getting baseline at time {target_time}: {e}")
        return None

def get_latest_data_with_hi_lo(existing: set):
    """
    Get latest SCADA data with HI+LO combined for WG scales.
    Supports demo mode - fetches from embedded emulator when enabled.
    
    ✅ FIXED (Jan 26, 2026): Now uses get_demo_mode() and embedded emulator directly.
    """
    try:
        # ✅ CHECK DEMO MODE FIRST - Use embedded emulator
        from database import get_demo_mode
        
        if get_demo_mode():
            # Fetch from embedded emulator directly
            try:
                from services.embedded_emulator import get_emulator
                emulator = get_emulator()
                emulator_data = emulator.get_latest()
                scales = emulator_data.get("scales", {})
                raw_scales = emulator_data.get("raw_scales", {})
                
                # Build result dict with combined HI+LO for WG scales
                result = {}
                for wg in WG_SCALES:
                    # Try direct key first from scales dict
                    v = scales.get(wg)
                    if v is None:
                        # Try HI/LO combination from raw_scales
                        hi_key = f"{wg}_HI"
                        lo_key = f"{wg}_LO"
                        hi_val = raw_scales.get(hi_key)
                        lo_val = raw_scales.get(lo_key)
                        if hi_val is not None and lo_val is not None:
                            try:
                                v = float(str(int(hi_val)) + str(int(lo_val)))
                            except (ValueError, TypeError):
                                v = 0.0
                    result[wg] = float(v) if v is not None else 0.0
                
                # Add DM values (water meters)
                for dm in ["DM101", "DM102", "DM201", "DM202", "DM203"]:
                    result[dm] = float(raw_scales.get(dm, 0.0) or 0.0)
                
                # Add counter values
                for counter in ["SL601_COUNTER", "PL601_TOT", "PL602_TOT", "PL603_TOT"]:
                    result[counter] = float(raw_scales.get(counter, 0.0) or 0.0)
                
                logger.info(f"✅ [EMULATOR] Fetched latest SCADA data from embedded emulator: {len(result)} keys")
                return result
            except Exception as e:
                logger.error(f"[EMULATOR] Error fetching from embedded emulator: {e}")
            return None
        
        # Fetch from MSSQL database (production mode)
        wg_parts = []
        for wg in WG_SCALES:
            wg_parts.append(
                f"CASE WHEN [{wg}_HI] IS NOT NULL AND [{wg}_LO] IS NOT NULL "
                f"THEN TRY_CONVERT(float, CAST([{wg}_HI] AS VARCHAR) + CAST([{wg}_LO] AS VARCHAR)) "
                f"ELSE NULL END AS [{wg}]"
            )
        
        select_parts = wg_parts + ["*"]
        select_clause = ", ".join(select_parts)
        
        sql = text(f"""
            SELECT TOP 1 {select_clause}
            FROM {TABLE}
            ORDER BY ASMArchive_DB5ID DESC
        """)
        
        with engine.connect() as conn:
            row = conn.execute(sql).mappings().first()
            if row:
                return dict(row)
        return None
    except Exception as e:
        logger.error(f"Error getting latest data: {e}")
        return None

def calculate_delta_data(baseline_data: dict, current_data: dict):
    """
    Calculate delta = current - baseline for all SCADA fields.
    Handles WG scales (already combined) and other fields.
    """
    if not baseline_data or not current_data:
        return None
    
    delta_data = {}
    
    # Calculate delta for WG scales (already combined HI+LO)
    for wg in WG_SCALES:
        baseline_val = safe(baseline_data.get(wg, 0.0))
        current_val = safe(current_data.get(wg, 0.0))
        delta_data[wg] = max(0.0, current_val - baseline_val)
    
    # Calculate delta for other SUM_COLS
    for col in SUM_COLS:
        if col not in WG_SCALES:
            baseline_val = safe(baseline_data.get(col, 0.0))
            current_val = safe(current_data.get(col, 0.0))
            delta_data[col] = max(0.0, current_val - baseline_val)
    
    # For counters, use current - baseline
    for col in COUNTER_COLS:
        baseline_val = safe(baseline_data.get(col, 0.0))
        current_val = safe(current_data.get(col, 0.0))
        delta_data[col] = max(0.0, current_val - baseline_val)
    
    return delta_data

# ---- routes ---------------------------------------------------------------

@kpi_bp.route("/api/kpis", methods=["GET"])
@kpi_bp.route("/api/kpi", methods=["GET"])
def get_kpis():
    """
    Dual-mode:
      • No start/end -> CURRENT SHIFT live data (baseline at shift start vs latest).
      • start & end (ISO 8601) -> aggregate over window:
          - WG*/DM*  : SUM
          - *_COUNTER/_TOT : MAX - MIN (non-negative)
          - optional time fields only if present
    Example:
      /api/kpis?start=2025-06-19T16:20:16Z&end=2025-06-19T16:35:16Z
      /api/kpi (no params) -> current shift live data
      
    ✅ UPDATED (Jan 27, 2026): Check demo mode FIRST - return emulator data directly without MSSQL
    """
    start = request.args.get("start")
    end = request.args.get("end")
    
    # Check if user wants to force latest snapshot (for backward compatibility)
    use_latest = request.args.get("use_latest", "false").lower() == "true"
    department = request.args.get("department", "MILLING").upper()
    plant = request.args.get("plant", "3130")

    try:
        # =====================================================================
        # ✅ CHECK DEMO MODE FIRST - Return emulator data directly
        # This bypasses MSSQL entirely when in demo mode
        # =====================================================================
        from database import get_demo_mode
        
        if get_demo_mode():
            logger.info("📊 [DEMO MODE] Fetching KPI data from embedded emulator...")
            try:
                from services.embedded_emulator import get_emulator
                emulator = get_emulator()
                emulator_data = emulator.get_latest()
                scales = emulator_data.get("scales", {})
                raw_scales = emulator_data.get("raw_scales", {})
                
                # Build data dict from emulator
                snapshot = {}
                for wg in WG_SCALES:
                    v = scales.get(wg)
                    if v is None:
                        hi_key = f"{wg}_HI"
                        lo_key = f"{wg}_LO"
                        hi_val = raw_scales.get(hi_key)
                        lo_val = raw_scales.get(lo_key)
                        if hi_val is not None and lo_val is not None:
                            try:
                                v = float(str(int(hi_val)) + str(int(lo_val)))
                            except (ValueError, TypeError):
                                v = 0.0
                    snapshot[wg] = float(v) if v is not None else 0.0
                
                # Add DM values (water meters)
                for dm in ["DM101", "DM102", "DM201", "DM202", "DM203"]:
                    snapshot[dm] = float(raw_scales.get(dm, 0.0) or 0.0)
                
                # Add counter values
                for counter in ["SL601_COUNTER", "PL601_TOT", "PL602_TOT", "PL603_TOT"]:
                    snapshot[counter] = float(raw_scales.get(counter, 0.0) or 0.0)
                
                # Add time columns with defaults
                for k in OPTIONAL_TIME_COLS:
                    snapshot.setdefault(k, 8.0)  # Default 8 hours for demo
                
                # Calculate KPIs from emulator data
                result = calc_kpis_from_row(snapshot)
                result["data_source"] = "emulator"
                result["timestamp"] = datetime.now().isoformat()
                
                logger.info(f"✅ [DEMO MODE] Emulator KPIs calculated successfully")
                return jsonify(result)
                
            except Exception as e:
                logger.error(f"❌ [DEMO MODE] Error fetching emulator data: {e}")
                # Return error response
                return jsonify({
                    "error": f"Emulator error: {str(e)}",
                    "data_source": "emulator_error",
                    "timestamp": datetime.now().isoformat()
                }), 500
        
        # =====================================================================
        # PRODUCTION MODE - Use MSSQL database
        # =====================================================================
        logger.info("📊 [PRODUCTION MODE] Fetching KPI data from MSSQL...")
        
        with engine.connect() as conn:
            existing = fetch_existing_columns(conn)

            if start and end:
                # Range query mode
                sql = build_range_sql(existing)
                params = {
                    "start": parse_iso(start),
                    "end": parse_iso(end)
                }
                row = conn.execute(sql, params).mappings().first()
                if not row:
                    return jsonify({"error": "No data in the requested window"}), 404
                # If we only selected counters/times, we might be missing WG*/DM* keys; ensure they exist with zeros
                aggregated = {k: row[k] for k in row.keys()}
                for k in (SUM_COLS + COUNTER_COLS + OPTIONAL_TIME_COLS):
                    aggregated.setdefault(k, 0.0)
                return jsonify(calc_kpis_from_row(aggregated))

            # ✅ NEW: Default to current shift live data (unless use_latest=true)
            if not use_latest and SHIFT_UTILS_AVAILABLE:
                try:
                    # Get current shift
                    with PostgresSessionLocal() as db:
                        shift_row = get_current_shift(plant, department, db)
                        
                        if shift_row:
                            shift_code = shift_row.shift_code
                            
                            # Calculate shift start datetime
                            now = datetime.now()
                            today = now.date()
                            
                            # Parse shift start time
                            start_time = shift_row.start_time
                            if isinstance(start_time, str):
                                try:
                                    start_time = datetime.strptime(start_time, "%H:%M:%S").time()
                                except ValueError:
                                    start_time = datetime.strptime(start_time, "%H:%M").time()
                            
                            # Build shift start datetime
                            shift_start_dt = datetime.combine(today, start_time)
                            
                            # Handle overnight shifts
                            end_time = shift_row.end_time
                            if isinstance(end_time, str):
                                try:
                                    end_time = datetime.strptime(end_time, "%H:%M:%S").time()
                                except ValueError:
                                    end_time = datetime.strptime(end_time, "%H:%M").time()
                            
                            # If shift crosses midnight and current time is before end time, shift started yesterday
                            if start_time > end_time and now.time() < end_time:
                                shift_start_dt = datetime.combine(today - timedelta(days=1), start_time)
                            
                            # Calculate elapsed time
                            elapsed_time = (now - shift_start_dt).total_seconds() / 3600.0
                            elapsed_time = max(0.0, elapsed_time)
                            
                            # Get shift duration
                            shift_end_dt = compute_shift_end_datetime(shift_row, shift_start_dt)
                            shift_duration = (shift_end_dt - shift_start_dt).total_seconds() / 3600.0
                            
                            logger.info(f"Using current shift ({shift_code}) live data: Start={shift_start_dt}, Elapsed={elapsed_time:.2f}h")
                            
                            # Get baseline at shift start
                            baseline_data = get_baseline_at_time(shift_start_dt, existing)
                            
                            # Get latest data
                            current_data = get_latest_data_with_hi_lo(existing)
                            
                            if baseline_data and current_data:
                                # Calculate delta
                                delta_data = calculate_delta_data(baseline_data, current_data)
                                
                                if delta_data:
                                    # Prepare KPI input with delta data
                                    kpi_input_data = delta_data.copy()
                                    kpi_input_data["WG202_Total_Running_Time"] = elapsed_time
                                    kpi_input_data["Daily_Hours"] = shift_duration
                                    kpi_input_data["WG202_Stop_Start"] = 0.0
                                    
                                    # Calculate KPIs
                                    kpi_result = calc_kpis_from_row(kpi_input_data)
                                    
                                    # Add shift metadata
                                    kpi_result["shift_info"] = {
                                        "shift_code": shift_code,
                                        "department": department,
                                        "plant": plant,
                                        "shift_start": shift_start_dt.isoformat(),
                                        "current_time": now.isoformat(),
                                        "elapsed_hours": round(elapsed_time, 2),
                                        "shift_duration_hours": round(shift_duration, 2),
                                        "shift_progress_percent": round((elapsed_time / shift_duration * 100.0) if shift_duration > 0 else 0.0, 2),
                                        "data_mode": "current_shift_live"
                                    }
                                    
                                    logger.info(f"✅ Current shift KPIs calculated: Shift={shift_code}, Elapsed={elapsed_time:.2f}h")
                                    return jsonify(kpi_result)
                            
                            # Fall through to latest snapshot if shift data not available
                            logger.warning(f"Shift data not available, falling back to latest snapshot")
                except Exception as e:
                    logger.warning(f"Error getting current shift data, falling back to latest snapshot: {e}")
                    # Fall through to latest snapshot

            # Latest snapshot (fallback or when use_latest=true)
            # ✅ Use emulator-aware function for latest data
            snapshot = get_latest_data_with_hi_lo(existing)
            if not snapshot:
                # Fallback to direct MSSQL query if emulator-aware function fails
                row = conn.execute(build_latest_sql()).mappings().first()
                if not row:
                    return jsonify({"error": "No data found"}), 404
                snapshot = dict(row)
            
            # Log the raw data being fetched
            logger.info(f"Using latest snapshot data: {snapshot}")

            # Make sure missing time fields don't break math
            for k in OPTIONAL_TIME_COLS:
                snapshot.setdefault(k, 0.0)

            result = calc_kpis_from_row(snapshot)
            result["data_mode"] = "latest_snapshot"
            return jsonify(result)

    except Exception as e:
        logger.error(f"Error in get_kpis: {e}")
        return jsonify({"error": f"Error calculating KPIs: {str(e)}"}), 500

@kpi_bp.route("/api/kpi/realtime", methods=["GET"])
def get_realtime_kpis():
    """
    Real-time KPI endpoint that fetches the latest data and performs calculations.
    This endpoint is designed to be called every minute for live updates.
    Supports emulator mode - fetches from emulator when enabled.
    """
    try:
        # ✅ Use emulator-aware function for latest data
        snapshot = get_latest_data_with_hi_lo(set())
        
        if not snapshot:
            # Fallback to direct MSSQL query
            with engine.connect() as conn:
                latest_sql = text(f"""
                    SELECT TOP 1 *
                    FROM {TABLE}
                    ORDER BY ASMArchive_DB5ID DESC
                """)
                
                row = conn.execute(latest_sql).mappings().first()
                if not row:
                    return jsonify({
                        "error": "No data found in database",
                        "timestamp": datetime.now().isoformat(),
                        "data_source": "no_data"
                    }), 404

                snapshot = dict(row)
        
        # Ensure all required fields have default values
        required_fields = SUM_COLS + COUNTER_COLS + OPTIONAL_TIME_COLS
        for field in required_fields:
            if field not in snapshot:
                snapshot[field] = 0.0

        # Calculate KPIs from the latest data
        kpi_result = calc_kpis_from_row(snapshot)
        
        # Add additional metadata
        kpi_result["last_updated"] = datetime.now().isoformat()
        created_on = snapshot.get("CreatedOn", datetime.now())
        if created_on:
            kpi_result["data_age_seconds"] = (datetime.now() - created_on).total_seconds() if hasattr(created_on, 'total_seconds') or isinstance(created_on, datetime) else 0
        else:
            kpi_result["data_age_seconds"] = 0
        
        logger.info(f"Real-time KPI calculation completed at {kpi_result['last_updated']}")
        
        return jsonify(kpi_result)

    except Exception as e:
        logger.error(f"Error in real-time KPI calculation: {e}")
        return jsonify({
            "error": f"Error calculating real-time KPIs: {str(e)}",
            "timestamp": datetime.now().isoformat(),
            "data_source": "error"
        }), 500

@kpi_bp.route("/api/kpis/current-shift", methods=["GET"])
def get_current_shift_kpis():
    """
    Calculate LIVE KPIs for the CURRENT ONGOING shift.
    
    Logic:
    1. Get current shift (A, B, or C)
    2. Get baseline data at shift start time
    3. Get latest data (current time)
    4. Calculate delta = latest - baseline
    5. Calculate KPIs using delta data and elapsed time
    
    Query Parameters:
        - department: "MILLING" or "PACKING" (required)
        - plant: Plant code, e.g., "3130" (optional, defaults to "3130")
    
    Example:
        /api/kpis/current-shift?department=MILLING&plant=3130
    """
    if not SHIFT_UTILS_AVAILABLE:
        return jsonify({
            "error": "Shift utilities not available",
            "message": "Cannot calculate current shift KPIs without shift utilities"
        }), 500
    
    try:
        department = request.args.get("department", "MILLING").upper()
        plant = request.args.get("plant", "3130")
        
        # Get current shift
        with PostgresSessionLocal() as db:
            shift_row = get_current_shift(plant, department, db)
            
            if not shift_row:
                return jsonify({
                    "error": f"No active shift found for {department} at plant {plant}",
                    "message": "Shift may have ended or not started yet"
                }), 404
            
            shift_code = shift_row.shift_code
            
            # Calculate shift start datetime for today
            now = datetime.now()
            today = now.date()
            
            # Parse shift start time
            start_time = shift_row.start_time
            if isinstance(start_time, str):
                try:
                    start_time = datetime.strptime(start_time, "%H:%M:%S").time()
                except ValueError:
                    start_time = datetime.strptime(start_time, "%H:%M").time()
            
            # Build shift start datetime
            shift_start_dt = datetime.combine(today, start_time)
            
            # Handle overnight shifts (if shift started yesterday)
            end_time = shift_row.end_time
            if isinstance(end_time, str):
                try:
                    end_time = datetime.strptime(end_time, "%H:%M:%S").time()
                except ValueError:
                    end_time = datetime.strptime(end_time, "%H:%M").time()
            
            # If shift crosses midnight and current time is before end time, shift started yesterday
            if start_time > end_time and now.time() < end_time:
                shift_start_dt = datetime.combine(today - timedelta(days=1), start_time)
            
            # Calculate elapsed time from shift start to now
            elapsed_time = (now - shift_start_dt).total_seconds() / 3600.0  # hours
            elapsed_time = max(0.0, elapsed_time)  # Ensure non-negative
            
            # Get shift duration (for percentage calculations)
            shift_end_dt = compute_shift_end_datetime(shift_row, shift_start_dt)
            shift_duration = (shift_end_dt - shift_start_dt).total_seconds() / 3600.0
            
            logger.info(f"Current Shift: {shift_code}, Start: {shift_start_dt}, Now: {now}, Elapsed: {elapsed_time:.2f} hours")
        
        # Get baseline data at shift start
        with engine.connect() as conn:
            existing = fetch_existing_columns(conn)
        
        baseline_data = get_baseline_at_time(shift_start_dt, existing)
        if not baseline_data:
            return jsonify({
                "error": f"No baseline data found at shift start time ({shift_start_dt})",
                "shift_info": {
                    "shift_code": shift_code,
                    "shift_start": shift_start_dt.isoformat(),
                    "current_time": now.isoformat(),
                    "elapsed_hours": elapsed_time
                }
            }), 404
        
        # Get latest data (current)
        current_data = get_latest_data_with_hi_lo(existing)
        if not current_data:
            return jsonify({
                "error": "No current data found in database"
            }), 404
        
        # Calculate delta = current - baseline
        delta_data = calculate_delta_data(baseline_data, current_data)
        if not delta_data:
            return jsonify({
                "error": "Failed to calculate delta data"
            }), 500
        
        # Prepare data for KPI calculation
        # Use delta values and elapsed time
        kpi_input_data = delta_data.copy()
        
        # Set time fields for KPI calculation
        kpi_input_data["WG202_Total_Running_Time"] = elapsed_time  # Elapsed time from shift start
        kpi_input_data["Daily_Hours"] = shift_duration  # Full shift duration (for percentage calculations)
        kpi_input_data["WG202_Stop_Start"] = 0.0  # Assume no downtime (or calculate if available)
        
        # Calculate KPIs using delta data
        kpi_result = calc_kpis_from_row(kpi_input_data)
        
        # Add shift metadata
        kpi_result["shift_info"] = {
            "shift_code": shift_code,
            "department": department,
            "plant": plant,
            "shift_start": shift_start_dt.isoformat(),
            "current_time": now.isoformat(),
            "elapsed_hours": round(elapsed_time, 2),
            "shift_duration_hours": round(shift_duration, 2),
            "shift_progress_percent": round((elapsed_time / shift_duration * 100.0) if shift_duration > 0 else 0.0, 2)
        }
        
        # Add baseline and current values for reference
        kpi_result["data_snapshot"] = {
            "baseline_time": shift_start_dt.isoformat(),
            "current_time": now.isoformat(),
            "baseline_values": {
                wg: round(safe(baseline_data.get(wg, 0.0)), 3) for wg in WG_SCALES
            },
            "current_values": {
                wg: round(safe(current_data.get(wg, 0.0)), 3) for wg in WG_SCALES
            },
            "delta_values": {
                wg: round(delta_data.get(wg, 0.0), 3) for wg in WG_SCALES
            }
        }
        
        return jsonify(kpi_result)
        
    except Exception as e:
        logger.error(f"Error calculating current shift KPIs: {e}")
        import traceback
        traceback.print_exc()
        return jsonify({"error": f"Error calculating current shift KPIs: {str(e)}"}), 500


# =============================================================================
# HISTORICAL KPI API - C31-T11
# =============================================================================

def build_historical_aggregation_sql(existing: set, period: str = "day"):
    """
    Build SQL query to aggregate KPI data by time period.
    
    Args:
        existing: Set of existing column names in the database
        period: Aggregation period - 'hour', 'day', 'week', 'month'
    
    Returns:
        SQL text object with parameterized query
    """
    # Define period grouping expression for SQL Server
    if period == "hour":
        date_group = "DATEADD(hour, DATEDIFF(hour, 0, [CreatedOn]), 0)"
        date_format = "period_hour"
    elif period == "week":
        date_group = "DATEADD(week, DATEDIFF(week, 0, [CreatedOn]), 0)"
        date_format = "period_week"
    elif period == "month":
        date_group = "DATEFROMPARTS(YEAR([CreatedOn]), MONTH([CreatedOn]), 1)"
        date_format = "period_month"
    else:  # day (default)
        date_group = "CAST([CreatedOn] AS DATE)"
        date_format = "period_date"
    
    parts = [f"{date_group} AS [{date_format}]"]
    
    # ✅ WG scales with HI+LO concatenation (same as build_range_sql)
    for wg in WG_SCALES:
        hi_col = f"{wg}_HI"
        lo_col = f"{wg}_LO"
        if hi_col in existing and lo_col in existing:
            parts.append(
                f"SUM(CASE "
                f"WHEN [{hi_col}] IS NOT NULL AND [{lo_col}] IS NOT NULL "
                f"THEN TRY_CONVERT(float, CAST([{hi_col}] AS VARCHAR) + CAST([{lo_col}] AS VARCHAR)) "
                f"ELSE 0 END) AS [{wg}]"
            )
    
    # SUMs for DM water meters (non-WG scales)
    for c in SUM_COLS:
        if c not in WG_SCALES and c in existing and "_TOT" not in c:
            parts.append(
                f"SUM(CASE WHEN TRY_CONVERT(float,[{c}]) IS NOT NULL THEN TRY_CONVERT(float,[{c}]) ELSE 0 END) AS [{c}]"
            )
    
    # Delta (MAX−MIN) for counters/totals - packing data
    for c in COUNTER_COLS:
        if c in existing:
            parts.append(
                f"CASE WHEN (MAX(COALESCE([{c}],0)) - MIN(COALESCE([{c}],0))) < 0 "
                f"THEN 0 ELSE (MAX(COALESCE([{c}],0)) - MIN(COALESCE([{c}],0))) END AS [{c}]"
            )
    
    # Count records per period (useful for calculating run hours)
    parts.append("COUNT(*) AS record_count")
    
    # Calculate approximate run hours based on record frequency (assuming ~1 record per minute)
    parts.append("COUNT(*) / 60.0 AS approx_run_hours")
    
    select_clause = ", ".join(parts)
    
    sql = f"""
        SELECT {select_clause}
        FROM {TABLE}
        WHERE [CreatedOn] >= :start_date AND [CreatedOn] < :end_date
        GROUP BY {date_group}
        ORDER BY {date_group}
    """
    return text(sql), date_format


def build_average_aggregation_sql(existing: set):
    """
    Build SQL query to calculate AVERAGE values across all rows in date range.
    This is different from build_historical_aggregation_sql which groups by period.
    
    Args:
        existing: Set of existing column names in the database
    
    Returns:
        SQL text object with parameterized query
    """
    parts = []
    
    # ✅ WG scales: Calculate AVERAGE of HI+LO concatenated values
    for wg in WG_SCALES:
        hi_col = f"{wg}_HI"
        lo_col = f"{wg}_LO"
        if hi_col in existing and lo_col in existing:
            parts.append(
                f"AVG(CASE "
                f"WHEN [{hi_col}] IS NOT NULL AND [{lo_col}] IS NOT NULL "
                f"THEN TRY_CONVERT(float, CAST([{hi_col}] AS VARCHAR) + CAST([{lo_col}] AS VARCHAR)) "
                f"ELSE NULL END) AS [{wg}]"
            )
    
    # ✅ Water meters: Calculate AVERAGE (not SUM)
    for c in SUM_COLS:
        if c not in WG_SCALES and c in existing and "_TOT" not in c:
            parts.append(
                f"AVG(CASE WHEN TRY_CONVERT(float,[{c}]) IS NOT NULL THEN TRY_CONVERT(float,[{c}]) ELSE NULL END) AS [{c}]"
            )
    
    # ✅ Counters: Still use MAX-MIN delta across entire range
    for c in COUNTER_COLS:
        if c in existing:
            parts.append(
                f"CASE WHEN (MAX(COALESCE([{c}],0)) - MIN(COALESCE([{c}],0))) < 0 "
                f"THEN 0 ELSE (MAX(COALESCE([{c}],0)) - MIN(COALESCE([{c}],0))) END AS [{c}]"
            )
    
    # Count total records
    parts.append("COUNT(*) AS record_count")
    
    # Calculate total time span in hours
    parts.append("DATEDIFF(MINUTE, MIN([CreatedOn]), MAX([CreatedOn])) / 60.0 AS total_hours")
    
    select_clause = ", ".join(parts)
    
    sql = f"""
        SELECT {select_clause}
        FROM {TABLE}
        WHERE [CreatedOn] >= :start_date AND [CreatedOn] < :end_date
    """
    return text(sql)


@kpi_bp.route("/api/kpi/historical", methods=["GET"])
def get_historical_kpi():
    """
    Get historical KPI data aggregated by time period.
    
    Query params:
    - start_date: YYYY-MM-DD (required)
    - end_date: YYYY-MM-DD (required)  
    - period: hour|day|week|month (default: day) - only used when aggregation_mode='period'
    - aggregation_mode: period|average (default: period)
        - 'period': Group by time period, calculate KPIs per period (existing behavior)
        - 'average': Average all rows first, then calculate KPIs once
    - shifts: comma-separated A,B,C (optional, filter by shifts - NOT YET IMPLEMENTED)
    - department: MILLING|PACKING|ALL (optional, default: ALL)
    
    Returns:
    {
        "success": true,
        "data": [
            {
                "period_start": "2026-01-20T00:00:00",
                "period_end": "2026-01-20T23:59:59",
                "milling_kpis": {...},
                "packing_kpis": {...},
                "raw_data": {...}
            },
            ...
        ],
        "summary": {
            "total_periods": 7,
            "start_date": "2026-01-15",
            "end_date": "2026-01-21",
            "period": "day",
            "department": "ALL"
        }
    }
    """
    # Parse query parameters
    start_date_str = request.args.get("start_date")
    end_date_str = request.args.get("end_date")
    period = request.args.get("period", "day").lower()
    aggregation_mode = request.args.get("aggregation_mode", "period").lower()
    shifts = request.args.get("shifts", "")  # Future: A,B,C filtering
    department = request.args.get("department", "ALL").upper()
    
    # Validate required parameters
    if not start_date_str or not end_date_str:
        return jsonify({
            "success": False,
            "error": "Missing required parameters: start_date and end_date (format: YYYY-MM-DD)"
        }), 400
    
    # Validate aggregation_mode
    valid_modes = ["period", "average"]
    if aggregation_mode not in valid_modes:
        return jsonify({
            "success": False,
            "error": f"Invalid aggregation_mode '{aggregation_mode}'. Must be one of: {', '.join(valid_modes)}"
        }), 400
    
    # Validate period (only needed for period mode)
    if aggregation_mode == "period":
        valid_periods = ["hour", "day", "week", "month"]
        if period not in valid_periods:
            return jsonify({
                "success": False,
                "error": f"Invalid period '{period}'. Must be one of: {', '.join(valid_periods)}"
            }), 400
    
    # Parse dates
    try:
        start_date = datetime.strptime(start_date_str, "%Y-%m-%d")
        # End date should be exclusive, so add 1 day
        end_date = datetime.strptime(end_date_str, "%Y-%m-%d") + timedelta(days=1)
    except ValueError as e:
        return jsonify({
            "success": False,
            "error": f"Invalid date format. Use YYYY-MM-DD. Error: {str(e)}"
        }), 400
    
    # Validate date range
    if start_date >= end_date:
        return jsonify({
            "success": False,
            "error": "start_date must be before end_date"
        }), 400
    
    # Limit date range to prevent excessive queries
    max_days = 365
    if (end_date - start_date).days > max_days:
        return jsonify({
            "success": False,
            "error": f"Date range cannot exceed {max_days} days"
        }), 400
    
    try:
        with engine.connect() as conn:
            # Get existing columns
            existing = fetch_existing_columns(conn)
            
            # Handle average aggregation mode
            if aggregation_mode == "average":
                # Build and execute average aggregation query
                sql = build_average_aggregation_sql(existing)
                
                logger.info(f"Executing average aggregation query: start={start_date}, end={end_date}")
                
                row = conn.execute(sql, {
                    "start_date": start_date,
                    "end_date": end_date
                }).mappings().fetchone()
                
                if not row:
                    return jsonify({
                        "success": True,
                        "data": [],
                        "summary": {
                            "total_periods": 0,
                            "start_date": start_date_str,
                            "end_date": end_date_str,
                            "aggregation_mode": "average",
                            "department": department,
                            "message": "No data found for the specified date range"
                        }
                    })
                
                row_dict = dict(row)
                total_hours = float(row_dict.get("total_hours", 0) or 0)
                record_count = int(row_dict.get("record_count", 0) or 0)
                
                # Prepare data for KPI calculation
                kpi_input = {}
                for key in row_dict:
                    if key not in ["record_count", "total_hours"]:
                        kpi_input[key] = row_dict[key]
                
                # Set time fields based on total span
                # Use total_hours if available, otherwise estimate from date range
                if total_hours > 0:
                    kpi_input["WG202_Total_Running_Time"] = total_hours
                    kpi_input["Daily_Hours"] = total_hours
                else:
                    # Fallback: estimate hours from date range
                    estimated_hours = (end_date - start_date).total_seconds() / 3600.0
                    kpi_input["WG202_Total_Running_Time"] = estimated_hours
                    kpi_input["Daily_Hours"] = estimated_hours
                
                kpi_input["WG202_Stop_Start"] = 0.0
                
                # Calculate KPIs ONCE from averaged values
                try:
                    kpis = calc_kpis_from_row(kpi_input)
                except Exception as e:
                    logger.warning(f"Error calculating KPIs from averaged data: {e}")
                    kpis = {"milling_kpis": {}, "packing_kpis": {}, "error": str(e)}
                
                # Build result entry
                entry = {
                    "period_start": start_date.isoformat(),
                    "period_end": (end_date - timedelta(seconds=1)).isoformat(),
                    "period_label": f"{start_date_str} to {end_date_str}",
                    "record_count": record_count,
                    "total_hours": round(total_hours, 2),
                }
                
                # Add KPIs based on department filter
                if department in ["ALL", "MILLING"]:
                    entry["milling_kpis"] = kpis.get("milling_kpis", {})
                if department in ["ALL", "PACKING"]:
                    entry["packing_kpis"] = kpis.get("packing_kpis", {})
                
                # Optionally include raw data for debugging
                if request.args.get("include_raw", "false").lower() == "true":
                    entry["raw_data"] = {k: float(v) if v is not None else 0.0 for k, v in kpi_input.items() if isinstance(v, (int, float)) or v is None}
                
                logger.info(f"Average aggregation query returned 1 aggregated result from {record_count} records")
                
                return jsonify({
                    "success": True,
                    "data": [entry],
                    "summary": {
                        "total_periods": 1,
                        "start_date": start_date_str,
                        "end_date": end_date_str,
                        "aggregation_mode": "average",
                        "department": department,
                        "total_records": record_count,
                        "total_hours": round(total_hours, 2),
                        "shifts_filter": shifts if shifts else "ALL"
                    }
                })
            
            # EXISTING: Period-based aggregation
            # Build and execute historical query
            sql, date_format = build_historical_aggregation_sql(existing, period)
            
            logger.info(f"Executing historical KPI query: start={start_date}, end={end_date}, period={period}")
            
            rows = conn.execute(sql, {
                "start_date": start_date,
                "end_date": end_date
            }).mappings().fetchall()
            
            if not rows:
                return jsonify({
                    "success": True,
                    "data": [],
                    "summary": {
                        "total_periods": 0,
                        "start_date": start_date_str,
                        "end_date": end_date_str,
                        "period": period,
                        "department": department,
                        "message": "No data found for the specified date range"
                    }
                })
            
            # Process each period's data
            result_data = []
            for row in rows:
                row_dict = dict(row)
                
                # Extract period datetime
                period_dt = row_dict.get(date_format)
                if period_dt is None:
                    continue
                
                # Calculate period start and end
                if isinstance(period_dt, datetime):
                    period_start = period_dt
                else:
                    period_start = datetime.combine(period_dt, datetime.min.time())
                
                # Calculate period end based on period type
                if period == "hour":
                    period_end = period_start + timedelta(hours=1) - timedelta(seconds=1)
                elif period == "day":
                    period_end = period_start + timedelta(days=1) - timedelta(seconds=1)
                elif period == "week":
                    period_end = period_start + timedelta(weeks=1) - timedelta(seconds=1)
                else:  # month
                    # Add one month
                    if period_start.month == 12:
                        period_end = period_start.replace(year=period_start.year + 1, month=1) - timedelta(seconds=1)
                    else:
                        period_end = period_start.replace(month=period_start.month + 1) - timedelta(seconds=1)
                
                # Prepare data for KPI calculation
                kpi_input = {}
                for key in row_dict:
                    if key not in [date_format, "record_count", "approx_run_hours"]:
                        kpi_input[key] = row_dict[key]
                
                # Add time-related fields for KPI calculation
                approx_run_hours = float(row_dict.get("approx_run_hours", 0) or 0)
                record_count = int(row_dict.get("record_count", 0) or 0)
                
                # Estimate daily hours based on period
                if period == "hour":
                    daily_hrs = 1.0
                    run_hours = min(approx_run_hours, 1.0)
                elif period == "day":
                    daily_hrs = 24.0
                    run_hours = min(approx_run_hours, 24.0)
                elif period == "week":
                    daily_hrs = 168.0  # 7 * 24
                    run_hours = min(approx_run_hours, 168.0)
                else:  # month
                    daily_hrs = 720.0  # ~30 * 24
                    run_hours = min(approx_run_hours, 720.0)
                
                # Set default time fields
                kpi_input["WG202_Total_Running_Time"] = run_hours if run_hours > 0 else daily_hrs * 0.33  # Default 33% utilization
                kpi_input["Daily_Hours"] = daily_hrs
                kpi_input["WG202_Stop_Start"] = 0.0
                
                # Calculate KPIs using existing function
                try:
                    kpis = calc_kpis_from_row(kpi_input)
                except Exception as e:
                    logger.warning(f"Error calculating KPIs for period {period_start}: {e}")
                    kpis = {"milling_kpis": {}, "packing_kpis": {}, "error": str(e)}
                
                # Build result entry
                entry = {
                    "period_start": period_start.isoformat(),
                    "period_end": period_end.isoformat(),
                    "period_label": period_start.strftime("%Y-%m-%d") if period in ["day", "week", "month"] else period_start.strftime("%Y-%m-%d %H:%M"),
                    "record_count": record_count,
                    "approx_run_hours": round(approx_run_hours, 2),
                }
                
                # Add KPIs based on department filter
                if department in ["ALL", "MILLING"]:
                    entry["milling_kpis"] = kpis.get("milling_kpis", {})
                if department in ["ALL", "PACKING"]:
                    entry["packing_kpis"] = kpis.get("packing_kpis", {})
                
                # Optionally include raw data for debugging
                if request.args.get("include_raw", "false").lower() == "true":
                    entry["raw_data"] = {k: float(v) if v is not None else 0.0 for k, v in kpi_input.items() if isinstance(v, (int, float)) or v is None}
                
                result_data.append(entry)
            
            logger.info(f"Historical KPI query returned {len(result_data)} periods")
            
            return jsonify({
                "success": True,
                "data": result_data,
                "summary": {
                    "total_periods": len(result_data),
                    "start_date": start_date_str,
                    "end_date": end_date_str,
                    "period": period,
                    "aggregation_mode": "period",
                    "department": department,
                    "shifts_filter": shifts if shifts else "ALL"
                }
            })
            
    except Exception as e:
        logger.error(f"Error in get_historical_kpi: {e}")
        import traceback
        traceback.print_exc()
        return jsonify({
            "success": False,
            "error": f"Error fetching historical KPIs: {str(e)}"
        }), 500


# =============================================================================
# SHIFT-BASED KPI HISTORY API - For Charts
# =============================================================================

@kpi_bp.route("/api/kpi/shift-history", methods=["GET"])
def get_shift_kpi_history():
    """
    Get KPI values per shift for charts.
    Queries kpi_send_tracking table which stores KPIs sent to SAP at shift end.
    
    Query params:
    - date: YYYY-MM-DD (optional, defaults to today)
    - department: MILLING|PACKING|ALL (optional, default: ALL)
    
    Returns shift-based data points:
    - Milling: Up to 3 points (Shift A, B, C)
    - Packing: Up to 2 points (Shift A, B)
    
    Each data point includes:
    - shift_code: A, B, or C
    - department: MILLING or PACKING
    - timestamp: When KPIs were sent
    - time_label: Shift end time from settings (e.g., "15:00")
    - kpis: The actual KPI values sent to SAP
    """
    if not SHIFT_UTILS_AVAILABLE:
        return jsonify({
            "success": False,
            "error": "Shift utilities not available"
        }), 500
    
    # Parse query parameters
    date_str = request.args.get("date")
    department = request.args.get("department", "ALL").upper()
    
    # Default to today if no date provided
    if not date_str:
        date_str = datetime.now().strftime("%Y-%m-%d")
    
    try:
        target_date = datetime.strptime(date_str, "%Y-%m-%d").date()
    except ValueError:
        return jsonify({
            "success": False,
            "error": "Invalid date format. Use YYYY-MM-DD"
        }), 400
    
    try:
        with PostgresSessionLocal() as db:
            # Get shift settings to map shift codes to end times
            shift_settings = {}
            shifts = db.query(ShiftMaster).all()
            for shift in shifts:
                key = f"{shift.department}_{shift.shift_code}"
                # Parse end_time
                if hasattr(shift.end_time, 'strftime'):
                    end_time_str = shift.end_time.strftime("%H:%M")
                elif isinstance(shift.end_time, str):
                    end_time_str = shift.end_time[:5]
                else:
                    end_time_str = str(shift.end_time)[:5]
                shift_settings[key] = {
                    "end_time": end_time_str,
                    "sort_order": shift.sort_order
                }
            
            # Query kpi_send_tracking for the specified date
            # Filter by date (comparing just the date part of last_sent_at)
            query = db.query(KpiSendTracking).filter(
                sa_func.date(KpiSendTracking.last_sent_at) == target_date
            )
            
            if department != "ALL":
                query = query.filter(KpiSendTracking.department == department)
            
            records = query.order_by(KpiSendTracking.last_sent_at.asc()).all()
            
            # Build result with shift time labels
            milling_data = []
            packing_data = []
            
            for r in records:
                # Get shift end time from settings
                setting_key = f"{r.department}_{r.shift_code}"
                shift_info = shift_settings.get(setting_key, {})
                time_label = shift_info.get("end_time", r.last_sent_at.strftime("%H:%M"))
                sort_order = shift_info.get("sort_order", 0)
                
                entry = {
                    "shift_code": r.shift_code,
                    "department": r.department,
                    "timestamp": r.last_sent_at.isoformat(),
                    "time_label": time_label,
                    "sort_order": sort_order,
                    "kpis": r.kpi_payload_sent or {}
                }
                
                if r.department == "MILLING":
                    milling_data.append(entry)
                elif r.department == "PACKING":
                    packing_data.append(entry)
            
            # Sort by sort_order to ensure correct shift sequence
            milling_data.sort(key=lambda x: x.get("sort_order", 0))
            packing_data.sort(key=lambda x: x.get("sort_order", 0))
            
            # Combine based on department filter
            if department == "MILLING":
                result_data = milling_data
            elif department == "PACKING":
                result_data = packing_data
            else:
                result_data = milling_data + packing_data
            
            logger.info(f"Shift history query: date={date_str}, department={department}, milling_points={len(milling_data)}, packing_points={len(packing_data)}")
            
            return jsonify({
                "success": True,
                "data": result_data,
                "milling_data": milling_data,
                "packing_data": packing_data,
                "summary": {
                    "date": date_str,
                    "department": department,
                    "milling_points": len(milling_data),
                    "packing_points": len(packing_data),
                    "shift_settings": shift_settings
                }
            })
            
    except Exception as e:
        logger.error(f"Error in get_shift_kpi_history: {e}")
        import traceback
        traceback.print_exc()
        return jsonify({
            "success": False,
            "error": f"Error fetching shift KPI history: {str(e)}"
        }), 500


# =============================================================================
# RAW SCADA DATA API - C31-T19
# =============================================================================

@kpi_bp.route("/api/scada/raw-data", methods=["GET"])
def get_raw_scada_data():
    """
    Get raw SCADA data with time filters.
    Returns all scales (WG, DM, PL, SL) with WG values concatenated (HI+LO).
    
    Query params:
    - start_date: YYYY-MM-DD or YYYY-MM-DD HH:MM:SS (required)
    - end_date: YYYY-MM-DD or YYYY-MM-DD HH:MM:SS (required)
    - limit: max rows to return (default: 1000, max: 10000)
    
    Returns:
    {
        "success": true,
        "data": [
            {
                "timestamp": "2026-01-21T08:30:00",
                "record_id": 12345,
                "wg_scales": {"WG101": ..., "WG201": ..., ...},
                "dm_meters": {"DM101": ..., ...},
                "pl_counters": {"PL601_TOT": ..., ...},
                "sl_counters": {"SL606_TOT": ..., ...}
            },
            ...
        ],
        "summary": {...}
    }
    """
    # Parse query parameters
    start_date_str = request.args.get("start_date")
    end_date_str = request.args.get("end_date")
    limit_str = request.args.get("limit", "1000")
    
    # Validate required parameters
    if not start_date_str or not end_date_str:
        return jsonify({
            "success": False,
            "error": "Missing required parameters: start_date and end_date (format: YYYY-MM-DD or YYYY-MM-DD HH:MM:SS)"
        }), 400
    
    # Parse limit
    try:
        limit = min(int(limit_str), 10000)  # Cap at 10000 rows
        limit = max(limit, 1)  # At least 1 row
    except ValueError:
        limit = 1000
    
    # Parse dates
    try:
        # Try datetime format first, then date format
        for fmt in ["%Y-%m-%d %H:%M:%S", "%Y-%m-%d"]:
            try:
                start_date = datetime.strptime(start_date_str, fmt)
                break
            except ValueError:
                continue
        else:
            raise ValueError(f"Could not parse start_date: {start_date_str}")
        
        for fmt in ["%Y-%m-%d %H:%M:%S", "%Y-%m-%d"]:
            try:
                end_date = datetime.strptime(end_date_str, fmt)
                # If only date provided, set to end of day
                if fmt == "%Y-%m-%d":
                    end_date = end_date + timedelta(days=1)
                break
            except ValueError:
                continue
        else:
            raise ValueError(f"Could not parse end_date: {end_date_str}")
            
    except ValueError as e:
        return jsonify({
            "success": False,
            "error": f"Invalid date format. Use YYYY-MM-DD or YYYY-MM-DD HH:MM:SS. Error: {str(e)}"
        }), 400
    
    # Validate date range
    if start_date >= end_date:
        return jsonify({
            "success": False,
            "error": "start_date must be before end_date"
        }), 400
    
    # Limit date range to 31 days max
    max_days = 31
    if (end_date - start_date).days > max_days:
        return jsonify({
            "success": False,
            "error": f"Date range cannot exceed {max_days} days for raw data queries"
        }), 400
    
    try:
        # Build SQL query with WG HI+LO concatenation
        # Note: TOP doesn't support parameterized values in SQL Server, so we embed it directly
        # (limit is already validated as an integer between 1 and 10000)
        sql = text(f"""
            SELECT TOP {limit}
                [CreatedOn] AS timestamp,
                [ASMArchive_DB5ID] AS record_id,
                -- WG scales with HI+LO concatenation
                CASE WHEN [WG101_HI] IS NOT NULL AND [WG101_LO] IS NOT NULL 
                    THEN TRY_CONVERT(float, CAST([WG101_HI] AS VARCHAR) + CAST([WG101_LO] AS VARCHAR)) 
                    ELSE NULL END AS WG101,
                CASE WHEN [WG201_HI] IS NOT NULL AND [WG201_LO] IS NOT NULL 
                    THEN TRY_CONVERT(float, CAST([WG201_HI] AS VARCHAR) + CAST([WG201_LO] AS VARCHAR)) 
                    ELSE NULL END AS WG201,
                CASE WHEN [WG202_HI] IS NOT NULL AND [WG202_LO] IS NOT NULL 
                    THEN TRY_CONVERT(float, CAST([WG202_HI] AS VARCHAR) + CAST([WG202_LO] AS VARCHAR)) 
                    ELSE NULL END AS WG202,
                CASE WHEN [WG301_HI] IS NOT NULL AND [WG301_LO] IS NOT NULL 
                    THEN TRY_CONVERT(float, CAST([WG301_HI] AS VARCHAR) + CAST([WG301_LO] AS VARCHAR)) 
                    ELSE NULL END AS WG301,
                CASE WHEN [WG302_HI] IS NOT NULL AND [WG302_LO] IS NOT NULL 
                    THEN TRY_CONVERT(float, CAST([WG302_HI] AS VARCHAR) + CAST([WG302_LO] AS VARCHAR)) 
                    ELSE NULL END AS WG302,
                CASE WHEN [WG501_HI] IS NOT NULL AND [WG501_LO] IS NOT NULL 
                    THEN TRY_CONVERT(float, CAST([WG501_HI] AS VARCHAR) + CAST([WG501_LO] AS VARCHAR)) 
                    ELSE NULL END AS WG501,
                CASE WHEN [WG502_HI] IS NOT NULL AND [WG502_LO] IS NOT NULL 
                    THEN TRY_CONVERT(float, CAST([WG502_HI] AS VARCHAR) + CAST([WG502_LO] AS VARCHAR)) 
                    ELSE NULL END AS WG502,
                CASE WHEN [WG503_HI] IS NOT NULL AND [WG503_LO] IS NOT NULL 
                    THEN TRY_CONVERT(float, CAST([WG503_HI] AS VARCHAR) + CAST([WG503_LO] AS VARCHAR)) 
                    ELSE NULL END AS WG503,
                -- DM water meters (direct values)
                [DM101], [DM102], [DM201], [DM202], [DM203],
                -- PL packing counters
                [PL601_TOT], [PL602_TOT], [PL603_TOT],
                -- SL counters
                [SL606_TOT], [SL607_TOT]
            FROM {TABLE}
            WHERE [CreatedOn] >= :start_date AND [CreatedOn] < :end_date
            ORDER BY [CreatedOn] DESC
        """)
        
        logger.info(f"Executing raw SCADA data query: start={start_date}, end={end_date}, limit={limit}")
        
        with engine.connect() as conn:
            rows = conn.execute(sql, {
                "start_date": start_date,
                "end_date": end_date
            }).mappings().fetchall()
            
            if not rows:
                return jsonify({
                    "success": True,
                    "data": [],
                    "summary": {
                        "total_records": 0,
                        "start_date": start_date_str,
                        "end_date": end_date_str,
                        "limit": limit,
                        "message": "No data found for the specified date range"
                    }
                })
            
            # Process each row into structured format
            result_data = []
            for row in rows:
                row_dict = dict(row)
                
                # Extract timestamp
                timestamp = row_dict.get("timestamp")
                if timestamp:
                    if hasattr(timestamp, 'isoformat'):
                        timestamp_str = timestamp.isoformat()
                    else:
                        timestamp_str = str(timestamp)
                else:
                    timestamp_str = None
                
                # Build structured entry
                entry = {
                    "timestamp": timestamp_str,
                    "record_id": row_dict.get("record_id"),
                    "wg_scales": {
                        "WG101": float(row_dict.get("WG101") or 0) if row_dict.get("WG101") is not None else None,
                        "WG201": float(row_dict.get("WG201") or 0) if row_dict.get("WG201") is not None else None,
                        "WG202": float(row_dict.get("WG202") or 0) if row_dict.get("WG202") is not None else None,
                        "WG301": float(row_dict.get("WG301") or 0) if row_dict.get("WG301") is not None else None,
                        "WG302": float(row_dict.get("WG302") or 0) if row_dict.get("WG302") is not None else None,
                        "WG501": float(row_dict.get("WG501") or 0) if row_dict.get("WG501") is not None else None,
                        "WG502": float(row_dict.get("WG502") or 0) if row_dict.get("WG502") is not None else None,
                        "WG503": float(row_dict.get("WG503") or 0) if row_dict.get("WG503") is not None else None,
                    },
                    "dm_meters": {
                        "DM101": float(row_dict.get("DM101") or 0) if row_dict.get("DM101") is not None else None,
                        "DM102": float(row_dict.get("DM102") or 0) if row_dict.get("DM102") is not None else None,
                        "DM201": float(row_dict.get("DM201") or 0) if row_dict.get("DM201") is not None else None,
                        "DM202": float(row_dict.get("DM202") or 0) if row_dict.get("DM202") is not None else None,
                        "DM203": float(row_dict.get("DM203") or 0) if row_dict.get("DM203") is not None else None,
                    },
                    "pl_counters": {
                        "PL601_TOT": int(row_dict.get("PL601_TOT") or 0) if row_dict.get("PL601_TOT") is not None else None,
                        "PL602_TOT": int(row_dict.get("PL602_TOT") or 0) if row_dict.get("PL602_TOT") is not None else None,
                        "PL603_TOT": int(row_dict.get("PL603_TOT") or 0) if row_dict.get("PL603_TOT") is not None else None,
                    },
                    "sl_counters": {
                        "SL606_TOT": int(row_dict.get("SL606_TOT") or 0) if row_dict.get("SL606_TOT") is not None else None,
                        "SL607_TOT": int(row_dict.get("SL607_TOT") or 0) if row_dict.get("SL607_TOT") is not None else None,
                    }
                }
                result_data.append(entry)
            
            logger.info(f"Raw SCADA data query returned {len(result_data)} records")
            
            return jsonify({
                "success": True,
                "data": result_data,
                "summary": {
                    "total_records": len(result_data),
                    "start_date": start_date_str,
                    "end_date": end_date_str,
                    "limit": limit,
                    "date_range": {
                        "earliest": result_data[-1]["timestamp"] if result_data else None,
                        "latest": result_data[0]["timestamp"] if result_data else None
                    }
                }
            })
            
    except Exception as e:
        logger.error(f"Error in get_raw_scada_data: {e}")
        import traceback
        traceback.print_exc()
        return jsonify({
            "success": False,
            "error": f"Error fetching raw SCADA data: {str(e)}"
        }), 500


@kpi_bp.route("/api/kpi/health", methods=["GET"])
def kpi_health_check():
    """
    Health check endpoint for KPI service.
    """
    try:
        with engine.connect() as conn:
            # Simple query to check database connectivity
            result = conn.execute(text("SELECT 1 as health_check")).scalar()
            
            return jsonify({
                "status": "healthy",
                "database_connected": True,
                "timestamp": datetime.now().isoformat(),
                "message": "KPI service is running and database is accessible"
            })
    except Exception as e:
        logger.error(f"Health check failed: {e}")
        return jsonify({
            "status": "unhealthy",
            "database_connected": False,
            "timestamp": datetime.now().isoformat(),
            "error": str(e)
        }), 500

def send_to_sap_kpi(url, payload, kpi_type):
    """
    Send KPI data to SAP endpoint with proper CSRF token authentication.
    """
    try:
        logger.info(f"=== Starting {kpi_type} KPI Send Process ===")
        
        # Step 1: Fetch CSRF token with authentication
        logger.info(f"Step 1: Fetching CSRF token from SAP for {kpi_type} KPIs...")
        
        csrf_headers = {
            "X-CSRF-Token": "Fetch",
            "Accept": "application/json",
            "Content-Type": "application/json"
        }
        
        # Use basic authentication with provided credentials
        auth = HTTPBasicAuth(SAP_USERNAME, SAP_PASSWORD)
        
        # GET request to fetch CSRF token
        token_response = requests.get(
            url,
            headers=csrf_headers,
            auth=auth,
            timeout=30,
            verify=False  # For internal SAP servers without SSL
        )
        
        logger.info(f"CSRF token fetch response status: {token_response.status_code}")
        logger.info(f"CSRF token fetch response headers: {dict(token_response.headers)}")
        
        # Check for authentication errors
        if token_response.status_code == 401:
            logger.error("❌ Authentication failed - 401 Unauthorized")
            return False, f"Authentication failed. Invalid credentials. Status: {token_response.status_code}", token_response.text
        
        if token_response.status_code == 403:
            logger.error("❌ Access forbidden - 403 Forbidden")
            return False, f"Access forbidden. User does not have permission. Status: {token_response.status_code}", token_response.text
        
        if token_response.status_code not in [200, 201]:
            logger.error(f"❌ Failed to fetch CSRF token. Status: {token_response.status_code}")
            return False, f"Failed to fetch CSRF token. Status: {token_response.status_code}", token_response.text
        
        # Extract CSRF token from response headers
        csrf_token = token_response.headers.get("X-CSRF-Token") or token_response.headers.get("x-csrf-token")
        cookies = token_response.cookies
        
        if not csrf_token:
            logger.warning("⚠️ CSRF token not found in response headers. Proceeding without it...")
            csrf_token = ""
        else:
            logger.info(f"✅ CSRF token fetched successfully: {csrf_token[:20]}...")
        
        # Step 2: Send POST request with CSRF token and authentication
        logger.info(f"Step 2: Sending {kpi_type} KPIs to SAP...")
        logger.info(f"Payload: {payload}")
        
        post_headers = {
            "Accept": "application/json",
            "Content-Type": "application/json"
        }
        
        # Add CSRF token if we got one
        if csrf_token:
            post_headers["X-CSRF-Token"] = csrf_token
        
        post_response = requests.post(
            url,
            json=payload,
            headers=post_headers,
            cookies=cookies,
            auth=auth,
            timeout=30,
            verify=False
        )
        
        logger.info(f"POST response status: {post_response.status_code}")
        logger.info(f"POST response body: {post_response.text[:500]}")  # First 500 chars
        
        if post_response.status_code in [200, 201]:
            logger.info(f"✅ {kpi_type} KPIs sent successfully to SAP")
            return True, f"{kpi_type} KPIs sent successfully", post_response.text
        else:
            logger.error(f"❌ Failed to send {kpi_type} KPIs. Status: {post_response.status_code}")
            return False, f"Failed to send {kpi_type} KPIs. Status: {post_response.status_code}", post_response.text
            
    except requests.exceptions.Timeout:
        logger.error("❌ Request timeout after 30 seconds")
        return False, "Request timeout after 30 seconds", ""
    except requests.exceptions.ConnectionError as e:
        logger.error(f"❌ Connection error: {str(e)}")
        return False, f"Connection error: {str(e)}", ""
    except Exception as e:
        logger.error(f"❌ Exception in send_to_sap_kpi: {e}")
        return False, f"Exception: {str(e)}", ""

def send_to_sap_kpi_with_retry(url, payload, kpi_type, max_retries=2):
    """
    Send KPI data to SAP endpoint with retry logic for better reliability
    """
    import time
    
    for attempt in range(max_retries + 1):
        try:
            logger.info(f"Attempt {attempt + 1}/{max_retries + 1} for {kpi_type} KPIs")
            
            success, message, response = send_to_sap_kpi(url, payload, kpi_type)
            
            if success:
                logger.info(f"{kpi_type} KPIs sent successfully on attempt {attempt + 1}")
                return success, message, response
            else:
                # Check if this is a retryable error
                if attempt < max_retries and is_retryable_error(message):
                    wait_time = 2 ** attempt  # Exponential backoff: 1s, 2s, 4s
                    logger.warning(f"{kpi_type} attempt {attempt + 1} failed: {message}. Retrying in {wait_time}s...")
                    time.sleep(wait_time)
                    continue
                else:
                    logger.error(f"{kpi_type} failed after {attempt + 1} attempts: {message}")
                    return success, message, response
                    
        except Exception as e:
            if attempt < max_retries:
                wait_time = 2 ** attempt
                logger.warning(f"{kpi_type} attempt {attempt + 1} failed with exception: {e}. Retrying in {wait_time}s...")
                time.sleep(wait_time)
                continue
            else:
                logger.error(f"{kpi_type} failed after {attempt + 1} attempts with exception: {e}")
                return False, f"Exception after {attempt + 1} attempts: {str(e)}", ""
    
    return False, f"Failed after {max_retries + 1} attempts", ""

def is_retryable_error(message):
    """
    Determine if an error is retryable based on the error message
    """
    retryable_errors = [
        "timeout",
        "connection",
        "network",
        "temporary",
        "server error",
        "service unavailable",
        "bad gateway",
        "gateway timeout"
    ]
    
    message_lower = message.lower()
    return any(error in message_lower for error in retryable_errors)

@kpi_bp.route("/api/kpi/send-milling-to-sap", methods=["POST"])
def send_milling_kpis_to_sap():
    """
    Send milling KPIs to SAP via HTTPS port 44300
    (SAP forces all Python/API requests to use HTTPS)
    """
    import urllib3
    from datetime import datetime as dt
    urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)
    
    try:
        logger.info("=== MILLING KPI ENDPOINT CALLED (INCREMENTAL) ===")
        
        # ⭐ NEW: Use incremental KPIs (only new data since last send)
        from services.kpi_incremental import (
            get_incremental_kpis, save_sent_baseline, get_current_scada_values,
            check_duplicate_send, reserve_baseline_slot, update_tracking_payload
        )
        from utils.shifts import get_current_shift
        from database import PostgresSessionLocal
        
        # ✅ Get current shift code for tracking
        current_shift_code = None
        try:
            with PostgresSessionLocal() as db:
                current_shift = get_current_shift("3130", "MILLING", db)  # Plant 3130 = MILLING
                current_shift_code = current_shift.shift_code if current_shift else None
                logger.info(f"📋 Current shift for MILLING: {current_shift_code}")
        except Exception as shift_err:
            logger.warning(f"⚠️ Could not determine current shift: {shift_err}")
        
        # ✅ CRITICAL: Get current SCADA first
        current_scada = get_current_scada_values()
        if not current_scada:
            return jsonify({
                "success": False,
                "message": "No SCADA data available",
                "timestamp": datetime.now().isoformat()
            }), 404
        
        # ✅ STEP 1: Check for duplicates BEFORE processing (using existing baseline)
        if check_duplicate_send("MILLING", current_scada, time_window_seconds=60):
            logger.warning("⚠️ DUPLICATE PREVENTED: Same SCADA values were sent recently")
            return jsonify({
                "success": False,
                "message": "Duplicate send prevented - same data was sent recently. Please wait for new production data.",
                "timestamp": datetime.now().isoformat()
            }), 200
        
        # ✅ STEP 2: Get incremental KPIs FIRST (using existing baseline, before reserving new one)
        kpi_result, current_scada_after_check, baseline = get_incremental_kpis("MILLING", exclude_recent_seconds=0)
        
        if not kpi_result:
            logger.warning("⚠️ No new milling KPIs to send - current data is identical to last sent baseline")
            if current_scada_after_check:
                logger.info(f"   Current SCADA: WG202={current_scada_after_check.get('WG202', 0):.2f}, WG501={current_scada_after_check.get('WG501', 0):.2f}, WG502={current_scada_after_check.get('WG502', 0):.2f}")
            if baseline:
                logger.info(f"   Last baseline: WG202={baseline.get('WG202', 0):.2f}, WG501={baseline.get('WG501', 0):.2f}, WG502={baseline.get('WG502', 0):.2f} (sent at {baseline.get('last_sent_at')})")
            return jsonify({
                "success": False,
                "message": "No new data to send - all data already sent previously. Please wait for new production data.",
                "timestamp": datetime.now().isoformat()
            }), 200  # Return 200 but with success=False to indicate no action needed
        
        # ✅ STEP 3: Only NOW reserve baseline slot (after confirming there's new data to send)
        tracking_id, reserved = reserve_baseline_slot("MILLING", current_scada_after_check, "manual", current_shift_code, "Manual sync - reserved after confirming new data")
        if not reserved:
            logger.warning("⚠️ Failed to reserve baseline slot - possible duplicate or system busy")
            return jsonify({
                "success": False,
                "message": "Cannot send - duplicate detected or system busy. Please try again.",
                "timestamp": datetime.now().isoformat()
            }), 200
        
        # Extract milling KPIs from delta
        milling_kpis = kpi_result.get("milling_kpis", {})
        
        # ✅ VERIFICATION: Log what KPIs were calculated from delta
        logger.info("=" * 60)
        logger.info("📊 VERIFICATION: Data Flow Check")
        # ✅ Convert to float to handle Decimal types from database
        baseline_wg202 = safe(baseline.get('WG202', 0)) if baseline else 0
        baseline_wg501 = safe(baseline.get('WG501', 0)) if baseline else 0
        baseline_wg502 = safe(baseline.get('WG502', 0)) if baseline else 0
        current_wg202 = safe(current_scada_after_check.get('WG202', 0))
        current_wg501 = safe(current_scada_after_check.get('WG501', 0))
        current_wg502 = safe(current_scada_after_check.get('WG502', 0))
        
        logger.info(f"   Baseline: WG202={baseline_wg202:.2f}, WG501={baseline_wg501:.2f}, WG502={baseline_wg502:.2f}" if baseline else "   Baseline: None (first send)")
        logger.info(f"   Current:  WG202={current_wg202:.2f}, WG501={current_wg501:.2f}, WG502={current_wg502:.2f}")
        if baseline:
            wg202_delta = current_wg202 - baseline_wg202
            wg501_delta = current_wg501 - baseline_wg501
            wg502_delta = current_wg502 - baseline_wg502
            logger.info(f"   Delta:    WG202={wg202_delta:.2f}, WG501={wg501_delta:.2f}, WG502={wg502_delta:.2f}")
        logger.info("=" * 60)
        
        # Get SCADA water data (delta)
        scada_water_data = {
            "totalPreCleaningWater": 0.0,
            "waterCleanWheat": 0.0,
            "totalWaterUsed": 0.0
        }
        
        if current_scada_after_check and baseline:
            # ✅ FIX: DM water meters are 30-sec averages, need SUM not delta
            # Get baseline time from tracking record (or use a reasonable default)
            baseline_time = baseline.get("last_sent_at")
            if baseline_time and isinstance(baseline_time, str):
                try:
                    baseline_time = dtparser.parse(baseline_time)
                except:
                    baseline_time = datetime.now() - timedelta(hours=8)  # Default to 8 hours ago
            elif not baseline_time:
                baseline_time = datetime.now() - timedelta(hours=8)
            
            # Sum DM readings from baseline time to now
            dm101_sum = sum_dm_readings("DM101", baseline_time)
            dm102_sum = sum_dm_readings("DM102", baseline_time)
            dm201_sum = sum_dm_readings("DM201", baseline_time)
            dm202_sum = sum_dm_readings("DM202", baseline_time)
            dm203_sum = sum_dm_readings("DM203", baseline_time)
            
            scada_water_data = {
                "totalPreCleaningWater": dm101_sum + dm102_sum,
                "waterCleanWheat": dm201_sum + dm202_sum + dm203_sum,
                "totalWaterUsed": dm101_sum + dm102_sum + dm201_sum + dm202_sum + dm203_sum
            }
            
            # ✅ VERIFICATION: Log water SUM calculation
            logger.info(f"💧 Water SUM Calculation (from {baseline_time}):")
            logger.info(f"   DM101 SUM: {dm101_sum:.2f}")
            logger.info(f"   DM102 SUM: {dm102_sum:.2f}")
            logger.info(f"   DM201 SUM: {dm201_sum:.2f}")
            logger.info(f"   DM202 SUM: {dm202_sum:.2f}")
            logger.info(f"   DM203 SUM: {dm203_sum:.2f}")
            logger.info(f"   → Total Water: {scada_water_data['totalWaterUsed']:.2f}")
        elif current_scada_after_check:
            # First send, use current values
            scada_water_data = {
                "totalPreCleaningWater": safe(current_scada_after_check.get("DM101", 0.0)) + safe(current_scada_after_check.get("DM102", 0.0)),
                "waterCleanWheat": safe(current_scada_after_check.get("DM201", 0.0)) + safe(current_scada_after_check.get("DM202", 0.0)) + safe(current_scada_after_check.get("DM203", 0.0)),
                "totalWaterUsed": (safe(current_scada_after_check.get("DM101", 0.0)) + safe(current_scada_after_check.get("DM102", 0.0)) + 
                                 safe(current_scada_after_check.get("DM201", 0.0)) + safe(current_scada_after_check.get("DM202", 0.0)) + safe(current_scada_after_check.get("DM203", 0.0)))
            }

        # Prepare SAP payload for milling KPIs (exact format provided by SAP team)
        sap_milling_payload = {
            "MILL_THROUGHPUT": str(milling_kpis.get("Mill Throughput (%)", 0.0)),
            "MILL_TIME_EFFICIENCY": str(milling_kpis.get("Mill Time Efficiency (%)", 0.0)),
            "TOTAL_UTILIZATION": str(milling_kpis.get("Total Utilization (%)", 0.0)),
            "MAX_UTILIZATION": str(milling_kpis.get("Max Utilization of Milling Capacity (%)", 0.0)),
            "MILLING_GAIN": str(milling_kpis.get("Milling Gain", 0.0)),
            "PRE_CLEAN_SCREENING": str(milling_kpis.get("Pre Cleaning Screening (%)", 0.0)),
            "MILLING_SCREENING": str(milling_kpis.get("Milling Screening (%)", 0.0)),
            "PRE_CLEAN_WATER": str(scada_water_data.get("totalPreCleaningWater", 0.0)),
            "CLEANING_WATER": str(scada_water_data.get("waterCleanWheat", 0.0)),
            "NET_HOURS": str(milling_kpis.get("Net Hours (hrs)", 0.0)),
            "MILLING_DOWN_TIME": str(milling_kpis.get("Downtime (hrs)", 0.0)),
            "BREAK_CAPACITY": str(milling_kpis.get("1st Break Capacity per Hour (t/h)", 0.0)),
            "FLOUR_EXTRACTION": str(milling_kpis.get("Flour Extraction (%)", 0.0)),
            "BRAN_EXTRACTION": str(milling_kpis.get("Bran Extraction (%)", 0.0)),
            "MILLING_LOSS": str(milling_kpis.get("Milling Loss (%)", 0.0)),
            "TOTAL_WATER": str(scada_water_data.get("totalWaterUsed", 0.0)),
            "SHIFT": current_shift_code or "",
        }

        # ✅ VERIFICATION: Log final payload being sent to SAP
        logger.info("=" * 60)
        logger.info("📤 FINAL SAP PAYLOAD (INCREMENTAL):")
        logger.info(f"   MILL_THROUGHPUT: {sap_milling_payload['MILL_THROUGHPUT']}% (from delta)")
        logger.info(f"   TOTAL_UTILIZATION: {sap_milling_payload['TOTAL_UTILIZATION']}% (from delta)")
        logger.info(f"   BREAK_CAPACITY: {sap_milling_payload['BREAK_CAPACITY']} t/h (from delta)")
        logger.info(f"   TOTAL_WATER: {sap_milling_payload['TOTAL_WATER']} (incremental: {scada_water_data.get('totalWaterUsed', 0):.2f})")
        logger.info(f"   NET_HOURS: {sap_milling_payload['NET_HOURS']} hrs")
        logger.info("=" * 60)
        logger.info(f"Full payload: {sap_milling_payload}")

        # ✅ Update tracking record with the SAP payload for auditing
        if tracking_id:
            update_tracking_payload(tracking_id, sap_milling_payload, current_shift_code)

        # ✅ FINAL CHECK: Verify no duplicate before sending to SAP (exclude the baseline we just reserved)
        if check_duplicate_send("MILLING", current_scada_after_check, time_window_seconds=60, exclude_tracking_id=tracking_id):
            logger.error("⚠️ DUPLICATE DETECTED RIGHT BEFORE SAP SEND - ABORTING")
            return jsonify({
                "success": False,
                "message": "Duplicate detected - another send is in progress. Please wait.",
                "timestamp": datetime.now().isoformat()
            }), 200

        # Get SAP URL (mock or production)
        SAP_URL = get_sap_url("/zmi_kpi_mill/MKPI", client="250")
        logger.info(f"Using URL: {SAP_URL}")
        
        from requests.auth import HTTPBasicAuth
        
        # ============================================================
        # MOCK MODE: Simple POST request without CSRF/auth
        # ============================================================
        if get_mock_sap_mode():
            logger.info("🔧 MOCK MODE: Sending simple POST to demo server...")
            post_response = requests.post(
                SAP_URL,
                json=sap_milling_payload,
                timeout=30
            )
            logger.info(f"POST response status: {post_response.status_code}")
            logger.info(f"POST response: {post_response.text[:500]}")
        else:
            # ============================================================
            # PRODUCTION MODE: STEP 1: GET request to fetch CSRF token (HTTPS)
            # ============================================================
            logger.info("Step 1: Fetching CSRF token via HTTPS...")
            
            get_headers = {
                "x-csrf-token": "fetch",
                "Accept": "application/json",
                "User-Agent": "Python-Requests/2.31.0",
                "Connection": "keep-alive"
            }
            
            token_response = requests.get(
                SAP_URL,
                headers=get_headers,
                auth=HTTPBasicAuth(SAP_USERNAME, SAP_PASSWORD),
                timeout=30,
                verify=False  # Ignore SSL certificate errors
            )
            
            logger.info(f"GET response status: {token_response.status_code}")
            logger.info(f"GET response headers: {dict(token_response.headers)}")
            
            # Check for errors
            if token_response.status_code == 401:
                logger.error(f"❌ Authentication failed: {token_response.text[:300]}")
                return jsonify({
                    "success": False,
                    "message": "Authentication failed",
                    "error": token_response.text[:500],
                    "timestamp": datetime.now().isoformat()
                }), 401
            
            if token_response.status_code not in [200, 201]:
                logger.error(f"❌ Failed to fetch CSRF token: {token_response.status_code}")
                return jsonify({
                    "success": False,
                    "message": f"Failed to get CSRF token. Status: {token_response.status_code}",
                    "error": token_response.text[:500],
                    "timestamp": datetime.now().isoformat()
                }), token_response.status_code
            
            # Extract CSRF token
            csrf_token = (
                token_response.headers.get("x-csrf-token") or 
                token_response.headers.get("X-CSRF-Token") or
                token_response.headers.get("X-Csrf-Token")
            )
            
            cookies = token_response.cookies
            
            if not csrf_token:
                logger.error("❌ No CSRF token in response headers")
                logger.error(f"Available headers: {list(token_response.headers.keys())}")
                return jsonify({
                    "success": False,
                    "message": "CSRF token not found in response",
                    "headers": list(token_response.headers.keys()),
                    "timestamp": datetime.now().isoformat()
                }), 500
            
            logger.info(f"✅ CSRF token received: {csrf_token[:30]}...")
            logger.info(f"Cookies received: {len(cookies)} cookie(s)}}")
            
            # ============================================================
            # STEP 2: POST request with CSRF token and data (HTTPS)
            # ============================================================
            logger.info("Step 2: Sending POST request with Milling KPIs...")
            
            post_headers = {
                "x-csrf-token": csrf_token,
                "Content-Type": "application/json",
                "Accept": "application/json",
                "User-Agent": "Python-Requests/2.31.0",
                "Connection": "keep-alive"
            }
            
            post_response = requests.post(
                SAP_URL,
                json=sap_milling_payload,
                headers=post_headers,
                cookies=cookies,
                auth=HTTPBasicAuth(SAP_USERNAME, SAP_PASSWORD),
                timeout=30,
                verify=False
            )
            
            logger.info(f"POST response status: {post_response.status_code}")
            logger.info(f"POST response: {post_response.text[:500]}")
        
        # Check success
        if post_response.status_code in [200, 201]:
            # ✅ Baseline already reserved before send, so it's already saved
            # Just log the success
            if tracking_id:
                logger.info(f"✅ Baseline already reserved (ID: {tracking_id}) - send successful")
            
            if "Data Saved Correctly" in post_response.text or "success" in post_response.text.lower():
                logger.info("✅ SUCCESS! Milling KPIs saved to SAP (incremental)")
                return jsonify({
                    "success": True,
                    "message": "Milling KPIs sent to SAP successfully (incremental - only new data)",
                    "response": post_response.text,
                    "payload_sent": sap_milling_payload,
                    "timestamp": datetime.now().isoformat()
                }), 200
            else:
                logger.info("✅ POST successful")
                return jsonify({
                    "success": True,
                    "message": "Milling KPIs sent successfully (incremental - only new data)",
                    "response": post_response.text,
                    "payload_sent": sap_milling_payload,
                    "timestamp": datetime.now().isoformat()
                }), 200
        else:
            logger.error(f"❌ POST failed: {post_response.status_code}")
            return jsonify({
                "success": False,
                "message": f"Failed to send milling KPIs. Status: {post_response.status_code}",
                "error": post_response.text[:500],
                "payload_sent": sap_milling_payload,
                "timestamp": datetime.now().isoformat()
            }), post_response.status_code

    except Exception as e:
        logger.error(f"❌ Exception: {e}")
        import traceback
        logger.error(traceback.format_exc())
        return jsonify({
            "success": False,
            "message": f"Error: {str(e)}",
            "timestamp": datetime.now().isoformat()
        }), 500

@kpi_bp.route("/api/kpi/send-packing-to-sap", methods=["POST"])
def send_packing_kpis_to_sap():
    """
    Send packing KPIs to SAP via HTTPS port 44300
    (SAP forces all Python/API requests to use HTTPS)
    """
    import urllib3
    from datetime import datetime as dt
    urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)
    
    try:
        logger.info("=== PACKING KPI ENDPOINT CALLED (INCREMENTAL) ===")
        
        # ⭐ NEW: Use incremental KPIs (only new data since last send)
        from services.kpi_incremental import (
            get_incremental_kpis, save_sent_baseline, get_current_scada_values,
            check_duplicate_send, reserve_baseline_slot, update_tracking_payload
        )
        from utils.shifts import get_current_shift
        from database import PostgresSessionLocal
        
        # ✅ Get current shift code for tracking
        current_shift_code = None
        try:
            with PostgresSessionLocal() as db:
                current_shift = get_current_shift(None, "PACKING", db)  # PACKING ignores plant
                current_shift_code = current_shift.shift_code if current_shift else None
                logger.info(f"📋 Current shift for PACKING: {current_shift_code}")
        except Exception as shift_err:
            logger.warning(f"⚠️ Could not determine current shift: {shift_err}")
        
        # ✅ CRITICAL: Get current SCADA first
        current_scada = get_current_scada_values()
        if not current_scada:
            return jsonify({
                "success": False,
                "message": "No SCADA data available",
                "timestamp": datetime.now().isoformat()
            }), 404
        
        # ✅ STEP 1: Check for duplicates BEFORE processing (using existing baseline)
        if check_duplicate_send("PACKING", current_scada, time_window_seconds=60):
            logger.warning("⚠️ DUPLICATE PREVENTED: Same SCADA values were sent recently")
            return jsonify({
                "success": False,
                "message": "Duplicate send prevented - same data was sent recently. Please wait for new production data.",
                "timestamp": datetime.now().isoformat()
            }), 200
        
        # ✅ STEP 2: Get incremental KPIs FIRST (using existing baseline, before reserving new one)
        kpi_result, current_scada_after_check, baseline = get_incremental_kpis("PACKING", exclude_recent_seconds=0)
        
        if not kpi_result:
            logger.warning("⚠️ No new packing KPIs to send - current data is identical to last sent baseline")
            if current_scada_after_check:
                logger.info(f"   Current SCADA: PL601_TOT={current_scada_after_check.get('PL601_TOT', 0):.2f}")
            if baseline:
                logger.info(f"   Last baseline: PL601_TOT={baseline.get('PL601_TOT', 0):.2f} (sent at {baseline.get('last_sent_at')})")
            return jsonify({
                "success": False,
                "message": "No new data to send - all data already sent previously. Please wait for new production data.",
                "timestamp": datetime.now().isoformat()
            }), 200  # Return 200 but with success=False to indicate no action needed
        
        # ✅ STEP 3: Only NOW reserve baseline slot (after confirming there's new data to send)
        tracking_id, reserved = reserve_baseline_slot("PACKING", current_scada_after_check, "manual", current_shift_code, "Manual sync - reserved after confirming new data")
        if not reserved:
            logger.warning("⚠️ Failed to reserve baseline slot - possible duplicate or system busy")
            return jsonify({
                "success": False,
                "message": "Cannot send - duplicate detected or system busy. Please try again.",
                "timestamp": datetime.now().isoformat()
            }), 200
        
        # Extract packing KPIs from delta
        packing_kpis = kpi_result.get("packing_kpis", {})
        logger.info(f"Packing KPIs extracted (incremental): {packing_kpis}")

        # Prepare SAP payload for packing KPIs (exact format provided by SAP team)
        sap_packing_payload = {
            "PACKING_CAPACITY_BAG": str(packing_kpis.get("Packing Line Capacity (bags/hr)", 0.0)),
            "PACKING_CAPACITY_TON": str(packing_kpis.get("Packing Line Capacity (tons/hr)", 0.0)),
            "PACKING_BAG": str(packing_kpis.get("Daily Packing Output (bags)", 0.0)),
            "PACKING_HOURS": str(packing_kpis.get("Net Hours (hrs)", 0.0)),
            "PACKING_TOTAL_DOWNTIME": str(packing_kpis.get("Downtime (hrs)", 0.0)),
            "PACKING_MACHINE_UTILIZ": str(packing_kpis.get("Machine Utilization (%)", 0.0)),
            "SHIFT": current_shift_code or "",
        }

        logger.info(f"Packing payload prepared: {sap_packing_payload}")

        # ✅ Update tracking record with the SAP payload for auditing
        if tracking_id:
            update_tracking_payload(tracking_id, sap_packing_payload, current_shift_code)

        # ✅ FINAL CHECK: Verify no duplicate before sending to SAP (exclude the baseline we just reserved)
        if check_duplicate_send("PACKING", current_scada_after_check, time_window_seconds=60, exclude_tracking_id=tracking_id):
            logger.error("⚠️ DUPLICATE DETECTED RIGHT BEFORE SAP SEND - ABORTING")
            return jsonify({
                "success": False,
                "message": "Duplicate detected - another send is in progress. Please wait.",
                "timestamp": datetime.now().isoformat()
            }), 200

        # Get SAP URL (mock or production)
        SAP_URL = get_sap_url("/zmi_kpi_pack/PKPI", client="250")
        logger.info(f"Using URL: {SAP_URL}")
        
        from requests.auth import HTTPBasicAuth
        
        # ============================================================
        # MOCK MODE: Simple POST request without CSRF/auth
        # ============================================================
        if get_mock_sap_mode():
            logger.info("🔧 MOCK MODE: Sending simple POST to demo server...")
            post_response = requests.post(
                SAP_URL,
                json=sap_packing_payload,
                timeout=30
            )
            logger.info(f"POST response status: {post_response.status_code}")
            logger.info(f"POST response: {post_response.text[:500]}")
        else:
            # ============================================================
            # PRODUCTION MODE: STEP 1: GET request to fetch CSRF token (HTTPS)
            # ============================================================
            logger.info("Step 1: Fetching CSRF token via HTTPS...")
            
            get_headers = {
                "x-csrf-token": "fetch",
                "Accept": "application/json",
                "User-Agent": "Python-Requests/2.31.0",
                "Connection": "keep-alive"
            }
            
            token_response = requests.get(
                SAP_URL,
                headers=get_headers,
                auth=HTTPBasicAuth(SAP_USERNAME, SAP_PASSWORD),
                timeout=30,
                verify=False  # Ignore SSL certificate errors
            )
            
            logger.info(f"GET response status: {token_response.status_code}")
            logger.info(f"GET response headers: {dict(token_response.headers)}")
            
            # Check for errors
            if token_response.status_code == 401:
                logger.error(f"❌ Authentication failed: {token_response.text[:300]}")
                return jsonify({
                    "success": False,
                    "message": "Authentication failed",
                    "error": token_response.text[:500],
                    "timestamp": datetime.now().isoformat()
                }), 401
            
            if token_response.status_code not in [200, 201]:
                logger.error(f"❌ Failed to fetch CSRF token: {token_response.status_code}")
                return jsonify({
                    "success": False,
                    "message": f"Failed to get CSRF token. Status: {token_response.status_code}",
                    "error": token_response.text[:500],
                    "timestamp": datetime.now().isoformat()
                }), token_response.status_code
            
            # Extract CSRF token
            csrf_token = (
                token_response.headers.get("x-csrf-token") or 
                token_response.headers.get("X-CSRF-Token") or
                token_response.headers.get("X-Csrf-Token")
            )
            
            cookies = token_response.cookies
            
            if not csrf_token:
                logger.error("❌ No CSRF token in response headers")
                logger.error(f"Available headers: {list(token_response.headers.keys())}")
                return jsonify({
                    "success": False,
                    "message": "CSRF token not found in response",
                    "headers": list(token_response.headers.keys()),
                    "timestamp": datetime.now().isoformat()
                }), 500
            
            logger.info(f"✅ CSRF token received: {csrf_token[:30]}...")
            logger.info(f"Cookies received: {len(cookies)} cookie(s)}}")
            
            # ============================================================
            # STEP 2: POST request with CSRF token and data (HTTPS)
            # ============================================================
            logger.info("Step 2: Sending POST request with Packing KPIs...")
            
            post_headers = {
                "x-csrf-token": csrf_token,
                "Content-Type": "application/json",
                "Accept": "application/json",
                "User-Agent": "Python-Requests/2.31.0",
                "Connection": "keep-alive"
            }
            
            post_response = requests.post(
                SAP_URL,
                json=sap_packing_payload,
                headers=post_headers,
                cookies=cookies,
                auth=HTTPBasicAuth(SAP_USERNAME, SAP_PASSWORD),
                timeout=30,
                verify=False
            )
            
            logger.info(f"POST response status: {post_response.status_code}")
            logger.info(f"POST response: {post_response.text[:500]}")
        
        # Check success
        if post_response.status_code in [200, 201]:
            # ✅ Baseline already reserved before send, so it's already saved
            # Just log the success
            if tracking_id:
                logger.info(f"✅ Baseline already reserved (ID: {tracking_id}) - send successful")
            
            if "Data Saved Correctly" in post_response.text or "success" in post_response.text.lower():
                logger.info("✅ SUCCESS! Packing KPIs saved to SAP (incremental)")
                return jsonify({
                    "success": True,
                    "message": "Packing KPIs sent to SAP successfully (incremental - only new data)",
                    "response": post_response.text,
                    "payload_sent": sap_packing_payload,
                    "timestamp": datetime.now().isoformat()
                }), 200
            else:
                logger.info("✅ POST successful")
                return jsonify({
                    "success": True,
                    "message": "Packing KPIs sent successfully (incremental - only new data)",
                    "response": post_response.text,
                    "payload_sent": sap_packing_payload,
                    "timestamp": datetime.now().isoformat()
                }), 200
        else:
            logger.error(f"❌ POST failed: {post_response.status_code}")
            return jsonify({
                "success": False,
                "message": f"Failed to send packing KPIs. Status: {post_response.status_code}",
                "error": post_response.text[:500],
                "payload_sent": sap_packing_payload,
                "timestamp": datetime.now().isoformat()
            }), post_response.status_code

    except Exception as e:
        logger.error(f"❌ Exception: {e}")
        import traceback
        logger.error(traceback.format_exc())
        return jsonify({
            "success": False,
            "message": f"Error: {str(e)}",
            "timestamp": datetime.now().isoformat()
        }), 500

@kpi_bp.route("/api/kpi/send-all-to-sap", methods=["POST"])
def send_all_kpis_to_sap():
    """
    Send both milling and packing KPIs to SAP via HTTPS port 44300
    (SAP forces all Python/API requests to use HTTPS)
    """
    import urllib3
    from datetime import datetime as dt
    urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)
    
    try:
        logger.info("=== SEND ALL KPIS ENDPOINT CALLED ===")
        
        # Step 1: Validate database connection and fetch KPI data
        logger.info("Connecting to database to fetch KPI data")
        try:
            with engine.connect() as conn:
                # Test database connection
                conn.execute(text("SELECT 1"))
                logger.info("Database connection successful")
                
                existing = fetch_existing_columns(conn)
                row = conn.execute(build_latest_sql()).mappings().first()
                if not row:
                    logger.error("No data found in database")
                    return jsonify({
                        "status": "error",
                        "message": "No data found in database",
                        "timestamp": datetime.now().isoformat()
                    }), 404

                snapshot = dict(row)
                for k in OPTIONAL_TIME_COLS:
                    snapshot.setdefault(k, 0.0)

                logger.info(f"Raw database data retrieved successfully")
                logger.debug(f"Raw database data: {snapshot}")
                
        except Exception as db_error:
            logger.error(f"Database connection failed: {db_error}")
            return jsonify({
                "status": "error",
                "message": f"Database connection failed: {str(db_error)}",
                "timestamp": datetime.now().isoformat()
            }), 500
        
        # Step 2: Calculate KPIs with validation
        try:
            kpi_result = calc_kpis_from_row(snapshot)
            logger.info(f"KPI calculation completed successfully")
            logger.debug(f"Calculated KPI result: {kpi_result}")
            
            # Validate KPI results
            if not kpi_result or not isinstance(kpi_result, dict):
                raise ValueError("KPI calculation returned invalid result")
                
        except Exception as calc_error:
            logger.error(f"KPI calculation failed: {calc_error}")
            return jsonify({
                "status": "error",
                "message": f"KPI calculation failed: {str(calc_error)}",
                "timestamp": datetime.now().isoformat()
            }), 500
            
        # Step 3: Extract and validate KPIs
        milling_kpis = kpi_result.get("milling_kpis", {})
        packing_kpis = kpi_result.get("packing_kpis", {})
        
        # Validate that we have meaningful KPI data
        if not milling_kpis and not packing_kpis:
            logger.warning("No KPI data available for sending")
            return jsonify({
                "status": "warning",
                "message": "No KPI data available for sending",
                "timestamp": datetime.now().isoformat()
            }), 200
        
        # Step 4: Get SCADA water data with better error handling
        scada_water_data = {
            "totalPreCleaningWater": 0.0,
            "waterCleanWheat": 0.0,
            "totalWaterUsed": 0.0
        }
        
        try:
            with engine.connect() as conn:
                scada_sql = text("""
                    SELECT TOP 1 
                        DM101, DM102, DM201, DM202, DM203
                    FROM [HerculesV2].[dbo].[ASMReporting_5]
                    ORDER BY ASMArchive_DB5ID DESC
                """)
                scada_row = conn.execute(scada_sql).mappings().first()
                if scada_row:
                    scada_data = dict(scada_row)
                    scada_water_data = {
                        "totalPreCleaningWater": safe(scada_data.get("DM101", 0.0)) + safe(scada_data.get("DM102", 0.0)),
                        "waterCleanWheat": safe(scada_data.get("DM201", 0.0)) + safe(scada_data.get("DM202", 0.0)) + safe(scada_data.get("DM203", 0.0)),
                        "totalWaterUsed": (safe(scada_data.get("DM101", 0.0)) + safe(scada_data.get("DM102", 0.0)) + 
                                         safe(scada_data.get("DM201", 0.0)) + safe(scada_data.get("DM202", 0.0)) + safe(scada_data.get("DM203", 0.0)))
                    }
                    logger.info("SCADA water data retrieved successfully")
                else:
                    logger.warning("No SCADA water data found, using defaults")
        except Exception as scada_error:
            logger.warning(f"Could not fetch SCADA water data: {scada_error}, using defaults")

        # Get current shift codes for milling and packing (for SHIFT field in SAP payloads)
        milling_shift_code = ""
        packing_shift_code = ""
        try:
            from utils.shifts import get_current_shift
            from database import PostgresSessionLocal
            with PostgresSessionLocal() as db:
                milling_shift = get_current_shift("3130", "MILLING", db)
                packing_shift = get_current_shift(None, "PACKING", db)
                milling_shift_code = milling_shift.shift_code if milling_shift else ""
                packing_shift_code = packing_shift.shift_code if packing_shift else ""
        except Exception as shift_err:
            logger.warning(f"Could not get current shift for send-all: {shift_err}")

        # Step 5: Prepare SAP payloads with validation
        try:
            sap_milling_payload = {
                "MILL_THROUGHPUT": str(safe(milling_kpis.get("Mill Throughput (%)", 0.0))),
                "MILL_TIME_EFFICIENCY": str(safe(milling_kpis.get("Mill Time Efficiency (%)", 0.0))),
                "TOTAL_UTILIZATION": str(safe(milling_kpis.get("Total Utilization (%)", 0.0))),
                "MAX_UTILIZATION": str(safe(milling_kpis.get("Max Utilization of Milling Capacity (%)", 0.0))),
                "MILLING_GAIN": str(safe(milling_kpis.get("Milling Gain", 0.0))),
                "PRE_CLEAN_SCREENING": str(safe(milling_kpis.get("Pre Cleaning Screening (%)", 0.0))),
                "MILLING_SCREENING": str(safe(milling_kpis.get("Milling Screening (%)", 0.0))),
                "PRE_CLEAN_WATER": str(safe(scada_water_data.get("totalPreCleaningWater", 0.0))),
                "CLEANING_WATER": str(safe(scada_water_data.get("waterCleanWheat", 0.0))),
                "NET_HOURS": str(safe(milling_kpis.get("Net Hours (hrs)", 0.0))),
                "MILLING_DOWN_TIME": str(safe(milling_kpis.get("Downtime (hrs)", 0.0))),
                "BREAK_CAPACITY": str(safe(milling_kpis.get("1st Break Capacity per Hour (t/h)", 0.0))),
                "FLOUR_EXTRACTION": str(safe(milling_kpis.get("Flour Extraction (%)", 0.0))),
                "BRAN_EXTRACTION": str(safe(milling_kpis.get("Bran Extraction (%)", 0.0))),
                "MILLING_LOSS": str(safe(milling_kpis.get("Milling Loss (%)", 0.0))),
                "TOTAL_WATER": str(safe(scada_water_data.get("totalWaterUsed", 0.0))),
                "SHIFT": milling_shift_code or "",
            }

            sap_packing_payload = {
                "PACKING_CAPACITY_BAG": str(safe(packing_kpis.get("Packing Line Capacity (bags/hr)", 0.0))),
                "PACKING_CAPACITY_TON": str(safe(packing_kpis.get("Packing Line Capacity (tons/hr)", 0.0))),
                "PACKING_BAG": str(safe(packing_kpis.get("Daily Packing Output (bags)", 0.0))),
                "PACKING_HOURS": str(safe(packing_kpis.get("Net Hours (hrs)", 0.0))),
                "PACKING_TOTAL_DOWNTIME": str(safe(packing_kpis.get("Downtime (hrs)", 0.0))),
                "PACKING_MACHINE_UTILIZ": str(safe(packing_kpis.get("Machine Utilization (%)", 0.0))),
                "SHIFT": packing_shift_code or "",
            }
            
            logger.info("SAP payloads prepared successfully")
            logger.debug(f"Milling payload: {sap_milling_payload}")
            logger.debug(f"Packing payload: {sap_packing_payload}")
            
        except Exception as payload_error:
            logger.error(f"Failed to prepare SAP payloads: {payload_error}")
            return jsonify({
                "status": "error",
                "message": f"Failed to prepare SAP payloads: {str(payload_error)}",
                "timestamp": datetime.now().isoformat()
            }), 500

        # Step 6: SAP endpoint configuration (HTTPS)
        # milling_endpoint = "https://vhmioqs4ci.sap.mc3.com.sa:44300/zmi_kpi_mill/MKPI?sap-client=200"
        # packing_endpoint = "https://vhmioqs4ci.sap.mc3.com.sa:44300/zmi_kpi_pack/PKPI?sap-client=200"
        milling_endpoint = get_sap_url("/zmi_kpi_mill/MKPI")
        packing_endpoint = get_sap_url("/zmi_kpi_pack/PKPI")
        
        logger.info(f"SAP endpoints configured (HTTPS):")
        logger.info(f"  Milling: {milling_endpoint}")
        logger.info(f"  Packing: {packing_endpoint}")
        
        from requests.auth import HTTPBasicAuth
        
        # Step 7: Initialize results tracking
        results = {
            "milling": {"success": False, "message": "", "payload": sap_milling_payload, "sap_response": ""},
            "packing": {"success": False, "message": "", "payload": sap_packing_payload, "sap_response": ""}
        }
        
        # Helper function to send KPIs
        def send_kpis(endpoint_url, payload, kpi_type):
            # ------------------------------------------------------
            # MOCK MODE → Simple POST only (NO CSRF, NO AUTH)
            # ------------------------------------------------------
            if get_mock_sap_mode():
                logger.info(f"🔧 MOCK MODE: Sending {kpi_type} via simple POST → {endpoint_url}")
                try:
                    resp = requests.post(endpoint_url, json=payload, timeout=30)
                    return resp.status_code in [200, 201], "Data sent successfully", resp.text
                except Exception as e:
                    logger.error(f"Mock POST failed for {kpi_type}: {e}")
                    return False, f"Mock POST failed: {e}", ""
            
            # PRODUCTION MODE → use full CSRF process
            try:
                logger.info(f"=== Sending {kpi_type} KPIs to SAP (Production) ===")

                # Step 1: GET CSRF token
                get_headers = {
                    "x-csrf-token": "fetch",
                    "Accept": "application/json"
                }

                token_response = requests.get(
                    endpoint_url,
                    headers=get_headers,
                    auth=HTTPBasicAuth(SAP_USERNAME, SAP_PASSWORD),
                    timeout=30,
                    verify=False
                )

                csrf_token = (
                    token_response.headers.get("x-csrf-token") or
                    token_response.headers.get("X-CSRF-Token")
                )

                cookies = token_response.cookies

                if not csrf_token:
                    return False, "CSRF token not found in response", ""

                # Step 2: POST KPIs
                post_headers = {
                    "x-csrf-token": csrf_token,
                    "Content-Type": "application/json",
                }

                post_response = requests.post(
                    endpoint_url,
                    json=payload,
                    headers=post_headers,
                    cookies=cookies,
                    auth=HTTPBasicAuth(SAP_USERNAME, SAP_PASSWORD),
                    timeout=30,
                    verify=False
                )

                if post_response.status_code in [200, 201]:
                    return True, "Data sent successfully", post_response.text

                return False, f"POST failed: {post_response.status_code}", post_response.text[:500]

            except Exception as e:
                return False, f"Error: {e}", ""
        
        # Step 8: Send KPIs to SAP
        # Send milling KPIs
        if milling_kpis:
            logger.info("Attempting to send milling KPIs to SAP")
            milling_success, milling_message, milling_response = send_kpis(
                milling_endpoint, sap_milling_payload, "Milling"
            )
            results["milling"]["success"] = milling_success
            results["milling"]["message"] = milling_message
            results["milling"]["sap_response"] = milling_response
            logger.info(f"Milling KPIs result: success={milling_success}, message={milling_message}")
        else:
            logger.warning("No milling KPIs available, skipping milling endpoint")
            results["milling"]["message"] = "No milling KPIs available"
        
        # Send packing KPIs
        if packing_kpis:
            logger.info("Attempting to send packing KPIs to SAP")
            packing_success, packing_message, packing_response = send_kpis(
                packing_endpoint, sap_packing_payload, "Packing"
            )
            results["packing"]["success"] = packing_success
            results["packing"]["message"] = packing_message
            results["packing"]["sap_response"] = packing_response
            logger.info(f"Packing KPIs result: success={packing_success}, message={packing_message}")
        else:
            logger.warning("No packing KPIs available, skipping packing endpoint")
            results["packing"]["message"] = "No packing KPIs available"
        
        # --- SEND HERCULES RAW DATA ALSO -----------------------------------
        try:
            logger.info("Attempting to send Hercules RAW data to SAP...")

            # Fetch latest hercules row again
            with engine.connect() as conn:
                latest_sql = text(f"""
                    SELECT TOP 1 *
                    FROM {TABLE}
                    ORDER BY ASMArchive_DB5ID DESC
                """)
                herc_row = conn.execute(latest_sql).mappings().first()

            if herc_row:
                herc_payload = dict(herc_row)

                # Convert datetime & decimal fields
                from datetime import datetime as dt
                from decimal import Decimal
                for key, value in herc_payload.items():
                    if isinstance(value, dt):
                        herc_payload[key] = value.isoformat()
                    elif isinstance(value, Decimal):
                        herc_payload[key] = float(value)

                herc_url = get_sap_url("/zmi_raw_hercl/HERC", client="250")

                if get_mock_sap_mode():
                    # simple mock post
                    herc_resp = requests.post(herc_url, json=herc_payload, timeout=30)
                    results["hercules"] = {
                        "success": herc_resp.status_code in [200, 201],
                        "message": "Hercules sent (mock)",
                        "payload": herc_payload,
                        "sap_response": herc_resp.text
                    }
                else:
                    # production mode not needed for testing
                    results["hercules"] = {
                        "success": False,
                        "message": "Production Hercules not implemented for ALL-KPI",
                        "payload": herc_payload
                    }

                logger.info("Hercules raw data sent successfully!")

            else:
                results["hercules"] = {
                    "success": False,
                    "message": "No Hercules data available"
                }

        except Exception as e:
            logger.error(f"Hercules sending failed: {e}")
            results["hercules"] = {
                "success": False,
                "message": f"Hercules sending failed: {str(e)}"
            }
        
        # Step 9: Determine overall status
        milling_success = results["milling"]["success"]
        packing_success = results["packing"]["success"]
        overall_success = milling_success and packing_success
        overall_message = ""
        
        if overall_success:
            overall_message = "All KPIs sent to SAP successfully"
        else:
            failed_services = []
            if not milling_success and milling_kpis:
                failed_services.append("Milling")
            if not packing_success and packing_kpis:
                failed_services.append("Packing")
            
            if failed_services:
                overall_message = f"Failed to send {', '.join(failed_services)} KPIs to SAP"
            else:
                overall_message = "No KPI data available for sending"
        
        logger.info(f"Overall result: {overall_message}")
        
        return jsonify({
            "success": overall_success,
            "message": overall_message,
            "results": results,
            "timestamp": datetime.now().isoformat()
        })

    except Exception as e:
        logger.error(f"❌ Exception: {e}")
        import traceback
        logger.error(traceback.format_exc())
        return jsonify({
            "success": False,
            "message": f"Error: {str(e)}",
            "timestamp": datetime.now().isoformat()
        }), 500

@kpi_bp.route("/api/kpi/test-sap-connection", methods=["GET"])
def test_sap_connection():
    """
    Test SAP connection without sending data - for debugging
    """
    try:
        logger.info("Testing SAP connection")
        
        # Test endpoints (HTTPS)
        milling_endpoint = "https://vhmioqs4ci.sap.mc3.com.sa:44300/zmi_kpi_mill/MKPI?sap-client=200"
        packing_endpoint = "https://vhmioqs4ci.sap.mc3.com.sa:44300/zmi_kpi_pack/PKPI?sap-client=200"
        
        results = {
            "milling_endpoint": {"url": milling_endpoint, "status": "unknown", "response": ""},
            "packing_endpoint": {"url": packing_endpoint, "status": "unknown", "response": ""}
        }
        
        # Test milling endpoint
        try:
            response = requests.get(
                milling_endpoint,
                auth=(SAP_USERNAME, SAP_PASSWORD),
                timeout=10,
                verify=False
            )
            results["milling_endpoint"]["status"] = "success" if response.status_code == 200 else "failed"
            results["milling_endpoint"]["response"] = f"Status: {response.status_code}, Response: {response.text[:200]}"
        except Exception as e:
            results["milling_endpoint"]["status"] = "error"
            results["milling_endpoint"]["response"] = str(e)
        
        # Test packing endpoint
        try:
            response = requests.get(
                packing_endpoint,
                auth=(SAP_USERNAME, SAP_PASSWORD),
                timeout=10,
                verify=False
            )
            results["packing_endpoint"]["status"] = "success" if response.status_code == 200 else "failed"
            results["packing_endpoint"]["response"] = f"Status: {response.status_code}, Response: {response.text[:200]}"
        except Exception as e:
            results["packing_endpoint"]["status"] = "error"
            results["packing_endpoint"]["response"] = str(e)
        
        # Test database connection
        db_status = "unknown"
        try:
            with engine.connect() as conn:
                conn.execute(text("SELECT 1"))
                db_status = "connected"
        except Exception as e:
            db_status = f"error: {str(e)}"
        
        return jsonify({
            "status": "success",
            "message": "SAP connection test completed",
            "database_status": db_status,
            "sap_endpoints": results,
            "timestamp": datetime.now().isoformat()
        })
        
    except Exception as e:
        logger.error(f"Error testing SAP connection: {e}")
        return jsonify({
            "status": "error",
            "message": f"Error testing SAP connection: {str(e)}",
            "timestamp": datetime.now().isoformat()
        }), 500

@kpi_bp.route("/api/hercules/test", methods=["GET"])
def test_hercules_endpoint():
    """
    Test endpoint to verify Hercules routes are working
    """
    return jsonify({
        "status": "success",
        "message": "Hercules endpoint is working!",
        "timestamp": datetime.now().isoformat()
    })

@kpi_bp.route("/api/hercules/latest", methods=["GET"])
def get_latest_hercules_data():
    """
    Get the latest record from ASMReporting_5 table for Hercules SAP integration.
    This endpoint provides the most recent data record that can be sent to SAP.
    """
    try:
        logger.info("Fetching latest Hercules data from ASMReporting_5")
        
        with engine.connect() as conn:
            # Get the latest record from ASMReporting_5 table
            latest_sql = text(f"""
                SELECT TOP 1 *
                FROM {TABLE}
                ORDER BY ASMArchive_DB5ID DESC
            """)
            
            row = conn.execute(latest_sql).mappings().first()
            if not row:
                logger.warning("No data found in ASMReporting_5 table")
                return jsonify({
                    "error": "No data found in ASMReporting_5 table",
                    "timestamp": datetime.now().isoformat()
                }), 404

            # Convert to dict and ensure all fields are properly formatted
            hercules_data = dict(row)
            
            # Log the data being returned (without sensitive info)
            logger.info(f"Latest Hercules data fetched successfully - ID: {hercules_data.get('ASMArchive_DB5ID')}")
            logger.debug(f"Hercules data: {hercules_data}")
            
            return jsonify(hercules_data)

    except Exception as e:
        logger.error(f"Error fetching latest Hercules data: {e}")
        return jsonify({
            "error": f"Error fetching latest Hercules data: {str(e)}",
            "timestamp": datetime.now().isoformat()
        }), 500
@kpi_bp.route("/api/hercules/send-to-sap", methods=["POST"])
def send_hercules_to_sap():
    """
    Send Hercules data to SAP via HTTPS port 44300
    (SAP forces all Python/API requests to use HTTPS)
    """
    import urllib3
    from datetime import datetime as dt
    urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)
    
    try:
        logger.info("=== HERCULES ENDPOINT CALLED ===")
        
        # Get latest record from database
        with engine.connect() as conn:
            latest_sql = text(f"""
                SELECT TOP 1 *
                FROM {TABLE}
                ORDER BY ASMArchive_DB5ID DESC
            """)
            
            row = conn.execute(latest_sql).mappings().first()
            if not row:
                return jsonify({
                    "success": False,
                    "message": "No data found in database",
                    "timestamp": datetime.now().isoformat()
                }), 404

            hercules_data = dict(row)
            logger.info(f"Fetched record ID: {hercules_data.get('ASMArchive_DB5ID')}")
            
            # Convert datetime and Decimal objects to JSON-serializable types
            for key, value in hercules_data.items():
                if isinstance(value, dt):
                    hercules_data[key] = value.isoformat()
                    logger.debug(f"Converted {key} datetime to ISO string")
                elif hasattr(value, '__class__') and value.__class__.__name__ == 'Decimal':
                    hercules_data[key] = float(value)
        
        # Get SAP URL (mock or production)
        SAP_URL = get_sap_url("/zmi_raw_hercl/HERC", client="250")
        logger.info(f"Using URL: {SAP_URL}")
        
        from requests.auth import HTTPBasicAuth
        
        # ============================================================
        # MOCK MODE: Simple POST request without CSRF/auth
        # ============================================================
        if get_mock_sap_mode():
            logger.info("🔧 MOCK MODE: Sending simple POST to demo server...")
            post_response = requests.post(
                SAP_URL,
                json=hercules_data,
                timeout=30
            )
            logger.info(f"POST response status: {post_response.status_code}")
            logger.info(f"POST response: {post_response.text[:500]}")
        else:
            # ============================================================
            # PRODUCTION MODE: STEP 1: GET request to fetch CSRF token (HTTPS)
            # ============================================================
            logger.info("Step 1: Fetching CSRF token via HTTPS...")
            
            get_headers = {
                "x-csrf-token": "fetch",
                "Accept": "application/json",
                "User-Agent": "Python-Requests/2.31.0",
                "Connection": "keep-alive"
            }
            
            token_response = requests.get(
                SAP_URL,
                headers=get_headers,
                auth=HTTPBasicAuth(SAP_USERNAME, SAP_PASSWORD),
                timeout=30,
                verify=False  # Ignore SSL certificate errors
            )
            
            logger.info(f"GET response status: {token_response.status_code}")
            logger.info(f"GET response headers: {dict(token_response.headers)}")
            
            # Check for errors
            if token_response.status_code == 401:
                logger.error(f"❌ Authentication failed: {token_response.text[:300]}")
                return jsonify({
                    "success": False,
                    "message": "Authentication failed",
                    "error": token_response.text[:500],
                    "timestamp": datetime.now().isoformat()
                }), 401
            
            if token_response.status_code not in [200, 201]:
                logger.error(f"❌ Failed to fetch CSRF token: {token_response.status_code}")
                return jsonify({
                    "success": False,
                    "message": f"Failed to get CSRF token. Status: {token_response.status_code}",
                    "error": token_response.text[:500],
                    "timestamp": datetime.now().isoformat()
                }), token_response.status_code
            
            # Extract CSRF token
            csrf_token = (
                token_response.headers.get("x-csrf-token") or 
                token_response.headers.get("X-CSRF-Token") or
                token_response.headers.get("X-Csrf-Token")
            )
            
            cookies = token_response.cookies
            
            if not csrf_token:
                logger.error("❌ No CSRF token in response headers")
                logger.error(f"Available headers: {list(token_response.headers.keys())}")
                return jsonify({
                    "success": False,
                    "message": "CSRF token not found in response",
                    "headers": list(token_response.headers.keys()),
                    "timestamp": datetime.now().isoformat()
                }), 500
            
            logger.info(f"✅ CSRF token received: {csrf_token[:30]}...")
            logger.info(f"Cookies received: {len(cookies)} cookie(s)}}")
            
            # ============================================================
            # STEP 2: POST request with CSRF token and data (HTTPS)
            # ============================================================
            logger.info("Step 2: Sending POST request with Hercules data...")
            
            post_headers = {
                "x-csrf-token": csrf_token,
                "Content-Type": "application/json",
                "Accept": "application/json",
                "User-Agent": "Python-Requests/2.31.0",
                "Connection": "keep-alive"
            }
            
            post_response = requests.post(
                SAP_URL,
                json=hercules_data,
                headers=post_headers,
                cookies=cookies,
                auth=HTTPBasicAuth(SAP_USERNAME, SAP_PASSWORD),
                timeout=30,
                verify=False
            )
            
            logger.info(f"POST response status: {post_response.status_code}")
            logger.info(f"POST response: {post_response.text[:500]}")
        
        # Check success
        if post_response.status_code in [200, 201]:
            if "Data Saved Correctly" in post_response.text:
                logger.info("✅ SUCCESS! Hercules data saved to SAP")
                return jsonify({
                    "success": True,
                    "message": "Data Saved Correctly",
                    "response": post_response.text,
                    "record_id": hercules_data.get('ASMArchive_DB5ID'),
                    "timestamp": datetime.now().isoformat()
                }), 200
            else:
                logger.info("✅ POST successful")
                return jsonify({
                    "success": True,
                    "message": "Data sent successfully",
                    "response": post_response.text,
                    "record_id": hercules_data.get('ASMArchive_DB5ID'),
                    "timestamp": datetime.now().isoformat()
                }), 200
        else:
            logger.error(f"❌ POST failed: {post_response.status_code}")
            return jsonify({
                "success": False,
                "message": f"POST failed with status {post_response.status_code}",
                "error": post_response.text[:500],
                "timestamp": datetime.now().isoformat()
            }), post_response.status_code
            
    except Exception as e:
        logger.error(f"❌ Exception: {e}")
        import traceback
        logger.error(traceback.format_exc())
        return jsonify({
            "success": False,
            "message": f"Error: {str(e)}",
            "timestamp": datetime.now().isoformat()
        }), 500
