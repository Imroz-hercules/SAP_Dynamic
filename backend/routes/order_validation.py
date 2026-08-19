

# from __future__ import annotations
# from typing import Dict, Any, List, Optional, Mapping
# from datetime import datetime
# import threading
# import time
# import re
# import ast
# import sys

# from flask import Blueprint, request, jsonify
# from werkzeug.exceptions import BadRequest, NotFound
# from sqlalchemy.orm import sessionmaker
# import threading

# # Services
# from services.scale_service import (
#     get_multiple_scada_readings,   # noqa: F401
#     capture_baseline_readings,
#     calculate_deltas,
# )
# from services.sap_confirmation import SAPConfirmationService

# # Database
# from database import postgres_engine
# from utils.shifts import get_current_shift, get_next_shift, is_shift_ended
# from models.shift_master import ShiftMaster

# try:
#     from models.process_order_pg import ProcessOrderPG as ProcessOrder
#     print("✅ ProcessOrder model imported successfully")
# except Exception as e:
#     print(f"❌ Failed to import ProcessOrder model: {e}")
#     ProcessOrder = None


# PostgresSessionLocal = sessionmaker(
#     bind=postgres_engine, autoflush=False, autocommit=False, future=True
# )


# def _db_session():
#     return PostgresSessionLocal()


# def _mapping_db_session():
#     """Return a session bound to the PostgreSQL DB for milling mappings."""
#     return PostgresSessionLocal()


# orders_bp = Blueprint("orders", __name__, url_prefix="/api/orders")

# # Module-level dictionary to track last calculated production from baseline for each shift
# # Key: (po_number, shift_code) -> last_total_production_from_baseline
# _last_shift_production_cache = {}

# # ✅ CRITICAL: Track maximum weight seen for each shift to prevent reverts
# # Key: (po_number, shift_code) -> maximum_weight_seen
# _max_shift_weight_cache = {}

# # =============================================================================
# # SPEC-CONFORMANT CLASSIFICATION MAPPINGS
# # =============================================================================

# PL_TO_SCADA = {
#     "PL601": "SL601_COUNTER",
#     "PL602": "SL602_COUNTER",
#     "PL603": "SL603_COUNTER",
#     "PL606": "SL606_COUNTER",
#     "PL607": "SL607_COUNTER",
# }

# # =============================================================================
# # MILLING PV SPECS - Version-specific formulas and equipment
# # =============================================================================
# # Based on "Confirmed Weight Scale" column from material version mapping table
# # MILLING PV SPECS - corrected from spreadsheet
# # =============================================================================
# # ⚠️ DEPRECATED: HARDCODED MILLING MAPPINGS
# # =============================================================================
# # These dictionaries are NO LONGER USED - all milling mappings are now stored
# # in the database table `milling_version_mappings` and accessed via the
# # MillingVersionMapping model.
# #
# # To add/update milling mappings, use the API endpoint:
# # POST /api/milling-mapping
# #
# # These are kept here temporarily for reference/migration purposes only.
# # =============================================================================

# # DEPRECATED: Use milling_version_mappings table instead
# # MILLING_PV_SPECS = {
# #     "LWSM": {"scales": ["WG101", "WG302", "DM101", "DM102"], "formula": "(WG101-WG302)+(DM101+DM102)"},
# #     "IWSM": {"scales": ["WG101", "WG302"], "formula": "(WG101-WG302)"},
# #     "SWSM": {"scales": ["WG101", "WG302"], "formula": "(WG101-WG302)"},
# #     "CWIM": {"scales": ["WG201", "WG301", "DM201", "DM202", "DM203"], "formula": "(WG201-WG301)+(DM201+DM202+DM203)"},
# #     "CWLM": {"scales": ["WG201", "WG301", "DM201", "DM202", "DM203"], "formula": "(WG201-WG301)+(DM201+DM202+DM203)"},
# #     "CWMM": {"scales": ["WG201", "WG301", "DM201", "DM202", "DM203"], "formula": "(WG201-WG301)+(DM201+DM202+DM203)"},
# #     "CWSM": {"scales": ["WG201", "WG301", "DM201", "DM202", "DM203"], "formula": "(WG201-WG301)+(DM201+DM202+DM203)"},
# #     "BKF1": {"scales": ["WG501"], "formula": "WG501"},
# #     "CKF1": {"scales": ["WG502"], "formula": "WG502"},
# #     "IWF1": {"scales": ["WG502"], "formula": "WG502"},
# #     "IWF2": {"scales": ["WG502"], "formula": "WG502"},
# #     "BRF1": {"scales": ["WG501"], "formula": "WG501"},
# #     "BRF2": {"scales": ["WG502"], "formula": "WG502"},
# #     "BRF3": {"scales": ["WG501"], "formula": "WG501"},
# #     "MMCF": {"scales": ["WG502"], "formula": "WG502"},
# # }

# # DEPRECATED: Use milling_version_mappings table instead
# # MILLING_PV_MAPPING_SPEC = {v: spec["scales"] for v, spec in MILLING_PV_SPECS.items()}

# # DEPRECATED: No longer used - overrides should be managed via DB
# # AUTH_MILLING_PV_OVERRIDES: Dict[str, List[str]] = {}

# # DEPRECATED: Use milling_version_mappings table (scale1, scale2, scale3 columns) instead
# # MILLING_BYPRODUCT_MAPPING = {
# #     "LWSM": {"scale1": "WG302", "scale2": None, "scale3": None},
# #     "IWSM": {"scale1": "WG302", "scale2": None, "scale3": None},
# #     "SWSM": {"scale1": "WG302", "scale2": None, "scale3": None},
# #     "CWIM": {"scale1": "WG301", "scale2": None, "scale3": None},
# #     "CWLM": {"scale1": "WG301", "scale2": None, "scale3": None},
# #     "CWMM": {"scale1": "WG301", "scale2": None, "scale3": None},
# #     "CWSM": {"scale1": "WG301", "scale2": None, "scale3": None},
# #     "BKF1": {"scale1": "WG503", "scale2": None, "scale3": None},
# #     "CKF1": {"scale1": "WG501", "scale2": "WG503", "scale3": None},
# #     "IWF1": {"scale1": "WG501", "scale2": "WG503", "scale3": None},
# #     "IWF2": {"scale1": "WG501", "scale2": "WG503", "scale3": None},
# #     "BRF1": {"scale1": "WG503", "scale2": None, "scale3": None},
# #     "BRF2": {"scale1": "WG501", "scale2": "WG503", "scale3": None},
# #     "BRF3": {"scale1": "WG501", "scale2": "WG503", "scale3": None},
# #     "MMCF": {"scale1": "WG501", "scale2": "WG503", "scale3": None},
# # }

# # =============================================================================
# # GLOBALS & CONSTANTS
# # =============================================================================

# import threading

# # NEW: Track multiple orders in parallel
# VALIDATION_STATES = {}  # Key: ponumber, Value: {isrunning, thread, progresspct, status}
# VALIDATION_LOCK = threading.Lock()

# # Global master switch for auto-validator
# AUTO_VALIDATOR_MASTER = {"isrunning": False}


# def is_auto_validator_enabled() -> bool:
#     """Return True if master auto-validator is ON."""
#     return AUTO_VALIDATOR_MASTER.get("isrunning", False)

# # Helper functions to safely access multi-order state
# def get_order_validation_state(ponumber: str):
#     """Get validation state for a specific order"""
#     with VALIDATION_LOCK:
#         return VALIDATION_STATES.get(ponumber, {
#             "isrunning": False,
#             "thread": None,
#             "progresspct": 0,
#             "status": "idle"
#         })

# def set_order_validation_state(ponumber: str, state: dict):
#     """Set validation state for a specific order"""
#     with VALIDATION_LOCK:
#         if ponumber not in VALIDATION_STATES:
#             VALIDATION_STATES[ponumber] = {}
#         VALIDATION_STATES[ponumber].update(state)

# def remove_order_validation_state(ponumber: str):
#     """Remove validation state when order completes"""
#     with VALIDATION_LOCK:
#         VALIDATION_STATES.pop(ponumber, None)

# def is_order_validating(ponumber: str) -> bool:
#     """Check if specific order is currently validating"""
#     state = get_order_validation_state(ponumber)
#     return state.get("isrunning", False)

# TOLERANCE_PCT = 0.0
# WORKER_SLEEP_SECONDS = 60


# # =============================================================================
# # SAFE ATTRIBUTE ACCESS
# # =============================================================================

# def get_attr_safe(obj, attr: str, default=None):
#     try:
#         return getattr(obj, attr, default)
#     except Exception:
#         return default


# def set_attr_safe(obj, attr: str, value):
#     try:
#         setattr(obj, attr, value)
#     except Exception:
#         pass


# def update_last_confirmed_qty(order) -> None:
#     """
#     Update last_confirmed_qty column with the sum of confirmed_shift_a, confirmed_shift_b, confirmed_shift_c.
#     This is called whenever any shift confirmation value changes.
#     """
#     confirmed_shift_a = float(get_attr_safe(order, "confirmed_shift_a", 0.0) or 0.0)
#     confirmed_shift_b = float(get_attr_safe(order, "confirmed_shift_b", 0.0) or 0.0)
#     confirmed_shift_c = float(get_attr_safe(order, "confirmed_shift_c", 0.0) or 0.0)
    
#     total_confirmed = confirmed_shift_a + confirmed_shift_b + confirmed_shift_c
#     set_attr_safe(order, "last_confirmed_qty", total_confirmed)
    
#     print(f"📊 Updated last_confirmed_qty: {total_confirmed:.2f} (A={confirmed_shift_a:.2f}, B={confirmed_shift_b:.2f}, C={confirmed_shift_c:.2f})")


# # =============================================================================
# # HELPERS
# # =============================================================================

# def _translate_pl_to_scada(pl_list: List[str]) -> List[str]:
#     return [PL_TO_SCADA[p] for p in pl_list if p in PL_TO_SCADA]


# def _resolve_milling_streams(version: str) -> Optional[List[str]]:
#     """
#     DEPRECATED: Returns scales list from DB-based milling_version_mappings.
#     For backward compatibility only - prefer using classify_order() instead.
#     """
#     from models.milling_version_mapping import MillingVersionMapping
    
#     v = (version or "").upper().strip()
    
#     try:
#         with _mapping_db_session() as db:
#             mapping = (
#                 db.query(MillingVersionMapping)
#                   .filter(MillingVersionMapping.version == v)
#                   .first()
#             )
#     except Exception:
#         return None
    
#     if mapping:
#         return mapping.scales or []
    
#     return None


# def _resolve_milling_streams_and_formula(version: str) -> Optional[Dict[str, Any]]:
#     """
#     DEPRECATED: Return confirmed-weight scales + formula for a milling PV from DB.
#     For backward compatibility only - prefer using classify_order() instead.
#     """
#     from models.milling_version_mapping import MillingVersionMapping
    
#     v = (version or "").upper().strip()
    
#     try:
#         with _mapping_db_session() as db:
#             mapping = (
#                 db.query(MillingVersionMapping)
#                   .filter(MillingVersionMapping.version == v)
#                   .first()
#             )
#     except Exception:
#         return None
    
#     if not mapping:
#         return None
    
#     # always return a fresh list
#     return {
#         "scales": list(mapping.scales or []),
#         "formula": mapping.formula or "",
#     }


# def _capture_byproduct_baselines(version: str, baselines: Dict[str, float], order=None) -> Dict[str, float]:
#     """
#     Capture baseline SCADA readings for all byproduct scales for a given version.
#     ALWAYS stores SCADA value for byproduct scales, even if it's 0 or already in baselines.
#     This ensures byproduct scale quantities are correctly stored.
    
#     Args:
#         version: Order version (e.g., "LWSM", "CKF1")
#         baselines: Existing baselines dict (will be updated with byproduct scales)
#         order: Optional ProcessOrder object to reset baseline_fixed_flags for byproduct scales
    
#     Returns:
#         Updated baselines dict with byproduct scales included
#     """
#     from services.scale_service import get_scada_reading
#     from models.milling_version_mapping import MillingVersionMapping
    
#     version_upper = (version or "").upper().strip()
    
#     if not version_upper:
#         print(f"⚠️ [byproduct_baselines] Version is empty, skipping byproduct baseline capture")
#         return baselines
    
#     # Get byproduct scales from DB
#     try:
#         with _mapping_db_session() as db:
#             mapping = (
#                 db.query(MillingVersionMapping)
#                   .filter(MillingVersionMapping.version == version_upper)
#                   .first()
#             )
#     except Exception as e:
#         print(f"⚠️ [byproduct_baselines] Error querying byproduct mapping for '{version_upper}': {e}")
#         return baselines
    
#     if not mapping:
#         print(f"⚠️ [byproduct_baselines] No mapping found for version '{version_upper}', skipping byproduct baselines")
#         return baselines
    
#     # Build byproduct scales dict from DB mapping
#     byp_scales = {
#         "scale1": mapping.scale1,
#         "scale2": mapping.scale2,
#         "scale3": mapping.scale3
#     }
    
#     # ✅ FIX: Capture baseline for each byproduct scale (scale1, scale2, scale3)
#     # ALWAYS capture, even if tag is already in baselines (may be both main and byproduct scale)
#     for scale_key in ["scale1", "scale2", "scale3"]:
#         tag = byp_scales.get(scale_key)
#         if tag:
#             # ✅ ALWAYS get fresh SCADA reading for byproduct scale
#             scada_val = get_scada_reading(tag)
            
#             # ✅ FIX: ALWAYS store SCADA value, even if it's 0 (0 is a valid baseline)
#             if scada_val is None:
#                 scada_val = 0.0
            
#             # ✅ FIX: Override existing baseline if this is a byproduct scale
#             # (Even if tag is also in main equipment list, byproduct baseline takes precedence)
#             baselines[tag] = float(scada_val)
#             print(f"📌 Byproduct baseline saved: {tag} = {scada_val:.2f} (overriding any existing baseline)")
            
#             # ✅ FIX: Reset baseline_fixed_flags for byproduct scales to allow fresh capture
#             if order:
#                 baseline_fixed_flags = get_attr_safe(order, "baseline_fixed_flags", {}) or {}
#                 if not isinstance(baseline_fixed_flags, dict):
#                     baseline_fixed_flags = {}
#                 tag_key = tag.lower()
#                 # Reset flag so byproduct baseline can be stored fresh
#                 baseline_fixed_flags[tag_key] = False
#                 set_attr_safe(order, "baseline_fixed_flags", baseline_fixed_flags)
    
#     return baselines


# def _set_byproduct_scales(order, version: str, baselines: Dict[str, float]) -> None:
#     """
#     Set byproduct scales (scale1, scale2, scale3) and their baseline quantities
#     when order validation starts. Only applies to MILLING orders.
    
#     Args:
#         order: ProcessOrder object
#         version: Order version (e.g., "LWSM", "CKF1")
#         baselines: Dictionary of baseline readings from SCADA (tag -> value)
#                    Should include both main equipment and byproduct scales
#     """
#     from models.milling_version_mapping import MillingVersionMapping
    
#     version_upper = (version or "").upper().strip()
    
#     if not version_upper:
#         print(f"⚠️ [set_byproduct_scales] Version is empty, clearing byproduct scales")
#         # Clear scales if version is empty
#         set_attr_safe(order, "scale1", None)
#         set_attr_safe(order, "scale1_qty", 0.0)
#         set_attr_safe(order, "scale2", None)
#         set_attr_safe(order, "scale2_qty", 0.0)
#         set_attr_safe(order, "scale3", None)
#         set_attr_safe(order, "scale3_qty", 0.0)
#         return
    
#     # Get byproduct scales from DB (MSSQL - same as API routes)
#     try:
#         with _mapping_db_session() as db:
#             mapping = (
#                 db.query(MillingVersionMapping)
#                   .filter(MillingVersionMapping.version == version_upper)
#                   .first()
#             )
#     except Exception as e:
#         print(f"⚠️ [set_byproduct_scales] Error querying byproduct mapping for '{version_upper}': {e}")
#         # Clear scales if error
#         set_attr_safe(order, "scale1", None)
#         set_attr_safe(order, "scale1_qty", 0.0)
#         set_attr_safe(order, "scale2", None)
#         set_attr_safe(order, "scale2_qty", 0.0)
#         set_attr_safe(order, "scale3", None)
#         set_attr_safe(order, "scale3_qty", 0.0)
#         return
    
#     if not mapping:
#         print(f"⚠️ [set_byproduct_scales] No byproduct scales defined for version '{version_upper}'")
#         # Clear scales if no mapping exists
#         set_attr_safe(order, "scale1", None)
#         set_attr_safe(order, "scale1_qty", 0.0)
#         set_attr_safe(order, "scale2", None)
#         set_attr_safe(order, "scale2_qty", 0.0)
#         set_attr_safe(order, "scale3", None)
#         set_attr_safe(order, "scale3_qty", 0.0)
#         return
    
#     scale1_tag = mapping.scale1
#     scale2_tag = mapping.scale2
#     scale3_tag = mapping.scale3
    
#     # Assign scale names to order
#     set_attr_safe(order, "scale1", scale1_tag)
#     set_attr_safe(order, "scale2", scale2_tag)
#     set_attr_safe(order, "scale3", scale3_tag)
    
#     # ✅ Get baseline readings from baselines dict (now includes byproduct scales)
#     scale1_baseline = float(baselines.get(scale1_tag, 0.0) or 0.0) if scale1_tag else 0.0
#     scale2_baseline = float(baselines.get(scale2_tag, 0.0) or 0.0) if scale2_tag else 0.0
#     scale3_baseline = float(baselines.get(scale3_tag, 0.0) or 0.0) if scale3_tag else 0.0
    
#     set_attr_safe(order, "scale1_qty", scale1_baseline)
#     set_attr_safe(order, "scale2_qty", scale2_baseline)
#     set_attr_safe(order, "scale3_qty", scale3_baseline)
    
#     print(f"✅ [set_byproduct_scales] Byproduct scales set for {version_upper}: "
#           f"scale1={scale1_tag} ({scale1_baseline:.2f}), "
#           f"scale2={scale2_tag} ({scale2_baseline:.2f}), "
#           f"scale3={scale3_tag} ({scale3_baseline:.2f})")


# # =============================================================================
# # SAFE FORMULA EVALUATOR
# # =============================================================================

# # Python 3.8+ uses ast.Constant instead of ast.Num
# ALLOWED_AST_NODES = (
#     ast.Expression, ast.BinOp, ast.UnaryOp, ast.Constant,
#     ast.Add, ast.Sub, ast.Mult, ast.Div, ast.Pow,
#     ast.USub, ast.UAdd, ast.Load, ast.Call, ast.Mod, ast.FloorDiv,
#     ast.Tuple, ast.List, ast.Subscript, ast.Index
# )
# # Python < 3.8 compatibility (ast.Num was deprecated)
# try:
#     ALLOWED_AST_NODES = ALLOWED_AST_NODES + (ast.Num,)
# except AttributeError:
#     pass  # ast.Num doesn't exist in Python 3.8+


# def _is_safe_ast(node: ast.AST) -> bool:
#     """Return True if node and all subnodes are permitted (no names, no attributes)."""
#     for n in ast.walk(node):
#         # Allow numeric constants (ast.Constant) and arithmetic operators
#         if not isinstance(n, ALLOWED_AST_NODES):
#             return False
#     return True


# def evaluate_formula_using_deltas(formula: str, deltas: Mapping[str, float]) -> float:
#     """
#     Safely evaluate a formula string where tokens like 'WG201' are replaced by numeric delta values.
#     Allowed operators: + - * / and parentheses.
    
#     Args:
#         formula: Formula string like "(WG201-WG301)+(DM201+DM202+DM203)"
#         deltas: Mapping of tag names to delta values, e.g., {"WG201": 40.0, "WG301": 5.0, ...}
    
#     Returns:
#         Evaluated result as float (0.0 if evaluation fails)
#     """
#     if not formula:
#         return 0.0

#     # Replace tags (WG201, DM201, etc.) with numeric literals.
#     # Use word boundary to avoid partial replacements.
#     expr = formula.strip()

#     # Replace each tag token by a numeric literal from deltas (use 0.0 default)
#     # Example: "(WG201-WG301)+(DM201+DM202+DM203)" => "(40.0-5.0)+(0.0+0.0+0.0)"
#     def _tag_repl(match):
#         tag = match.group(0)
#         val = float(deltas.get(tag, 0.0) or 0.0)
#         # Use repr to keep numeric formatting safe
#         return repr(val)

#     # Match tokens consisting of letters+digits like WG201, DM202, etc.
#     expr = re.sub(r'\b[A-Za-z]{1,5}\d{1,4}\b', _tag_repl, expr)

#     # Now validate expression only contains digits, ., whitespace, arithmetic symbols and parentheses
#     if re.search(r'[A-Za-z_]', expr):
#         # if any alpha remains, it's unsafe
#         print(f"⚠️ Unsafe tokens in formula after substitution: {formula} -> {expr}")
#         return 0.0

#     # Parse to AST and ensure it's safe (only arithmetic)
#     try:
#         node = ast.parse(expr, mode='eval')
#         if not _is_safe_ast(node):
#             print(f"⚠️ Unsafe expression in formula: {formula}")
#             return 0.0
#         result = eval(compile(node, "<formula>", mode="eval"), {"__builtins__": {}})
#         return float(result)
#     except Exception as e:
#         # fallback - log and return 0.0 to avoid crashing production
#         print(f"⚠️ Failed to evaluate formula '{formula}' with deltas {deltas}: {e}")
#         return 0.0

# def classify_order(order) -> Dict[str, Any]:
#     """
#     Classification logic for MILLING & PACKING:

#     - MILLING (fully dynamic):
#         ✔ Scales from milling_version_mappings.scales
#         ✔ Formula from milling_version_mappings.formula
#         ✔ Byproduct scale1/2/3 from milling_version_mappings

#     - PACKING (unchanged):
#         ✔ PL → SCADA mapping
#         ✔ Bag size, pallets info
#     """

#     material_code = str(order.material or "").strip()
#     version = (order.version or "").upper().strip()

#     result = {
#         "order_type": None,
#         "equipment": [],     # Main confirmed-weight scales
#         "formula": "",
#         "version": version,
#         "byproduct": {},     # scale1/scale2/scale3
#         "packing_info": {},
#         "error": None
#     }

#     # ---------------------------------------------------------
#     # MATERIAL PREFIX → MILLING / PACKING
#     # ---------------------------------------------------------
#     material_stripped = material_code.lstrip("0")
#     if len(material_stripped) < 2:
#         result["error"] = f"Invalid material code: {material_code}"
#         return result

#     prefix = material_stripped[:2]

#     if prefix == "13":
#         result["order_type"] = "MILLING"
#     elif prefix == "14":
#         result["order_type"] = "PACKING"
#     else:
#         result["error"] = f"Unknown material prefix: {prefix}"
#         return result

#     # =========================================================
#     #             ✔✔✔ MILLING — NOW 100% DYNAMIC
#     # =========================================================
#     if result["order_type"] == "MILLING":
#         from models.milling_version_mapping import MillingVersionMapping

#         # Validate version is not empty
#         if not version:
#             result["error"] = f"Version is empty or missing for order"
#             print(f"❌ [classify_order] Version is empty for material {material_code}")
#             return result

#         try:
#             with _mapping_db_session() as db:
#                 mapping = (
#                     db.query(MillingVersionMapping)
#                       .filter(MillingVersionMapping.version == version)
#                       .first()
#                 )
#         except Exception as e:
#             error_msg = f"Database error querying milling mapping for version '{version}': {e}"
#             print(f"❌ [classify_order] {error_msg}")
#             result["error"] = error_msg
#             return result

#         if not mapping:
#             error_msg = f"No milling mapping found for version '{version}'. Please add it via /api/milling-mapping"
#             print(f"❌ [classify_order] {error_msg}")
#             result["error"] = error_msg
#             return result

#         # ---------------------------
#         # MAIN SCALE LIST
#         # ---------------------------
#         result["equipment"] = mapping.scales or []

#         # ---------------------------
#         # FORMULA
#         # ---------------------------
#         result["formula"] = mapping.formula or ""

#         # ---------------------------
#         # BYPRODUCT scale1/2/3
#         # ---------------------------
#         result["byproduct"] = {
#             "scale1": mapping.scale1,
#             "scale2": mapping.scale2,
#             "scale3": mapping.scale3
#         }

#         return result

#     # =========================================================
#     #                   PACKING (UNCHANGED)
#     # =========================================================
#     try:
#         from models.palletizer_mapping import PalletizerMapping

#         with _db_session() as db:
#             mapping = db.query(PalletizerMapping).filter(
#                 PalletizerMapping.version == version
#             ).first()

#         if not mapping:
#             result["error"] = f"No palletizer mapping found for version {version}"
#             return result

#         # Convert palletizer code → SCADA PL tag
#         result["equipment"] = _translate_pl_to_scada([mapping.palletizer])
#         result["formula"] = ""

#         result["packing_info"] = {
#             "bag_size_kg": float(mapping.bag_size_kg or 0),
#             "bags_per_pallet": int(mapping.bags_per_pallet or 0),
#             "kg_per_pallet": float(mapping.kg_per_pallet or 0),
#             "description": f"{version} → {mapping.palletizer}"
#         }

#     except Exception as e:
#         print(f"❌ Error querying palletizer mapping for {version}: {e}")
#         result["error"] = f"Database error: {e}"
#         return result

#     return result

# def get_current_production(order, classification: Dict, db=None, force_fresh_baseline: bool = False, use_shift_baselines: bool = True) -> Dict[str, Any]:
#     """
#     ✅ FIXED: Use SHIFT baselines (not global baselines) for accurate production tracking
    
#     Args:
#         use_shift_baselines: If True, use shift-specific baselines (for worker)
#                             If False, use global baselines (for manual checks)
#     """
#     from services.scale_service import get_scada_reading, calculate_deltas
    
#     # ✅ CRITICAL: Refresh order to ensure we have latest baseline values from database
#     # This ensures we read fresh shift baselines, not stale cached values
#     if db is not None:
#         try:
#             db.refresh(order)
#         except Exception:
#             pass  # If refresh fails, continue with current order state
    
#     main_equipment = classification.get("equipment", []) or []
#     if not main_equipment:
#         return {"error": "No main equipment mapped", "total": 0.0}
    
#     order_type = classification.get("order_type")
#     packing_info = classification.get("packing_info", {}) or {}
    
#     # ================================================================
#     # ✅ CRITICAL FIX: Use SHIFT baselines (not global baselines)
#     # This ensures production is calculated from shift start, preserving
#     # previous production when order is restarted
#     # ================================================================
#     baselines_main = {}
    
#     if use_shift_baselines:
#         # ✅ Use shift-specific baselines (for worker - accurate after restart)
#         current_shift = get_attr_safe(order, "current_shift", "A")
#         shift_baseline_field = f"baseline_shift_{current_shift.lower()}_start"
#         shift_baselines = get_attr_safe(order, shift_baseline_field, None)
        
#         if shift_baselines and isinstance(shift_baselines, dict):
#             # ✅ CRITICAL FIX: Handle both simple dict format {'TAG': float} and nested dict format {'TAG': {'current': float}}
#             # Extract current values if nested dict format is detected
#             baselines_main = {}
#             for tag in main_equipment:
#                 if tag in shift_baselines:
#                     value = shift_baselines[tag]
#                     # Handle nested dict format {'current': val, 'delta': val}
#                     if isinstance(value, dict):
#                         current_val = float(value.get('current', 0.0) or 0.0)
#                     else:
#                         current_val = float(value or 0.0)
#                     baselines_main[tag] = current_val
#                 else:
#                     # Tag not in shift baselines, use global baseline as fallback
#                     baseline_attr = f"baseline_{tag.lower()}"
#                     baselines_main[tag] = float(get_attr_safe(order, baseline_attr, 0.0) or 0.0)
#             print(f"✅ Using SHIFT baselines for production calculation: {baselines_main}")
#         else:
#             # Fallback to global baselines if shift baselines not found
#             print(f"⚠️ Shift baselines not found, falling back to global baselines")
#             for tag in main_equipment:
#                 baseline_attr = f"baseline_{tag.lower()}"
#                 baselines_main[tag] = float(get_attr_safe(order, baseline_attr, 0.0) or 0.0)
#     else:
#         # Use global baselines (for manual checks or initial setup)
#         for tag in main_equipment:
#             baseline_attr = f"baseline_{tag.lower()}"
#             baselines_main[tag] = float(get_attr_safe(order, baseline_attr, 0.0) or 0.0)
    
#     # ================================================================
#     # Calculate deltas from baselines
#     # ================================================================
#     deltas_main = calculate_deltas(main_equipment, baselines_main, order, db=db)
#     per_tag_delta_main = {tag: float(info.get("delta", 0.0) or 0.0) for tag, info in deltas_main.items()}
    
#     # ================================================================
#     # Calculate total production
#     # ================================================================
#     if order_type == "MILLING" and classification.get("formula"):
#         formula = classification["formula"]
#         total_main = evaluate_formula_using_deltas(formula, per_tag_delta_main)
#     else:
#         total_main = sum(per_tag_delta_main.values())
    
#     # Convert to bags if PACKING
#     if order_type == "PACKING":
#         bag_size = float(packing_info.get("bag_size_kg") or 1.0)
#         total_main = total_main * bag_size
    
#     # ============================================================
#     # NEW: For a BRAND-NEW order, hide the first SCADA jump
#     # so UI starts at 0.00 KG and delta = 0.0 for all scales.
#     # ============================================================
#     po_number = get_attr_safe(order, "order_id", "UNKNOWN")
#     confirmed_qty_check = float(get_attr_safe(order, "confirmed_qty", 0.0) or 0.0)
#     weight_a_check = float(get_attr_safe(order, "weight_shift_a", 0.0) or 0.0)
#     weight_b_check = float(get_attr_safe(order, "weight_shift_b", 0.0) or 0.0)
#     weight_c_check = float(get_attr_safe(order, "weight_shift_c", 0.0) or 0.0)
#     is_truly_brand_new = (
#         confirmed_qty_check == 0.0
#         and weight_a_check == 0.0
#         and weight_b_check == 0.0
#         and weight_c_check == 0.0
#     )

#     if is_truly_brand_new:
#         # Use the same cache the worker uses
#         current_shift = get_attr_safe(order, "current_shift", "A").lower()
#         cache_key = (po_number, current_shift)
#         last_total_production = _last_shift_production_cache.get(cache_key, 0.0)

#         # ✅ IMPROVED LOGIC: Hide small deltas for brand-new orders
#         # This handles both cases:
#         # 1. Worker hasn't run yet (cache=0) - hide any SCADA jump
#         # 2. Worker has run first cycle (cache > 0) - hide if delta is small (< 2.0 kg)
#         #    because small deltas are likely SCADA settling from previous order, not real production
#         should_hide_delta = False
        
#         if last_total_production == 0.0 and total_main > 0.0:
#             # Worker hasn't run yet, but we see SCADA jump - hide it
#             should_hide_delta = True
#             print(
#                 f"🔍 [{po_number}] get_current_production: brand-new order, "
#                 f"worker hasn't run yet, total_main={total_main:.2f} – hiding as 0.0 for UI"
#             )
#         elif last_total_production > 0.0 and total_main > 0.0 and total_main <= 2.0:
#             # Worker has run, but delta is very small (< 2.0 kg) - likely SCADA settling, hide it
#             should_hide_delta = True
#             print(
#                 f"🔍 [{po_number}] get_current_production: brand-new order, "
#                 f"small delta detected (total_main={total_main:.2f}, cache={last_total_production:.2f}) – "
#                 f"likely SCADA settling, hiding as 0.0 for UI"
#             )
        
#         if should_hide_delta:
#             # Force all per-scale deltas to 0
#             for tag in per_tag_delta_main.keys():
#                 per_tag_delta_main[tag] = 0.0
#             for tag, info in deltas_main.items():
#                 # keep baseline, but set current = baseline and delta = 0
#                 baseline_val = float(info.get("baseline", 0.0) or 0.0)
#                 info["baseline"] = baseline_val
#                 info["current"] = baseline_val
#                 info["delta"] = 0.0

#             # And total production for UI = 0
#             total_main = 0.0
    
#     # ================================================================
#     # Get byproduct baselines (if MILLING)
#     # ================================================================
#     byp_tags = [get_attr_safe(order, "scale1"), get_attr_safe(order, "scale2"), get_attr_safe(order, "scale3")]
#     byp_tags = [t for t in byp_tags if t]
#     byproduct_baselines = {tag: float(get_attr_safe(order, f"baseline_{tag.lower()}", 0.0) or 0.0) for tag in byp_tags}
    
#     return {
#         "total": total_main,
#         "deltas": deltas_main,
#         "baselines": baselines_main,
#         "per_scale": per_tag_delta_main,
#         "byproduct_baselines": byproduct_baselines,
#     }

# def check_order_completion(order, classification: Dict) -> Dict[str, Any]:
#     """
#     Check if order is complete. Uses confirmed_qty which is already updated by the worker.
#     ✅ CRITICAL: The worker already updates confirmed_qty = preserved_confirmed_qty + total_production
#     So we just need to check if confirmed_qty >= target_qty
#     """
#     # ✅ CRITICAL: Use confirmed_qty directly (worker already updates it correctly)
#     # The worker calculates: display_total = preserved_confirmed_qty + total_production
#     # And sets: confirmed_qty = min(display_total, target_qty)
#     # So confirmed_qty is already the total production (capped at target)
#     existing_confirmed = float(get_attr_safe(order, "confirmed_qty", 0.0) or 0.0)
    
#     # Get fresh production for variance calculation
#     if get_attr_safe(order, "shift_end_time"):
#     # Do NOT take SCADA deltas after shift end (would double count)
#         new_production = 0.0
#     else:
#         prod_info = get_current_production(order, classification)
#         new_production = float(prod_info.get("total", 0.0) or 0.0)
#     # new_production = float(prod_info.get("total", 0.0) or 0.0) if not prod_info.get("error") else 0.0
    
#     # ✅ CRITICAL: For completion check, use confirmed_qty + new_production to get the actual total
#     # (confirmed_qty might be capped at target, but we need to check if total production >= target)
#     total_actual = existing_confirmed
    
#     order_type = classification["order_type"]
#     if order_type == "MILLING":
#         target_qty = float(get_attr_safe(order, "expected_weight") or get_attr_safe(order, "quantity") or 0.0)
#         unit = "KG"
#     else:
#         target_qty = float(get_attr_safe(order, "quantity") or 0.0)
#         unit = "BAG"
    
#     if target_qty == 0:
#         return {"is_complete": False, "error": "Invalid target quantity"}
    
#     overall_variance = total_actual - target_qty
#     overall_variance_pct = (overall_variance / target_qty) * 100.0 if target_qty > 0 else 0.0
    
#     # ✅ CRITICAL: Check completion using both methods:
#     # 1. total_actual >= target_qty (includes latest production)
#     # 2. confirmed_qty >= target_qty (worker already capped it at target)
#     # Order is complete if either condition is true
#     is_complete = (total_actual >= target_qty) or (existing_confirmed >= target_qty)
    
#     overflow = max(0.0, total_actual - target_qty)
    
#     # Log completion check for debugging
#     if existing_confirmed >= target_qty * 0.99:  # Log when close to completion
#         print(f"🔍 [Completion Check] confirmed_qty={existing_confirmed:.2f}, target={target_qty:.2f}, total_actual={total_actual:.2f}, is_complete={is_complete}")
    
#     return {
#         "is_complete": is_complete,
#         "actual_qty": round(total_actual, 3),
#         "target_qty": round(target_qty, 3),
#         "variance": round(overall_variance, 3),
#         "variance_pct": round(overall_variance_pct, 2),
#         "overflow": round(overflow, 3),
#         "unit": unit
#     }
# def update_order_scales(order, deltas: Dict) -> None:
#     """
#     Update scale quantities.

#     ✔ MILLING:
#         - DO NOT update byproduct scale quantities.
#         - Byproduct scale1/2/3 quantities are captured ONCE at order start.

#     ✔ PACKING:
#         - Convert pallets -> bags
#         - Update scale1/2/3 quantities dynamically
#     """

#     order_type = (get_attr_safe(order, "order_type", "") or "").strip().upper()

#     # --------------------------------------------------------
#     # MILLING — DO NOT TOUCH BYPRODUCT QUANTITIES
#     # --------------------------------------------------------
#     if order_type == "MILLING":
#         # Byproduct scale1/2/3_qty remain fixed after initialization.
#         # Deliberately do nothing here.
#         return

#     # --------------------------------------------------------
#     # PACKING — UPDATE SCALE QUANTITIES (PALLETS → BAGS)
#     # --------------------------------------------------------
#     if order_type == "PACKING":
#         classification = classify_order(order)
#         packing_info = classification.get("packing_info", {})
#         bags_per_pallet = float(packing_info.get("bag_size_kg") or 1)

#         scale1_tag = str(get_attr_safe(order, "scale1") or "").upper()
#         scale2_tag = str(get_attr_safe(order, "scale2") or "").upper()
#         scale3_tag = str(get_attr_safe(order, "scale3") or "").upper()

#         for tag, delta_info in deltas.items():
#             pallets = float(delta_info.get("delta", 0.0) or 0.0)
#             if pallets <= 0:
#                 continue

#             bags = pallets * bags_per_pallet
#             tag_cmp = str(tag or "").upper()

#             if tag_cmp == scale1_tag:
#                 set_attr_safe(order, "scale1_qty", bags)
#             elif tag_cmp == scale2_tag:
#                 set_attr_safe(order, "scale2_qty", bags)
#             elif tag_cmp == scale3_tag:
#                 set_attr_safe(order, "scale3_qty", bags)

#         return


# def serialize_order(row: Any) -> Dict[str, Any]:
#     def format_datetime(dt):
#         if dt is None:
#             return None
#         if hasattr(dt, 'isoformat'):
#             return dt.isoformat()
#         return str(dt)

#     return {
#         "id": get_attr_safe(row, "id"),
#         "po_number": get_attr_safe(row, "order_id"),
#         "material": get_attr_safe(row, "material"),
#         "version": get_attr_safe(row, "version"),
#         "batch": get_attr_safe(row, "batch"),
#         "quantity": get_attr_safe(row, "quantity"),
#         "unit": get_attr_safe(row, "unit") or get_attr_safe(row, "uom"),
#         "status": get_attr_safe(row, "status", "Pending"),
#         "priority": get_attr_safe(row, "priority", 0),
#         "expected_weight": get_attr_safe(row, "expected_weight"),
#         "confirmed_qty": get_attr_safe(row, "confirmed_qty"),
#         "last_confirmed_qty": get_attr_safe(row, "last_confirmed_qty", 0),
#         "is_final_sent": get_attr_safe(row, "is_final_sent", False),
#         "validation_method": get_attr_safe(row, "validation_method"),
#         "order_type": get_attr_safe(row, "order_type"),
#         "confirmed_text": get_attr_safe(row, "confirmed_text"),
#         "created_at": format_datetime(get_attr_safe(row, "created_at")),
#         "scale1": get_attr_safe(row, "scale1"),
#         "scale1_qty": get_attr_safe(row, "scale1_qty"),
#         "scale2": get_attr_safe(row, "scale2"),
#         "scale2_qty": get_attr_safe(row, "scale2_qty"),
#         "scale3": get_attr_safe(row, "scale3"),
#         "scale3_qty": get_attr_safe(row, "scale3_qty"),
#     }


# # =============================================================================
# # SHIFT HELPERS (unchanged except where needed)
# # =============================================================================



# def calculate_shift_weight(order, shift: str, classification: Dict, db=None) -> float:
#     """
#     Calculate total production weight for a specific shift.
    
#     ✅ CRITICAL: Always uses the latest baseline from database to prevent using stale baselines after restart.
    
#     Returns:
#         - MILLING: Weight in KG (from formula or sum of deltas)
#         - PACKING: Count in PALLETS (will be converted to bags later)
#     """
#     try:
#         equipment = classification["equipment"]
#         formula = classification.get("formula", "")
#         order_type = classification.get("order_type")
#         po_number = get_attr_safe(order, "order_id", "UNKNOWN")

#         if not equipment:
#             return 0.0

#         # ✅ CRITICAL: Refresh order from database to ensure we have latest baseline values
#         # This is especially important after restart when baseline was just updated
#         if db is not None:
#             try:
#                 db.refresh(order)
#                 print(f"✅ [{po_number}] calculate_shift_weight: Refreshed order from database to get latest baseline")
#             except Exception as e:
#                 print(f"⚠️ [{po_number}] calculate_shift_weight: Failed to refresh order: {e}")

#         # Get baseline for this shift
#         baseline_field = f"baseline_shift_{shift.lower()}_start"
#         shift_baselines = get_attr_safe(order, baseline_field, None)
        
#         # ✅ CRITICAL DEBUG: Log baseline source to help troubleshoot
#         if shift_baselines:
#             print(f"🔍 [{po_number}] calculate_shift_weight: Using shift baseline from {baseline_field}: {shift_baselines}")
#         else:
#             print(f"⚠️ [{po_number}] calculate_shift_weight: No shift baseline found in {baseline_field}, will use global baseline")

#         # If we have shift-specific baselines, use them
#         if shift_baselines and isinstance(shift_baselines, dict):
#             # ✅ CRITICAL FIX: Handle both simple dict format {'TAG': float} and nested dict format {'TAG': {'current': float}}
#             # Extract current values if nested dict format is detected
#             baselines = {}
#             for tag in equipment:
#                 if tag in shift_baselines:
#                     value = shift_baselines[tag]
#                     # Handle nested dict format {'current': val, 'delta': val}
#                     if isinstance(value, dict):
#                         current_val = float(value.get('current', 0.0) or 0.0)
#                     else:
#                         current_val = float(value or 0.0)
#                     baselines[tag] = current_val
#                 else:
#                     # Tag not in shift baselines, use global baseline as fallback
#                     baseline_attr = f"baseline_{tag.lower()}"
#                     baselines[tag] = float(get_attr_safe(order, baseline_attr, 0.0) or 0.0)
#             baseline_source = "shift_baselines"
#         else:
#             # Fallback to regular baselines (shouldn't happen in normal flow)
#             baselines = {}
#             for tag in equipment:
#                 baseline_attr = f"baseline_{tag.lower()}"
#                 baselines[tag] = float(get_attr_safe(order, baseline_attr, 0.0) or 0.0)
#             baseline_source = "regular_baselines"
#             print(f"⚠️ [{po_number}] calculate_shift_weight: No shift baselines found for shift {shift}, using regular baselines")

#         # ✅ ADD DEBUG: Print baselines
#         if int(time.time()) % 30 == 0:
#             print(f"🔍 [{po_number}] Baselines from {baseline_source}: {baselines}")

#         # Compute deltas
#         deltas = calculate_deltas(equipment, baselines, order=order, db=None)
#         per_tag_delta = {tag: float(deltas[tag].get("delta", 0.0) or 0.0) for tag in equipment}

#         # ✅ ADD DEBUG: Print deltas
#         if int(time.time()) % 30 == 0:
#             print(f"🔍 [{po_number}] Deltas: {per_tag_delta}")

#         # ---- MILLING ---- use formula (same as live production)
#         if order_type == "MILLING" and formula:
#             result = evaluate_formula_using_deltas(formula, per_tag_delta)
            
#             # ✅ CRITICAL DEBUG: Check if result is reasonable
#             sum_of_deltas = sum(per_tag_delta.values())
#             if int(time.time()) % 30 == 0:
#                 print(f"🔍 [{po_number}] calculate_shift_weight MILLING:")
#                 print(f"  Formula: {formula}")
#                 print(f"  Deltas: {per_tag_delta}")
#                 print(f"  Formula result: {result:.2f} KG")
#                 print(f"  Sum of deltas: {sum_of_deltas:.2f}")
#                 if sum_of_deltas > 0:
#                     ratio = result / sum_of_deltas
#                     print(f"  Ratio (formula/sum): {ratio:.2f}")
#                     if ratio > 5.0:
#                         print(f"  ⚠️ WARNING: Formula result is {ratio:.1f}x larger than sum of deltas - possible multiplication issue!")
#                 else:
#                     print(f"  Ratio: N/A (sum of deltas is 0)")
            
#             return result

#         # ---- PACKING ---- simply sum delta (in pallet count, will be converted to bags later)
#         result = sum(per_tag_delta.values())
#         # Debug logging for PACKING
#         if int(time.time()) % 30 == 0:
#             print(f"🔍 [{po_number}] calculate_shift_weight PACKING: deltas={per_tag_delta}, result={result:.2f} pallets (from {baseline_source})")
#         return result

#     except Exception as e:
#         po_number = get_attr_safe(order, "order_id", "UNKNOWN")
#         print(f"❌ [{po_number}] Error calculating shift weight: {e}")
#         import traceback
#         traceback.print_exc()
#         return 0.0




# # def end_shift_and_confirm(order, current_shift: str, classification: Dict, sap_service, force_final: bool = False) -> Dict[str, Any]:
# #     """
# #     ✅ FIXED: End shift and send remaining production to SAP.
    
# #     Key fixes:
# #     - DON'T update confirmed_qty (auto-validator handles it)
# #     - DON'T use last_confirmed_qty (not needed)
# #     - Only send REMAINING production (weight_shift_X - confirmed_shift_X)
# #     - Track confirmations in confirmed_shift_X columns
# #     """
# #     try:
# #         shift_weight = calculate_shift_weight(order, current_shift, classification)
        
# #         order_type = classification["order_type"]
# #         if order_type == "MILLING":
# #             target = float(get_attr_safe(order, "expected_weight") or get_attr_safe(order, "quantity") or 0.0)
# #             shift_weight_stored = shift_weight
# #             uom = "KG"
# #         else:
# #             # PACKING: Convert pallets to bags
# #             target = float(get_attr_safe(order, "quantity") or 0.0)
# #             packing_info = classification.get("packing_info", {})
# #             bags_per_pallet = packing_info.get("bag_size_kg", 1)
# #             shift_weight_stored = shift_weight * bags_per_pallet
# #             uom = "BAG"
        
# #         # ✅ CRITICAL: Store shift production in weight_shift_X (ACCUMULATE, don't overwrite)
# #         # When restarting in the same shift, we need to add to existing weight, not replace it
# #         try:
# #             shift_field = f"weight_shift_{current_shift.lower()}"
# #             # ✅ Read existing shift weight (may have production from before restart)
# #             existing_shift_weight = float(get_attr_safe(order, shift_field, 0.0) or 0.0)
            
# #             # ✅ Accumulate: Add new production to existing shift weight
# #             accumulated_shift_weight = existing_shift_weight + shift_weight_stored
# #             set_attr_safe(order, shift_field, accumulated_shift_weight)
# #             set_attr_safe(order, "shift_end_time", datetime.now())
            
# #             if existing_shift_weight > 0.0:
# #                 print(f"✅ Shift {current_shift}: Accumulated weight {existing_shift_weight:.2f} + new {shift_weight_stored:.2f} = {accumulated_shift_weight:.2f} {uom}")
# #             else:
# #             print(f"✅ Shift {current_shift}: Produced {shift_weight_stored:.2f} {uom}")
# #         except Exception as e:
# #             print(f"⚠️ Failed to record shift weight: {e}")
        
# #         # ================================================================
# #         # ✅ CHECK REMAINING PRODUCTION (deduplication)
# #         # ================================================================
# #         shift_weight_field = f"weight_shift_{current_shift.lower()}"
# #         confirmed_field = f"confirmed_shift_{current_shift.lower()}"
        
# #         total_shift_production = float(get_attr_safe(order, shift_weight_field, 0.0) or 0.0)
# #         already_confirmed_for_shift = float(get_attr_safe(order, confirmed_field, 0.0) or 0.0)
        
# #         remaining_shift_production = total_shift_production - already_confirmed_for_shift
        
# #         # ================================================================
# #         # ✅ CALCULATE TOTAL CONFIRMED TO SAP (from all shifts)
# #         # ================================================================
# #         confirmed_shift_a = float(get_attr_safe(order, "confirmed_shift_a", 0.0) or 0.0)
# #         confirmed_shift_b = float(get_attr_safe(order, "confirmed_shift_b", 0.0) or 0.0)
# #         confirmed_shift_c = float(get_attr_safe(order, "confirmed_shift_c", 0.0) or 0.0)
        
# #         total_confirmed_to_sap = confirmed_shift_a + confirmed_shift_b + confirmed_shift_c
        
# #         print(f"📊 Total confirmed to SAP: {total_confirmed_to_sap:.2f} {uom}")
# #         print(f"   Shift A: {confirmed_shift_a:.2f}, Shift B: {confirmed_shift_b:.2f}, Shift C: {confirmed_shift_c:.2f}")
        
# #         # ================================================================
# #         # ✅ CALCULATE REMAINING TO TARGET
# #         # ================================================================
# #         remaining_to_target = target - total_confirmed_to_sap
        
# #         # ✅ CRITICAL: If force_final=True (order is complete), always send final confirmation
# #         # even if there's no remaining shift production or already fully confirmed
# #         if force_final:
# #             if remaining_to_target > 0:
# #                 # Order is complete but not fully confirmed to SAP - send remaining as final confirmation
# #                 confirm_qty = remaining_to_target
# #                 print(f"🔔 FORCE FINAL: Order complete, sending remaining {confirm_qty:.2f} {uom} as final confirmation")
# #             else:
# #                 # Order is complete and already fully confirmed to SAP - send 0 quantity with final flag
# #                 # This ensures the final_confirmation flag is set in SAP
# #                 confirm_qty = 0.0
# #                 print(f"🔔 FORCE FINAL: Order complete and already fully confirmed to SAP. Sending final confirmation flag with 0 quantity.")
# #         elif remaining_shift_production <= 0:
# #             # No remaining shift production and not forcing final
# #             if remaining_to_target <= 0:
# #                 print(f"✅ Shift {current_shift} fully confirmed. Order already fully confirmed to SAP.")
# #                 plant = get_attr_safe(order, "plant", "3130")
# #                 department = "MILLING" if order_type == "MILLING" else "PACKING"
# #                 with _db_session() as db:
# #                     next_shift_row = get_next_shift(current_shift, plant, department, db)
# #                     next_shift = next_shift_row.shift_code if next_shift_row else "A"
# #                 return {
# #                     "success": True,
# #                     "order_complete": False,
# #                     "next_shift": next_shift,
# #                     "confirmed_qty": 0.0,
# #                     "message": f"Shift {current_shift} already fully confirmed"
# #                 }
# #             else:
# #                 # Shift is confirmed but order not fully confirmed to SAP - use remaining to target
# #                 confirm_qty = remaining_to_target
# #                 print(f"⚠️ Shift {current_shift} confirmed but order not fully confirmed to SAP. Sending remaining {confirm_qty:.2f} {uom}")
# #         else:
# #             # Normal case: send remaining shift production (up to target)
# #         confirm_qty = min(remaining_shift_production, remaining_to_target)
        
# #         # ✅ CRITICAL: If force_final=True, always send even if confirm_qty is 0 (to set final flag)
# #         if confirm_qty <= 0 and not force_final:
# #             print(f"⚠️ No new production to confirm in Shift {current_shift}")
# #             plant = get_attr_safe(order, "plant", "3130")
# #             department = "MILLING" if order_type == "MILLING" else "PACKING"
# #             with _db_session() as db:
# #                 next_shift_row = get_next_shift(current_shift, plant, department, db)
# #                 next_shift = next_shift_row.shift_code if next_shift_row else "A"
# #             return {
# #                 "success": True,
# #                 "order_complete": False,
# #                 "next_shift": next_shift,
# #                 "confirmed_qty": 0.0,
# #                 "message": "No new confirmation needed"
# #             }
        
# #         print(f"📤 Sending to SAP: {confirm_qty:.2f} {uom}")
# #         print(f"   (Shift total: {total_shift_production:.2f}, Already sent: {already_confirmed_for_shift:.2f})")
        
# #         new_total_confirmed_to_sap = total_confirmed_to_sap + confirm_qty
# #         # ✅ CRITICAL: If force_final=True, always set final_confirmation flag
# #         is_final_confirmation = force_final or (new_total_confirmed_to_sap >= target)

# #         print(f"🔍 Final check: {new_total_confirmed_to_sap:.2f} >= {target:.2f} = {is_final_confirmation} (force_final={force_final})")
        
# #         # ================================================================
# #         # ✅ BUILD SAP PAYLOAD
# #         # ✅ CRITICAL: Always include byproduct scales (even if order not validated)
# #         # ================================================================
# #         # ✅ CRITICAL: Refresh order to get latest scale values from database
# #         # This ensures we have the most up-to-date scale values
# #         try:
# #             # If order is in a session, refresh it
# #             if hasattr(order, '__session__') or hasattr(order, '_sa_instance_state'):
# #                 # Order is already in a session, we can't refresh here
# #                 # But we can ensure we read the latest values
# #                 pass
# #         except:
# #             pass
        
# #         # ✅ CRITICAL: Read scale values with proper defaults
# #         # Ensure byproduct scales are always included, even if None or 0
# #         scale1_tag = get_attr_safe(order, "scale1") or ""
# #         scale1_qty_val = float(get_attr_safe(order, "scale1_qty", 0.0) or 0.0)
# #         scale2_tag = get_attr_safe(order, "scale2") or ""
# #         scale2_qty_val = float(get_attr_safe(order, "scale2_qty", 0.0) or 0.0)
# #         scale3_tag = get_attr_safe(order, "scale3") or ""
# #         scale3_qty_val = float(get_attr_safe(order, "scale3_qty", 0.0) or 0.0)
        
# #         print(f"📊 [SAP Payload] Byproduct scales: scale1={scale1_tag} ({scale1_qty_val:.2f}), scale2={scale2_tag} ({scale2_qty_val:.2f}), scale3={scale3_tag} ({scale3_qty_val:.2f})")
        
# #         order_data = {
# #             'po_number': order.order_id,
# #             'confirmed_weight': confirm_qty,  # ✅ Only remaining
# #             'last_confirmed_qty': 0,  # For SAP reference
# #             'total_qty': target,
# #             'material': get_attr_safe(order, "material"),
# #             'version': get_attr_safe(order, "version"),
# #             'material_desc': get_attr_safe(order, "material_desc"),
# #             'batch': get_attr_safe(order, "batch"),
# #             'uom': uom,
# #             'plant': get_attr_safe(order, "plant"),
# #             'created_at': get_attr_safe(order, "created_at"),
# #             'shift': current_shift,
# #             'validation_method': 'Automatic',
# #             'confirmed_text': f'Auto: {"FINAL " if is_final_confirmation else ""}Shift {current_shift} End - {confirm_qty:.2f} {uom}',
# #             'scrap': get_attr_safe(order, "scrap", 0) or 0,
# #             # ✅ CRITICAL: Always include byproduct scales (even if empty/None)
# #             # This ensures they appear in SAP payload for mid-shift and end-shift confirmations
# #             'scale1': scale1_tag,
# #             'scale1_qty': scale1_qty_val,
# #             'scale2': scale2_tag,
# #             'scale2_qty': scale2_qty_val,
# #             'scale3': scale3_tag,
# #             'scale3_qty': scale3_qty_val,
# #             'final_confirmation': "X" if is_final_confirmation else ""
# #         }
        
# #         # ================================================================
# #         # ✅ SEND TO SAP
# #         # ================================================================
# #         sap_result = sap_service.push_confirmation([order_data], 'online')
        
# #         if sap_result.get('success'):
# #             # ================================================================
# #             # ✅ UPDATE DATABASE (DON'T touch confirmed_qty!)
# #             # ================================================================
            
# #             # Update confirmed_shift_X to accumulate what was sent
# #             new_shift_confirmed = already_confirmed_for_shift + confirm_qty
# #             set_attr_safe(order, confirmed_field, new_shift_confirmed)
            
# #             print(f"✅ Updated {confirmed_field} from {already_confirmed_for_shift:.2f} to {new_shift_confirmed:.2f}")
            
# #             # ✅ DON'T update confirmed_qty - auto-validator handles it
# #             # ✅ DON'T update last_confirmed_qty - we don't use it anymore
            
# #             # Handle overflow (if shift produced more than target)
# #             overflow = max(0, new_total_confirmed_to_sap - target)
# #             if overflow > 0:
# #                 set_attr_safe(order, "overflow_weight", overflow)
# #                 print(f"⚠️ Overflow: {overflow:.2f} {uom}")
            
# #             # ================================================================
# #             # ✅ CHECK ORDER COMPLETION (based on SAP confirmations)
# #             # ================================================================
# #             if new_total_confirmed_to_sap >= target:
# #                 set_attr_safe(order, "is_target_reached", True)
# #                 set_attr_safe(order, "status", "Validated")
# #                 set_attr_safe(order, "validation_method", "Automatic")
# #                 set_attr_safe(order, "is_final_sent", True)
                
# #                 print(f"✅ ORDER COMPLETE: {new_total_confirmed_to_sap:.2f}/{target:.2f} {uom}")
# #                 print(f"   Shift A: {confirmed_shift_a:.2f}, Shift B: {confirmed_shift_b:.2f}, Shift C: {confirmed_shift_c:.2f}")
                
# #                 return {
# #                     "success": True,
# #                     "order_complete": True,
# #                     "confirmed_qty": confirm_qty,
# #                     "message": f"Order completed in shift {current_shift}"
# #                 }
# #             else:
# #                 # Order not complete - get next shift
# #                 plant = get_attr_safe(order, "plant", "3130")
# #                 department = "MILLING" if order_type == "MILLING" else "PACKING"
                
# #                 with _db_session() as db:
# #                     next_shift_row = get_next_shift(current_shift, plant, department, db)
# #                     next_shift = next_shift_row.shift_code if next_shift_row else "A"
                
# #                 print(f"✅ Shift {current_shift} ended. Confirmed {confirm_qty:.2f} {uom}. Next: {next_shift}")
# #                 print(f"   Progress: {new_total_confirmed_to_sap:.2f}/{target:.2f} {uom} ({(new_total_confirmed_to_sap/target*100):.1f}%)")
                
# #                 return {
# #                     "success": True,
# #                     "order_complete": False,
# #                     "next_shift": next_shift,
# #                     "confirmed_qty": confirm_qty,
# #                     "message": f"Shift {current_shift} completed"
# #                 }
# #         else:
# #             error_msg = sap_result.get('message', 'Unknown SAP error')
# #             print(f"❌ SAP Failed: {error_msg}")
# #             return {
# #                 "success": False,
# #                 "message": f"SAP confirmation failed: {error_msg}",
# #                 "confirmed_qty": 0.0,
# #                 "order_complete": False
# #             }
    
# #     except Exception as e:
# #         print(f"❌ Error ending shift: {e}")
# #         import traceback
# #         traceback.print_exc()
# #         return {
# #             "success": False,
# #             "message": str(e),
# #             "confirmed_qty": 0.0,
# #             "order_complete": False
# #         }

# def end_shift_and_confirm(order, current_shift: str, classification: Dict, sap_service, force_final: bool = False) -> Dict[str, Any]:
#     """
#     End shift and send remaining production to SAP.
    
#     CRITICAL RULES:
#     1. NEVER modify weight_shift_X (only READ it)
#     2. Only send ACTUAL production (not target)
#     3. Track confirmations in confirmed_shift_X
#     """
#     try:
#         po_number = get_attr_safe(order, "order_id", "UNKNOWN")
        
#         # ================================================================
#         # ✅ DETERMINE ORDER TYPE AND TARGET
#         # ================================================================
#         order_type = classification["order_type"]
#         if order_type == "MILLING":
#             target = float(get_attr_safe(order, "expected_weight") or get_attr_safe(order, "quantity") or 0.0)
#             uom = "KG"
#         else:
#             target = float(get_attr_safe(order, "quantity") or 0.0)
#             uom = "BAG"
        
#         # ================================================================
#         # ✅ READ EXISTING SHIFT PRODUCTION (DON'T MODIFY!)
#         # ================================================================
#         shift_field = f"weight_shift_{current_shift.lower()}"
#         total_shift_production = float(get_attr_safe(order, shift_field, 0.0) or 0.0)
        
#         # ❌ DELETE ANY CODE THAT DOES THIS:
#         # set_attr_safe(order, shift_field, anything)  # NEVER MODIFY weight_shift_X here!
        
#         # ✅ Just mark shift end time
#         set_attr_safe(order, "shift_end_time", datetime.now())
        
#         print(f"✅ [{po_number}] Shift {current_shift} actual production = {total_shift_production:.2f} {uom}")
#         print(f"   Target = {target:.2f} {uom}")
        
#         # ❌ CRITICAL CHECK: Make sure we're using ACTUAL production, not target!
#         if total_shift_production == target and total_shift_production > 0:
#             print(f"⚠️ [{po_number}] WARNING: Shift production exactly equals target!")
#             print(f"   This might indicate a bug where target is being used instead of actual production")
#             print(f"   Verify weight_shift_{current_shift.lower()} in database is correct")
        
#         # ================================================================
#         # ✅ CHECK REMAINING PRODUCTION (deduplication)
#         # ================================================================
#         confirmed_field = f"confirmed_shift_{current_shift.lower()}"
#         already_confirmed_for_shift = float(get_attr_safe(order, confirmed_field, 0.0) or 0.0)
        
#         # ✅ CRITICAL: Use ACTUAL production, not target!
#         remaining_shift_production = total_shift_production - already_confirmed_for_shift
        
#         print(f"   Total shift production: {total_shift_production:.2f}")
#         print(f"   Already confirmed: {already_confirmed_for_shift:.2f}")
#         print(f"   Remaining to send: {remaining_shift_production:.2f}")
        
#         # ================================================================
#         # ✅ CALCULATE TOTAL CONFIRMED TO SAP (from all shifts)
#         # ================================================================
#         confirmed_shift_a = float(get_attr_safe(order, "confirmed_shift_a", 0.0) or 0.0)
#         confirmed_shift_b = float(get_attr_safe(order, "confirmed_shift_b", 0.0) or 0.0)
#         confirmed_shift_c = float(get_attr_safe(order, "confirmed_shift_c", 0.0) or 0.0)
        
#         total_confirmed_to_sap = confirmed_shift_a + confirmed_shift_b + confirmed_shift_c
        
#         print(f"📊 Total confirmed to SAP: {total_confirmed_to_sap:.2f} {uom}")
#         print(f"   Shift A: {confirmed_shift_a:.2f}, Shift B: {confirmed_shift_b:.2f}, Shift C: {confirmed_shift_c:.2f}")
        
#         # ================================================================
#         # ✅ CALCULATE REMAINING TO TARGET
#         # ================================================================
#         remaining_to_target = target - total_confirmed_to_sap
        
#         # ================================================================
#         # ✅ DETERMINE CONFIRMATION QUANTITY
#         # Use ACTUAL production (remaining_shift_production), not target!
#         # ================================================================
#         if force_final:
#             if remaining_to_target > 0:
#                 # ✅ Send remaining to reach target (but don't exceed actual production)
#                 confirm_qty = min(remaining_to_target, remaining_shift_production)
#                 print(f"🔔 FORCE FINAL: Sending {confirm_qty:.2f} {uom}")
#             else:
#                 confirm_qty = 0.0
#                 print(f"🔔 FORCE FINAL: Already at target, sending 0 with final flag")
#         elif remaining_shift_production <= 0:
#             if remaining_to_target <= 0:
#                 # Already confirmed
#                 print(f"✅ Shift {current_shift} fully confirmed")
#                 plant = get_attr_safe(order, "plant", "3130")
#                 department = "MILLING" if order_type == "MILLING" else "PACKING"
#                 with _db_session() as db:
#                     next_shift_row = get_next_shift(current_shift, plant, department, db)
#                     next_shift = next_shift_row.shift_code if next_shift_row else "A"
#                 return {
#                     "success": True,
#                     "order_complete": False,
#                     "next_shift": next_shift,
#                     "confirmed_qty": 0.0,
#                     "message": f"Shift {current_shift} already confirmed"
#                 }
#             else:
#                 # Shift confirmed but order not complete
#                 # ❌ DON'T send remaining_to_target if there's no production!
#                 confirm_qty = 0.0
#                 print(f"⚠️ Shift {current_shift} has no remaining production")
#         else:
#             # ✅ CRITICAL: Send ACTUAL production, capped at remaining target
#             confirm_qty = min(remaining_shift_production, remaining_to_target)
#             print(f"📤 Normal confirmation: {confirm_qty:.2f} {uom}")
#             print(f"   (min of remaining_production={remaining_shift_production:.2f}, remaining_target={remaining_to_target:.2f})")
        
#         # ✅ Check if there's anything to send
#         if confirm_qty <= 0 and not force_final:
#             print(f"⚠️ No production to confirm in Shift {current_shift}")
#             plant = get_attr_safe(order, "plant", "3130")
#             department = "MILLING" if order_type == "MILLING" else "PACKING"
#             with _db_session() as db:
#                 next_shift_row = get_next_shift(current_shift, plant, department, db)
#                 next_shift = next_shift_row.shift_code if next_shift_row else "A"
#             return {
#                 "success": True,
#                 "order_complete": False,
#                 "next_shift": next_shift,
#                 "confirmed_qty": 0.0,
#                 "message": "No new confirmation needed"
#             }
        
#         # ================================================================
#         # ✅ BUILD SAP PAYLOAD
#         # ================================================================
#         new_total_confirmed_to_sap = total_confirmed_to_sap + confirm_qty
#         is_final_confirmation = force_final or (new_total_confirmed_to_sap >= target)
        
#         print(f"📤 Sending to SAP: {confirm_qty:.2f} {uom}")
#         print(f"   (Shift total: {total_shift_production:.2f}, Already sent: {already_confirmed_for_shift:.2f})")
#         print(f"🔍 Final check: {new_total_confirmed_to_sap:.2f} >= {target:.2f} = {is_final_confirmation} (force_final={force_final})")
        
#         # Read scale values
#         scale1_tag = get_attr_safe(order, "scale1") or ""
#         scale1_qty_val = float(get_attr_safe(order, "scale1_qty", 0.0) or 0.0)
#         scale2_tag = get_attr_safe(order, "scale2") or ""
#         scale2_qty_val = float(get_attr_safe(order, "scale2_qty", 0.0) or 0.0)
#         scale3_tag = get_attr_safe(order, "scale3") or ""
#         scale3_qty_val = float(get_attr_safe(order, "scale3_qty", 0.0) or 0.0)
        
#         print(f"📊 [SAP Payload] Byproduct scales: scale1={scale1_tag} ({scale1_qty_val:.2f}), scale2={scale2_tag} ({scale2_qty_val:.2f}), scale3={scale3_tag} ({scale3_qty_val:.2f})")
        
#         order_data = {
#             'po_number': order.order_id,
#             'confirmed_weight': confirm_qty,
#             'last_confirmed_qty': 0,
#             'total_qty': target,
#             'material': get_attr_safe(order, "material"),
#             'version': get_attr_safe(order, "version"),
#             'material_desc': get_attr_safe(order, "material_desc"),
#             'batch': get_attr_safe(order, "batch"),
#             'uom': uom,
#             'plant': get_attr_safe(order, "plant"),
#             'created_at': get_attr_safe(order, "created_at"),
#             'shift': current_shift,
#             'validation_method': 'Automatic',
#             'confirmed_text': f'Auto: {"FINAL " if is_final_confirmation else ""}Shift {current_shift} End - {confirm_qty:.2f} {uom}',
#             'scrap': get_attr_safe(order, "scrap", 0) or 0,
#             'scale1': scale1_tag,
#             'scale1_qty': scale1_qty_val,
#             'scale2': scale2_tag,
#             'scale2_qty': scale2_qty_val,
#             'scale3': scale3_tag,
#             'scale3_qty': scale3_qty_val,
#             'final_confirmation': "X" if is_final_confirmation else ""
#         }
        
#         # ================================================================
#         # ✅ SEND TO SAP
#         # ================================================================
#         sap_result = sap_service.push_confirmation([order_data], 'online')
        
#         if sap_result.get('success'):
#             # ================================================================
#             # ✅ UPDATE DATABASE (Only confirmed_shift_X, NOT weight_shift_X)
#             # ================================================================
#             new_shift_confirmed = already_confirmed_for_shift + confirm_qty
#             set_attr_safe(order, confirmed_field, new_shift_confirmed)
            
#             # ✅ Update last_confirmed_qty with total of all shift confirmations
#             # Recalculate after updating the shift confirmation
#             confirmed_shift_a_after = float(get_attr_safe(order, "confirmed_shift_a", 0.0) or 0.0)
#             confirmed_shift_b_after = float(get_attr_safe(order, "confirmed_shift_b", 0.0) or 0.0)
#             confirmed_shift_c_after = float(get_attr_safe(order, "confirmed_shift_c", 0.0) or 0.0)
#             total_confirmed_after = confirmed_shift_a_after + confirmed_shift_b_after + confirmed_shift_c_after
#             set_attr_safe(order, "last_confirmed_qty", total_confirmed_after)
            
#             print(f"✅ Updated {confirmed_field} from {already_confirmed_for_shift:.2f} to {new_shift_confirmed:.2f}")
#             print(f"📊 Updated last_confirmed_qty: {total_confirmed_after:.2f} (A={confirmed_shift_a_after:.2f}, B={confirmed_shift_b_after:.2f}, C={confirmed_shift_c_after:.2f})")
            
#             # Handle overflow
#             overflow = max(0, new_total_confirmed_to_sap - target)
#             if overflow > 0:
#                 set_attr_safe(order, "overflow_weight", overflow)
#                 print(f"⚠️ Overflow: {overflow:.2f} {uom}")
            
#             # ================================================================
#             # ✅ CHECK ORDER COMPLETION
#             # ================================================================
#             if new_total_confirmed_to_sap >= target:
#                 set_attr_safe(order, "is_target_reached", True)
#                 set_attr_safe(order, "status", "Validated")
#                 set_attr_safe(order, "validation_method", "Automatic")
#                 set_attr_safe(order, "is_final_sent", True)
                
#                 print(f"✅ ORDER COMPLETE: {new_total_confirmed_to_sap:.2f}/{target:.2f} {uom}")
                
#                 return {
#                     "success": True,
#                     "order_complete": True,
#                     "confirmed_qty": confirm_qty,
#                     "message": f"Order completed in shift {current_shift}"
#                 }
#             else:
#                 # Get next shift
#                 plant = get_attr_safe(order, "plant", "3130")
#                 department = "MILLING" if order_type == "MILLING" else "PACKING"
                
#                 with _db_session() as db:
#                     next_shift_row = get_next_shift(current_shift, plant, department, db)
#                     next_shift = next_shift_row.shift_code if next_shift_row else "A"
                
#                 print(f"✅ Shift {current_shift} ended. Confirmed {confirm_qty:.2f} {uom}. Next: {next_shift}")
#                 print(f"   Progress: {new_total_confirmed_to_sap:.2f}/{target:.2f} {uom}")
                
#                 return {
#                     "success": True,
#                     "order_complete": False,
#                     "next_shift": next_shift,
#                     "confirmed_qty": confirm_qty,
#                     "message": f"Shift {current_shift} completed"
#                 }
#         else:
#             error_msg = sap_result.get('message', 'Unknown SAP error')
#             print(f"❌ SAP Failed: {error_msg}")
#             return {
#                 "success": False,
#                 "message": f"SAP confirmation failed: {error_msg}",
#                 "confirmed_qty": 0.0,
#                 "order_complete": False
#             }
    
#     except Exception as e:
#         po_number = get_attr_safe(order, "order_id", "UNKNOWN")
#         print(f"❌ [{po_number}] Error ending shift: {e}")
#         import traceback
#         traceback.print_exc()
#         return {
#             "success": False,
#             "message": str(e),
#             "confirmed_qty": 0.0,
#             "order_complete": False
#         }

# def init_and_start_order_worker(db, order, classification):
#     """
#     FINAL: Always reset SCADA equipment baseline columns on (re)start.
#     Preserves confirmed_qty. Does NOT skip baseline reset just because shift baselines exist.
#     """

#     po_number = order.order_id

#     # --- 1. Preserve confirmed_qty (never reset) ---
#     db.refresh(order)
#     confirmed_qty_so_far = float(order.confirmed_qty if hasattr(order, 'confirmed_qty') and order.confirmed_qty is not None else 0.0)
#     set_attr_safe(order, "confirmed_qty", confirmed_qty_so_far)
#     print(f"✅ [{po_number}] Preserved confirmed_qty on (re)start: {confirmed_qty_so_far:.2f}")
    
#     # 💥 CRITICAL FIX: CLEAR ALL OLD SHIFT BASELINES FOR NEW ORDER
#     # This ensures worker uses fresh baselines, not old shift baselines from previous order
#     print(f"🧹 [{po_number}] Clearing ALL old shift baselines for fresh start...")
#     for s in ["a", "b", "c"]:
#         set_attr_safe(order, f"baseline_shift_{s}_start", {})
#         set_attr_safe(order, f"baseline_shift_{s}_time", None)
#         print(f"🧹 [{po_number}] Cleared baseline_shift_{s}_start and baseline_shift_{s}_time")
    
#     # ✅ CRITICAL: Commit shift baseline clearing to database immediately
#     db.add(order)
#     db.flush()
#     db.commit()
#     db.refresh(order)
#     print(f"✅ [{po_number}] Shift baseline clearing committed to database")
    
#     # 💥 CRITICAL FIX: CLEAR ALL PRODUCTION CACHES FOR ALL SHIFTS
#     # This ensures worker starts fresh without any cached values from previous order
#     # ✅ CRITICAL: ALWAYS clear cache unconditionally - use pop() to avoid KeyError
#     # This ensures we remove any stale cache from deleted orders with the same PO number
#     print(f"🧹 [{po_number}] Clearing ALL production caches for all shifts...")
#     for s in ["a", "b", "c"]:
#         cache_key = (po_number, s)
#         # Use pop() with default to safely remove cache even if it doesn't exist
#         old_prod_cache = _last_shift_production_cache.pop(cache_key, None)
#         if old_prod_cache is not None:
#             print(f"🧹 [{po_number}] Cleared _last_shift_production_cache for shift {s.upper()} (had value: {old_prod_cache:.2f})")
#         old_max_cache = _max_shift_weight_cache.pop(cache_key, None)
#         if old_max_cache is not None:
#             print(f"🧹 [{po_number}] Cleared _max_shift_weight_cache for shift {s.upper()} (had value: {old_max_cache:.2f})")
    
#     print(f"✅ [{po_number}] All shift baselines and production caches cleared for fresh start")

#     # --- 2. Fetch equipment/scada baselines ---
#     order_type = classification.get("order_type")
#     equipment = classification.get("equipment", []) or []
#     if not equipment:
#         print(f"❌ [{po_number}] No equipment mapped")
#         return

#     # ✅ CRITICAL FIX: Reset ALL baseline columns to 0 first to ensure clean state
#     # This prevents old baseline values from interfering with new order baselines
#     print(f"🔄 [{po_number}] Resetting all baseline columns to 0 before capturing fresh SCADA values...")
#     # PACKING: Bag counter baselines
#     set_attr_safe(order, "baseline_sl601_counter", 0.0)
#     set_attr_safe(order, "baseline_sl602_counter", 0.0)
#     set_attr_safe(order, "baseline_sl603_counter", 0.0)
#     set_attr_safe(order, "baseline_sl606_counter", 0.0)
#     set_attr_safe(order, "baseline_sl607_counter", 0.0)
#     # MILLING: Flour/Bran output baselines
#     set_attr_safe(order, "baseline_wg101", 0.0)
#     set_attr_safe(order, "baseline_wg201", 0.0)
#     set_attr_safe(order, "baseline_wg202", 0.0)
#     set_attr_safe(order, "baseline_wg301", 0.0)
#     set_attr_safe(order, "baseline_wg302", 0.0)
#     set_attr_safe(order, "baseline_wg501", 0.0)
#     set_attr_safe(order, "baseline_wg502", 0.0)
#     set_attr_safe(order, "baseline_wg503", 0.0)
#     # WATER DOSING METER baselines
#     set_attr_safe(order, "baseline_dm101", 0.0)
#     set_attr_safe(order, "baseline_dm102", 0.0)
#     set_attr_safe(order, "baseline_dm201", 0.0)
#     set_attr_safe(order, "baseline_dm202", 0.0)
#     set_attr_safe(order, "baseline_dm203", 0.0)
    
#     # ✅ CRITICAL: Flush baseline reset to database BEFORE capturing fresh SCADA values
#     db.add(order)
#     db.flush()
    
#     # ✅ VERIFY: Refresh order to confirm baselines were reset
#     db.refresh(order)
#     print(f"✅ [{po_number}] All baseline columns reset to 0 and flushed to database")

#     # 💥 CRITICAL FIX: CLEAR SCADA CACHE BEFORE CAPTURING BASELINES
#     # This ensures we get FRESH SCADA values, not stale cached values from previous order
#     print(f"🧹 [{po_number}] Clearing SCADA cache before capturing baselines...")
#     try:
#         from services.scale_service import clear_scada_cache
#         clear_scada_cache()
#         print(f"✅ [{po_number}] SCADA cache cleared")
#     except Exception as e:
#         print(f"⚠️ [{po_number}] Could not clear SCADA cache: {e}")
    
#     # ✅ CRITICAL: Wait after clearing cache to ensure fresh values are available
#     time.sleep(0.3)

#     # ✅ CRITICAL: Longer delay before capturing baselines to ensure SCADA values have settled
#     # This is especially important when starting a new order immediately after previous one completes
#     # The delay ensures we capture truly fresh baselines, not residual values from previous order
#     # Increased delay to 1.0s to ensure previous order's SCADA values have fully cleared
#     # Take multiple readings to ensure we get stable, fresh values
#     print(f"⏳ [{po_number}] Waiting for SCADA values to settle before capturing baselines...")
#     time.sleep(1.0)
    
#     # ✅ CRITICAL: Take multiple baseline readings to ensure we get truly fresh values
#     # First reading might still have residual values from previous order
#     baselines_1 = capture_baseline_readings(equipment)
#     time.sleep(0.5)  # Wait between readings
#     baselines_2 = capture_baseline_readings(equipment)
#     time.sleep(0.5)  # Wait again
#     baselines_3 = capture_baseline_readings(equipment)
    
#     # Use the most recent reading (should be most stable)
#     baselines = baselines_3 if baselines_3 else (baselines_2 if baselines_2 else baselines_1)
    
#     if not baselines:
#         print(f"❌ [{po_number}] Failed to capture baselines")
#         return
    
#     print(f"✅ [{po_number}] Captured baseline (3rd reading, most stable): {baselines}")
#     if not baselines:
#         print(f"❌ [{po_number}] Failed to capture baselines")
#         return

#     # 🚦🚦🚦 ALWAYS SET MAIN BASELINE COLUMNS, UNCONDITIONALLY 🚦🚦🚦
#     for tag, val in baselines.items():
#         set_attr_safe(order, f"baseline_{tag.lower()}", float(val or 0.0))
#     print(f"✅ [{po_number}] Main equipment baseline columns set with fresh SCADA values: {baselines}")

#     # -- Shift and basic order state setup --
#     plant = get_attr_safe(order, "plant", "3130")
#     department = "MILLING" if order_type == "MILLING" else "PACKING"
#     shift_row = get_current_shift(plant, department, db)
#     current_shift = shift_row.shift_code if shift_row else "A"
#     set_attr_safe(order, "current_shift", current_shift)
#     set_attr_safe(order, "shift_start_time", datetime.now())
#     set_attr_safe(order, "order_type", order_type)
#     set_attr_safe(order, "status", "InProgress")
#     set_attr_safe(order, "validation_method", "Automatic")

#     # ✅ CRITICAL: Set FRESH shift baseline (old ones were cleared above)
#     # This ensures worker uses fresh baseline, not old shift baseline from previous order
#     print(f"✅ [{po_number}] Setting FRESH shift baseline for shift {current_shift.upper()}: {baselines}")
#     set_attr_safe(order, f"baseline_shift_{current_shift.lower()}_start", baselines)
#     set_attr_safe(order, f"baseline_shift_{current_shift.lower()}_time", datetime.now())
    
#     # ✅ CRITICAL: Commit shift baseline immediately to ensure it's persisted before worker starts
#     db.add(order)
#     db.flush()
#     db.commit()
#     db.refresh(order)
#     print(f"✅ [{po_number}] Fresh shift baseline committed to database")
    
#     # ✅ CRITICAL FIX: For brand new orders, update shift baseline to current SCADA immediately
#     # This absorbs any timing delta between baseline capture and worker start
#     # Do this immediately at order start, not wait for first worker cycle
#     if confirmed_qty_so_far == 0.0:
#         # Longer delay to let SCADA values fully settle after baseline capture
#         # This ensures we get truly current values, not residual from previous order
#         # Increased to 1.0s to ensure SCADA values have fully settled
#         print(f"⏳ [{po_number}] Waiting for SCADA values to settle before final baseline update...")
#         time.sleep(1.0)
#         # Get current SCADA readings to update baseline (absorbs timing delta)
#         # Take multiple readings to ensure we get stable, fresh values
#         current_scada_for_baseline_1 = get_multiple_scada_readings(equipment)
#         time.sleep(0.5)  # Delay between readings
#         current_scada_for_baseline_2 = get_multiple_scada_readings(equipment)
#         time.sleep(0.5)  # Delay again
#         current_scada_for_baseline_3 = get_multiple_scada_readings(equipment)
#         # Use the most recent reading (should be most stable and fresh)
#         current_scada_for_baseline = current_scada_for_baseline_3 if current_scada_for_baseline_3 else (current_scada_for_baseline_2 if current_scada_for_baseline_2 else current_scada_for_baseline_1)
#         if current_scada_for_baseline:
#             # Extract current values (floats) from SCADA readings dict
#             updated_baseline_dict = {}
#             for tag in equipment:
#                 if tag in current_scada_for_baseline:
#                     reading = current_scada_for_baseline[tag]
#                     if isinstance(reading, dict):
#                         current_val = float(reading.get('current', 0.0) or 0.0)
#                     else:
#                         current_val = float(reading or 0.0)
                    
#                     # ✅ CRITICAL: For brand new orders, ALWAYS update baseline to current SCADA
#                     # This absorbs any timing delta, regardless of how high current is
#                     # The only exception is if current is suspiciously high (10x+) which indicates it's definitely from previous order
#                     initial_baseline = float(baselines.get(tag, 0.0) or 0.0)
#                     if initial_baseline > 0.0 and current_val > initial_baseline * 10.0:
#                         # Current value is extremely high (10x+) - definitely from previous order
#                         # Use initial baseline instead to avoid false deltas
#                         print(f"⚠️ [{po_number}] {tag}: Current SCADA ({current_val:.2f}) is extremely high vs initial baseline ({initial_baseline:.2f}) - using initial baseline to avoid false delta")
#                         updated_baseline_dict[tag] = initial_baseline
#                     else:
#                         # Always use current SCADA value to absorb timing delta
#                         # Even if it's higher than initial baseline, it's likely just a timing difference
#                         updated_baseline_dict[tag] = current_val
#                         if current_val != initial_baseline:
#                             print(f"✅ [{po_number}] {tag}: Updating baseline from {initial_baseline:.2f} to {current_val:.2f} to absorb timing delta")
#                 else:
#                     # Fallback to original baseline if tag not in current readings
#                     updated_baseline_dict[tag] = float(baselines.get(tag, 0.0) or 0.0)
            
#             # ✅ CRITICAL: Update BOTH shift baseline JSON AND individual baseline columns
#             # The UI reads from individual baseline columns (baseline_wg201, etc.) for delta calculation
#             # So we must update both to ensure deltas show correctly
#             print(f"🔄 [{po_number}] Updating baselines - BEFORE: shift_baseline={get_attr_safe(order, f'baseline_shift_{current_shift.lower()}_start', {})}")
#             for tag in equipment:
#                 baseline_attr = f"baseline_{tag.lower()}"
#                 old_val = float(get_attr_safe(order, baseline_attr, 0.0) or 0.0)
#                 new_val = float(updated_baseline_dict.get(tag, 0.0) or 0.0)
#                 if old_val != new_val:
#                     print(f"   {tag}: baseline_{tag.lower()} = {old_val:.2f} → {new_val:.2f}")
            
#             set_attr_safe(order, f"baseline_shift_{current_shift.lower()}_start", updated_baseline_dict)
#             set_attr_safe(order, f"baseline_shift_{current_shift.lower()}_time", datetime.now())
            
#             # Update individual baseline columns so UI shows correct deltas
#             for tag, val in updated_baseline_dict.items():
#                 set_attr_safe(order, f"baseline_{tag.lower()}", float(val or 0.0))
            
#             db.add(order)
#             db.flush()
#             db.commit()  # ✅ CRITICAL: Commit immediately so UI reads correct baselines
#             db.refresh(order)
            
#             # Verify the update
#             print(f"✅ [{po_number}] Brand new order - updated shift baseline AND individual baseline columns to absorb timing delta")
#             print(f"   AFTER commit: shift_baseline={get_attr_safe(order, f'baseline_shift_{current_shift.lower()}_start', {})}")
#             for tag in equipment:
#                 baseline_attr = f"baseline_{tag.lower()}"
#                 final_val = float(get_attr_safe(order, baseline_attr, 0.0) or 0.0)
#                 print(f"   {tag}: baseline_{tag.lower()} = {final_val:.2f} (should match {updated_baseline_dict.get(tag, 0.0):.2f})")
    
#     # ✅ CRITICAL FIX: For brand new orders, ensure shift weights start at 0
#     # This prevents showing false production from timing differences between baseline capture and first worker cycle
#     # Only reset if this is a brand new order (confirmed_qty = 0 and all shift weights = 0)
#     if confirmed_qty_so_far == 0.0:
#         # Check if shift weights are already 0 (brand new order)
#         existing_weight_a = float(get_attr_safe(order, "weight_shift_a", 0.0) or 0.0)
#         existing_weight_b = float(get_attr_safe(order, "weight_shift_b", 0.0) or 0.0)
#         existing_weight_c = float(get_attr_safe(order, "weight_shift_c", 0.0) or 0.0)
        
#         if existing_weight_a == 0.0 and existing_weight_b == 0.0 and existing_weight_c == 0.0:
#             # Brand new order - explicitly set all shift weights to 0 to ensure clean start
#             set_attr_safe(order, "weight_shift_a", 0.0)
#             set_attr_safe(order, "weight_shift_b", 0.0)
#             set_attr_safe(order, "weight_shift_c", 0.0)
#             print(f"✅ [{po_number}] Brand new order - initialized all shift weights to 0")

#     # -- Byproduct/Packing assignment as usual --
#     if order_type == "MILLING":
#         version = get_attr_safe(order, "version", "").strip().upper()
#         byproduct_baselines = _capture_byproduct_baselines(version, baselines, order=order)
#         for tag, value in byproduct_baselines.items():
#             set_attr_safe(order, f"baseline_{tag.lower()}", float(value or 0.0))
#         _set_byproduct_scales(order, version, byproduct_baselines)
#     elif order_type == "PACKING":
#         if equipment:
#             tag = equipment[0]
#             set_attr_safe(order, "scale1", tag)
#             set_attr_safe(order, "scale1_qty", float(baselines.get(tag, 0.0) or 0.0))
#         else:
#             set_attr_safe(order, "scale1", None)
#             set_attr_safe(order, "scale1_qty", 0.0)
#         set_attr_safe(order, "scale2", None)
#         set_attr_safe(order, "scale2_qty", 0.0)
#         set_attr_safe(order, "scale3", None)
#         set_attr_safe(order, "scale3_qty", 0.0)

#     db.add(order)
#     db.commit()
#     print(f"✅ [{po_number}] All baseline columns and order state committed to DB.")

#     # --- Start auto-validation worker thread, as usual ---
#     # ✅ CRITICAL: Wait 1.5 seconds after baseline update to ensure it's fully committed and propagated
#     # This prevents the worker from reading stale baseline values on first cycle
#     # Worker MUST wait for baseline to be ready before starting
#     print(f"⏳ [{po_number}] Waiting 1.5 seconds for baseline to fully propagate before starting worker...")
#     time.sleep(1.5)  # CRITICAL: 1.5 second delay to ensure baseline is fully committed and ready
    
#     print(f"✅ [{po_number}] Starting validation thread...")
#     thread = threading.Thread(
#         target=auto_validation_worker,
#         args=(po_number, classification),
#         daemon=True,
#         name=f"Validation-{po_number}"
#     )
#     set_order_validation_state(po_number, {
#         "isrunning": True,  # ✅ CRITICAL: Must match the key checked in is_order_validating()
#         "thread": thread,
#         "progress_pct": 0
#     })
#     thread.start()
    
#     # ✅ CRITICAL: Verify worker thread actually started
#     time.sleep(0.1)  # Small delay to let thread start
#     if thread.is_alive():
#         print(f"✅ [{po_number}] Worker thread started and is ALIVE - will process confirmed_qty updates")
#     else:
#         print(f"❌ [{po_number}] CRITICAL: Worker thread started but is NOT ALIVE! This will prevent confirmed_qty updates!")
    
#     # ✅ CRITICAL: Verify is_order_validating returns True
#     if is_order_validating(po_number):
#         print(f"✅ [{po_number}] is_order_validating() = True - worker should be running")
#     else:
#         print(f"❌ [{po_number}] CRITICAL: is_order_validating() = False! Worker might not be running!")
    
#     print(f"✅ [{po_number}] Worker thread initialization complete")

# def _schedule_next_orders_after_completion():
#     """
#     Called by a worker when an order completes normally.
#     If master is ON:
#       - If there is no MILLING in progress, start next Pending MILLING by priority.
#       - If there is no PACKING in progress, start next Pending PACKING by priority.
#     """
#     print("=" * 80)
#     print("🔁 [SCHEDULER] ========== SCHEDULER CALLED ==========")
#     print("=" * 80)
    
#     if not is_auto_validator_enabled() or ProcessOrder is None:
#         print("🔁 [SCHEDULER] ❌ Skipping - auto-validator not enabled or ProcessOrder not available")
#         print(f"   is_auto_validator_enabled()={is_auto_validator_enabled()}, ProcessOrder={ProcessOrder is not None}")
#         return

#     print("🔁 [SCHEDULER] ✅ Starting scheduler to find next priority orders...")
    
#     # ✅ CRITICAL: Wait before starting next order to ensure previous order cleanup is complete
#     # and SCADA values have fully settled. This prevents inheriting previous order's SCADA values
#     print("⏳ [SCHEDULER] Waiting for previous order cleanup and SCADA values to settle...")
#     time.sleep(2.0)  # Increased delay to ensure SCADA values are fresh
    
#     # ✅ CRITICAL: Also wait a bit more to ensure worker threads have fully stopped
#     # This prevents has_milling/has_packing from being incorrectly True
#     print("⏳ [SCHEDULER] Waiting for worker threads to fully stop...")
#     time.sleep(1.0)  # Additional delay to ensure workers are stopped
    
#     with _db_session() as db:
#         # ✅ CRITICAL: Refresh all orders to ensure we have latest status from database
#         # This ensures completed orders show as "Validated" not "InProgress"
#         print("🔍 [SCHEDULER] Refreshing order statuses from database...")
#         all_orders = db.query(ProcessOrder).all()
#         for o in all_orders:
#             try:
#                 db.refresh(o)
#             except:
#                 pass
        
#         # Existing InProgress orders (used to check if we already have milling/packing running)
#         # ✅ CRITICAL: Filter out orders that are actually Validated but might still show as InProgress
#         # This can happen if the status wasn't fully committed yet
#         all_inprogress = db.query(ProcessOrder).filter(
#             ProcessOrder.status == "InProgress"
#         ).all()
        
#         # Filter to only include orders that are actually validating (worker is running)
#         # ✅ CRITICAL: Also double-check order status - if status is "Validated", exclude it even if worker state says validating
#         inprogress_orders = []
#         for o in all_inprogress:
#             po_num = get_attr_safe(o, "order_id", "UNKNOWN")
#             actual_status = get_attr_safe(o, "status", "UNKNOWN")
#             is_validating = is_order_validating(po_num)
            
#             # ✅ CRITICAL: Only include if:
#             # 1. Status is actually "InProgress" (not "Validated")
#             # 2. Worker is actually running
#             if actual_status == "InProgress" and is_validating:
#                 inprogress_orders.append(o)
#             else:
#                 # Order shows as InProgress but status is wrong or worker is not running - exclude it
#                 print(f"⚠️ [SCHEDULER] Order {po_num} excluded: status={actual_status}, is_validating={is_validating}")
#                 # If status is Validated but still shows as InProgress in query, fix it
#                 if actual_status == "Validated":
#                     print(f"   Order {po_num} is Validated but was in InProgress query - this is a database inconsistency")

#         print(f"🔁 [SCHEDULER] Found {len(inprogress_orders)} InProgress order(s) with active workers")
#         for o in inprogress_orders:
#             po_num = get_attr_safe(o, "order_id", "UNKNOWN")
#             order_type = get_attr_safe(o, "order_type", "UNKNOWN")
#             is_validating = is_order_validating(po_num)
#             print(f"   - {po_num}: type={order_type}, status=InProgress, is_validating={is_validating}")

#         has_milling = any(
#             (get_attr_safe(o, "order_type") or "").upper() == "MILLING"
#             and is_order_validating(o.order_id)
#             for o in inprogress_orders
#         )
#         has_packing = any(
#             (get_attr_safe(o, "order_type") or "").upper() == "PACKING"
#             and is_order_validating(o.order_id)
#             for o in inprogress_orders
#         )

#         print(f"🔁 [SCHEDULER] has_milling={has_milling}, has_packing={has_packing}")

#         # ✅ CRITICAL: Query pending orders and verify their status
#         pending_orders = db.query(ProcessOrder).filter(
#             ProcessOrder.status == "Pending"
#         ).order_by(ProcessOrder.priority.asc()).all()
        
#         # Also check for any orders that might be in a weird state
#         try:
#             from sqlalchemy import func
#             all_orders_status = db.query(ProcessOrder.status, func.count(ProcessOrder.id)).group_by(ProcessOrder.status).all()
#             status_breakdown = {status: count for status, count in all_orders_status}
#             print(f"🔍 [SCHEDULER] Order status breakdown: {status_breakdown}")
#         except Exception as e:
#             print(f"⚠️ [SCHEDULER] Could not get status breakdown: {e}")

#         print(f"🔁 [SCHEDULER] Found {len(pending_orders)} Pending order(s)")
        
#         # ✅ CRITICAL: Verify pending orders are actually Pending
#         for o in pending_orders:
#             po_num = get_attr_safe(o, "order_id", "UNKNOWN")
#             actual_status = get_attr_safe(o, "status", "UNKNOWN")
#             if actual_status != "Pending":
#                 print(f"⚠️ [SCHEDULER] WARNING: Order {po_num} in pending_orders but status is {actual_status}!")
        
#         # ✅ CRITICAL: Log all pending orders for debugging
#         if len(pending_orders) > 0:
#             print(f"🔍 [SCHEDULER] Pending orders list (sorted by priority):")
#             for i, o in enumerate(pending_orders, 1):
#                 po_num = get_attr_safe(o, "order_id", "UNKNOWN")
#                 priority = get_attr_safe(o, "priority", 999)
#                 db_order_type = get_attr_safe(o, "order_type", "UNKNOWN")
#                 material = get_attr_safe(o, "material", "UNKNOWN")
#                 version = get_attr_safe(o, "version", "UNKNOWN")
#                 print(f"   {i}. {po_num}: priority={priority}, db_order_type={db_order_type}, material={material}, version={version}")
#         else:
#             print(f"⚠️ [SCHEDULER] No pending orders found in database!")

#         next_milling = None
#         next_milling_class = None
#         next_packing = None
#         next_packing_class = None

#         # Choose first eligible pending Milling + Packing (priority order)
#         for order in pending_orders:
#             po_number = order.order_id

#             # If somehow already validating, skip
#             if is_order_validating(po_number):
#                 print(f"🔁 [SCHEDULER] Skipping {po_number} - already validating")
#                 continue

#             classification = classify_order(order)
#             if classification.get("error"):
#                 print(f"❌ [SCHEDULER] Classification error for pending {po_number}: {classification['error']}")
#                 continue

#             otype = classification.get("order_type")
#             priority = get_attr_safe(order, "priority", 999)
#             print(f"🔁 [SCHEDULER] Checking {po_number}: classified_type={otype}, priority={priority}, has_milling={has_milling}, next_milling={next_milling is not None}")

#             if not has_milling and otype == "MILLING" and next_milling is None:
#                 next_milling = order
#                 next_milling_class = classification
#                 print(f"🔁 [SCHEDULER] ✅✅✅ SELECTED next MILLING: {po_number} (priority {priority}) ✅✅✅")
#                 print(f"   Conditions met: has_milling={has_milling}, otype==MILLING={otype == 'MILLING'}, next_milling is None={next_milling is None}")

#             if not has_packing and otype == "PACKING" and next_packing is None:
#                 next_packing = order
#                 next_packing_class = classification
#                 print(f"🔁 [SCHEDULER] ✅ Selected next PACKING: {po_number} (priority {priority})")

#             if (has_milling or next_milling) and (has_packing or next_packing):
#                 print(f"🔁 [SCHEDULER] Found both types, stopping search")
#                 break
        
#         # ✅ CRITICAL: Log what we found
#         print(f"🔍 [SCHEDULER] Summary: next_milling={next_milling.order_id if next_milling else None}, next_packing={next_packing.order_id if next_packing else None}")

#         # ✅ CRITICAL: Log summary before starting orders
#         print(f"🔍 [SCHEDULER] Pre-start check: has_milling={has_milling}, next_milling={next_milling.order_id if next_milling else None}, next_milling_class={next_milling_class is not None}")
        
#         # Start next Milling
#         if not has_milling and next_milling and next_milling_class:
#             po_number_milling = next_milling.order_id
#             print(f"🔁 [SCHEDULER] ✅ Starting next MILLING order {po_number_milling}")
#             print(f"🔍 [SCHEDULER] Conditions: has_milling={has_milling}, next_milling={next_milling is not None}, next_milling_class={next_milling_class is not None}")
#             try:
#                 # 💥 CRITICAL: Stop any existing worker for this order before starting new one
#                 # This ensures old worker thread doesn't interfere with new baseline capture
#                 if is_order_validating(po_number_milling):
#                     print(f"🛑 [SCHEDULER] Stopping existing worker for {po_number_milling} before starting fresh...")
#                     set_order_validation_state(po_number_milling, {"isrunning": False})
#                     time.sleep(0.5)  # Wait for worker to stop
#                     print(f"✅ [SCHEDULER] Worker stopped for {po_number_milling}")
                
#                 # ✅ CRITICAL: Refresh order from database to ensure clean state
#                 db.refresh(next_milling)
#                 # ✅ CRITICAL: Longer delay before starting to ensure previous order cleanup is complete
#                 # This prevents SCADA values from previous order from affecting new order baselines
#                 print("⏳ [SCHEDULER] Waiting before starting MILLING order to ensure SCADA values are fresh...")
#                 time.sleep(1.5)  # Increased delay to ensure SCADA values are truly fresh
#                 # ✅ CRITICAL: Ensure order status is Pending before starting
#                 db.refresh(next_milling)
#                 current_status = get_attr_safe(next_milling, "status", "UNKNOWN")
#                 if current_status != "Pending":
#                     print(f"⚠️ [SCHEDULER] WARNING: Order {next_milling.order_id} status is {current_status}, expected Pending. Setting to Pending...")
#                     set_attr_safe(next_milling, "status", "Pending")
#                     db.add(next_milling)
#                     db.commit()
#                     db.refresh(next_milling)
                
#                 print(f"🔍 [SCHEDULER] Starting MILLING order {next_milling.order_id} (status before start: {get_attr_safe(next_milling, 'status', 'UNKNOWN')})")
#                 init_and_start_order_worker(db, next_milling, next_milling_class)
                
#                 # ✅ CRITICAL: Verify order was started successfully
#                 db.refresh(next_milling)
#                 final_status = get_attr_safe(next_milling, "status", "UNKNOWN")
#                 is_validating_check = is_order_validating(next_milling.order_id)
                
#                 if final_status == "InProgress" and is_validating_check:
#                     print(f"✅ [SCHEDULER] ✅✅✅ Successfully started MILLING order {next_milling.order_id} - status={final_status}, is_validating={is_validating_check} ✅✅✅")
#                 else:
#                     print(f"⚠️ [SCHEDULER] ⚠️⚠️⚠️ WARNING: MILLING order {next_milling.order_id} may not have started correctly - status={final_status}, is_validating={is_validating_check} ⚠️⚠️⚠️")
#                     print(f"   Expected: status=InProgress, is_validating=True")
#                     print(f"   Actual: status={final_status}, is_validating={is_validating_check}")
                
#                 # ✅ CRITICAL: Small delay to ensure database commit completes before next operation
#                 time.sleep(0.2)
#             except Exception as e:
#                 print(f"❌ [SCHEDULER] Failed to start MILLING order {next_milling.order_id}: {e}")
#                 import traceback
#                 traceback.print_exc()
#         elif has_milling:
#             print(f"🔁 [SCHEDULER] ⏭️ Skipping MILLING - already have one in progress (has_milling={has_milling})")
#             print(f"   This means there's an InProgress MILLING order with an active worker")
#         elif not next_milling:
#             print(f"🔁 [SCHEDULER] ⏭️ No pending MILLING orders found (checked {len(pending_orders)} pending orders)")
#             print(f"   This could mean:")
#             print(f"   - No pending orders exist")
#             print(f"   - All pending orders are PACKING type")
#             print(f"   - All pending MILLING orders failed classification")
#         else:
#             print(f"🔁 [SCHEDULER] ⚠️⚠️⚠️ MILLING conditions NOT MET - order NOT started! ⚠️⚠️⚠️")
#             print(f"   has_milling={has_milling}")
#             print(f"   next_milling={next_milling.order_id if next_milling else None}")
#             print(f"   next_milling_class={next_milling_class is not None}")
#             print(f"   This should not happen - investigate why conditions are not met!")

#         # Start next Packing
#         if not has_packing and next_packing and next_packing_class:
#             po_number_packing = next_packing.order_id
#             print(f"🔁 [SCHEDULER] ✅ Starting next PACKING order {po_number_packing}")
#             print(f"🔍 [SCHEDULER] Conditions: has_packing={has_packing}, next_packing={next_packing is not None}, next_packing_class={next_packing_class is not None}")
#             try:
#                 # 💥 CRITICAL: Stop any existing worker for this order before starting new one
#                 # This ensures old worker thread doesn't interfere with new baseline capture
#                 if is_order_validating(po_number_packing):
#                     print(f"🛑 [SCHEDULER] Stopping existing worker for {po_number_packing} before starting fresh...")
#                     set_order_validation_state(po_number_packing, {"isrunning": False})
#                     time.sleep(0.5)  # Wait for worker to stop
#                     print(f"✅ [SCHEDULER] Worker stopped for {po_number_packing}")
                
#                 # ✅ CRITICAL: Refresh order from database to ensure clean state
#                 db.refresh(next_packing)
#                 # ✅ CRITICAL: Longer delay before starting to ensure previous order cleanup is complete
#                 # This prevents SCADA values from previous order from affecting new order baselines
#                 print("⏳ [SCHEDULER] Waiting before starting PACKING order to ensure SCADA values are fresh...")
#                 time.sleep(1.5)  # Increased delay to ensure SCADA values are truly fresh
#                 # ✅ CRITICAL: Ensure order status is Pending before starting
#                 db.refresh(next_packing)
#                 current_status = get_attr_safe(next_packing, "status", "UNKNOWN")
#                 if current_status != "Pending":
#                     print(f"⚠️ [SCHEDULER] WARNING: Order {next_packing.order_id} status is {current_status}, expected Pending. Setting to Pending...")
#                     set_attr_safe(next_packing, "status", "Pending")
#                     db.add(next_packing)
#                     db.commit()
#                     db.refresh(next_packing)
                
#                 print(f"🔍 [SCHEDULER] Starting PACKING order {next_packing.order_id} (status before start: {get_attr_safe(next_packing, 'status', 'UNKNOWN')})")
#                 init_and_start_order_worker(db, next_packing, next_packing_class)
                
#                 # ✅ CRITICAL: Verify order was started successfully
#                 db.refresh(next_packing)
#                 final_status = get_attr_safe(next_packing, "status", "UNKNOWN")
#                 is_validating_check = is_order_validating(next_packing.order_id)
                
#                 if final_status == "InProgress" and is_validating_check:
#                     print(f"✅ [SCHEDULER] ✅✅✅ Successfully started PACKING order {next_packing.order_id} - status={final_status}, is_validating={is_validating_check} ✅✅✅")
#                 else:
#                     print(f"⚠️ [SCHEDULER] ⚠️⚠️⚠️ WARNING: PACKING order {next_packing.order_id} may not have started correctly - status={final_status}, is_validating={is_validating_check} ⚠️⚠️⚠️")
#                     print(f"   Expected: status=InProgress, is_validating=True")
#                     print(f"   Actual: status={final_status}, is_validating={is_validating_check}")
                
#                 # ✅ CRITICAL: Small delay to ensure database commit completes before next operation
#                 time.sleep(0.2)
#             except Exception as e:
#                 print(f"❌ [SCHEDULER] Failed to start PACKING order {next_packing.order_id}: {e}")
#                 import traceback
#                 traceback.print_exc()
#         elif has_packing:
#             print(f"🔁 [SCHEDULER] ⏭️ Skipping PACKING - already have one in progress (has_packing={has_packing})")
#         elif not next_packing:
#             print(f"🔁 [SCHEDULER] ⏭️ No pending PACKING orders found (checked {len(pending_orders)} pending orders)")
#         else:
#             print(f"🔁 [SCHEDULER] ⚠️ PACKING conditions not met: has_packing={has_packing}, next_packing={next_packing is not None}, next_packing_class={next_packing_class is not None}")
        
#         # ✅ CRITICAL: Summary log at end of scheduler
#         milling_attempted = next_milling is not None and next_milling_class is not None
#         packing_attempted = next_packing is not None and next_packing_class is not None
        
#         # Check if orders were actually started
#         milling_started = False
#         packing_started = False
#         if milling_attempted:
#             # Check if the order is now InProgress
#             db.refresh(next_milling)
#             final_status = get_attr_safe(next_milling, "status", "UNKNOWN")
#             is_validating = is_order_validating(next_milling.order_id)
#             milling_started = (final_status == "InProgress" and is_validating)
        
#         if packing_attempted:
#             # Check if the order is now InProgress
#             db.refresh(next_packing)
#             final_status = get_attr_safe(next_packing, "status", "UNKNOWN")
#             is_validating = is_order_validating(next_packing.order_id)
#             packing_started = (final_status == "InProgress" and is_validating)
        
#         print(f"🔁 [SCHEDULER] ========== SCHEDULER COMPLETE ==========")
#         print(f"🔁 [SCHEDULER] Summary:")
#         print(f"   - InProgress orders (with workers): {len(inprogress_orders)}")
#         print(f"   - Pending orders: {len(pending_orders)}")
#         print(f"   - has_milling: {has_milling}")
#         print(f"   - has_packing: {has_packing}")
#         print(f"   - next_milling found: {next_milling.order_id if next_milling else 'None'}")
#         print(f"   - next_packing found: {next_packing.order_id if next_packing else 'None'}")
#         print(f"   - MILLING order attempted: {milling_attempted}")
#         print(f"   - MILLING order started: {milling_started}")
#         print(f"   - PACKING order attempted: {packing_attempted}")
#         print(f"   - PACKING order started: {packing_started}")
        
#         if milling_attempted and not milling_started:
#             print(f"⚠️ [SCHEDULER] ⚠️⚠️⚠️ MILLING order was attempted but NOT started! ⚠️⚠️⚠️")
#             print(f"   Check logs above for errors during init_and_start_order_worker")
        
#         if packing_attempted and not packing_started:
#             print(f"⚠️ [SCHEDULER] ⚠️⚠️⚠️ PACKING order was attempted but NOT started! ⚠️⚠️⚠️")
#             print(f"   Check logs above for errors during init_and_start_order_worker")
        
#         print(f"🔁 [SCHEDULER] ========================================")
#         print("=" * 80)


# # =============================================================================
# # TEST ENDPOINT: Manually trigger scheduler (for debugging)
# # =============================================================================
# @orders_bp.route("/auto-validator/test-scheduler", methods=["POST"])
# def test_scheduler():
#     """
#     Test endpoint to manually trigger the scheduler.
#     This helps debug why orders are not starting automatically.
#     """
#     try:
#         from backend.database import get_db
#         db = next(get_db())
#         print("=" * 80)
#         print("🧪 [TEST] Manually triggering scheduler...")
#         print("=" * 80)
#         _schedule_next_orders_after_completion()
#         return jsonify({
#             "success": True,
#             "message": "Scheduler triggered successfully. Check console logs for details."
#         })
#     except Exception as e:
#         print(f"❌ [TEST] Error triggering scheduler: {e}")
#         import traceback
#         traceback.print_exc()
#         return jsonify({
#             "success": False,
#             "error": str(e)
#         }), 500

# # =============================================================================
# # AUTO-VALIDATOR WORKER (keeps previous behavior but uses corrected totals)
# # =============================================================================
# def auto_validation_worker(po_number: str, classification: Dict):
#     """
#     ✅ FINAL: Robust auto-validator 
#     - confirmed_qty is always the sum of all shift weights, never double-counted, never reset.
#     - Shift weights and confirmed_qty stay correct across stops, restarts, and shift changes.
#     - Works for any SCADA/plant restarts — no manual fixing ever needed.
#     """
#     print(f"✅ [Worker-{po_number}] Auto-validator worker started")
#     sap_service = SAPConfirmationService()
#     WORKER_WAIT = 1
#     order_completed_normally = False
#     first_cycle = True

#     try:
#         while True:
#             # Stop check
#             if not is_order_validating(po_number):
#                 if not first_cycle:
#                     print(f"🛑 [Worker-{po_number}] Stop signal - exiting")
#                     break
#                 else:
#                     print(f"⚠️ [Worker-{po_number}] is_order_validating() false on first cycle - ignoring")
#             first_cycle = False

#             try:
#                 # ✅ CRITICAL: Log that worker is running for this order
#                 # This helps identify if worker is running for all orders or just the first one
#                 print(f"🔄 [Worker-{po_number}] Worker cycle starting - checking order status and processing production...")
                
#                 with _db_session() as db:
#                     current_order = db.query(ProcessOrder).filter(
#                         ProcessOrder.order_id == po_number
#                     ).first()

#                     if not current_order:
#                         print(f"❌ [Worker-{po_number}] Order not found - exiting")
#                         break

#                     if current_order.status != "InProgress":
#                         print(f"⏳ [Worker-{po_number}] Status is {current_order.status}, waiting...")
#                         time.sleep(WORKER_WAIT)
#                         continue
                    
#                     # ✅ CRITICAL: Log that we're processing this order
#                     print(f"✅ [Worker-{po_number}] Order is InProgress - processing production cycle...")

#                     order_type = classification.get("order_type")
#                     equipment = classification.get("equipment", []) or []

#                     # Target and UOM
#                     if order_type == "MILLING":
#                         target_qty = float(get_attr_safe(current_order, "expected_weight") or 0.0)
#                         uom = "KG"
#                     else:
#                         target_qty = float(get_attr_safe(current_order, "quantity") or 0.0)
#                         uom = "BAG"

#                     # ------- SHIFT CHANGE LOGIC --------
#                     shift_changed = False
#                     if order_type in ["MILLING", "PACKING"]:
#                         plant = get_attr_safe(current_order, "plant", "3130")
#                         department = "MILLING" if order_type == "MILLING" else "PACKING"
#                         shift_row = get_current_shift(plant, department, db)
#                         realtime_shift = shift_row.shift_code if shift_row else "A"
#                         stored_shift = get_attr_safe(current_order, "current_shift", None)

#                         if stored_shift is None:
#                             print(f"🆕 [Worker-{po_number}] Initializing shift {realtime_shift}")
#                             shift_baselines = capture_baseline_readings(equipment)
#                             if shift_baselines:
#                                 set_attr_safe(current_order, f"baseline_shift_{realtime_shift.lower()}_start", shift_baselines)
#                                 set_attr_safe(current_order, f"baseline_shift_{realtime_shift.lower()}_time", datetime.now())
#                             set_attr_safe(current_order, "current_shift", realtime_shift)
#                             set_attr_safe(current_order, "shift_start_time", datetime.now())
#                             db.commit()
#                         elif stored_shift != realtime_shift:
#                             print(f"🔄 [Worker-{po_number}] Shift change {stored_shift} → {realtime_shift}")
                            
#                             # End the previous shift and send confirmation to SAP
#                             shift_result = end_shift_and_confirm(current_order, stored_shift, classification, sap_service)
                            
#                             # ✅ CRITICAL: Ensure order changes (including last_confirmed_qty) are committed
#                             db.add(current_order)
#                             db.commit()
                            
#                             if shift_result.get("success") and shift_result.get("order_complete"):
#                                 print(f"🏁 [Worker-{po_number}] Order completed during shift-change")
#                                 order_completed_normally = True
#                                 break
                            
#                             # ❌ OLD COMMENT WAS WRONG HERE:
#                             # "DO NOT reset shift baselines" is what causes weight_shift_b = 10

#                             # ✅ NEW: capture fresh baselines for the NEW shift
#                             new_shift_baselines = capture_baseline_readings(equipment)
#                             if new_shift_baselines:
#                                 set_attr_safe(
#                                     current_order,
#                                     f"baseline_shift_{realtime_shift.lower()}_start",
#                                     new_shift_baselines,
#                                 )
#                                 set_attr_safe(
#                                     current_order,
#                                     f"baseline_shift_{realtime_shift.lower()}_time",
#                                     datetime.now(),
#                                 )
#                                 print(f"✅ [Worker-{po_number}] Set fresh baselines for shift {realtime_shift}: {new_shift_baselines}")
#                             else:
#                                 print(f"⚠️ [Worker-{po_number}] Failed to capture baselines for new shift {realtime_shift} — keeping previous ones")
                            
#                             # Update current shift marker
#                             set_attr_safe(current_order, "current_shift", realtime_shift)
#                             set_attr_safe(current_order, "shift_start_time", datetime.now())
#                             db.commit()
#                             shift_changed = True

#                         if shift_changed:
#                             print(f"⏭️ [Worker-{po_number}] Skipping to next cycle after shift change")
#                             time.sleep(WORKER_WAIT)
#                             continue

#                     # ----- PRODUCTION AND SHIFT WEIGHTS -----
#                     # ✅ CRITICAL: Shift weights are preserved and accumulated
#                     # Refresh order from DB to ensure we have latest shift weights (including preserved values)
#                     db.refresh(current_order)
                    
#                     # Read current shift weights BEFORE any calculations (these are preserved from before restart)
#                     weight_a_before = float(get_attr_safe(current_order, "weight_shift_a", 0.0) or 0.0)
#                     weight_b_before = float(get_attr_safe(current_order, "weight_shift_b", 0.0) or 0.0)
#                     weight_c_before = float(get_attr_safe(current_order, "weight_shift_c", 0.0) or 0.0)
#                     print(f"🔍 [Worker-{po_number}] Current shift weights from DB: A={weight_a_before:.2f}, B={weight_b_before:.2f}, C={weight_c_before:.2f} {uom}")
                    
#                     # Only update the currently active shift
#                     current_shift = get_attr_safe(current_order, "current_shift", "A").lower()
#                     print(f"🔍 [Worker-{po_number}] Active shift: {current_shift.upper()}")
                    
#                     for code in ["a", "b", "c"]:
#                         shift_field = f"weight_shift_{code}"
#                         try:
#                             # ✅ CRITICAL: Get existing shift weight from database (preserved from before restart)
#                             existing_shift_weight_db = float(get_attr_safe(current_order, shift_field, 0.0) or 0.0)
                            
#                             # ✅ CRITICAL: Track maximum weight seen to prevent reverts
#                             # Use the maximum of DB value and cached maximum to prevent decreases
#                             cache_key_weight = (po_number, code)
#                             max_weight_seen = _max_shift_weight_cache.get(cache_key_weight, 0.0)
#                             existing_shift_weight = max(existing_shift_weight_db, max_weight_seen)
                            
#                             # If DB value is higher than cached max, update the cache
#                             if existing_shift_weight_db > max_weight_seen:
#                                 _max_shift_weight_cache[cache_key_weight] = existing_shift_weight_db
#                                 print(f"🔍 [Worker-{po_number}] Shift {code.upper()}: Updated max weight cache to {existing_shift_weight_db:.2f} (was {max_weight_seen:.2f})")
                            
#                             # Only update shift if currently active
#                             if current_shift == code:
#                                 print(f"🔍 [Worker-{po_number}] Calculating production for Shift {code.upper()} (existing weight={existing_shift_weight:.2f} {uom})")
                                
#                                 # Calculate TOTAL production from shift baseline to current SCADA
#                                 # This is the total production in this shift since the baseline was captured
#                                 # ✅ CRITICAL: This should return the DELTA (current - baseline), not the absolute current value
#                                 # ✅ CRITICAL: Pass db to ensure calculate_shift_weight refreshes order and uses latest baseline
#                                 total_production_from_baseline = calculate_shift_weight(current_order, code.upper(), classification, db=db)
                                
#                                 # ✅ SAFETY CHECK: If total_production_from_baseline is suspiciously large (close to current SCADA reading),
#                                 # it might indicate that the baseline wasn't set correctly or we're using absolute values instead of deltas.
#                                 # Log a warning but continue - the increment calculation should handle this.
#                                 if total_production_from_baseline > 1000.0 and existing_shift_weight == 0.0:
#                                     print(f"⚠️ [Worker-{po_number}] Shift {code.upper()}: WARNING - total_production_from_baseline ({total_production_from_baseline:.2f}) is very large. This might indicate baseline wasn't set correctly or we're using absolute SCADA reading instead of delta.")
                                
#                                 if order_type == "MILLING":
#                                     total_production = total_production_from_baseline
#                                 else:
#                                     packing_info = classification.get("packing_info", {})
#                                     bags_per_pallet = packing_info.get("bags_per_pallet", 1)
#                                     if bags_per_pallet == 1:
#                                         bags_per_pallet = packing_info.get("bag_size_kg", 1)
#                                     total_production = total_production_from_baseline * bags_per_pallet
                                
#                                 print(f"🔍 [Worker-{po_number}] Shift {code.upper()}: total_production from baseline = {total_production:.2f} {uom}")
                                
#                                 # ✅ CRITICAL: Track last calculated production to prevent double-counting
#                                 # Key: (po_number, shift_code) -> last_total_production
#                                 cache_key = (po_number, code)
#                                 last_total_production = _last_shift_production_cache.get(cache_key, 0.0)
                                
#                                 # ✅ CRITICAL FIX: Detect if baseline changed after restart
#                                 # When order is restarted, baseline is updated but cache might still have old value
#                                 # We need to detect this and reset the cache to prevent double-counting
#                                 baseline_changed_after_restart = False
                                
#                                 # ✅ CRITICAL: If existing_shift_weight > 0, it means order was restarted
#                                 # In this case, total_production is calculated from NEW baseline
#                                 # If cache has old value (last_total_production > total_production), reset it
#                                 if existing_shift_weight > 0.0:
#                                     if last_total_production > total_production:
#                                         # Cache has old value from before restart - reset it
#                                         print(f"🚨 [Worker-{po_number}] Shift {code.upper()}: CRITICAL - Baseline changed after restart!")
#                                         print(f"   existing_weight={existing_shift_weight:.2f}, cache={last_total_production:.2f}, current={total_production:.2f}")
#                                         print(f"   Cache has old value from before restart - resetting cache")
#                                         baseline_changed_after_restart = True
#                                         _last_shift_production_cache[cache_key] = 0.0
#                                         last_total_production = 0.0
#                                         print(f"✅ [Worker-{po_number}] Shift {code.upper()}: Cache reset to 0 after detecting baseline change")
#                                     elif last_total_production > 0.0 and total_production < last_total_production * 0.5:
#                                         # Production dropped significantly - baseline was reset
#                                         print(f"🚨 [Worker-{po_number}] Shift {code.upper()}: CRITICAL - Baseline changed after restart!")
#                                         print(f"   existing_weight={existing_shift_weight:.2f}, cache={last_total_production:.2f}, current={total_production:.2f}")
#                                         print(f"   Production dropped significantly - baseline was reset, clearing cache")
#                                         baseline_changed_after_restart = True
#                                         _last_shift_production_cache[cache_key] = 0.0
#                                         last_total_production = 0.0
#                                         print(f"✅ [Worker-{po_number}] Shift {code.upper()}: Cache reset to 0 after detecting baseline change")
#                                     elif last_total_production == 0.0:
#                                         # Cache is already cleared (was cleared on restart) - this is correct
#                                         print(f"✅ [Worker-{po_number}] Shift {code.upper()}: Cache is 0 (was cleared on restart) - correct state")
                                
#                                 # ✅ CRITICAL FIX: Detect first cycle scenarios
#                                 # Check if this is a brand new order (confirmed_qty = 0 and all shift weights = 0)
#                                 confirmed_qty_check = float(get_attr_safe(current_order, "confirmed_qty", 0.0) or 0.0)
#                                 weight_a_check = float(get_attr_safe(current_order, "weight_shift_a", 0.0) or 0.0)
#                                 weight_b_check = float(get_attr_safe(current_order, "weight_shift_b", 0.0) or 0.0)
#                                 weight_c_check = float(get_attr_safe(current_order, "weight_shift_c", 0.0) or 0.0)
#                                 is_truly_brand_new = (confirmed_qty_check == 0.0 and weight_a_check == 0.0 and weight_b_check == 0.0 and weight_c_check == 0.0)
                                
#                                 # ✅ CRITICAL: For brand new orders, FORCE clear cache to prevent inheriting values from deleted orders
#                                 # This is especially important if the new order has the same PO number as a deleted order
#                                 if is_truly_brand_new and last_total_production > 0.0:
#                                     print(f"🚨 [Worker-{po_number}] Shift {code.upper()}: Brand new order but cache has old value ({last_total_production:.2f})!")
#                                     print(f"   This might be from a deleted order - FORCING cache clear")
#                                     _last_shift_production_cache[cache_key] = 0.0
#                                     last_total_production = 0.0
#                                     print(f"✅ [Worker-{po_number}] Shift {code.upper()}: Cache force cleared for brand new order")
                                
#                                 # ✅ CRITICAL: Also clear max weight cache for brand new orders
#                                 if is_truly_brand_new and cache_key in _max_shift_weight_cache:
#                                     max_weight_value = _max_shift_weight_cache[cache_key]
#                                     if max_weight_value > 0.0:
#                                         print(f"🚨 [Worker-{po_number}] Shift {code.upper()}: Brand new order but max weight cache has old value ({max_weight_value:.2f})!")
#                                         print(f"   This might be from a deleted order - FORCING cache clear")
#                                         del _max_shift_weight_cache[cache_key]
#                                         print(f"✅ [Worker-{po_number}] Shift {code.upper()}: Max weight cache force cleared for brand new order")
                                
#                                 is_first_cycle_after_restart = (last_total_production == 0.0 and existing_shift_weight > 0.0) or baseline_changed_after_restart
#                                 is_first_cycle_brand_new = (last_total_production == 0.0 and existing_shift_weight == 0.0 and is_truly_brand_new)
                                
#                                 # ✅ CRITICAL DEBUG: Log first cycle detection
#                                 print(f"🔍 [Worker-{po_number}] Shift {code.upper()}: First cycle detection - is_first_cycle_after_restart={is_first_cycle_after_restart}, is_first_cycle_brand_new={is_first_cycle_brand_new}, is_truly_brand_new={is_truly_brand_new}, last_total_production={last_total_production:.2f}, existing_shift_weight={existing_shift_weight:.2f}, total_production={total_production:.2f}")
                                
#                                 # ✅ CRITICAL: If existing_weight > 0 but cache is wrong, force reset
#                                 # This handles cases where cache wasn't cleared properly on restart
#                                 if existing_shift_weight > 0.0 and last_total_production > total_production and not baseline_changed_after_restart:
#                                     # Cache has old value but we didn't detect baseline change - force reset
#                                     print(f"🚨 [Worker-{po_number}] Shift {code.upper()}: FORCE RESET - existing_weight={existing_shift_weight:.2f} but cache={last_total_production:.2f} > current={total_production:.2f}")
#                                     print(f"   Cache wasn't cleared properly - forcing reset")
#                                     _last_shift_production_cache[cache_key] = 0.0
#                                     last_total_production = 0.0
#                                     baseline_changed_after_restart = True
#                                     print(f"✅ [Worker-{po_number}] Shift {code.upper()}: Cache force reset to 0")
                                
#                                 if is_first_cycle_after_restart:
#                                     print(f"🔍 [Worker-{po_number}] Shift {code.upper()}: First cycle after restart - existing_weight={existing_shift_weight:.2f} preserved, total_production={total_production:.2f} (NEW production to be added)")
#                                 elif is_first_cycle_brand_new:
#                                     # ✅ IMPROVED LOGIC: For a brand-new order, only ignore SMALL deltas (< 2.0 kg)
#                                     # Small deltas are likely SCADA settling from previous order.
#                                     # LARGE deltas (> 2.0 kg) are real production and should be counted.
#                                     #
#                                     # So we:
#                                     #   - If total_production <= 2.0 kg: ignore it (SCADA settling), cache it, keep weight at 0
#                                     #   - If total_production > 2.0 kg: count it as real production, set weight = total_production

#                                     noise_threshold = 2.0  # 2.0 kg threshold - anything smaller is likely noise/settling

#                                     if total_production <= noise_threshold:
#                                         # Small production - likely SCADA settling, ignore it
#                                         print(
#                                             f"🔍 [Worker-{po_number}] Shift {code.upper()}: "
#                                             f"Brand NEW order, first cycle - total_production={total_production:.2f} "
#                                             f"(small delta, treating as SCADA settling, NOT counting for this order)"
#                                         )

#                                         # Initialize caches to this starting offset
#                                         _last_shift_production_cache[cache_key] = total_production
#                                         _max_shift_weight_cache[cache_key_weight] = 0.0

#                                         # Explicitly force shift weight to 0 for a fresh order
#                                         if hasattr(current_order, shift_field):
#                                             setattr(current_order, shift_field, 0.0)
#                                         else:
#                                             set_attr_safe(current_order, shift_field, 0.0)
#                                         print(
#                                             f"🔒 [Worker-{po_number}] Shift {code.upper()} SET to 0.0 "
#                                             f"(brand new order, first cycle ignored – next cycles will only count NEW production)"
#                                         )
                                        
#                                         # ✅ CRITICAL: Even though we're skipping this cycle, ensure confirmed_qty is 0
#                                         # This prevents any stale confirmed_qty from previous orders
#                                         # For automatically started orders, this ensures clean start
#                                         if hasattr(current_order, "confirmed_qty"):
#                                             current_order.confirmed_qty = 0.0
#                                         else:
#                                             set_attr_safe(current_order, "confirmed_qty", 0.0)
                                        
#                                         # ✅ CRITICAL: Commit shift weight and confirmed_qty immediately
#                                         # This ensures they're persisted even though we're using continue
#                                         try:
#                                             db.add(current_order)
#                                             db.flush()
#                                             db.commit()
                                            
#                                             # ✅ CRITICAL: Verify commit by querying database directly
#                                             db.refresh(current_order)
#                                             verified_weight = float(get_attr_safe(current_order, shift_field, 0.0) or 0.0)
#                                             verified_confirmed = float(get_attr_safe(current_order, "confirmed_qty", 0.0) or 0.0)
                                            
#                                             # Also query directly from database to double-check
#                                             verify_order = db.query(ProcessOrder).filter(ProcessOrder.order_id == po_number).first()
#                                             if verify_order:
#                                                 direct_weight = float(get_attr_safe(verify_order, shift_field, 0.0) or 0.0)
#                                                 direct_confirmed = float(get_attr_safe(verify_order, "confirmed_qty", 0.0) or 0.0)
#                                                 if direct_weight != 0.0 or direct_confirmed != 0.0:
#                                                     print(f"⚠️ [Worker-{po_number}] WARNING: Direct query shows weight={direct_weight:.2f}, confirmed={direct_confirmed:.2f} but we set both to 0.0!")
#                                                 else:
#                                                     print(f"✅ [Worker-{po_number}] Shift {code.upper()} and confirmed_qty committed and verified in database (both set to 0.0)")
#                                             else:
#                                                 print(f"⚠️ [Worker-{po_number}] Could not verify commit - order not found in direct query")
#                                         except Exception as e:
#                                             print(f"⚠️ [Worker-{po_number}] Failed to commit shift weight and confirmed_qty: {e}")
#                                             import traceback
#                                             traceback.print_exc()
#                                             db.rollback()

#                                         # Skip normal accumulation logic for this first cycle
#                                         continue
#                                     else:
#                                         # Large production - this is REAL production, count it!
#                                         print(
#                                             f"🔍 [Worker-{po_number}] Shift {code.upper()}: "
#                                             f"Brand NEW order, first cycle - total_production={total_production:.2f} "
#                                             f"(REAL production detected, counting it)"
#                                         )

#                                         # Initialize caches to current production
#                                         _last_shift_production_cache[cache_key] = total_production
#                                         _max_shift_weight_cache[cache_key_weight] = total_production

#                                         # Set shift weight directly to total_production (this is real production)
#                                         if hasattr(current_order, shift_field):
#                                             setattr(current_order, shift_field, total_production)
#                                         else:
#                                             set_attr_safe(current_order, shift_field, total_production)
#                                         print(
#                                             f"✅ [Worker-{po_number}] Shift {code.upper()} SET to {total_production:.2f} "
#                                             f"(brand new order, first cycle - real production counted)"
#                                         )

#                                         # ✅ CRITICAL: Also update confirmed_qty immediately to match shift weight
#                                         # This ensures "Current" shows the production right away
#                                         target_qty = float(get_attr_safe(current_order, "expected_weight") or get_attr_safe(current_order, "quantity") or 0.0)
#                                         display_total = min(total_production, target_qty)
#                                         if hasattr(current_order, "confirmed_qty"):
#                                             current_order.confirmed_qty = display_total
#                                         else:
#                                             set_attr_safe(current_order, "confirmed_qty", display_total)
#                                         print(
#                                             f"✅ [Worker-{po_number}] confirmed_qty SET to {display_total:.2f} "
#                                             f"(brand new order, first cycle - matching shift weight)"
#                                         )

#                                         # ✅ CRITICAL: Flush and commit immediately to ensure weight and confirmed_qty are persisted
#                                         # This is necessary because we're using 'continue' which skips the normal commit
#                                         # ✅ CRITICAL: Use direct commit with refresh to ensure values are actually in database
#                                         try:
#                                             db.add(current_order)
#                                             db.flush()
#                                             db.commit()
#                                             # ✅ CRITICAL: Refresh to verify commit worked
#                                             db.refresh(current_order)
#                                             # Verify the values were actually committed
#                                             verified_weight = float(get_attr_safe(current_order, shift_field, 0.0) or 0.0)
#                                             verified_confirmed = float(get_attr_safe(current_order, "confirmed_qty", 0.0) or 0.0)
#                                             if abs(verified_weight - total_production) > 0.01 or abs(verified_confirmed - display_total) > 0.01:
#                                                 print(f"⚠️ [Worker-{po_number}] WARNING: Commit verification failed! weight={verified_weight:.2f} (expected {total_production:.2f}), confirmed={verified_confirmed:.2f} (expected {display_total:.2f})")
#                                                 # Retry commit
#                                                 if hasattr(current_order, shift_field):
#                                                     setattr(current_order, shift_field, total_production)
#                                                 if hasattr(current_order, "confirmed_qty"):
#                                                     current_order.confirmed_qty = display_total
#                                                 db.add(current_order)
#                                                 db.commit()
#                                                 db.refresh(current_order)
#                                                 print(f"✅ [Worker-{po_number}] Retry commit completed")
#                                             else:
#                                                 print(f"✅ [Worker-{po_number}] Shift {code.upper()} weight and confirmed_qty committed and verified: weight={verified_weight:.2f}, confirmed={verified_confirmed:.2f} {uom}")
#                                         except Exception as e:
#                                             print(f"⚠️ [Worker-{po_number}] Failed to commit shift weight and confirmed_qty: {e}")
#                                             import traceback
#                                             traceback.print_exc()
#                                             db.rollback()

#                                         # Skip normal accumulation logic since we already set the weight and confirmed_qty
#                                         continue
                                
#                                 # Calculate increment: only add new production since last cycle
#                                 # ✅ CRITICAL FIX: After restart, baseline is reset, so total_production is calculated from NEW baseline
#                                 # If existing_shift_weight > 0, it means we have production from BEFORE restart (from OLD baseline)
#                                 # We need to preserve existing_weight and only add NEW production from NEW baseline
#                                 # The cache should be reset to 0 on restart, but if it wasn't, we need to handle it here
                                
#                                 # ✅ CRITICAL: Detect if this is after restart (baseline was reset)
#                                 # If existing_weight > 0 but total_production is calculated from new baseline,
#                                 # we need to reset cache and treat all current production as new
#                                 if existing_shift_weight > 0.0:
#                                     # Order was restarted - existing_weight is from old baseline, total_production is from new baseline
#                                     # We should preserve existing_weight and add only NEW production (increment from new baseline)
#                                     # But if cache has old value, increment calculation will be wrong
                                    
#                                     # ✅ CRITICAL: If cache has old value (last_total_production > total_production),
#                                     # it means baseline was reset but cache wasn't cleared - reset it now
#                                     if last_total_production > total_production:
#                                         print(f"🚨 [Worker-{po_number}] Shift {code.upper()}: CRITICAL - Cache has old value after restart!")
#                                         print(f"   existing_weight={existing_shift_weight:.2f}, cache={last_total_production:.2f}, current={total_production:.2f}")
#                                         print(f"   Baseline was reset - clearing cache and treating all current production as new")
#                                         _last_shift_production_cache[cache_key] = 0.0
#                                         last_total_production = 0.0
#                                         production_increment = total_production  # All current production is new from new baseline
#                                         print(f"✅ [Worker-{po_number}] Shift {code.upper()}: Cache reset, increment={production_increment:.2f} (all new from new baseline)")
#                                     elif last_total_production == 0.0:
#                                         # Cache is already 0 (was cleared on restart) - all current production is new
#                                         production_increment = total_production
#                                         print(f"🔍 [Worker-{po_number}] Shift {code.upper()}: After restart - cache=0, increment={production_increment:.2f} (all new from new baseline)")
#                                     else:
#                                         # Cache has value but it's less than total_production - normal increment
#                                         production_increment = total_production - last_total_production
#                                         print(f"🔍 [Worker-{po_number}] Shift {code.upper()}: Normal increment - cache={last_total_production:.2f}, current={total_production:.2f}, increment={production_increment:.2f}")
#                                 else:
#                                     # No existing weight - normal increment calculation
#                                     production_increment = total_production - last_total_production
                                
#                                 # ✅ DEBUG: Log cache state for troubleshooting
#                                 if last_total_production > 0.0:
#                                     print(f"🔍 [Worker-{po_number}] Shift {code.upper()}: CACHE STATE - last_total={last_total_production:.2f} (from cache), current_total={total_production:.2f}, increment={production_increment:.2f} {uom}")
#                                 print(f"🔍 [Worker-{po_number}] Shift {code.upper()}: existing_weight={existing_shift_weight:.2f}, last_total={last_total_production:.2f}, current_total={total_production:.2f}, increment={production_increment:.2f} {uom}")
                                
#                                 # ✅ SAFETY CHECK: If increment is suspiciously large compared to existing weight,
#                                 # it might indicate double-counting. Log a warning but still process.
#                                 if existing_shift_weight > 0 and production_increment > existing_shift_weight * 2:
#                                     print(f"⚠️ [Worker-{po_number}] Shift {code.upper()}: Large increment detected! existing={existing_shift_weight:.2f}, increment={production_increment:.2f} - possible double-counting?")
                                
#                                 # ✅ CRITICAL: Only accumulate if there's new production (increment > 0)
#                                 # This prevents double-counting by only adding the increment, not the total
#                                 # NEVER decrease shift weight - it should only increase or stay the same
#                                 # ✅ CRITICAL: If total_production > 0 but increment is 0 or negative, it means cache is wrong
#                                 # Force update shift weight to total_production if it's higher than existing
#                                 if total_production > existing_shift_weight and production_increment <= 0.01:
#                                     print(f"🚨 [Worker-{po_number}] Shift {code.upper()}: CRITICAL - total_production={total_production:.2f} > existing_weight={existing_shift_weight:.2f} but increment={production_increment:.2f} <= 0.01!")
#                                     print(f"   This means cache is wrong or production wasn't counted. FORCING update to {total_production:.2f}")
#                                     # Force update shift weight to total_production
#                                     if hasattr(current_order, shift_field):
#                                         setattr(current_order, shift_field, total_production)
#                                     else:
#                                         set_attr_safe(current_order, shift_field, total_production)
                                    
#                                     # ✅ CRITICAL: Commit immediately to ensure it's persisted
#                                     try:
#                                         db.add(current_order)
#                                         db.flush()
#                                         db.commit()
#                                         db.refresh(current_order)
#                                         print(f"✅ [Worker-{po_number}] Shift {code.upper()} FORCED to {total_production:.2f} {uom} and COMMITTED to database")
#                                     except Exception as e:
#                                         print(f"⚠️ [Worker-{po_number}] Failed to commit forced shift weight: {e}")
#                                         import traceback
#                                         traceback.print_exc()
                                    
#                                     _last_shift_production_cache[cache_key] = total_production
#                                     _max_shift_weight_cache[cache_key_weight] = total_production
                                    
#                                     # Skip normal accumulation since we already set and committed the weight
#                                     continue
                                
#                                 if production_increment > 0.01:
#                                     # ✅ CRITICAL: Before adding increment, verify it's reasonable
#                                     # If increment is suspiciously large compared to existing weight, it might be wrong
#                                     # This can happen if cache wasn't cleared properly after restart
#                                     if existing_shift_weight > 0.0 and production_increment > existing_shift_weight:
#                                         print(f"🚨 [Worker-{po_number}] Shift {code.upper()}: WARNING - Increment ({production_increment:.2f}) > existing_weight ({existing_shift_weight:.2f})!")
#                                         print(f"   This might indicate cache wasn't cleared properly after restart")
#                                         print(f"   Checking if this is first cycle after restart...")
                                        
#                                         # If this is first cycle after restart, increment should equal total_production
#                                         # If not, something is wrong - reset cache and recalculate
#                                         if not is_first_cycle_after_restart and last_total_production > 0.0:
#                                             print(f"🚨 [Worker-{po_number}] Shift {code.upper()}: Cache has old value! Resetting cache and recalculating increment")
#                                             _last_shift_production_cache[cache_key] = 0.0
#                                             production_increment = total_production  # All current production is new
#                                             print(f"✅ [Worker-{po_number}] Shift {code.upper()}: Cache reset, increment recalculated to {production_increment:.2f}")
                                    
#                                     # Add only the increment to existing weight
#                                     accumulated_shift_weight = existing_shift_weight + production_increment
                                    
#                                     # ✅ CRITICAL: Ensure we never decrease (safety check)
#                                     if accumulated_shift_weight < existing_shift_weight:
#                                         print(f"⚠️ [Worker-{po_number}] Shift {code.upper()}: Prevented decrease! Keeping {existing_shift_weight:.2f} instead of {accumulated_shift_weight:.2f} {uom}")
#                                         accumulated_shift_weight = existing_shift_weight
                                    
#                                     # ✅ CRITICAL: Use MAX to ensure shift weight never decreases
#                                     # This protects against any edge cases where calculations might go wrong
#                                     final_shift_weight = max(existing_shift_weight, accumulated_shift_weight)
                                    
#                                     # ✅ CRITICAL: Ensure final weight is never less than maximum seen
#                                     final_shift_weight = max(final_shift_weight, max_weight_seen)
                                    
#                                     # ✅ CRITICAL: Update max weight cache
#                                     if final_shift_weight > max_weight_seen:
#                                         _max_shift_weight_cache[cache_key_weight] = final_shift_weight
                                    
#                                     # ✅ CRITICAL: Use direct assignment to ensure shift weight is set
#                                     if hasattr(current_order, shift_field):
#                                         setattr(current_order, shift_field, final_shift_weight)
#                                     else:
#                                         set_attr_safe(current_order, shift_field, final_shift_weight)
                                    
#                                     # ✅ CRITICAL: Commit shift weight immediately to ensure it's persisted
#                                     # This is especially important for new production - it must be committed!
#                                     try:
#                                         db.add(current_order)
#                                         db.flush()
#                                         db.commit()
#                                         db.refresh(current_order)
#                                         print(f"✅ [Worker-{po_number}] Shift {code.upper()} UPDATED to {final_shift_weight:.2f} {uom} and COMMITTED to database")
#                                     except Exception as e:
#                                         print(f"⚠️ [Worker-{po_number}] Failed to commit shift weight update: {e}")
#                                         import traceback
#                                         traceback.print_exc()
#                                         db.rollback()
                                    
#                                     # ✅ CRITICAL: Always update cache IMMEDIATELY after calculating increment
#                                     # This ensures cache stays in sync with actual production from baseline
#                                     # This prevents double-counting on subsequent cycles
#                                     # ✅ CRITICAL: Update cache BEFORE logging to ensure it's set for next cycle
#                                     _last_shift_production_cache[cache_key] = total_production
#                                     if is_first_cycle_after_restart:
#                                         print(f"🔍 [Worker-{po_number}] Shift {code.upper()}: Cache initialized to {total_production:.2f} after restart (existing_weight={existing_shift_weight:.2f} preserved)")
                                    
#                                     if final_shift_weight > existing_shift_weight:
#                                         print(f"✅ [Worker-{po_number}] Shift {code.upper()} UPDATED: {existing_shift_weight:.2f} + {production_increment:.2f} = {final_shift_weight:.2f} {uom} (cache updated to {total_production:.2f})")
#                                     else:
#                                         print(f"🔒 [Worker-{po_number}] Shift {code.upper()} PRESERVED: {final_shift_weight:.2f} {uom} (MAX safeguard prevented change, but cache updated to {total_production:.2f})")
#                                 elif production_increment < -0.01:
#                                     # Production decreased - could be:
#                                     # 1. SCADA reading went down temporarily (temporary glitch) - don't update cache
#                                     # 2. Baseline was reset after restart (baseline change) - MUST update cache
                                    
#                                     # ✅ CRITICAL: If existing_weight > 0 and increment is very negative,
#                                     # it likely means baseline was reset but we didn't detect it earlier
#                                     # In this case, we MUST update cache to current production
#                                     if existing_shift_weight > 0.0 and abs(production_increment) > existing_shift_weight * 0.5:
#                                         # Very large negative increment - likely baseline reset
#                                         print(f"🚨 [Worker-{po_number}] Shift {code.upper()}: Large negative increment ({production_increment:.2f}) detected!")
#                                         print(f"   existing_weight={existing_shift_weight:.2f}, cache={last_total_production:.2f}, current={total_production:.2f}")
#                                         print(f"   This likely means baseline was reset - updating cache to current production")
#                                         _last_shift_production_cache[cache_key] = total_production
#                                         print(f"✅ [Worker-{po_number}] Shift {code.upper()}: Cache updated to {total_production:.2f} after detecting baseline reset")
#                                     else:
#                                         # Small negative increment - likely temporary SCADA glitch
#                                         # DO NOT update cache - keep last_total_production as is
#                                         print(f"⚠️ [Worker-{po_number}] Shift {code.upper()}: Production decreased ({production_increment:.2f}), preserving weight and cache (likely temporary SCADA glitch)")
                                    
#                                     # DO NOT decrease shift weight - preserve existing (use MAX to be safe)
#                                     final_shift_weight = max(existing_shift_weight, max_weight_seen, 0.0)  # Never decrease below max seen
#                                     # ✅ CRITICAL: Update max weight cache if needed
#                                     if final_shift_weight > max_weight_seen:
#                                         _max_shift_weight_cache[cache_key_weight] = final_shift_weight
#                                     print(f"🔒 [Worker-{po_number}] Shift {code.upper()}: Weight preserved at {final_shift_weight:.2f} {uom} (max_seen={max_weight_seen:.2f})")
#                                     # ✅ CRITICAL: Use direct assignment to ensure shift weight is set
#                                     if hasattr(current_order, shift_field):
#                                         setattr(current_order, shift_field, final_shift_weight)
#                                     else:
#                                         set_attr_safe(current_order, shift_field, final_shift_weight)
                                    
#                                     # ✅ CRITICAL: Flush shift weight immediately
#                                     try:
#                                         db.add(current_order)
#                                         db.flush()
#                                     except Exception as e:
#                                         print(f"⚠️ [Worker-{po_number}] Failed to flush shift weight: {e}")
#                                     # Cache remains unchanged - don't update it with lower value
#                                 else:
#                                     # No new production (increment ≈ 0), preserve existing weight
#                                     # ✅ CRITICAL: Always preserve existing weight, never overwrite with lower value
#                                     # ✅ CRITICAL FIX: If total_production is significantly higher than existing weight,
#                                     # it means production wasn't counted properly. Force update!
#                                     if total_production > existing_shift_weight + 1.0:  # At least 1kg difference
#                                         print(f"🚨 [Worker-{po_number}] Shift {code.upper()}: CRITICAL - total_production={total_production:.2f} > existing_weight={existing_shift_weight:.2f} but increment={production_increment:.2f} ≈ 0!")
#                                         print(f"   Production wasn't counted! FORCING update to {total_production:.2f}")
#                                         final_shift_weight = total_production
#                                         # ✅ CRITICAL: Use direct assignment to ensure shift weight is set
#                                         if hasattr(current_order, shift_field):
#                                             setattr(current_order, shift_field, final_shift_weight)
#                                         else:
#                                             set_attr_safe(current_order, shift_field, final_shift_weight)
                                        
#                                         # ✅ CRITICAL: Commit immediately to ensure it's persisted
#                                         try:
#                                             db.add(current_order)
#                                             db.flush()
#                                             db.commit()
#                                             db.refresh(current_order)
#                                             print(f"✅ [Worker-{po_number}] Shift {code.upper()} FORCED to {final_shift_weight:.2f} {uom} and COMMITTED to database")
#                                         except Exception as e:
#                                             print(f"⚠️ [Worker-{po_number}] Failed to commit forced shift weight: {e}")
#                                             import traceback
#                                             traceback.print_exc()
#                                             db.rollback()
                                        
#                                         _last_shift_production_cache[cache_key] = total_production
#                                         _max_shift_weight_cache[cache_key_weight] = total_production
#                                     else:
#                                         # Normal case: no new production, preserve existing
#                                         final_shift_weight = max(existing_shift_weight, max_weight_seen, 0.0)  # Never decrease below max seen
#                                         # ✅ CRITICAL: Update max weight cache if needed
#                                         if final_shift_weight > max_weight_seen:
#                                             _max_shift_weight_cache[cache_key_weight] = final_shift_weight
                                        
#                                         # ✅ CRITICAL: Use direct assignment to ensure shift weight is set
#                                         if hasattr(current_order, shift_field):
#                                             setattr(current_order, shift_field, final_shift_weight)
#                                         else:
#                                             set_attr_safe(current_order, shift_field, final_shift_weight)
                                        
#                                         # ✅ CRITICAL: Commit shift weight immediately to ensure it's persisted
#                                         # This is especially important for preserved weights - they must be committed!
#                                         # Even if the value didn't change, we need to commit to ensure database has the latest value
#                                         try:
#                                             db.add(current_order)
#                                             db.flush()
#                                             db.commit()
#                                             db.refresh(current_order)
#                                             print(f"✅ [Worker-{po_number}] Shift {code.upper()} PRESERVED at {final_shift_weight:.2f} {uom} and COMMITTED to database")
#                                         except Exception as e:
#                                             print(f"⚠️ [Worker-{po_number}] Failed to commit preserved shift weight: {e}")
#                                             import traceback
#                                             traceback.print_exc()
#                                             db.rollback()
                                        
#                                         if existing_shift_weight > 0:
#                                             print(f"🔒 [Worker-{po_number}] Shift {code.upper()} PRESERVED: {final_shift_weight:.2f} {uom} (no new production, max_seen={max_weight_seen:.2f})")
#                                         # ✅ CRITICAL: Only update cache if total_production >= last_total_production
#                                         # This prevents cache from being updated with lower values that could cause issues
#                                         if total_production >= last_total_production:
#                                             _last_shift_production_cache[cache_key] = total_production
#                                         else:
#                                             print(f"🔒 [Worker-{po_number}] Shift {code.upper()}: Cache preserved at {last_total_production:.2f} (total_production={total_production:.2f} is lower)")
#                             else:
#                                 # Inactive shift - preserve weight (don't recalculate)
#                                 if existing_shift_weight > 0:
#                                     print(f"🔒 [Worker-{po_number}] Shift {code.upper()} (inactive): Preserving weight={existing_shift_weight:.2f} {uom}")
#                             # For inactive shifts, weight is preserved (not recalculated)
#                         except Exception as e:
#                             print(f"⚠️ [Worker-{po_number}] Failed to update {shift_field}: {e}")
#                             import traceback
#                             traceback.print_exc()
                    
#                     # ✅ CRITICAL FINAL SAFEGUARD: After all shift weight updates, check if production exists but weights are still 0
#                     # This catches cases where first cycle logic didn't run or production wasn't counted
#                     db.refresh(current_order)
#                     final_weight_a = float(get_attr_safe(current_order, "weight_shift_a", 0.0) or 0.0)
#                     final_weight_b = float(get_attr_safe(current_order, "weight_shift_b", 0.0) or 0.0)
#                     final_weight_c = float(get_attr_safe(current_order, "weight_shift_c", 0.0) or 0.0)
#                     final_weights_sum = final_weight_a + final_weight_b + final_weight_c
                    
#                     # Check if we have production from SCADA but shift weights are 0
#                     # This means production wasn't counted - force update!
#                     if final_weights_sum == 0.0:
#                         # Recalculate total production from current SCADA to see if we missed it
#                         try:
#                             current_shift_for_check = get_attr_safe(current_order, "current_shift", "A").lower()
#                             if current_shift_for_check == code:
#                                 # This is the active shift - check if we have production
#                                 if total_production > 2.0:  # Real production detected
#                                     print(f"🚨 [Worker-{po_number}] CRITICAL FINAL CHECK: Shift {code.upper()} has production={total_production:.2f} but weight is still 0!")
#                                     print(f"   FORCING shift weight update to {total_production:.2f}")
#                                     set_attr_safe(current_order, shift_field, total_production)
#                                     # Update cache with correct key format (same as used elsewhere)
#                                     cache_key_final = (po_number, code)
#                                     cache_key_weight_final = (po_number, code)  # Same format as line 6521
#                                     _last_shift_production_cache[cache_key_final] = total_production
#                                     _max_shift_weight_cache[cache_key_weight_final] = total_production
#                                     print(f"✅ [Worker-{po_number}] Shift {code.upper()} FINALLY FORCED to {total_production:.2f} {uom}")
#                         except Exception as e:
#                             print(f"⚠️ [Worker-{po_number}] Error in final safeguard check: {e}")
                    
#                     # ✅ CRITICAL: Refresh order to get latest shift weights after individual commits
#                     # Since we're now committing shift weights immediately when they're updated,
#                     # we just need to refresh to get the latest committed values
#                     # This ensures confirmed_qty calculation uses the most recent values from database
#                     # ✅ CRITICAL: For automatically started orders, this refresh is ESSENTIAL
#                     # Without it, confirmed_qty calculation might use stale shift weight values
#                     db.refresh(current_order)
                    
#                     # ✅ CRITICAL: Double-check that shift weights are actually in the database
#                     # If they're still 0 after refresh, it means the individual commits didn't work
#                     weight_a_check = float(get_attr_safe(current_order, "weight_shift_a", 0.0) or 0.0)
#                     weight_b_check = float(get_attr_safe(current_order, "weight_shift_b", 0.0) or 0.0)
#                     weight_c_check = float(get_attr_safe(current_order, "weight_shift_c", 0.0) or 0.0)
#                     if weight_a_check == 0.0 and weight_b_check == 0.0 and weight_c_check == 0.0:
#                         print(f"⚠️ [Worker-{po_number}] WARNING: All shift weights are 0 after refresh! This might indicate commits didn't work.")
#                         print(f"   Check logs above for commit errors.")

#                     # ✅ CRITICAL: Read shift weights from order object after flush and refresh
#                     # The flush ensures updates are in the session, and refresh ensures we have the latest values
#                     # We'll commit these updates at the end of the cycle
#                     weight_a = float(get_attr_safe(current_order, "weight_shift_a", 0.0) or 0.0)
#                     weight_b = float(get_attr_safe(current_order, "weight_shift_b", 0.0) or 0.0)
#                     weight_c = float(get_attr_safe(current_order, "weight_shift_c", 0.0) or 0.0)
                    
#                     print(f"🔍 [Worker-{po_number}] Shift weights after update: A={weight_a:.2f}, B={weight_b:.2f}, C={weight_c:.2f} {uom}")
                    
#                     # ✅ confirmed_qty = sum of all shift weights (already includes preserved values)
#                     scada_total = weight_a + weight_b + weight_c
#                     display_total = min(scada_total, target_qty)
#                     overflow = max(scada_total - target_qty, 0.0)

#                     # ✅ CRITICAL: Refresh order AGAIN before reading confirmed_qty to ensure we have the latest value
#                     # This is especially important for restarted orders where confirmed_qty might have been updated
#                     # in a previous cycle but the object might be stale
#                     db.refresh(current_order)
#                     old_confirmed = float(get_attr_safe(current_order, "confirmed_qty", 0.0) or 0.0)
#                     print(f"🔍 [Worker-{po_number}] Read old_confirmed from database after refresh: {old_confirmed:.2f} {uom}")
                    
#                     print(f"🔍 [Worker-{po_number}] Calculated totals: scada_total={scada_total:.2f}, display_total={display_total:.2f}, old_confirmed={old_confirmed:.2f} {uom}")
                    
#                     # ✅ CRITICAL FIX: confirmed_qty should ALWAYS follow shift weights
#                     # If shift weights are > 0, confirmed_qty MUST be updated to match
#                     # Only block if ALL shift weights are 0 AND scada_total is small (< 2.0 kg) - this is SCADA settling
#                     shift_weights_sum = weight_a + weight_b + weight_c
#                     is_brand_new_still_zero = (old_confirmed == 0.0 and weight_a == 0.0 and weight_b == 0.0 and weight_c == 0.0)
                    
#                     if is_brand_new_still_zero and scada_total > 0.0 and scada_total <= 2.0:
#                         # Brand new order, first cycle - shift weights still 0 and scada_total is small (SCADA settling)
#                         # Keep confirmed_qty at 0 (this is just noise, not real production)
#                         print(f"🔒 [Worker-{po_number}] Brand new order first cycle - keeping confirmed_qty at 0.0 (shift weights=0, scada_total={scada_total:.2f} is SCADA settling, will count from next cycle)")
#                         final_confirmed = 0.0
#                     elif shift_weights_sum > 0.0:
#                         # ✅ CRITICAL: Shift weights are > 0, so confirmed_qty MUST match display_total
#                         # This handles both new orders (old_confirmed=0) and existing orders (old_confirmed>0)
#                         # ✅ CRITICAL FIX: For restarted orders, ALWAYS update to display_total if shift weights increased
#                         # Don't use max() here - we want to update even if old_confirmed is higher (shouldn't happen, but be safe)
#                         # The safeguard at line 6811 will prevent decreases
#                         if display_total > old_confirmed:
#                             # Production increased - update confirmed_qty
#                             final_confirmed = display_total
#                             print(f"✅ [Worker-{po_number}] confirmed_qty updating: {old_confirmed:.2f} → {final_confirmed:.2f} (scada_total={scada_total:.2f}, shift weights: A={weight_a:.2f}, B={weight_b:.2f}, C={weight_c:.2f})")
#                         elif display_total == old_confirmed:
#                             # No change - keep existing
#                             final_confirmed = old_confirmed
#                             print(f"🔍 [Worker-{po_number}] confirmed_qty unchanged: {old_confirmed:.2f} (scada_total={scada_total:.2f}, shift weights: A={weight_a:.2f}, B={weight_b:.2f}, C={weight_c:.2f})")
#                         else:
#                             # display_total < old_confirmed (shouldn't happen, but use max to prevent decrease)
#                             final_confirmed = max(old_confirmed, display_total)
#                             print(f"⚠️ [Worker-{po_number}] confirmed_qty preserved: {final_confirmed:.2f} (display_total={display_total:.2f} < old_confirmed={old_confirmed:.2f}, preventing decrease)")
                        
#                         # ✅ CRITICAL: Double-check - if shift weights increased but confirmed_qty didn't, force update
#                         if shift_weights_sum > old_confirmed and final_confirmed <= old_confirmed:
#                             print(f"🚨 [Worker-{po_number}] CRITICAL: shift_weights_sum={shift_weights_sum:.2f} > old_confirmed={old_confirmed:.2f} but final_confirmed={final_confirmed:.2f} - FORCING update!")
#                             final_confirmed = display_total
#                     elif scada_total > 2.0:
#                         # Shift weights are 0 but scada_total is large (real production detected)
#                         # This shouldn't happen if first cycle logic worked, but if it does, count it!
#                         print(f"⚠️ [Worker-{po_number}] Shift weights=0 but scada_total={scada_total:.2f} is large (real production), counting it!")
#                         final_confirmed = display_total
#                     else:
#                         # old_confirmed is 0, shift weights are 0, scada_total is small - keep at 0
#                         final_confirmed = 0.0
#                         print(f"🔍 [Worker-{po_number}] No production detected - keeping confirmed_qty at 0.0 (scada_total={scada_total:.2f}, shift weights: A={weight_a:.2f}, B={weight_b:.2f}, C={weight_c:.2f})")
                    
#                     # ✅ CRITICAL: Final safeguard - ensure confirmed_qty never decreases
#                     final_confirmed = max(final_confirmed, old_confirmed)
                    
#                     # ✅ CRITICAL FIX: FORCE update confirmed_qty if shift weights show production
#                     # This is especially important for orders after the first one that are automatically started
#                     # If shift weights are > 0, confirmed_qty MUST equal display_total, no exceptions!
#                     if shift_weights_sum > 0.0:
#                         # ✅ CRITICAL: For automatically started orders, ALWAYS set confirmed_qty to display_total
#                         # This ensures "Current" shows the production immediately, even on first cycle
#                         # NO CONDITIONS - if shift weights > 0, confirmed_qty MUST be set!
#                         final_confirmed = display_total
#                         print(f"✅ [Worker-{po_number}] FORCING confirmed_qty to {final_confirmed:.2f} because shift_weights_sum={shift_weights_sum:.2f} > 0 (automatically started order)")
                        
#                         # Double-check: if shift weights > 0 but confirmed_qty is still 0, force it
#                         if final_confirmed == 0.0 and shift_weights_sum > 0.0:
#                             print(f"🚨 [Worker-{po_number}] CRITICAL: shift_weights_sum={shift_weights_sum:.2f} but confirmed_qty is 0! FORCING update to {display_total:.2f}")
#                             final_confirmed = display_total
                    
#                     # ✅ CRITICAL: Set confirmed_qty - this MUST happen for ALL orders, EVERY cycle
#                     # No conditions, no exceptions - if shift weights show production, confirmed_qty must be set
#                     # This is especially critical for orders after the first one that are automatically started
#                     print(f"🔍 [Worker-{po_number}] Setting confirmed_qty: old={old_confirmed:.2f}, new={final_confirmed:.2f}, shift_weights_sum={shift_weights_sum:.2f}, display_total={display_total:.2f}")
                    
#                     # ✅ CRITICAL: Use direct assignment as primary method, set_attr_safe as fallback
#                     # This ensures confirmed_qty is ALWAYS set, even if set_attr_safe has issues
#                     if hasattr(current_order, "confirmed_qty"):
#                         current_order.confirmed_qty = final_confirmed
#                         print(f"✅ [Worker-{po_number}] confirmed_qty set via direct assignment: {final_confirmed:.2f}")
#                     else:
#                         print(f"⚠️ [Worker-{po_number}] confirmed_qty attribute not found, using set_attr_safe")
#                         set_attr_safe(current_order, "confirmed_qty", final_confirmed)
                    
#                     # ✅ CRITICAL: Double-check that confirmed_qty was actually set
#                     # Sometimes set_attr_safe might not work if the attribute doesn't exist or has issues
#                     try:
#                         test_confirmed = float(get_attr_safe(current_order, "confirmed_qty", 0.0) or 0.0)
#                         if abs(test_confirmed - final_confirmed) > 0.01:
#                             print(f"⚠️ [Worker-{po_number}] WARNING: confirmed_qty not set correctly! Expected {final_confirmed:.2f} but got {test_confirmed:.2f}")
#                             # Try direct assignment
#                             if hasattr(current_order, "confirmed_qty"):
#                                 current_order.confirmed_qty = final_confirmed
#                                 print(f"✅ [Worker-{po_number}] Fixed confirmed_qty using direct assignment: {final_confirmed:.2f}")
#                     except Exception as e:
#                         print(f"⚠️ [Worker-{po_number}] Error checking confirmed_qty: {e}")
                    
#                     # ✅ CRITICAL: Always log confirmed_qty updates for debugging
#                     if abs(final_confirmed - old_confirmed) > 0.0001:  # Log only if there's a meaningful change
#                         if final_confirmed > old_confirmed:
#                             print(f"📌 [Worker-{po_number}] ✅ confirmed_qty UPDATED: {old_confirmed:.2f} → {final_confirmed:.2f}/{target_qty:.2f} (sum of shifts: A={weight_a:.2f}, B={weight_b:.2f}, C={weight_c:.2f})")
#                         elif final_confirmed < old_confirmed:
#                             print(f"🔒 [Worker-{po_number}] confirmed_qty preserved at {final_confirmed:.2f} (prevented decrease from {old_confirmed:.2f} to {display_total:.2f})")
#                     else:
#                         # Log even if no change, to confirm the value is being set
#                         if shift_weights_sum > 0.0:
#                             print(f"🔍 [Worker-{po_number}] confirmed_qty = {final_confirmed:.2f}/{target_qty:.2f} (no change, shift weights: A={weight_a:.2f}, B={weight_b:.2f}, C={weight_c:.2f})")
                    
#                     # ✅ CRITICAL: Add order to session and commit confirmed_qty immediately
#                     # This ensures the value is persisted to database right away, not waiting for end of cycle
#                     # This is especially important for automatically started orders and restarted orders
#                     # ✅ CRITICAL: ALWAYS add order to session, even if it's already there
#                     # This ensures confirmed_qty changes are tracked by SQLAlchemy
#                     # ✅ CRITICAL: For restarted orders, we MUST commit even if final_confirmed == old_confirmed
#                     # This ensures the database has the latest value, especially after restart
#                     db.add(current_order)
#                     db.flush()
                    
#                     # ✅ CRITICAL: Commit confirmed_qty immediately to ensure it's stored in database
#                     # This prevents the issue where confirmed_qty is 0 until order restart
#                     # ✅ CRITICAL: For automatically started orders and restarted orders, this commit is ESSENTIAL
#                     # Without it, confirmed_qty will remain stale even though shift weights are correct
#                     # ✅ CRITICAL: Commit EVERY cycle when shift weights > 0, even if confirmed_qty didn't change
#                     # This ensures database always has the latest value, especially for restarted orders
#                     try:
#                         db.commit()
#                         if abs(final_confirmed - old_confirmed) > 0.01:
#                             print(f"✅ [Worker-{po_number}] ✅✅✅ confirmed_qty UPDATED and committed: {old_confirmed:.2f} → {final_confirmed:.2f} ✅✅✅")
#                         else:
#                             print(f"✅ [Worker-{po_number}] ✅✅✅ confirmed_qty committed (no change): {final_confirmed:.2f} (shift_weights_sum={shift_weights_sum:.2f}) ✅✅✅")
#                     except Exception as e:
#                         print(f"⚠️ [Worker-{po_number}] ⚠️⚠️⚠️ FAILED to commit confirmed_qty: {e} ⚠️⚠️⚠️")
#                         import traceback
#                         traceback.print_exc()
#                         db.rollback()
#                         # ✅ CRITICAL: Retry commit after rollback
#                         try:
#                             # Re-read shift weights to ensure we have latest values
#                             db.refresh(current_order)
#                             weight_a_retry = float(get_attr_safe(current_order, "weight_shift_a", 0.0) or 0.0)
#                             weight_b_retry = float(get_attr_safe(current_order, "weight_shift_b", 0.0) or 0.0)
#                             weight_c_retry = float(get_attr_safe(current_order, "weight_shift_c", 0.0) or 0.0)
#                             shift_weights_sum_retry = weight_a_retry + weight_b_retry + weight_c_retry
#                             display_total_retry = min(shift_weights_sum_retry, target_qty)
                            
#                             # Force update confirmed_qty to match shift weights
#                             current_order.confirmed_qty = display_total_retry
#                             db.add(current_order)
#                             db.commit()
#                             print(f"✅ [Worker-{po_number}] confirmed_qty committed on retry: {display_total_retry:.2f} (recalculated from shift weights)")
#                         except Exception as e2:
#                             print(f"❌ [Worker-{po_number}] CRITICAL: Retry commit also failed: {e2}")
                    
#                     # ✅ CRITICAL: Verify confirmed_qty was set correctly after commit
#                     db.refresh(current_order)
#                     verified_confirmed = float(get_attr_safe(current_order, "confirmed_qty", 0.0) or 0.0)
#                     if abs(verified_confirmed - final_confirmed) > 0.01:
#                         print(f"⚠️ [Worker-{po_number}] WARNING: confirmed_qty mismatch after commit! Set to {final_confirmed:.2f} but database shows {verified_confirmed:.2f}")
#                         # Try to fix it
#                         set_attr_safe(current_order, "confirmed_qty", final_confirmed)
#                         db.add(current_order)
#                         db.commit()
#                         db.refresh(current_order)
#                         verified_confirmed = float(get_attr_safe(current_order, "confirmed_qty", 0.0) or 0.0)
#                         if abs(verified_confirmed - final_confirmed) > 0.01:
#                             print(f"❌ [Worker-{po_number}] CRITICAL: confirmed_qty still wrong after retry! Database shows {verified_confirmed:.2f}, expected {final_confirmed:.2f}")
#                         else:
#                             print(f"✅ [Worker-{po_number}] confirmed_qty fixed after retry: {verified_confirmed:.2f}")
#                     else:
#                         print(f"✅ [Worker-{po_number}] confirmed_qty verified in database: {verified_confirmed:.2f}")
                    
#                     # ✅ CRITICAL FINAL SAFEGUARD: Double-check confirmed_qty matches shift weights
#                     # This is especially important for automatically started orders
#                     # If shift weights > 0 but confirmed_qty doesn't match, force update
#                     if shift_weights_sum > 0.0:
#                         final_verified = float(get_attr_safe(current_order, "confirmed_qty", 0.0) or 0.0)
#                         if abs(final_verified - display_total) > 0.01:
#                             print(f"🚨 [Worker-{po_number}] CRITICAL FINAL CHECK: shift_weights_sum={shift_weights_sum:.2f} but confirmed_qty={final_verified:.2f} != display_total={display_total:.2f}")
#                             print(f"   FORCING final update of confirmed_qty to {display_total:.2f}")
#                             current_order.confirmed_qty = display_total
#                             db.add(current_order)
#                             db.commit()
#                             db.refresh(current_order)
#                             final_check = float(get_attr_safe(current_order, "confirmed_qty", 0.0) or 0.0)
#                             if abs(final_check - display_total) > 0.01:
#                                 print(f"❌ [Worker-{po_number}] CRITICAL: Final confirmed_qty update failed! DB shows {final_check:.2f}, expected {display_total:.2f}")
#                             else:
#                                 print(f"✅ [Worker-{po_number}] Final confirmed_qty update successful: {final_check:.2f}")
                    
#                     if overflow > 0:
#                         set_attr_safe(current_order, "overflow_weight", overflow)

#                     # PACKING PER SCALE
#                     try:
#                         if order_type == "PACKING":
#                             deltas_main = {}  # (Fill with your normal scale-deltas logic)
#                             update_order_scales(current_order, deltas_main)
#                     except Exception as e:
#                         print(f"⚠️ [Worker-{po_number}] update_order_scales: {e}")

#                     # UI STATUS
#                     progress = min(100.0, (display_total / target_qty) * 100.0 if target_qty > 0 else 0.0)
#                     set_order_validation_state(po_number, {
#                         "isrunning": True,  # ✅ CRITICAL: Must match the key checked in is_order_validating()
#                         "progress_pct": progress,
#                         "current_production": display_total,
#                         "target": target_qty,
#                         "status": "running",
#                         "unit": uom,
#                     })

#                     # COMPLETION
#                     completion = check_order_completion(current_order, classification)
#                     if completion.get("is_complete", False):
#                         print(f"🏁 [Worker-{po_number}] ORDER COMPLETE!")
#                         order_type_completed = classification.get("order_type", "UNKNOWN")
#                         print(f"🔍 [Worker-{po_number}] Completed order type: {order_type_completed}")
                        
#                         current_shift = get_attr_safe(current_order, "current_shift", None)
#                         if current_shift:
#                             end_shift_and_confirm(current_order, current_shift, classification, sap_service, force_final=True)
#                             # ✅ CRITICAL: Ensure order changes (including last_confirmed_qty) are committed
#                             db.add(current_order)
#                             db.commit()
#                         set_attr_safe(current_order, "status", "Validated")
#                         set_attr_safe(current_order, "validation_method", "Automatic")
#                         set_attr_safe(current_order, "is_target_reached", True)
#                         set_attr_safe(current_order, "is_final_sent", True)
                        
#                         # ✅ CRITICAL: Commit order status change immediately
#                         db.add(current_order)
#                         db.commit()
#                         db.refresh(current_order)
                        
#                         # ✅ CRITICAL: Verify status was updated
#                         final_status = get_attr_safe(current_order, "status", "UNKNOWN")
#                         print(f"✅ [Worker-{po_number}] Order status updated to: {final_status}")
                        
#                         if final_status != "Validated":
#                             print(f"⚠️ [Worker-{po_number}] WARNING: Status is {final_status}, expected Validated!")
                        
#                         # ✅ CRITICAL: Stop worker state immediately so scheduler doesn't think order is still running
#                         print(f"🛑 [Worker-{po_number}] Stopping worker state before scheduler runs...")
#                         set_order_validation_state(po_number, {"isrunning": False})
                        
#                         # ✅ CRITICAL: Wait a moment for state to propagate
#                         time.sleep(0.5)
                        
#                         order_completed_normally = True
#                         print(f"✅ [Worker-{po_number}] Order completed normally - will trigger scheduler in finally block")
#                         break
#                     db.commit()

#             except Exception as e:
#                 print(f"❌ [Worker-{po_number}] Error in cycle: {e}")
#                 import traceback
#                 traceback.print_exc()
#                 time.sleep(WORKER_WAIT)
#                 continue
#             time.sleep(WORKER_WAIT)

#         print(f"🏁 [Worker-{po_number}] Worker loop exited")

#     except Exception as e:
#         print(f"❌ [Worker-{po_number}] Fatal error: {e}")
#         import traceback
#         traceback.print_exc()

#     finally:
#         try:
#             remove_order_validation_state(po_number)
#         except Exception:
#             pass
#         print(f"🛑 [Worker-{po_number}] Auto-validator stopped")
#         if order_completed_normally and is_auto_validator_enabled():
#             try:
#                 print(f"🔁 [Worker-{po_number}] Order completed normally - triggering scheduler to start next order")
#                 print(f"🔍 [Worker-{po_number}] order_completed_normally={order_completed_normally}, is_auto_validator_enabled()={is_auto_validator_enabled()}")
#                 print(f"🔍 [Worker-{po_number}] Order type that completed: {classification.get('order_type', 'UNKNOWN') if 'classification' in locals() else 'UNKNOWN'}")
                
#                 # ✅ CRITICAL: Ensure worker state is fully cleared before scheduler runs
#                 # Sometimes the state might not be fully cleared yet
#                 set_order_validation_state(po_number, {"isrunning": False})
#                 time.sleep(0.5)  # Wait for state to propagate
                
#                 _schedule_next_orders_after_completion()
#                 print(f"✅ [Worker-{po_number}] Scheduler completed")
#             except Exception as e:
#                 print(f"⚠️ [Worker-{po_number}] ⚠️⚠️⚠️ FAILED to schedule next order: {e} ⚠️⚠️⚠️")
#                 import traceback
#                 traceback.print_exc()
#         else:
#             reason = []
#             if not order_completed_normally:
#                 reason.append("order_completed_normally=False")
#             if not is_auto_validator_enabled():
#                 reason.append("auto_validator not enabled")
#             print(f"🔍 [Worker-{po_number}] Not triggering scheduler: {', '.join(reason) if reason else 'unknown reason'}")

# # =============================================================================
# # API ENDPOINTS
# # =============================================================================

# @orders_bp.route("", methods=["GET"])
# def list_orders():
#     if ProcessOrder is None:
#         return jsonify([])
#     status = request.args.get("status")
#     statuses = request.args.get("statuses")
#     with _db_session() as db:
#         q = db.query(ProcessOrder)
#         if statuses:
#             status_list = [s.strip() for s in statuses.split(",")]
#             q = q.filter(ProcessOrder.status.in_(status_list))
#         elif status and status != "All":
#             q = q.filter(ProcessOrder.status == status)
#         rows = q.order_by(ProcessOrder.priority.asc(), ProcessOrder.id.asc()).all()
#     return jsonify([serialize_order(r) for r in rows])

# @orders_bp.route("/<string:po_number>/start", methods=["POST"])
# def start_order(po_number: str):
#     """
#     Start validation for a specific order.
#     ✅ Supports parallel validation (per-order threads).
#     ✅ Ensures by-product scales (scale1/2/3 + *_qty) are stored for MILLING.
#     ✅ On restart after STOP: uses FRESH baselines, preserves confirmed_qty.
#     """
#     if is_order_validating(po_number):
#         return jsonify({
#             "success": False,
#             "message": f"Order {po_number} is already being validated"
#         }), 400

#     if ProcessOrder is None:
#         raise BadRequest("ProcessOrder model not available")

#     with _db_session() as db:
#         order = db.query(ProcessOrder).filter(
#             ProcessOrder.order_id == po_number
#         ).first()

#         if not order:
#             raise NotFound(f"Order {po_number} not found")

#         # ✅ CRITICAL: Refresh order from database to get latest values
#         db.refresh(order)
        
#         # ✅ CRITICAL: Clear production cache for this order on restart
#         # This ensures we start tracking from 0 after baseline is captured
#         # ✅ CRITICAL: For brand new orders (after deleting old order), ALWAYS clear cache
#         # This prevents new orders from inheriting cached values from deleted orders
#         # ✅ CRITICAL: ALWAYS clear cache unconditionally - don't check if it exists
#         # This ensures we remove any stale cache from deleted orders with the same PO number
#         for shift_code in ["a", "b", "c"]:
#             cache_key = (po_number, shift_code)
#             # ✅ CRITICAL: ALWAYS clear cache - use pop() with default to avoid KeyError
#             # This ensures we remove cache even if it exists from a deleted order
#             old_cache_value = _last_shift_production_cache.pop(cache_key, None)
#             if old_cache_value is not None:
#                 print(f"🧹 [Start-{po_number}] Cleared production cache for shift {shift_code.upper()} (had value: {old_cache_value:.2f})")
#             else:
#                 # Cache doesn't exist - this is fine, but log it for brand new orders
#                 print(f"🔍 [Start-{po_number}] No production cache found for shift {shift_code.upper()} (will be initialized fresh)")
            
#             # ✅ CRITICAL: Also clear max weight cache for brand new orders
#             # Only initialize max weight cache if we have preserved weight (restart scenario)
#             weight_field = f"weight_shift_{shift_code}"
#             preserved_weight = float(get_attr_safe(order, weight_field, 0.0) or 0.0)
#             if preserved_weight > 0.0:
#                 # Restart scenario - initialize max weight cache from preserved weight
#                 # But first, clear any existing cache to ensure clean state
#                 old_max_cache = _max_shift_weight_cache.pop(cache_key, None)
#                 if old_max_cache is not None and old_max_cache != preserved_weight:
#                     print(f"🧹 [Start-{po_number}] Cleared old max weight cache for shift {shift_code.upper()} (had value: {old_max_cache:.2f}, will use preserved: {preserved_weight:.2f})")
#                 _max_shift_weight_cache[cache_key] = preserved_weight
#                 print(f"🔍 [Start-{po_number}] Initialized max weight cache for shift {shift_code.upper()} to {preserved_weight:.2f}")
#             else:
#                 # Brand new order - ALWAYS clear max weight cache if it exists (from deleted order)
#                 old_max_cache = _max_shift_weight_cache.pop(cache_key, None)
#                 if old_max_cache is not None:
#                     print(f"🧹 [Start-{po_number}] Cleared max weight cache for shift {shift_code.upper()} (had value: {old_max_cache:.2f} from deleted order)")
#                 else:
#                     print(f"🔍 [Start-{po_number}] No max weight cache for shift {shift_code.upper()} (brand new order)")
        
#         # ✅ CRITICAL: Read confirmed_qty IMMEDIATELY after refreshing (before any modifications)
#         # Read directly from the order object to ensure we get the actual database value
#         preserved_confirmed_qty = float(order.confirmed_qty if hasattr(order, 'confirmed_qty') and order.confirmed_qty is not None else 0.0)
#         if preserved_confirmed_qty > 0.0:
#             print(f"🔍 [{po_number}] Found existing confirmed_qty in DB: {preserved_confirmed_qty} - will preserve on restart")
#         else:
#             print(f"🔍 [{po_number}] confirmed_qty is 0 or None in DB - will set to 0 for new order")
        
#         # ✅ CRITICAL: Preserve shift weights (DO NOT reset them!)
#         preserved_weight_a = float(get_attr_safe(order, "weight_shift_a", 0.0) or 0.0)
#         preserved_weight_b = float(get_attr_safe(order, "weight_shift_b", 0.0) or 0.0)
#         preserved_weight_c = float(get_attr_safe(order, "weight_shift_c", 0.0) or 0.0)
#         if preserved_weight_a > 0.0 or preserved_weight_b > 0.0 or preserved_weight_c > 0.0:
#             print(f"🔍 [{po_number}] Found existing shift weights in DB: A={preserved_weight_a:.2f}, B={preserved_weight_b:.2f}, C={preserved_weight_c:.2f} - will preserve on restart")
#         else:
#             print(f"🔍 [{po_number}] All shift weights are 0 in DB - new order")

#         # Allow re-init ONLY if InProgress but scales are empty (legacy fix)
#         if order.status == "InProgress":
#             has_scales = any([
#                 get_attr_safe(order, "scale1"),
#                 get_attr_safe(order, "scale2"),
#                 get_attr_safe(order, "scale3"),
#             ])
#             if has_scales:
#                 return jsonify({
#                     "success": False,
#                     "message": "Order already InProgress with scales set"
#                 }), 400
#             else:
#                 print(f"♻️ Re-initialising InProgress order {po_number} (scale1/2/3 were empty)")

#         # Debug: Log order details before classification
#         order_version = (get_attr_safe(order, "version") or "").strip().upper()
#         order_material = str(get_attr_safe(order, "material") or "").strip()
#         print(f"🔍 [Start-{po_number}] Classifying order: version='{order_version}', material='{order_material}'")
        
#         classification = classify_order(order)
#         if classification.get("error"):
#             error_msg = classification['error']
#             print(f"❌ [Start-{po_number}] Classification failed: {error_msg}")
#             raise BadRequest(f"Classification failed: {error_msg}")

#         equipment = classification.get("equipment", [])
#         if not equipment:
#             raise BadRequest("No equipment mapped for this order")

#         order_type_new = classification["order_type"]
#         set_attr_safe(order, "order_type", order_type_new)

#         # ✅ CRITICAL: FIRST reset ALL baseline columns to 0 to ensure clean slate
#         print(f"🔄 [{po_number}] Resetting all baseline columns to 0 before capturing fresh SCADA values...")
#         # PACKING: Bag counter baselines
#         set_attr_safe(order, "baseline_sl601_counter", 0.0)
#         set_attr_safe(order, "baseline_sl602_counter", 0.0)
#         set_attr_safe(order, "baseline_sl603_counter", 0.0)
#         set_attr_safe(order, "baseline_sl606_counter", 0.0)
#         set_attr_safe(order, "baseline_sl607_counter", 0.0)
#         # MILLING: Flour/Bran output baselines
#         set_attr_safe(order, "baseline_wg101", 0.0)
#         set_attr_safe(order, "baseline_wg201", 0.0)
#         set_attr_safe(order, "baseline_wg202", 0.0)
#         set_attr_safe(order, "baseline_wg301", 0.0)
#         set_attr_safe(order, "baseline_wg302", 0.0)
#         set_attr_safe(order, "baseline_wg501", 0.0)
#         set_attr_safe(order, "baseline_wg502", 0.0)
#         set_attr_safe(order, "baseline_wg503", 0.0)
#         # WATER DOSING METER baselines
#         set_attr_safe(order, "baseline_dm101", 0.0)
#         set_attr_safe(order, "baseline_dm102", 0.0)
#         set_attr_safe(order, "baseline_dm201", 0.0)
#         set_attr_safe(order, "baseline_dm202", 0.0)
#         set_attr_safe(order, "baseline_dm203", 0.0)
        
#         # ✅ CRITICAL: Commit baseline reset to database BEFORE capturing fresh SCADA values
#         db.add(order)
#         db.flush()  # Flush to ensure reset is in database before SCADA capture
        
#         # ✅ VERIFY: Refresh order to confirm baselines were reset in database
#         db.refresh(order)
#         baseline_wg502_check = float(get_attr_safe(order, "baseline_wg502", 0.0) or 0.0)
#         baseline_wg501_check = float(get_attr_safe(order, "baseline_wg501", 0.0) or 0.0)
#         print(f"✅ [{po_number}] All baseline columns reset to 0 and flushed to database")
#         print(f"🔍 [{po_number}] Verification: baseline_wg502={baseline_wg502_check}, baseline_wg501={baseline_wg501_check}")

#         # ✅ CAPTURE FRESH SCADA BASELINES (always new on start!)
#         baselines = capture_baseline_readings(equipment)
#         if not baselines:
#             raise BadRequest("Failed to capture SCADA baselines")

#         for tag in equipment:
#             baselines.setdefault(tag, 0.0)

#         # Initialize shift
#         plant = get_attr_safe(order, "plant", "3130")
#         department = "MILLING" if order_type_new == "MILLING" else "PACKING"
#         shift_row = get_current_shift(plant, department, db)
#         current_shift = shift_row.shift_code if shift_row else "A"
#         set_attr_safe(order, "current_shift", current_shift)
#         set_attr_safe(order, "shift_start_time", datetime.now())

#         # ✅ OVERWRITE ALL baseline_* COLUMNS WITH FRESH SCADA VALUES
#         print(f"📊 [{po_number}] Setting fresh SCADA baselines: {baselines}")
#         for tag, value in baselines.items():
#             set_attr_safe(order, f"baseline_{tag.lower()}", float(value or 0.0))
#             print(f"  ✅ baseline_{tag.lower()} = {value}")

#         # ✅ CRITICAL: MARK ALL BASELINES AS "FIXED" TO PREVENT RE-CAPTURE
#         baseline_fixed_flags = {tag.lower(): True for tag in equipment}
#         set_attr_safe(order, "baseline_fixed_flags", baseline_fixed_flags)

#         # Handle MILLING vs PACKING scale setup
#         if order_type_new == "MILLING":
#             version = (get_attr_safe(order, "version") or "").strip().upper()
#             print(f"🛠 Setting by-product scales for {po_number} / {version}")

#             # Capture byproduct baselines (overrides if same tag)
#             baselines = _capture_byproduct_baselines(version, baselines, order=order)

#             # Save all baselines (main + byproduct)
#             for tag, val in baselines.items():
#                 set_attr_safe(order, f"baseline_{tag.lower()}", float(val or 0.0))

#             _set_byproduct_scales(order, version, baselines)

#             # ✅ CRITICAL: Always capture fresh shift baselines on restart
#             # This allows us to track NEW production after restart
#             # Shift WEIGHTS are preserved (not reset), so we accumulate: old_weight + new_production
#             set_attr_safe(
#                 order,
#                 f"baseline_shift_{current_shift.lower()}_start",
#                 baselines,
#             )
#             # ✅ Store baseline capture time for tracking
#             set_attr_safe(order, f"baseline_shift_{current_shift.lower()}_time", datetime.now())
#             print(f"✅ [{po_number}] Set fresh shift baselines for shift {current_shift} (shift weight preserved for accumulation)")

#             # ✅ Also mark byproduct scales as fixed
#             all_tags = set(equipment)
#             for scale_key in ["scale1", "scale2", "scale3"]:
#                 tag = get_attr_safe(order, scale_key)
#                 if tag:
#                     all_tags.add(tag)
#             updated_flags = {tag.lower(): True for tag in all_tags}
#             set_attr_safe(order, "baseline_fixed_flags", updated_flags)

#         else:
#             # PACKING logic (unchanged)
#             pallet_equipment = equipment
#             if pallet_equipment:
#                 tag = pallet_equipment[0]
#                 set_attr_safe(order, "scale1", tag)
#                 set_attr_safe(order, "scale1_qty", float(baselines.get(tag, 0.0) or 0.0))
#             else:
#                 set_attr_safe(order, "scale1", None)
#                 set_attr_safe(order, "scale1_qty", 0.0)

#             # Clear extra scales
#             for i in [2, 3]:
#                 set_attr_safe(order, f"scale{i}", None)
#                 set_attr_safe(order, f"scale{i}_qty", 0.0)

#             # ✅ CRITICAL: Always capture fresh shift baselines on restart
#             # This allows us to track NEW production after restart
#             # Shift WEIGHTS are preserved (not reset), so we accumulate: old_weight + new_production
#             # ✅ FIX: Create shift baseline dict with ALL pallet equipment tags (not just first one)
#             shift_baseline_dict = {}
#             if pallet_equipment:
#                 for tag in pallet_equipment:
#                     shift_baseline_dict[tag] = float(baselines.get(tag, 0.0) or 0.0)
            
#             set_attr_safe(
#                 order,
#                 f"baseline_shift_{current_shift.lower()}_start",
#                 shift_baseline_dict,
#             )
#             # ✅ Store baseline capture time for tracking
#             set_attr_safe(order, f"baseline_shift_{current_shift.lower()}_time", datetime.now())
#             print(f"✅ [{po_number}] Set fresh PACKING shift baselines for shift {current_shift}: {shift_baseline_dict} (shift weight preserved for accumulation)")

#         # ✅ CRITICAL: Get order status BEFORE any modifications (for brand new order check)
#         current_status_before = get_attr_safe(order, "status", "Pending")
        
#         # ✅ CRITICAL: Detect if this is a brand new order (after deleting old order)
#         # Brand new orders should have all values = 0 and status = Pending
#         is_brand_new_order = (
#             preserved_confirmed_qty == 0.0 and 
#             preserved_weight_a == 0.0 and 
#             preserved_weight_b == 0.0 and 
#             preserved_weight_c == 0.0 and
#             current_status_before == "Pending"
#         )
        
#         # ✅ CRITICAL: For brand new orders, FORCE clear all caches to prevent inheriting values from deleted orders
#         # This is especially important if the new order has the same PO number as a deleted order
#         if is_brand_new_order:
#             print(f"🆕 [{po_number}] Brand new order detected - FORCING cache clear to prevent inheriting values from deleted orders")
#             for shift_code in ["a", "b", "c"]:
#                 cache_key = (po_number, shift_code)
#                 # ✅ CRITICAL: Use pop() to force delete from both caches, even if they don't exist
#                 # This ensures we remove any stale cache from deleted orders
#                 old_prod_cache = _last_shift_production_cache.pop(cache_key, None)
#                 if old_prod_cache is not None:
#                     print(f"🧹 [Start-{po_number}] FORCED clear production cache for shift {shift_code.upper()} (removed value: {old_prod_cache:.2f} from deleted order)")
#                 old_max_cache = _max_shift_weight_cache.pop(cache_key, None)
#                 if old_max_cache is not None:
#                     print(f"🧹 [Start-{po_number}] FORCED clear max weight cache for shift {shift_code.upper()} (removed value: {old_max_cache:.2f} from deleted order)")
#             print(f"✅ [{po_number}] All caches cleared for brand new order - will start fresh")
        
#         # --- Overflow & auto-validation logic ---
#         # ✅ CRITICAL FIX: Only apply overflow if this is NOT a brand new order
#         # Brand new orders should start with confirmed_qty = 0, not inherit overflow from old deleted orders
        
#         overflow_applied = 0.0
#         if not is_brand_new_order:
#             # Only check for overflow if this is a restart of an existing order (not a brand new order)
#             current_version = (get_attr_safe(order, "version") or "").strip().upper()
#             completed_with_overflow_list = db.query(ProcessOrder).filter(
#                 ProcessOrder.status == "Validated",
#                 ProcessOrder.overflow_weight > 0
#             ).order_by(ProcessOrder.id.desc()).all()

#             completed_with_overflow = None
#             for candidate in completed_with_overflow_list:
#                 candidate_type = get_attr_safe(candidate, "order_type", "")
#                 if not candidate_type:
#                     try:
#                         candidate_class = classify_order(candidate)
#                         if not candidate_class.get("error"):
#                             candidate_type = candidate_class.get("order_type", "")
#                             set_attr_safe(candidate, "order_type", candidate_type)
#                             db.add(candidate)
#                     except Exception:
#                         pass

#                 candidate_version = (get_attr_safe(candidate, "version") or "").strip().upper()
#                 if candidate_type == order_type_new and candidate_version == current_version:
#                     completed_with_overflow = candidate
#                     break

#             if completed_with_overflow:
#                 overflow_weight = float(get_attr_safe(completed_with_overflow, "overflow_weight", 0.0) or 0.0)
#                 if overflow_weight > 0:
#                     overflow_applied = overflow_weight
#                     set_attr_safe(order, "confirmed_qty", overflow_applied)
#                     set_attr_safe(completed_with_overflow, "overflow_weight", 0.0)
#                     db.add(completed_with_overflow)
#                     db.commit()
#                     print(f"✅ Applied overflow {overflow_applied} from {completed_with_overflow.order_id} to {order.order_id}")
#         else:
#             print(f"✅ [{po_number}] Brand new order detected - skipping overflow application (confirmed_qty=0, all shift weights=0, status was Pending)")

#         # ✅ CRITICAL: Preserve confirmed_qty if it exists (for restarted orders)
#         # Overflow handling: if overflow is applied, it's already set above
#         set_attr_safe(order, "status", "InProgress")

#         if overflow_applied == 0.0:
#             # Use the preserved confirmed_qty value we read at the start
#             # NEVER reset confirmed_qty if it has a value - only set to 0 for brand new orders
#             if preserved_confirmed_qty > 0.0:
#                 # ✅ CRITICAL: Explicitly preserve the existing confirmed_qty for restarted orders
#                 # This MUST be set BEFORE any other operations that might affect confirmed_qty
#                 set_attr_safe(order, "confirmed_qty", preserved_confirmed_qty)
#                 print(f"✅ [{po_number}] PRESERVING confirmed_qty: {preserved_confirmed_qty} (DO NOT RESET)")
#                 # Verify it was set correctly
#                 verify_qty = float(order.confirmed_qty if hasattr(order, 'confirmed_qty') and order.confirmed_qty is not None else 0.0)
#                 if verify_qty != preserved_confirmed_qty:
#                     print(f"⚠️ [{po_number}] WARNING: confirmed_qty mismatch! Expected {preserved_confirmed_qty}, got {verify_qty}")
#                     # Force set it again
#                     set_attr_safe(order, "confirmed_qty", preserved_confirmed_qty)
#                     print(f"✅ [{po_number}] Force-set confirmed_qty to {preserved_confirmed_qty}")
#                 else:
#                     print(f"✅ [{po_number}] Verified: confirmed_qty correctly set to {verify_qty}")
#             else:
#                 # Brand new order, set to 0
#                 # ✅ CRITICAL: Force set to 0 even if database has stale value from deleted order
#                 set_attr_safe(order, "confirmed_qty", 0.0)
#                 print(f"ℹ️ [{po_number}] Setting confirmed_qty to 0.0 for brand new order (force clear any stale values)")
                
#                 # ✅ CRITICAL: Also ensure all shift weights are 0 for brand new orders
#                 # This prevents inheriting values from deleted orders
#                 set_attr_safe(order, "weight_shift_a", 0.0)
#                 set_attr_safe(order, "weight_shift_b", 0.0)
#                 set_attr_safe(order, "weight_shift_c", 0.0)
#                 print(f"🧹 [{po_number}] Force cleared all shift weights to 0.0 for brand new order")
#         else:
#             print(f"✅ Keeping overflow in confirmed_qty: {overflow_applied}")
        
#         # ✅ CRITICAL: Explicitly preserve shift weights (DO NOT reset them!)
#         # Shift weights accumulate production across restarts
#         set_attr_safe(order, "weight_shift_a", preserved_weight_a)
#         set_attr_safe(order, "weight_shift_b", preserved_weight_b)
#         set_attr_safe(order, "weight_shift_c", preserved_weight_c)
#         if preserved_weight_a > 0.0 or preserved_weight_b > 0.0 or preserved_weight_c > 0.0:
#             print(f"✅ [{po_number}] PRESERVING shift weights: A={preserved_weight_a:.2f}, B={preserved_weight_b:.2f}, C={preserved_weight_c:.2f} (DO NOT RESET)")

#         # Auto-validate if overflow >= target
#         order_auto_validated = False
#         if overflow_applied > 0:
#             target_qty = float(
#                 get_attr_safe(order, "expected_weight") or get_attr_safe(order, "quantity") or 0.0
#             ) if order_type_new == "MILLING" else float(get_attr_safe(order, "quantity") or 0.0)
#             unit = "KG" if order_type_new == "MILLING" else "BAG"

#             if target_qty > 0 and overflow_applied >= target_qty:
#                 # ✅ FIXED: Don't calculate or accumulate shift weight here
#                 # The auto-validator worker already tracks weight_shift_X in real-time
#                 # Just mark shift end time if needed
#                 current_shift = get_attr_safe(order, "current_shift", None)
#                 if current_shift:
#                     set_attr_safe(order, "shift_end_time", datetime.now())

#                 set_attr_safe(order, "status", "Validated")
#                 set_attr_safe(order, "is_final_sent", False)
#                 set_attr_safe(order, "current_shift", None)
#                 set_attr_safe(order, "validation_method", "Automatic")
#                 set_attr_safe(order, "confirmed_qty", target_qty)
#                 set_attr_safe(order, "confirmed_text", f"Auto: Target met instantly from overflow ({overflow_applied:.2f}/{target_qty:.2f} {unit})")
#                 excess = overflow_applied - target_qty
#                 set_attr_safe(order, "overflow_weight", max(0.0, excess))
#                 order_auto_validated = True

#         if not order_auto_validated:
#             set_attr_safe(order, "is_final_sent", False)

#         db.add(order)
#         db.commit()
        
#         # ✅ CRITICAL: Verify preserved confirmed_qty and shift weights were committed correctly
#         db.refresh(order)
#         final_confirmed_qty = float(order.confirmed_qty if hasattr(order, 'confirmed_qty') and order.confirmed_qty is not None else 0.0)
#         final_weight_a = float(get_attr_safe(order, "weight_shift_a", 0.0) or 0.0)
#         final_weight_b = float(get_attr_safe(order, "weight_shift_b", 0.0) or 0.0)
#         final_weight_c = float(get_attr_safe(order, "weight_shift_c", 0.0) or 0.0)
        
#         if preserved_confirmed_qty > 0.0 and overflow_applied == 0.0:
#             if final_confirmed_qty != preserved_confirmed_qty:
#                 print(f"❌ [{po_number}] ERROR: confirmed_qty not preserved after commit! Expected {preserved_confirmed_qty:.2f}, got {final_confirmed_qty:.2f}")
#                 # Force set it again
#                 set_attr_safe(order, "confirmed_qty", preserved_confirmed_qty)
#                 db.add(order)
#                 db.commit()
#                 print(f"✅ [{po_number}] Fixed: confirmed_qty set to {preserved_confirmed_qty:.2f}")
#             else:
#                 print(f"✅ [{po_number}] Verified: confirmed_qty={final_confirmed_qty:.2f} correctly committed to database")
        
#         # Verify shift weights were preserved
#         if preserved_weight_a > 0.0 or preserved_weight_b > 0.0 or preserved_weight_c > 0.0:
#             if final_weight_a != preserved_weight_a or final_weight_b != preserved_weight_b or final_weight_c != preserved_weight_c:
#                 print(f"❌ [{po_number}] ERROR: Shift weights not preserved after commit!")
#                 print(f"   Expected: A={preserved_weight_a:.2f}, B={preserved_weight_b:.2f}, C={preserved_weight_c:.2f}")
#                 print(f"   Got: A={final_weight_a:.2f}, B={final_weight_b:.2f}, C={final_weight_c:.2f}")
#                 # Force set them again
#                 set_attr_safe(order, "weight_shift_a", preserved_weight_a)
#                 set_attr_safe(order, "weight_shift_b", preserved_weight_b)
#                 set_attr_safe(order, "weight_shift_c", preserved_weight_c)
#                 db.add(order)
#                 db.commit()
#                 print(f"✅ [{po_number}] Fixed: Shift weights restored")
#             else:
#                 print(f"✅ [{po_number}] Verified: Shift weights preserved correctly: A={final_weight_a:.2f}, B={final_weight_b:.2f}, C={final_weight_c:.2f}")

#         final_status = get_attr_safe(order, "status", "InProgress")

#         if not order_auto_validated:
#             validation_thread = threading.Thread(
#                 target=auto_validation_worker,
#                 args=(po_number, classification),
#                 daemon=True,
#                 name=f"Validation-{po_number}",
#             )
#             set_order_validation_state(po_number, {
#                 "isrunning": True,
#                 "thread": validation_thread,
#                 "progress_pct": 0,
#                 "status": "running",
#                 "started_at": datetime.now().isoformat()
#             })
#             validation_thread.start()
#             print(f"🚀 Started validation thread for {po_number}")

#     return jsonify({
#         "success": True,
#         "po_number": po_number,
#         "status": final_status,
#         "order_type": classification["order_type"],
#         "equipment": equipment,
#         "formula": classification.get("formula", ""),
#         "baselines": baselines,
#         "auto_validated": order_auto_validated,
#     })

# @orders_bp.route("/<string:po_number>/validate", methods=["POST"])
# def validate_order(po_number: str):
#     if ProcessOrder is None:
#         raise BadRequest("ProcessOrder model not available")

#     with _db_session() as db:
#         order = db.query(ProcessOrder).filter(
#             ProcessOrder.order_id == po_number
#         ).first()

#         if not order:
#             raise NotFound(f"Order {po_number} not found")

#         if order.status != "InProgress":
#             return jsonify({
#                 "success": False,
#                 "message": f"Cannot validate order with status '{order.status}'"
#             }), 400

#         classification = classify_order(order)
#         if classification.get("error"):
#             raise BadRequest(f"Classification failed: {classification['error']}")

#         completion = check_order_completion(order, classification)
#         if completion.get("error"):
#             raise BadRequest(f"Validation failed: {completion['error']}")

#         if completion["is_complete"]:
#             # ✅ FIXED: Don't calculate or accumulate shift weight here
#             # The auto-validator worker already tracks weight_shift_X in real-time
#             # Just mark shift end time if needed
#             current_shift = get_attr_safe(order, "current_shift", None)
#             if current_shift:
#                 set_attr_safe(order, "shift_end_time", datetime.now())

#             set_attr_safe(order, "status", "Validated")
#             set_attr_safe(order, "validation_method", "Manual")
#             set_attr_safe(order, "confirmed_qty", completion["actual_qty"])

#             # Let shift_auto_confirm send SAP
#             set_attr_safe(order, "is_final_sent", False)
#             set_attr_safe(order, "shift_end_time", datetime.now())
#             set_attr_safe(order, "current_shift", None)

#             overflow = completion.get("overflow", 0.0)
#             if overflow > 0:
#                 set_attr_safe(order, "overflow_weight", overflow)
            
#             # ✅ CRITICAL: Stop validation worker for this order if running
#             print(f"🛑 [Validate-{po_number}] Stopping validation worker...")
#             set_order_validation_state(po_number, {"isrunning": False})
            
#             # ✅ CRITICAL: Wait for worker to fully stop before proceeding
#             # This ensures the scheduler doesn't think there's still an order in progress
#             import time
#             time.sleep(1.0)  # Wait 1 second for worker to stop
#             print(f"✅ [Validate-{po_number}] Worker stopped, proceeding with validation...")
            
#             # ✅ CRITICAL FIX: Capture final SCADA readings at validation time and store them
#             # This ensures that when viewing a validated order, we show the correct final values
#             # We preserve the original baseline (used during production) and store final SCADA readings
#             print(f"🔄 [Validate-{po_number}] Capturing final SCADA readings at validation time...")
#             try:
#                 from services.scale_service import clear_scada_cache, get_multiple_scada_readings
#                 # ✅ CRITICAL: Clear SCADA cache multiple times to ensure truly fresh values
#                 clear_scada_cache()
#                 import time
#                 time.sleep(0.2)
#                 clear_scada_cache()  # Clear again to be sure
#                 print(f"✅ [Validate-{po_number}] SCADA cache cleared (twice) before capturing final readings")
#             except Exception as e:
#                 print(f"⚠️ [Validate-{po_number}] Could not clear SCADA cache: {e}")
#                 get_multiple_scada_readings = None
#                 import time
            
#             # ✅ CRITICAL: Wait longer for fresh SCADA values to ensure we get the latest readings
#             # This is especially important if SCADA values are still updating
#             time.sleep(0.5)
            
#             # Get equipment list for this order
#             equipment = classification.get("equipment", [])
#             if equipment and get_multiple_scada_readings:
#                 # ✅ CRITICAL: Take multiple readings to ensure we get the most recent/final value
#                 # First reading might still be cached or slightly stale
#                 print(f"🔍 [Validate-{po_number}] Taking multiple SCADA readings to ensure final values...")
#                 final_readings_1 = get_multiple_scada_readings(equipment, force_fresh=True)
#                 time.sleep(0.3)
#                 final_readings_2 = get_multiple_scada_readings(equipment, force_fresh=True)
#                 time.sleep(0.3)
#                 final_readings_3 = get_multiple_scada_readings(equipment, force_fresh=True)
                
#                 # Use the most recent reading (should be the final value)
#                 final_readings = final_readings_3 if final_readings_3 else (final_readings_2 if final_readings_2 else final_readings_1)
                
#                 print(f"🔍 [Validate-{po_number}] Final SCADA readings captured (3 attempts):")
#                 for tag in equipment:
#                     if tag in final_readings:
#                         reading_data = final_readings[tag]
#                         if isinstance(reading_data, dict):
#                             val = reading_data.get("current", 0.0)
#                         else:
#                             val = reading_data
#                         print(f"   {tag}: {val}")
                
#                 if final_readings:
#                     print(f"✅ [Validate-{po_number}] Captured final SCADA readings: {final_readings}")
                    
#                     # ✅ CRITICAL: Update baseline to final SCADA reading at validation time
#                     # This ensures that when viewing a validated order, baseline = final SCADA reading
#                     # Deltas will be calculated as: current_SCADA - baseline (which will be 0 or very small for validated orders)
#                     # NOTE: We do NOT store deltas in scale_qty - scale_qty is ONLY for byproduct scales at order start
#                     print(f"🔄 [Validate-{po_number}] Updating baseline columns to final SCADA readings...")
#                     for tag, reading_data in final_readings.items():
#                         baseline_attr = f"baseline_{tag.lower()}"
#                         if isinstance(reading_data, dict):
#                             final_current = float(reading_data.get("current", 0.0) or 0.0)
#                         else:
#                             final_current = float(reading_data or 0.0)
                        
#                         old_baseline = float(get_attr_safe(order, baseline_attr, 0.0) or 0.0)
#                         set_attr_safe(order, baseline_attr, final_current)
#                         if old_baseline != final_current:
#                             print(f"   ✅ {tag}: baseline updated from {old_baseline:.2f} to {final_current:.2f} (final SCADA reading)")
#                         else:
#                             print(f"   ✓ {tag}: baseline already correct at {final_current:.2f}")
                    
#                     # ✅ CRITICAL: Flush baseline updates before commit to ensure they're saved
#                     db.add(order)
#                     db.flush()
#                     print(f"✅ [Validate-{po_number}] Baseline updates flushed to database")
                    
#                     # Also update shift baseline if current_shift exists
#                     if current_shift:
#                         final_baselines_dict = {}
#                         for tag, reading_data in final_readings.items():
#                             if isinstance(reading_data, dict):
#                                 final_baselines_dict[tag] = float(reading_data.get("current", 0.0) or 0.0)
#                             else:
#                                 final_baselines_dict[tag] = float(reading_data or 0.0)
                        
#                         set_attr_safe(
#                             order,
#                             f"baseline_shift_{current_shift.lower()}_start",
#                             final_baselines_dict
#                         )
#                         print(f"✅ [Validate-{po_number}] Updated shift baseline for shift {current_shift}")
                    
#                     print(f"✅ [Validate-{po_number}] Final SCADA readings captured and stored at validation time")
#                 else:
#                     print(f"⚠️ [Validate-{po_number}] Failed to capture final SCADA readings, keeping existing values")
#             else:
#                 print(f"⚠️ [Validate-{po_number}] No equipment found or get_multiple_scada_readings unavailable, skipping final reading capture")
#         else:
#             set_attr_safe(order, "status", "Validation_Failed")
#             set_attr_safe(order, "confirmed_qty", completion["actual_qty"])
#             set_attr_safe(
#                 order,
#                 "confirmed_text",
#                 f"Target not reached: {completion['actual_qty']:.2f}/"
#                 f"{completion['target_qty']:.2f} {completion['unit']}"
#             )

#         db.add(order)
#         db.commit()
        
#         # ✅ CRITICAL: Refresh order to ensure baseline updates are fully persisted
#         # This ensures the validated order's baseline values are correctly saved before scheduler starts
#         db.refresh(order)
        
#         # ✅ CRITICAL: Verify baseline values were actually saved correctly
#         if completion["is_complete"] and equipment:
#             print(f"🔍 [Validate-{po_number}] Verifying baseline values after commit...")
#             for tag in equipment:
#                 baseline_attr = f"baseline_{tag.lower()}"
#                 saved_baseline = float(get_attr_safe(order, baseline_attr, 0.0) or 0.0)
#                 print(f"   {tag}: saved baseline = {saved_baseline:.2f}")
        
#         print(f"✅ [Validate-{po_number}] Order refreshed after commit - baseline values verified and persisted")
        
#         # ✅ CRITICAL: Add a small delay to ensure database changes are fully propagated
#         # This prevents race conditions where the scheduler might read stale baseline values
#         import time
#         time.sleep(0.5)
        
#         # ✅ CRITICAL: Trigger scheduler to start next priority order of same type (after commit)
#         # Only if order was successfully validated and auto-validator is enabled
#         if completion["is_complete"] and is_auto_validator_enabled():
#             try:
#                 order_type_validated = classification.get("order_type", "UNKNOWN")
#                 print(f"🔁 [Manual Validate-{po_number}] Order type: {order_type_validated}, triggering scheduler to start next priority order")
#                 print(f"🔍 [Manual Validate-{po_number}] Conditions: is_complete={completion['is_complete']}, is_auto_validator_enabled()={is_auto_validator_enabled()}")
                
#                 # ✅ CRITICAL: Wait a bit more to ensure worker thread has fully exited
#                 # This prevents the scheduler from thinking there's still an order in progress
#                 time.sleep(0.5)
                
#                 _schedule_next_orders_after_completion()
#                 print(f"✅ [Manual Validate-{po_number}] Scheduler completed")
#             except Exception as e:
#                 print(f"⚠️ [Manual Validate-{po_number}] Failed to schedule next order: {e}")
#                 import traceback
#                 traceback.print_exc()
#         else:
#             print(f"🔍 [Manual Validate-{po_number}] Not triggering scheduler: is_complete={completion.get('is_complete', False)}, is_auto_validator_enabled()={is_auto_validator_enabled()}")

#     return jsonify({
#         "success": True,
#         "po_number": po_number,
#         "order_type": classification["order_type"],
#         "validation_result": completion,
#         "order_status": order.status
#     })

# @orders_bp.route("/<int:order_id>/reject", methods=["POST"])
# def reject_order(order_id: int):
#     if ProcessOrder is None:
#         raise BadRequest("ProcessOrder model not available")
#     try:
#         data = request.get_json() or {}
#         remarks = data.get("remarks", "")
#         rejected_by = data.get("rejected_by", "")
#         po_number = None
#         with _db_session() as db:
#             order = db.query(ProcessOrder).filter(ProcessOrder.id == order_id).first()
#             if not order:
#                 raise NotFound(f"Order with ID {order_id} not found")
#             if order.status != "InProgress":
#                 return jsonify({"success": False, "message": f"Cannot reject order with status '{order.status}'. Only InProgress orders can be rejected."}), 400
#             po_number = get_attr_safe(order, "order_id", "")
#             set_attr_safe(order, "status", "Rejected")
#             set_attr_safe(order, "validation_method", "Manual")
#             rejection_text = f"Rejected: {remarks}"
#             if rejected_by:
#                 rejection_text += f" (by {rejected_by})"
#             set_attr_safe(order, "confirmed_text", rejection_text)
#             if AUTO_VALIDATOR_STATE["isrunning"] and AUTO_VALIDATOR_STATE["current_order"] == po_number:
#                 AUTO_VALIDATOR_STATE["current_order"] = None
#                 print(f"🛑 Order {po_number} rejected - Auto-validator will move to next priority order")
#             db.add(order)
#             db.commit()
#         return jsonify({"success": True, "po_number": po_number or f"ID-{order_id}", "order_id": order_id, "status": "Rejected", "message": f"Order {po_number or f'ID-{order_id}'} rejected successfully. Auto-validator will move to next order if running."})
#     except NotFound as e:
#         return jsonify({"error": str(e)}), 404
#     except BadRequest as e:
#         return jsonify({"error": str(e)}), 400
#     except Exception as e:
#         print(f"❌ Error rejecting order: {e}")
#         import traceback
#         traceback.print_exc()
#         return jsonify({"error": f"Failed to reject order: {str(e)}"}), 500


# @orders_bp.route("/<string:po_number>/stop", methods=["POST"])
# def stop_order(po_number: str):
#     if ProcessOrder is None:
#         raise BadRequest("ProcessOrder model not available")
#     with _db_session() as db:
#         order = db.query(ProcessOrder).filter(ProcessOrder.order_id == po_number).first()
#         if not order:
#             raise NotFound(f"Order {po_number} not found")
#         if order.status != "InProgress":
#             return jsonify({
#                 "success": False,
#                 "message": f"Cannot stop order with status '{order.status}'. Only InProgress orders can be stopped."
#             }), 400

#         # ✅ 1. Set status to Pending
#         set_attr_safe(order, "status", "Pending")

#         # ✅ 2. Signal worker to stop via validation state
#         set_order_validation_state(po_number, {"isrunning": False})

#         # ✅ 3. Reset baseline_fixed_flags so new baselines are captured on restart
#         baseline_fixed_flags = get_attr_safe(order, "baseline_fixed_flags", {}) or {}
#         for key in list(baseline_fixed_flags.keys()):
#             baseline_fixed_flags[key] = False
#         set_attr_safe(order, "baseline_fixed_flags", baseline_fixed_flags)

#         # ✅ 4. Reset ALL baseline column values to 0
#         # PACKING: Bag counter baselines
#         set_attr_safe(order, "baseline_sl601_counter", 0.0)
#         set_attr_safe(order, "baseline_sl602_counter", 0.0)
#         set_attr_safe(order, "baseline_sl603_counter", 0.0)
#         set_attr_safe(order, "baseline_sl606_counter", 0.0)
#         set_attr_safe(order, "baseline_sl607_counter", 0.0)
        
#         # MILLING: Flour/Bran output baselines
#         set_attr_safe(order, "baseline_wg101", 0.0)
#         set_attr_safe(order, "baseline_wg201", 0.0)
#         set_attr_safe(order, "baseline_wg202", 0.0)
#         set_attr_safe(order, "baseline_wg301", 0.0)
#         set_attr_safe(order, "baseline_wg302", 0.0)
#         set_attr_safe(order, "baseline_wg501", 0.0)
#         set_attr_safe(order, "baseline_wg502", 0.0)
#         set_attr_safe(order, "baseline_wg503", 0.0)
        
#         # WATER DOSING METER baselines
#         set_attr_safe(order, "baseline_dm101", 0.0)
#         set_attr_safe(order, "baseline_dm102", 0.0)
#         set_attr_safe(order, "baseline_dm201", 0.0)
#         set_attr_safe(order, "baseline_dm202", 0.0)
#         set_attr_safe(order, "baseline_dm203", 0.0)
        
#         # ✅ CRITICAL: Reset shift baseline JSON fields (these are used for production calculation)
#         set_attr_safe(order, "baseline_shift_a_start", None)
#         set_attr_safe(order, "baseline_shift_b_start", None)
#         set_attr_safe(order, "baseline_shift_c_start", None)

#         db.add(order)
#         db.commit()
#         print(f"✅ [{po_number}] Reset all baseline values to 0 and shift baselines to NULL")

#     return jsonify({
#         "success": True,
#         "po_number": po_number,
#         "status": "Pending",
#         "message": f"Order {po_number} stopped. Validation frozen."
#     })

# @orders_bp.route("/<string:po_number>/progress", methods=["GET"])
# def get_progress(po_number: str):
#     if ProcessOrder is None:
#         raise NotFound("ProcessOrder model not available")

#     try:
#         with _db_session() as db:
#             # 1️⃣ Fetch order safely
#             order = db.query(ProcessOrder).filter(ProcessOrder.order_id == po_number).first()
#             if not order:
#                 raise NotFound(f"Order {po_number} not found")

#             # 2️⃣ Classify order (MILLING / PACKING)
#             classification = classify_order(order)
#             if classification.get("error"):
#                 return jsonify({"po_number": po_number, "error": classification["error"]}), 400

#             order_type = classification["order_type"]
#             equipment = classification["equipment"]

#             # ✅ FIX: If auto-validator is stopped, calculate deltas from baseline and current SCADA
#             # NOTE: scale_qty is ONLY for byproduct scales at order start, NOT for production deltas
#             if not is_order_validating(po_number):
#                 # ✅ CRITICAL: Refresh order to get latest confirmed_qty and baseline from database
#                 db.refresh(order)
                
#                 # Determine unit and target
#                 if order_type == "MILLING":
#                     target = float(get_attr_safe(order, "expected_weight") or get_attr_safe(order, "quantity") or 0.0)
#                     unit = "KG"
#                 else:
#                     target = float(get_attr_safe(order, "quantity") or 0.0)
#                     unit = "BAG"

#                 # ✅ CRITICAL: Get stored confirmed_qty (preserved from previous run)
#                 # ⚠️ IMPORTANT: confirmed_qty is READ-ONLY in this endpoint - we NEVER modify it
#                 # confirmed_qty is only updated by the worker, not by the progress endpoint
#                 confirmed_qty_from_db = float(get_attr_safe(order, "confirmed_qty", 0.0) or 0.0)
#                 current_display = confirmed_qty_from_db
#                 print(f"📊 [Progress-{po_number}] Order stopped - returning preserved confirmed_qty: {current_display:.2f} {unit} (READ-ONLY, will NOT be modified)")
#                 overflow = float(get_attr_safe(order, "overflow_weight", 0.0) or 0.0)
#                 progress_pct = min(100.0, (current_display / target * 100) if target > 0 else 0.0)
#                 remaining = max(0.0, target - current_display)

#                 # ✅ CRITICAL: Calculate deltas from baseline and current SCADA readings (FOR DISPLAY ONLY)
#                 # ⚠️ IMPORTANT: These deltas are ONLY for display in the dialog - they do NOT affect confirmed_qty
#                 # confirmed_qty is preserved in database and should NOT be modified by this endpoint
#                 # Do NOT use scale_qty - it's only for byproduct scales at order start
#                 from services.scale_service import get_multiple_scada_readings
                
#                 # ✅ CRITICAL: Check if shift has ended (baseline was reset)
#                 # If shift ended, baseline was reset but confirmed_qty is preserved
#                 # In this case, deltas should be calculated from the NEW baseline (after reset)
#                 # But these deltas are just for display - they don't represent production to add to confirmed_qty
#                 shift_end_time = get_attr_safe(order, "shift_end_time")
#                 baseline_was_reset = shift_end_time is not None
                
#                 # Get current SCADA readings
#                 current_readings = get_multiple_scada_readings(equipment, force_fresh=True)
                
#                 # Build scale details from baseline and current SCADA (not scale_qty)
#                 scale_details = []
#                 for i, tag in enumerate(equipment, 1):
#                     baseline = float(get_attr_safe(order, f"baseline_{tag.lower()}", 0.0) or 0.0)
                    
#                     # Get current SCADA reading
#                     reading_data = current_readings.get(tag, {})
#                     if isinstance(reading_data, dict):
#                         current_scada = float(reading_data.get("current", 0.0) or 0.0)
#                     else:
#                         current_scada = float(reading_data or 0.0)
                    
#                     # ✅ FIX: Calculate delta from baseline (for display only)
#                     # If baseline was reset, this delta represents production since the reset
#                     # But this is ONLY for display - confirmed_qty already has the preserved value
#                     delta = max(0.0, current_scada - baseline)
                    
#                     scale_detail = {
#                         "scale_number": i,
#                         "scale_tag": tag,
#                         "baseline": round(float(baseline), 3),
#                         "current_reading": round(float(current_scada), 3),  # Current SCADA reading
#                         "delta": round(float(delta), 3),  # Calculated from baseline (DISPLAY ONLY)
#                         "description": get_attr_safe(order, f"scale{i}") or tag,
#                     }
#                     scale_details.append(scale_detail)

#                 # Build equipment details from baseline and current SCADA (not scale_qty)
#                 equipment_details = {}
#                 for tag in equipment:
#                     baseline = float(get_attr_safe(order, f"baseline_{tag.lower()}", 0.0) or 0.0)
                    
#                     # Get current SCADA reading
#                     reading_data = current_readings.get(tag, {})
#                     if isinstance(reading_data, dict):
#                         current_scada = float(reading_data.get("current", 0.0) or 0.0)
#                     else:
#                         current_scada = float(reading_data or 0.0)
                    
#                     # ✅ FIX: Calculate delta from baseline (for display only)
#                     # This delta is ONLY for display - it does NOT affect confirmed_qty
#                     delta = max(0.0, current_scada - baseline)
                    
#                     equipment_details[tag] = {
#                         "baseline": round(float(baseline), 3),
#                         "current": round(float(current_scada), 3),  # Current SCADA reading
#                         "delta": round(float(delta), 3),  # Calculated from baseline (DISPLAY ONLY - does NOT affect confirmed_qty)
#                     }

#                 # Return calculated values from baseline and current SCADA (not from scale_qty)
#                 response = {
#                     "po_number": po_number,
#                     "order_type": order_type,
#                     "status": get_attr_safe(order, "status"),
#                     "material": get_attr_safe(order, "material"),
#                     "version": get_attr_safe(order, "version"),
#                     "batch": get_attr_safe(order, "batch"),
#                     "target": round(float(target), 3),
#                     "current": round(float(current_display), 3),
#                     "remaining": round(float(remaining), 3),
#                     "progress_pct": round(float(progress_pct), 2),
#                     "unit": unit,
#                     "overflow": round(float(overflow), 3),
#                     "confirmed_qty": float(confirmed_qty_from_db),  # ✅ Use the value we read earlier (READ-ONLY)
#                     # "last_confirmed_qty": float(get_attr_safe(order, "last_confirmed_qty", 0) or 0),
#                     "equipment_list": equipment,
#                     "formula": classification.get("formula", ""),
#                     "scale_details": scale_details,
#                     "equipment_details": equipment_details,
#                     "scale_breakdown": {tag: round(float(equipment_details.get(tag, {}).get("delta", 0.0) or 0.0), 3) for tag in equipment},
#                     "timestamp": datetime.now().isoformat(),
#                     "auto_validation": "stopped",
#                     # ✅ CRITICAL: Add warning that deltas are display-only and do NOT affect confirmed_qty
#                     "_warning": "Deltas shown are for display only and do NOT affect confirmed_qty. confirmed_qty is preserved in database and only updated by the worker."
#                 }
#                 # ✅ CRITICAL: Verify confirmed_qty was not modified (safety check)
#                 db.refresh(order)
#                 final_confirmed_qty = float(get_attr_safe(order, "confirmed_qty", 0.0) or 0.0)
#                 if abs(final_confirmed_qty - confirmed_qty_from_db) > 0.0001:
#                     print(f"⚠️ [Progress-{po_number}] WARNING: confirmed_qty changed during progress call! {confirmed_qty_from_db:.2f} → {final_confirmed_qty:.2f}")
#                 else:
#                     print(f"✅ [Progress-{po_number}] confirmed_qty unchanged: {confirmed_qty_from_db:.2f} (verified)")
#                 return jsonify(response)

#             # 3️⃣ Get SCADA readings + baselines (only when auto-validator is running)
#             # ✅ CRITICAL: Refresh order to ensure we have latest baseline values from database
#             db.refresh(order)
#             prod_info = get_current_production(order, classification, db=db)
#             if prod_info.get("error"):
#                 return jsonify({"po_number": po_number, "error": prod_info["error"]}), 400

#             deltas = prod_info["deltas"]
#             baselines = prod_info["baselines"]
#             per_scale = prod_info["per_scale"]
#             baseline_needs_fix = prod_info.get("baseline_needs_fix", False)

#             new_production = float(prod_info.get("total", 0.0) or 0.0)
#             order_type = classification["order_type"]
#             equipment = classification["equipment"]

#             # 4️⃣ Determine unit and target
#             if order_type == "MILLING":
#                 target = float(get_attr_safe(order, "expected_weight") or get_attr_safe(order, "quantity") or 0.0)
#                 unit = "KG"
#             else:
#                 target = float(get_attr_safe(order, "quantity") or 0.0)
#                 unit = "BAG"

#             # 5️⃣ Calculate progress quantities
#             # ✅ CRITICAL: Refresh order to get latest shift weight from database
#             db.refresh(order)
            
#             # ✅ CRITICAL: For active orders, use shift weight (worker updates this in real-time)
#             # confirmed_qty is only set when order completes/validates, so for active orders we use shift weight
#             current_shift = get_attr_safe(order, "current_shift", "A").upper()
#             shift_weight_field = f"weight_shift_{current_shift.lower()}"
#             shift_weight = float(get_attr_safe(order, shift_weight_field, 0.0) or 0.0)
            
#             # ✅ Display logic: Prefer confirmed_qty if available (preserved cumulative production)
#             # ⚠️ IMPORTANT: confirmed_qty is READ-ONLY in this endpoint - we NEVER modify it
#             # confirmed_qty is only updated by the worker, not by the progress endpoint
#             # confirmed_qty is preserved even after shift ends and represents total production
#             confirmed_qty_from_db = float(get_attr_safe(order, "confirmed_qty", 0.0) or 0.0)
            
#             if confirmed_qty_from_db > 0.0:
#                 # ✅ CRITICAL: Use confirmed_qty directly - it represents cumulative production
#                 # The worker may update confirmed_qty continuously or at shift end
#                 # Either way, confirmed_qty is the source of truth for total production
#                 current_display = min(confirmed_qty_from_db, target)
#                 print(f"📊 [Progress-{po_number}] Using confirmed_qty (preserved cumulative): {confirmed_qty_from_db:.2f} {unit} (READ-ONLY)")
#             elif shift_weight > 0.0:
#                 # No confirmed_qty yet, use shift weight (first shift, no previous production)
#                 current_display = min(shift_weight, target)
#                 print(f"📊 [Progress-{po_number}] Using shift weight for current: {shift_weight:.2f} {unit} (shift {current_shift})")
#             else:
#                 # Worker hasn't accumulated yet, use SCADA delta as fallback
#                 current_display = min(new_production, target)
#                 print(f"📊 [Progress-{po_number}] Shift weight is 0, using SCADA delta as fallback: {new_production:.2f} {unit}")

#             overflow = max(0.0, current_display - target)

#             # ✅ CRITICAL: update_order_scales only updates scale1_qty, scale2_qty, scale3_qty
#             # It does NOT modify confirmed_qty - confirmed_qty is only updated by the worker
#             update_order_scales(order, deltas)

#             # Store overflow
#             if overflow > 0:
#                 set_attr_safe(order, "overflow_weight", overflow)

#             # Calculate progress
#             progress_pct = min(100.0, (current_display / target * 100)) if target > 0 else 0.0
#             remaining = max(0.0, target - current_display)


#             # 6️⃣ Build scale details for UI
#             scale_details = []
#             for i, tag in enumerate(equipment, 1):
#                 baseline = baselines.get(tag, 0.0)
#                 delta = per_scale.get(tag, 0.0)
#                 current_reading = deltas.get(tag, {}).get("current", 0.0)
                
#                 # ✅ DEBUG: Log baseline and current values to help troubleshoot
#                 baseline_from_db = float(get_attr_safe(order, f"baseline_{tag.lower()}", 0.0) or 0.0)
#                 if abs(baseline - baseline_from_db) > 0.01:
#                     print(f"⚠️ [Progress-{po_number}] {tag}: Baseline mismatch! From prod_info={baseline:.2f}, from DB={baseline_from_db:.2f}")
#                 print(f"🔍 [Progress-{po_number}] {tag}: baseline={baseline:.2f}, current={current_reading:.2f}, delta={delta:.2f}")

#                 scale_detail = {
#                     "scale_number": i,
#                     "scale_tag": tag,
#                     "baseline": round(float(baseline), 3),
#                     "current_reading": round(float(current_reading), 3),
#                     "delta": round(float(delta), 3),
#                     "description": get_attr_safe(order, f"scale{i}") or tag,
#                 }
#                 scale_details.append(scale_detail)

#             # 7️⃣ Commit once — includes baseline fixes + progress updates
#             if baseline_needs_fix:
#                 print(f"✅ Fixing baselines for {po_number} — committing changes.")
#             db.commit()

#             # 8️⃣ Prepare per-scale summary
#             equipment_details = {}
#             for tag in equipment:
#                 d = deltas.get(tag, {})
#                 equipment_details[tag] = {
#                     "baseline": round(float(baselines.get(tag, 0.0)), 3),
#                     "current": round(float(d.get("current", 0.0)), 3),
#                     "delta": round(float(d.get("delta", 0.0)), 3),
#                 }

#             # 9️⃣ Return clean JSON response
#             response = {
#                 "po_number": po_number,
#                 "order_type": order_type,
#                 "status": get_attr_safe(order, "status"),
#                 "material": get_attr_safe(order, "material"),
#                 "version": get_attr_safe(order, "version"),
#                 "batch": get_attr_safe(order, "batch"),
#                 "target": round(float(target), 3),
#                 "current": round(float(current_display), 3),
#                 "remaining": round(float(remaining), 3),
#                 "progress_pct": round(float(progress_pct), 2),
#                 "unit": unit,
#                 "overflow": round(float(overflow), 3),
#                 "confirmed_qty": float(confirmed_qty_from_db),  # ✅ Use the value we read earlier (READ-ONLY)
#                 # "last_confirmed_qty": float(get_attr_safe(order, "last_confirmed_qty", 0) or 0),
#                 "equipment_list": equipment,
#                 "formula": classification.get("formula", ""),
#                 "scale_details": scale_details,
#                 "equipment_details": equipment_details,
#                 "scale_breakdown": {tag: round(float(val), 3) for tag, val in per_scale.items()},
#                 "timestamp": datetime.now().isoformat(),
#                 "auto_validation": "running",
#                 # ✅ CRITICAL: Add warning that deltas are display-only and do NOT affect confirmed_qty
#                 "_warning": "Deltas shown are for display only and do NOT affect confirmed_qty. confirmed_qty is only updated by the worker."
#             }

#             # ✅ CRITICAL: Verify confirmed_qty was not modified (safety check)
#             db.refresh(order)
#             final_confirmed_qty = float(get_attr_safe(order, "confirmed_qty", 0.0) or 0.0)
#             if abs(final_confirmed_qty - confirmed_qty_from_db) > 0.0001:
#                 print(f"⚠️ [Progress-{po_number}] WARNING: confirmed_qty changed during progress call! {confirmed_qty_from_db:.2f} → {final_confirmed_qty:.2f}")
#             else:
#                 print(f"✅ [Progress-{po_number}] confirmed_qty unchanged: {confirmed_qty_from_db:.2f} (verified)")

#             return jsonify(response)

#     except NotFound as e:
#         return jsonify({"error": str(e)}), 404
#     except Exception as e:
#         print(f"❌ ERROR in get_progress: {e}")
#         import traceback
#         traceback.print_exc()
#         db.rollback()
#         return jsonify({"error": f"Internal error: {str(e)}"}), 500

# @orders_bp.route("/auto-validator/start", methods=["POST"])
# def start_auto_validator():
#     """
#     Start validation for next Milling + Packing orders in parallel.

#     Behaviour:
#     - Resume all existing InProgress orders (if not already validating).
#     - If no Milling in progress, find next Pending order whose classification is MILLING.
#     - If no Packing in progress, find next Pending order whose classification is PACKING.
#     - Initialize them (baselines, shift, status=InProgress) and spawn workers.
#     """
#     global AUTO_VALIDATOR_MASTER
    
#     print("=" * 80)
#     print("🚀 START AUTO-VALIDATOR ENDPOINT CALLED")
#     print("=" * 80)
    
#     # Set master switch to True
#     AUTO_VALIDATOR_MASTER["isrunning"] = True
#     print("⚡ AUTO VALIDATOR MASTER = ON")
#     sys.stdout.flush()
    
#     with _db_session() as db:
#         started_orders: List[str] = []

#         # =========================================================
#         # STEP 1: Resume InProgress orders (NO DELAY NEEDED)
#         # =========================================================
#         inprogress_orders = db.query(ProcessOrder).filter(
#             ProcessOrder.status == "InProgress"
#         ).all()

#         print(f"🔍 Found {len(inprogress_orders)} InProgress orders to resume")

#         for order in inprogress_orders:
#             po_number = order.order_id

#             if is_order_validating(po_number):
#                 print(f"⏭️ {po_number} already validating")
#                 continue

#             classification = classify_order(order)
#             if classification.get("error"):
#                 print(f"❌ Classification error for {po_number}: {classification['error']}")
#                 continue

#             thread = threading.Thread(
#                 target=auto_validation_worker,
#                 args=(po_number, classification),
#                 daemon=True,
#                 name=f"Validation-{po_number}",
#             )

#             set_order_validation_state(po_number, {
#                 "isrunning": True,
#                 "thread": thread,
#                 "progress_pct": 0,
#             })

#             thread.start()
#             started_orders.append(po_number)
#             print(f"🔁 Resumed: {po_number}")

#         # Flags to know if we already have MILLING/PACKING work running
#         has_milling = any(get_attr_safe(o, "order_type") == "MILLING" for o in inprogress_orders)
#         has_packing = any(get_attr_safe(o, "order_type") == "PACKING" for o in inprogress_orders)

#         # =========================================================
#         # STEP 2 & 3: Find next Pending orders by CLASSIFICATION,
#         #             not by DB order_type filter.
#         # =========================================================
#         pending_orders = db.query(ProcessOrder).filter(
#             ProcessOrder.status == "Pending"
#         ).order_by(ProcessOrder.priority.asc()).all()

#         print(f"🔍 Found {len(pending_orders)} Pending orders")

#         next_milling = None
#         next_milling_class = None
#         next_packing = None
#         next_packing_class = None

#         # Classify pending orders and pick first Milling & first Packing
#         print(f"🔍 Classifying {len(pending_orders)} Pending orders to find Milling/Packing...")
#         sys.stdout.flush()
#         for order in pending_orders:
#             po_number = order.order_id

#             if is_order_validating(po_number):
#                 print(f"⏭️ {po_number} pending but already validating in state map, skipping")
#                 sys.stdout.flush()
#                 continue

#             classification = classify_order(order)
#             if classification.get("error"):
#                 print(f"❌ Classification error for pending {po_number}: {classification['error']}")
#                 sys.stdout.flush()
#                 continue

#             c_type = classification.get("order_type")
#             print(f"🔍 Order {po_number} classified as: {c_type}")
#             sys.stdout.flush()

#             if not has_milling and c_type == "MILLING" and next_milling is None:
#                 next_milling = order
#                 next_milling_class = classification
#                 print(f"✅ Selected MILLING order: {po_number}")
#                 sys.stdout.flush()

#             if not has_packing and c_type == "PACKING" and next_packing is None:
#                 next_packing = order
#                 next_packing_class = classification
#                 print(f"✅ Selected PACKING order: {po_number}")
#                 sys.stdout.flush()

#             # If we already chose both, stop scanning
#             if (has_milling or next_milling) and (has_packing or next_packing):
#                 print(f"✅ Found both Milling and Packing orders, stopping scan")
#                 sys.stdout.flush()
#                 break

#         # =========================================================
#         # STEP 2: Start MILLING Pending Order (with byproduct scales)
#         # =========================================================
#         print(f"🔍 Checking MILLING start conditions: has_milling={has_milling}, next_milling={next_milling is not None}, next_milling_class={next_milling_class is not None}")
#         sys.stdout.flush()
#         if not has_milling and next_milling and next_milling_class:
#             order = next_milling
#             classification = next_milling_class
#             po_number = order.order_id

#             # ✅ CRITICAL: Refresh order from database to get latest values
#             db.refresh(order)
            
#             # ✅ CRITICAL: Clear production cache for this order on restart
#             # This ensures we start tracking from 0 after baseline is captured
#             # ✅ CRITICAL: ALWAYS clear cache unconditionally - use pop() to avoid KeyError
#             # This ensures we remove any stale cache from deleted orders with the same PO number
#             for shift_code in ["a", "b", "c"]:
#                 cache_key = (po_number, shift_code)
#                 # Use pop() with default to safely remove cache even if it doesn't exist
#                 old_prod_cache = _last_shift_production_cache.pop(cache_key, None)
#                 if old_prod_cache is not None:
#                     print(f"🧹 [AutoStart-{po_number}] Cleared production cache for shift {shift_code.upper()} (had value: {old_prod_cache:.2f})")
#                 # Initialize max weight cache from preserved weight
#                 weight_field = f"weight_shift_{shift_code}"
#                 preserved_weight = float(get_attr_safe(order, weight_field, 0.0) or 0.0)
#                 if preserved_weight > 0.0:
#                     # But first, clear any existing cache to ensure clean state
#                     old_max_cache = _max_shift_weight_cache.pop(cache_key, None)
#                     if old_max_cache is not None and old_max_cache != preserved_weight:
#                         print(f"🧹 [AutoStart-{po_number}] Cleared old max weight cache for shift {shift_code.upper()} (had value: {old_max_cache:.2f}, will use preserved: {preserved_weight:.2f})")
#                     _max_shift_weight_cache[cache_key] = preserved_weight
#                     print(f"🔍 [AutoStart-{po_number}] Initialized max weight cache for shift {shift_code.upper()} to {preserved_weight:.2f}")
#                 else:
#                     # Brand new order - ALWAYS clear max weight cache if it exists (from deleted order)
#                     old_max_cache = _max_shift_weight_cache.pop(cache_key, None)
#                     if old_max_cache is not None:
#                         print(f"🧹 [AutoStart-{po_number}] Cleared max weight cache for shift {shift_code.upper()} (had value: {old_max_cache:.2f} from deleted order)")
            
#             # ✅ CRITICAL: Read confirmed_qty IMMEDIATELY after refreshing (before any modifications)
#             # Read directly from the order object to ensure we get the actual database value
#             preserved_confirmed_qty_milling = float(order.confirmed_qty if hasattr(order, 'confirmed_qty') and order.confirmed_qty is not None else 0.0)
#             if preserved_confirmed_qty_milling > 0.0:
#                 print(f"🔍 [{po_number}] Found existing confirmed_qty in DB: {preserved_confirmed_qty_milling} - will preserve on restart")
#                 sys.stdout.flush()
#             else:
#                 print(f"🔍 [{po_number}] confirmed_qty is 0 or None in DB - will set to 0 for new order")
#                 sys.stdout.flush()
            
#             # ✅ CRITICAL: Preserve shift weights (DO NOT reset them!)
#             preserved_weight_a_milling = float(get_attr_safe(order, "weight_shift_a", 0.0) or 0.0)
#             preserved_weight_b_milling = float(get_attr_safe(order, "weight_shift_b", 0.0) or 0.0)
#             preserved_weight_c_milling = float(get_attr_safe(order, "weight_shift_c", 0.0) or 0.0)
#             if preserved_weight_a_milling > 0.0 or preserved_weight_b_milling > 0.0 or preserved_weight_c_milling > 0.0:
#                 print(f"🔍 [{po_number}] Found existing shift weights in DB: A={preserved_weight_a_milling:.2f}, B={preserved_weight_b_milling:.2f}, C={preserved_weight_c_milling:.2f} - will preserve on restart")
#                 sys.stdout.flush()

#             print(f"🧮 Preparing MILLING order {po_number}")

#             equipment = classification.get("equipment", []) or []
            
#             # ✅ CRITICAL: FIRST reset ALL baseline columns to 0 to ensure clean slate
#             print(f"🔄 [{po_number}] Resetting all baseline columns to 0 before capturing fresh SCADA values...")
#             # PACKING: Bag counter baselines
#             set_attr_safe(order, "baseline_sl601_counter", 0.0)
#             set_attr_safe(order, "baseline_sl602_counter", 0.0)
#             set_attr_safe(order, "baseline_sl603_counter", 0.0)
#             set_attr_safe(order, "baseline_sl606_counter", 0.0)
#             set_attr_safe(order, "baseline_sl607_counter", 0.0)
#             # MILLING: Flour/Bran output baselines
#             set_attr_safe(order, "baseline_wg101", 0.0)
#             set_attr_safe(order, "baseline_wg201", 0.0)
#             set_attr_safe(order, "baseline_wg202", 0.0)
#             set_attr_safe(order, "baseline_wg301", 0.0)
#             set_attr_safe(order, "baseline_wg302", 0.0)
#             set_attr_safe(order, "baseline_wg501", 0.0)
#             set_attr_safe(order, "baseline_wg502", 0.0)
#             set_attr_safe(order, "baseline_wg503", 0.0)
#             # WATER DOSING METER baselines
#             set_attr_safe(order, "baseline_dm101", 0.0)
#             set_attr_safe(order, "baseline_dm102", 0.0)
#             set_attr_safe(order, "baseline_dm201", 0.0)
#             set_attr_safe(order, "baseline_dm202", 0.0)
#             set_attr_safe(order, "baseline_dm203", 0.0)
            
#             # ✅ CRITICAL: Commit baseline reset to database BEFORE capturing fresh SCADA values
#             db.add(order)
#             db.flush()  # Flush to ensure reset is in database before SCADA capture
            
#             # ✅ VERIFY: Refresh order to confirm baselines were reset in database
#             db.refresh(order)
#             baseline_wg502_check = float(get_attr_safe(order, "baseline_wg502", 0.0) or 0.0)
#             baseline_wg501_check = float(get_attr_safe(order, "baseline_wg501", 0.0) or 0.0)
#             print(f"✅ [{po_number}] All baseline columns reset to 0 and flushed to database")
#             print(f"🔍 [{po_number}] Verification: baseline_wg502={baseline_wg502_check}, baseline_wg501={baseline_wg501_check}")
            
#             baselines = capture_baseline_readings(equipment)

#             if not baselines:
#                 print(f"⚠️ No baselines captured for MILLING {po_number}, skipping")
#             else:
#                 # Ensure every equipment tag has at least a default baseline entry
#                 for tag in equipment:
#                     baselines.setdefault(tag, 0.0)

#                 # ---- Shift detection ----
#                 plant = get_attr_safe(order, "plant", "3130")
#                 shift_row = get_current_shift(plant, "MILLING", db)
#                 current_shift = shift_row.shift_code if shift_row else "A"

#                 set_attr_safe(order, "current_shift", current_shift)
#                 set_attr_safe(order, "shift_start_time", datetime.now())
#                 set_attr_safe(order, "order_type", "MILLING")   # normalize
#                 set_attr_safe(order, "status", "InProgress")
#                 set_attr_safe(order, "validation_method", "Automatic")
#                 # ✅ CRITICAL: Use the preserved confirmed_qty value we read at the start
#                 # NEVER reset confirmed_qty if it has a value - only set to 0 for brand new orders
#                 if preserved_confirmed_qty_milling > 0.0:
#                     # Explicitly preserve the existing confirmed_qty for restarted orders
#                     set_attr_safe(order, "confirmed_qty", preserved_confirmed_qty_milling)
#                     print(f"✅ [{po_number}] PRESERVING confirmed_qty: {preserved_confirmed_qty_milling} (DO NOT RESET)")
#                     # Verify it was set correctly
#                     verify_qty = float(order.confirmed_qty if hasattr(order, 'confirmed_qty') and order.confirmed_qty is not None else 0.0)
#                     if verify_qty != preserved_confirmed_qty_milling:
#                         print(f"⚠️ [{po_number}] WARNING: confirmed_qty mismatch! Expected {preserved_confirmed_qty_milling}, got {verify_qty}")
#                     else:
#                         print(f"✅ [{po_number}] Verified: confirmed_qty correctly set to {verify_qty}")
#                     sys.stdout.flush()
#                 else:
#                     # Brand new order, set to 0
#                     set_attr_safe(order, "confirmed_qty", 0.0)
#                     print(f"ℹ️ [{po_number}] Setting confirmed_qty to 0.0 for brand new order")
#                     sys.stdout.flush()
                
#                 # ✅ CRITICAL: Explicitly preserve shift weights (DO NOT reset them!)
#                 set_attr_safe(order, "weight_shift_a", preserved_weight_a_milling)
#                 set_attr_safe(order, "weight_shift_b", preserved_weight_b_milling)
#                 set_attr_safe(order, "weight_shift_c", preserved_weight_c_milling)
#                 if preserved_weight_a_milling > 0.0 or preserved_weight_b_milling > 0.0 or preserved_weight_c_milling > 0.0:
#                     print(f"✅ [{po_number}] PRESERVING shift weights: A={preserved_weight_a_milling:.2f}, B={preserved_weight_b_milling:.2f}, C={preserved_weight_c_milling:.2f} (DO NOT RESET)")
#                     sys.stdout.flush()

#                 # ---- BYPRODUCT baselines + scale1/2/3 assignment ----
#                 version = (get_attr_safe(order, "version") or "").strip().upper()
#                 print(f"🛠 [AUTO-START] Setting by-product scales for {po_number} / {version}")

#                 # 1) Capture ALL baselines (main + byproduct)
#                 baselines = _capture_byproduct_baselines(version, baselines, order=order)

#                 # 2) Save main + byproduct baselines into baseline_* columns
#                 for tag, value in baselines.items():
#                     set_attr_safe(order, f"baseline_{tag.lower()}", float(value or 0.0))

#                 # 3) Set scale1/2/3 tags and their baseline quantities
#                 _set_byproduct_scales(order, version, baselines)

#                 # ✅ CRITICAL: Always capture fresh shift baselines on restart
#                 # This allows us to track NEW production after restart
#                 # Shift WEIGHTS are preserved (not reset), so we accumulate: old_weight + new_production
#                 set_attr_safe(
#                     order,
#                     f"baseline_shift_{current_shift.lower()}_start",
#                     baselines,
#                 )
#                 # ✅ Store baseline capture time for tracking
#                 set_attr_safe(order, f"baseline_shift_{current_shift.lower()}_time", datetime.now())
#                 print(f"✅ [{po_number}] Set fresh shift baselines for shift {current_shift} (shift weight preserved for accumulation)")

#                 db.add(order)
#                 db.commit()
                
#                 # ✅ CRITICAL: Verify preserved confirmed_qty and shift weights were committed correctly
#                 db.refresh(order)
#                 final_confirmed_qty = float(order.confirmed_qty if hasattr(order, 'confirmed_qty') and order.confirmed_qty is not None else 0.0)
#                 final_weight_a = float(get_attr_safe(order, "weight_shift_a", 0.0) or 0.0)
#                 final_weight_b = float(get_attr_safe(order, "weight_shift_b", 0.0) or 0.0)
#                 final_weight_c = float(get_attr_safe(order, "weight_shift_c", 0.0) or 0.0)
                
#                 if preserved_confirmed_qty_milling > 0.0:
#                     if final_confirmed_qty != preserved_confirmed_qty_milling:
#                         print(f"❌ [{po_number}] ERROR: confirmed_qty not preserved after commit! Expected {preserved_confirmed_qty_milling:.2f}, got {final_confirmed_qty:.2f}")
#                         # Force set it again
#                         set_attr_safe(order, "confirmed_qty", preserved_confirmed_qty_milling)
#                         db.add(order)
#                         db.commit()
#                         print(f"✅ [{po_number}] Fixed: confirmed_qty set to {preserved_confirmed_qty_milling:.2f}")
#                     else:
#                         print(f"✅ [{po_number}] Verified: confirmed_qty={final_confirmed_qty:.2f} correctly committed to database")
                
#                 # Verify shift weights were preserved
#                 if preserved_weight_a_milling > 0.0 or preserved_weight_b_milling > 0.0 or preserved_weight_c_milling > 0.0:
#                     if final_weight_a != preserved_weight_a_milling or final_weight_b != preserved_weight_b_milling or final_weight_c != preserved_weight_c_milling:
#                         print(f"❌ [{po_number}] ERROR: Shift weights not preserved after commit!")
#                         print(f"   Expected: A={preserved_weight_a_milling:.2f}, B={preserved_weight_b_milling:.2f}, C={preserved_weight_c_milling:.2f}")
#                         print(f"   Got: A={final_weight_a:.2f}, B={final_weight_b:.2f}, C={final_weight_c:.2f}")
#                         # Force set them again
#                         set_attr_safe(order, "weight_shift_a", preserved_weight_a_milling)
#                         set_attr_safe(order, "weight_shift_b", preserved_weight_b_milling)
#                         set_attr_safe(order, "weight_shift_c", preserved_weight_c_milling)
#                         db.add(order)
#                         db.commit()
#                         print(f"✅ [{po_number}] Fixed: Shift weights restored")
#                     else:
#                         print(f"✅ [{po_number}] Verified: Shift weights preserved correctly: A={final_weight_a:.2f}, B={final_weight_b:.2f}, C={final_weight_c:.2f}")

#                 # tiny delay so worker session can see committed data
#                 time.sleep(0.2)

#                 print(
#                     f"✅ Initialized MILLING {po_number} "
#                     f"(scale1={order.scale1}, scale2={order.scale2}, scale3={order.scale3}) "
#                     f"— starting thread..."
#                 )

#                 thread = threading.Thread(
#                     target=auto_validation_worker,
#                     args=(po_number, classification),
#                     daemon=True,
#                     name=f"Validation-{po_number}",
#                 )

#                 set_order_validation_state(po_number, {
#                     "isrunning": True,
#                     "thread": thread,
#                     "progress_pct": 0,
#                 })

#                 thread.start()
#                 started_orders.append(po_number)
#                 print(f"▶️ Started MILLING: {po_number}")

#         # =========================================================
#         # STEP 3: Start PACKING Pending Order (with pallet scale1)
#         # =========================================================
#         print(f"🔍 Checking PACKING start conditions: has_packing={has_packing}, next_packing={next_packing is not None}, next_packing_class={next_packing_class is not None}")
#         sys.stdout.flush()
#         if not has_packing and next_packing and next_packing_class:
#             order = next_packing
#             classification = next_packing_class
#             po_number = order.order_id

#             # ✅ CRITICAL: Refresh order from database to get latest values
#             db.refresh(order)
            
#             # ✅ CRITICAL: Clear production cache for this order on restart
#             # This ensures we start tracking from 0 after baseline is captured
#             # ✅ CRITICAL: ALWAYS clear cache unconditionally - use pop() to avoid KeyError
#             # This ensures we remove any stale cache from deleted orders with the same PO number
#             for shift_code in ["a", "b", "c"]:
#                 cache_key = (po_number, shift_code)
#                 # Use pop() with default to safely remove cache even if it doesn't exist
#                 old_prod_cache = _last_shift_production_cache.pop(cache_key, None)
#                 if old_prod_cache is not None:
#                     print(f"🧹 [AutoStart-{po_number}] Cleared production cache for shift {shift_code.upper()} (had value: {old_prod_cache:.2f})")
#                 # Initialize max weight cache from preserved weight
#                 weight_field = f"weight_shift_{shift_code}"
#                 preserved_weight = float(get_attr_safe(order, weight_field, 0.0) or 0.0)
#                 if preserved_weight > 0.0:
#                     # But first, clear any existing cache to ensure clean state
#                     old_max_cache = _max_shift_weight_cache.pop(cache_key, None)
#                     if old_max_cache is not None and old_max_cache != preserved_weight:
#                         print(f"🧹 [AutoStart-{po_number}] Cleared old max weight cache for shift {shift_code.upper()} (had value: {old_max_cache:.2f}, will use preserved: {preserved_weight:.2f})")
#                     _max_shift_weight_cache[cache_key] = preserved_weight
#                     print(f"🔍 [AutoStart-{po_number}] Initialized max weight cache for shift {shift_code.upper()} to {preserved_weight:.2f}")
#                 else:
#                     # Brand new order - ALWAYS clear max weight cache if it exists (from deleted order)
#                     old_max_cache = _max_shift_weight_cache.pop(cache_key, None)
#                     if old_max_cache is not None:
#                         print(f"🧹 [AutoStart-{po_number}] Cleared max weight cache for shift {shift_code.upper()} (had value: {old_max_cache:.2f} from deleted order)")
            
#             # ✅ CRITICAL: Read confirmed_qty IMMEDIATELY after refreshing (before any modifications)
#             # Read directly from the order object to ensure we get the actual database value
#             preserved_confirmed_qty_packing = float(order.confirmed_qty if hasattr(order, 'confirmed_qty') and order.confirmed_qty is not None else 0.0)
#             if preserved_confirmed_qty_packing > 0.0:
#                 print(f"🔍 [{po_number}] Found existing confirmed_qty in DB: {preserved_confirmed_qty_packing} - will preserve on restart")
#                 sys.stdout.flush()
#             else:
#                 print(f"🔍 [{po_number}] confirmed_qty is 0 or None in DB - will set to 0 for new order")
#                 sys.stdout.flush()
            
#             # ✅ CRITICAL: Preserve shift weights (DO NOT reset them!)
#             preserved_weight_a_packing = float(get_attr_safe(order, "weight_shift_a", 0.0) or 0.0)
#             preserved_weight_b_packing = float(get_attr_safe(order, "weight_shift_b", 0.0) or 0.0)
#             preserved_weight_c_packing = float(get_attr_safe(order, "weight_shift_c", 0.0) or 0.0)
#             if preserved_weight_a_packing > 0.0 or preserved_weight_b_packing > 0.0 or preserved_weight_c_packing > 0.0:
#                 print(f"🔍 [{po_number}] Found existing shift weights in DB: A={preserved_weight_a_packing:.2f}, B={preserved_weight_b_packing:.2f}, C={preserved_weight_c_packing:.2f} - will preserve on restart")
#                 sys.stdout.flush()

#             print(f"🧮 Preparing PACKING order {po_number}")

#             equipment = classification.get("equipment", []) or []
            
#             # ✅ CRITICAL: FIRST reset ALL baseline columns to 0 to ensure clean slate
#             print(f"🔄 [{po_number}] Resetting all baseline columns to 0 before capturing fresh SCADA values...")
#             # PACKING: Bag counter baselines
#             set_attr_safe(order, "baseline_sl601_counter", 0.0)
#             set_attr_safe(order, "baseline_sl602_counter", 0.0)
#             set_attr_safe(order, "baseline_sl603_counter", 0.0)
#             set_attr_safe(order, "baseline_sl606_counter", 0.0)
#             set_attr_safe(order, "baseline_sl607_counter", 0.0)
#             # MILLING: Flour/Bran output baselines
#             set_attr_safe(order, "baseline_wg101", 0.0)
#             set_attr_safe(order, "baseline_wg201", 0.0)
#             set_attr_safe(order, "baseline_wg202", 0.0)
#             set_attr_safe(order, "baseline_wg301", 0.0)
#             set_attr_safe(order, "baseline_wg302", 0.0)
#             set_attr_safe(order, "baseline_wg501", 0.0)
#             set_attr_safe(order, "baseline_wg502", 0.0)
#             set_attr_safe(order, "baseline_wg503", 0.0)
#             # WATER DOSING METER baselines
#             set_attr_safe(order, "baseline_dm101", 0.0)
#             set_attr_safe(order, "baseline_dm102", 0.0)
#             set_attr_safe(order, "baseline_dm201", 0.0)
#             set_attr_safe(order, "baseline_dm202", 0.0)
#             set_attr_safe(order, "baseline_dm203", 0.0)
            
#             # ✅ CRITICAL: Commit baseline reset to database BEFORE capturing fresh SCADA values
#             db.add(order)
#             db.flush()  # Flush to ensure reset is in database before SCADA capture
            
#             # ✅ VERIFY: Refresh order to confirm baselines were reset in database
#             db.refresh(order)
#             baseline_sl601_check = float(get_attr_safe(order, "baseline_sl601_counter", 0.0) or 0.0)
#             print(f"✅ [{po_number}] All baseline columns reset to 0 and flushed to database")
#             print(f"🔍 [{po_number}] Verification: baseline_sl601_counter={baseline_sl601_check}")
            
#             baselines = capture_baseline_readings(equipment)

#             if not baselines:
#                 print(f"⚠️ No baselines captured for PACKING {po_number}, skipping")
#             else:
#                 # ---- Shift detection ----
#                 plant = get_attr_safe(order, "plant", "3130")
#                 shift_row = get_current_shift(plant, "PACKING", db)
#                 current_shift = shift_row.shift_code if shift_row else "A"

#                 set_attr_safe(order, "current_shift", current_shift)
#                 set_attr_safe(order, "shift_start_time", datetime.now())
#                 set_attr_safe(order, "order_type", "PACKING")   # normalize
#                 set_attr_safe(order, "status", "InProgress")
#                 set_attr_safe(order, "validation_method", "Automatic")
#                 # ✅ CRITICAL: Use the preserved confirmed_qty value we read at the start
#                 # NEVER reset confirmed_qty if it has a value - only set to 0 for brand new orders
#                 if preserved_confirmed_qty_packing > 0.0:
#                     # Explicitly preserve the existing confirmed_qty for restarted orders
#                     set_attr_safe(order, "confirmed_qty", preserved_confirmed_qty_packing)
#                     print(f"✅ [{po_number}] PRESERVING confirmed_qty: {preserved_confirmed_qty_packing} (DO NOT RESET)")
#                     # Verify it was set correctly
#                     verify_qty = float(order.confirmed_qty if hasattr(order, 'confirmed_qty') and order.confirmed_qty is not None else 0.0)
#                     if verify_qty != preserved_confirmed_qty_packing:
#                         print(f"⚠️ [{po_number}] WARNING: confirmed_qty mismatch! Expected {preserved_confirmed_qty_packing}, got {verify_qty}")
#                     else:
#                         print(f"✅ [{po_number}] Verified: confirmed_qty correctly set to {verify_qty}")
#                     sys.stdout.flush()
#                 else:
#                     # Brand new order, set to 0
#                     set_attr_safe(order, "confirmed_qty", 0.0)
#                     print(f"ℹ️ [{po_number}] Setting confirmed_qty to 0.0 for brand new order")
#                     sys.stdout.flush()
                
#                 # ✅ CRITICAL: Explicitly preserve shift weights (DO NOT reset them!)
#                 set_attr_safe(order, "weight_shift_a", preserved_weight_a_packing)
#                 set_attr_safe(order, "weight_shift_b", preserved_weight_b_packing)
#                 set_attr_safe(order, "weight_shift_c", preserved_weight_c_packing)
#                 if preserved_weight_a_packing > 0.0 or preserved_weight_b_packing > 0.0 or preserved_weight_c_packing > 0.0:
#                     print(f"✅ [{po_number}] PRESERVING shift weights: A={preserved_weight_a_packing:.2f}, B={preserved_weight_b_packing:.2f}, C={preserved_weight_c_packing:.2f} (DO NOT RESET)")
#                     sys.stdout.flush()

#                 # 1) Save baselines into baseline_* columns
#                 for tag, value in baselines.items():
#                     set_attr_safe(order, f"baseline_{tag.lower()}", float(value or 0.0))

#                 # 2) Set scale1 = palletizer tag, qty = its baseline
#                 pallet_equipment = equipment
#                 if pallet_equipment:
#                     tag = pallet_equipment[0]
#                     set_attr_safe(order, "scale1", tag)
#                     set_attr_safe(
#                         order,
#                         "scale1_qty",
#                         float(baselines.get(tag, 0.0) or 0.0),
#                     )
#                 else:
#                     set_attr_safe(order, "scale1", None)
#                     set_attr_safe(order, "scale1_qty", 0.0)

#                 # Clear extra scales for packing
#                 set_attr_safe(order, "scale2", None)
#                 set_attr_safe(order, "scale2_qty", 0.0)
#                 set_attr_safe(order, "scale3", None)
#                 set_attr_safe(order, "scale3_qty", 0.0)

#                 # ✅ CRITICAL: Always capture fresh shift baselines on restart
#                 # This allows us to track NEW production after restart
#                 # Shift WEIGHTS are preserved (not reset), so we accumulate: old_weight + new_production
#                 # ✅ FIX: Create shift baseline dict with ALL pallet equipment tags (not just first one)
#                 shift_baseline_dict = {}
#                 if pallet_equipment:
#                     for tag in pallet_equipment:
#                         shift_baseline_dict[tag] = float(baselines.get(tag, 0.0) or 0.0)
                
#                 set_attr_safe(
#                     order,
#                     f"baseline_shift_{current_shift.lower()}_start",
#                     shift_baseline_dict,
#                 )
#                 # ✅ Store baseline capture time for tracking
#                 set_attr_safe(order, f"baseline_shift_{current_shift.lower()}_time", datetime.now())
#                 print(f"✅ [{po_number}] Set fresh PACKING shift baselines for shift {current_shift}: {shift_baseline_dict} (shift weight preserved for accumulation)")

#                 db.add(order)
#                 db.commit()
                
#                 # ✅ CRITICAL: Verify preserved confirmed_qty and shift weights were committed correctly
#                 db.refresh(order)
#                 final_confirmed_qty = float(order.confirmed_qty if hasattr(order, 'confirmed_qty') and order.confirmed_qty is not None else 0.0)
#                 final_weight_a = float(get_attr_safe(order, "weight_shift_a", 0.0) or 0.0)
#                 final_weight_b = float(get_attr_safe(order, "weight_shift_b", 0.0) or 0.0)
#                 final_weight_c = float(get_attr_safe(order, "weight_shift_c", 0.0) or 0.0)
                
#                 if preserved_confirmed_qty_packing > 0.0:
#                     if final_confirmed_qty != preserved_confirmed_qty_packing:
#                         print(f"❌ [{po_number}] ERROR: confirmed_qty not preserved after commit! Expected {preserved_confirmed_qty_packing:.2f}, got {final_confirmed_qty:.2f}")
#                         # Force set it again
#                         set_attr_safe(order, "confirmed_qty", preserved_confirmed_qty_packing)
#                         db.add(order)
#                         db.commit()
#                         print(f"✅ [{po_number}] Fixed: confirmed_qty set to {preserved_confirmed_qty_packing:.2f}")
#                     else:
#                         print(f"✅ [{po_number}] Verified: confirmed_qty={final_confirmed_qty:.2f} correctly committed to database")
                
#                 # Verify shift weights were preserved
#                 if preserved_weight_a_packing > 0.0 or preserved_weight_b_packing > 0.0 or preserved_weight_c_packing > 0.0:
#                     if final_weight_a != preserved_weight_a_packing or final_weight_b != preserved_weight_b_packing or final_weight_c != preserved_weight_c_packing:
#                         print(f"❌ [{po_number}] ERROR: Shift weights not preserved after commit!")
#                         print(f"   Expected: A={preserved_weight_a_packing:.2f}, B={preserved_weight_b_packing:.2f}, C={preserved_weight_c_packing:.2f}")
#                         print(f"   Got: A={final_weight_a:.2f}, B={final_weight_b:.2f}, C={final_weight_c:.2f}")
#                         # Force set them again
#                         set_attr_safe(order, "weight_shift_a", preserved_weight_a_packing)
#                         set_attr_safe(order, "weight_shift_b", preserved_weight_b_packing)
#                         set_attr_safe(order, "weight_shift_c", preserved_weight_c_packing)
#                         db.add(order)
#                         db.commit()
#                         print(f"✅ [{po_number}] Fixed: Shift weights restored")
#                     else:
#                         print(f"✅ [{po_number}] Verified: Shift weights preserved correctly: A={final_weight_a:.2f}, B={final_weight_b:.2f}, C={final_weight_c:.2f}")

#                 time.sleep(0.2)

#                 print(
#                     f"✅ Initialized PACKING {po_number} "
#                     f"(scale1={order.scale1}, scale1_qty={order.scale1_qty}) "
#                     f"— starting thread..."
#                 )

#                 thread = threading.Thread(
#                     target=auto_validation_worker,
#                     args=(po_number, classification),
#                     daemon=True,
#                     name=f"Validation-{po_number}",
#                 )

#                 set_order_validation_state(po_number, {
#                     "isrunning": True,
#                     "thread": thread,
#                     "progress_pct": 0,
#                 })

#                 thread.start()
#                 started_orders.append(po_number)
#                 print(f"▶️ Started PACKING: {po_number}")

#         # =========================================================
#         # RESPONSE
#         # =========================================================
#         print(f"🔍 Start summary: {len(started_orders)} order(s) started: {started_orders}")
#         sys.stdout.flush()
#         print("=" * 80)
#         print("🚀 START AUTO-VALIDATOR ENDPOINT COMPLETED")
#         print("=" * 80)
#         sys.stdout.flush()
        
#         if started_orders:
#             return jsonify({
#                 "success": True,
#                 "orders": started_orders,
#                 "count": len(started_orders),
#             })
#         else:
#             return jsonify({
#                 "success": False,
#                 "message": "No orders to start (no eligible Pending orders or classification errors)",
#             }), 400

# @orders_bp.route("/auto-validator/status", methods=["GET"])
# def get_auto_validator_status():
#     """Get status of all validating orders and master switch status"""
    
#     # Get master switch status (read-only, don't modify it)
#     is_running = AUTO_VALIDATOR_MASTER.get("isrunning", False)
    
#     with VALIDATION_LOCK:
#         validating_orders = [
#             {
#                 "po_number": po,
#                 "progress_pct": state.get("progress_pct", 0),
#                 "status": state.get("status", "unknown"),
#                 "current_production": state.get("current_production", 0),
#                 "target": state.get("target", 0),
#                 "unit": state.get("unit", "")
#             }
#             for po, state in VALIDATION_STATES.items()
#             if state.get("isrunning")
#         ]
    
#     return jsonify({
#         "is_running": is_running,
#         "validating_orders": validating_orders,
#         "count": len(validating_orders),
#         "message": f"{len(validating_orders)} order(s) validating" if is_running else "Auto-validator is stopped"
#     })

# @orders_bp.route("/auto-validator/stop", methods=["POST"])
# def stop_auto_validator():
#     """
#     Stop the global auto-validator master switch and signal all active order validations to stop.
#     This will prevent new orders from starting and stop all currently running validations.
    
#     Also updates database:
#     - Sets order status to "Pending" for all InProgress orders
#     - Resets baseline_fixed_flags to allow fresh baselines on next start
#     - Preserves confirmed_qty (does NOT reset it)
#     """
#     global AUTO_VALIDATOR_MASTER

#     print("=" * 80)
#     print("🛑 STOP AUTO-VALIDATOR ENDPOINT CALLED")
#     print("=" * 80)
#     sys.stdout.flush()
#     print("🛑 Stopping auto-validator master switch...")
#     sys.stdout.flush()

#     # Set master switch to False
#     AUTO_VALIDATOR_MASTER["isrunning"] = False
#     print("⚡ AUTO VALIDATOR MASTER = OFF")
#     sys.stdout.flush()

#     stopped_orders: list[str] = []
#     db_updated_count = 0

#     # CRITICAL: Update database FIRST (before stopping workers) to ensure it happens
#     print("🔍 CRITICAL: Updating database FIRST before stopping workers...")
#     sys.stdout.flush()
#     print("🔍 Starting database update process...")
#     sys.stdout.flush()
#     print(f"🔍 Database engine: {postgres_engine}")
#     print(f"🔍 Database URL: {postgres_engine.url if hasattr(postgres_engine, 'url') else 'N/A'}")
#     print(f"🔍 Checking ProcessOrder model availability: {ProcessOrder is not None}")
#     print(f"🔍 ProcessOrder model: {ProcessOrder}")
#     sys.stdout.flush()

#     sql_updated_count = 0

#     # SQL used for baseline reset (shared by primary + fallback)
#     reset_baselines_sql_str = """
#         UPDATE process_orders
#         SET
#             -- MILLING: Flour/Bran output baselines
#             baseline_wg101 = 0,
#             baseline_wg201 = 0,
#             baseline_wg202 = 0,
#             baseline_wg301 = 0,
#             baseline_wg302 = 0,
#             baseline_wg501 = 0,
#             baseline_wg502 = 0,
#             baseline_wg503 = 0,
            
#             -- WATER DOSING METER baselines
#             baseline_dm101 = 0,
#             baseline_dm102 = 0,
#             baseline_dm201 = 0,
#             baseline_dm202 = 0,
#             baseline_dm203 = 0,

#             -- PACKING: Bag counter baselines
#             baseline_sl601_counter = 0,
#             baseline_sl602_counter = 0,
#             baseline_sl603_counter = 0,
#             baseline_sl606_counter = 0,
#             baseline_sl607_counter = 0
#         WHERE status = 'Pending';
#     """

#     try:
#         from sqlalchemy import text
#         print("🔍 Using PostgresSessionLocal for SQL execution...")
#         sys.stdout.flush()

#         db_session = PostgresSessionLocal()
#         print("✅ Database session created")
#         sys.stdout.flush()
#         try:
#             # 1️⃣ Check how many InProgress orders exist
#             print("🔍 Checking InProgress orders count...")
#             sys.stdout.flush()
#             check_result = db_session.execute(
#                 text("SELECT COUNT(*) FROM process_orders WHERE status = 'InProgress'")
#             )
#             inprogress_count = check_result.scalar()
#             print(f"🔍 Found {inprogress_count} InProgress order(s) in PostgreSQL process_orders table")
#             sys.stdout.flush()

#             # 2️⃣ Update all InProgress → Pending
#             if inprogress_count > 0:
#                 print("🔄 Executing UPDATE (InProgress → Pending)...")
#                 sys.stdout.flush()

#                 update_sql = text("""
#                     UPDATE process_orders 
#                     SET status = 'Pending', 
#                         baseline_fixed_flags = '{}'::jsonb,
#                         updated_at = NOW(),
#                         -- Reset ALL baseline values to 0
#                         baseline_wg101 = 0,
#                         baseline_wg201 = 0,
#                         baseline_wg202 = 0,
#                         baseline_wg301 = 0,
#                         baseline_wg302 = 0,
#                         baseline_wg501 = 0,
#                         baseline_wg502 = 0,
#                         baseline_wg503 = 0,
#                         baseline_dm101 = 0,
#                         baseline_dm102 = 0,
#                         baseline_dm201 = 0,
#                         baseline_dm202 = 0,
#                         baseline_dm203 = 0,
#                         baseline_sl601_counter = 0,
#                         baseline_sl602_counter = 0,
#                         baseline_sl603_counter = 0,
#                         baseline_sl606_counter = 0,
#                         baseline_sl607_counter = 0,
#                         -- Reset shift baseline JSON fields (CRITICAL - these are used for production calculation)
#                         baseline_shift_a_start = NULL,
#                         baseline_shift_b_start = NULL,
#                         baseline_shift_c_start = NULL
#                     WHERE status = 'InProgress'
#                 """)
#                 print(f"🔍 SQL: {update_sql}")
#                 sys.stdout.flush()

#                 update_result = db_session.execute(update_sql)
#                 try:
#                     sql_updated_count = update_result.rowcount
#                     print(f"🔍 Rowcount from result: {sql_updated_count}")
#                 except Exception as rowcount_error:
#                     print(f"⚠️ Could not get rowcount: {rowcount_error}, using inprogress_count")
#                     sql_updated_count = inprogress_count

#                 print(f"🔍 About to commit {sql_updated_count} order(s)...")
#                 sys.stdout.flush()
#                 db_session.commit()
#                 print("✅ Commit completed (InProgress → Pending)")
#                 sys.stdout.flush()
#             else:
#                 print("ℹ️ No InProgress orders found in database to update")

#             # 3️⃣ NOW reset baselines for all Pending orders (including just updated)
#             print("🔄 Resetting baselines for all Pending orders...")
#             reset_baselines_sql = text(reset_baselines_sql_str)
#             db_session.execute(reset_baselines_sql)
#             db_session.commit()
#             print("✅ BASELINES RESET after STOP")
#             sys.stdout.flush()

#             # 4️⃣ Verify there are no InProgress orders left
#             verify_result = db_session.execute(
#                 text("SELECT COUNT(*) FROM process_orders WHERE status = 'InProgress'")
#             )
#             remaining_inprogress = verify_result.scalar()
#             print(f"✅ Verification: {remaining_inprogress} InProgress order(s) remaining (should be 0)")
#             sys.stdout.flush()

#         except Exception as session_error:
#             db_session.rollback()
#             print(f"❌ Session error, rolling back: {session_error}")
#             raise session_error
#         finally:
#             db_session.close()
#             print("🔍 Database session closed")

#     except Exception as sql_error:
#         # PRIMARY SQL FAILED → use fallback raw connection
#         print(f"❌ Direct SQL UPDATE failed: {sql_error}")
#         import traceback
#         print("=" * 80)
#         print("SQL UPDATE ERROR TRACEBACK:")
#         traceback.print_exc()
#         print("=" * 80)
#         sql_updated_count = 0

#         print("🔄 FALLBACK: Trying raw connection approach...")
#         sys.stdout.flush()
#         try:
#             conn = postgres_engine.raw_connection()
#             try:
#                 cursor = conn.cursor()
#                 # 1️⃣ InProgress → Pending + Reset baselines
#                 cursor.execute("""
#                     UPDATE process_orders 
#                     SET status = 'Pending', 
#                         baseline_fixed_flags = '{}'::jsonb,
#                         updated_at = NOW(),
#                         -- Reset ALL baseline values to 0
#                         baseline_wg101 = 0,
#                         baseline_wg201 = 0,
#                         baseline_wg202 = 0,
#                         baseline_wg301 = 0,
#                         baseline_wg302 = 0,
#                         baseline_wg501 = 0,
#                         baseline_wg502 = 0,
#                         baseline_wg503 = 0,
#                         baseline_dm101 = 0,
#                         baseline_dm102 = 0,
#                         baseline_dm201 = 0,
#                         baseline_dm202 = 0,
#                         baseline_dm203 = 0,
#                         baseline_sl601_counter = 0,
#                         baseline_sl602_counter = 0,
#                         baseline_sl603_counter = 0,
#                         baseline_sl606_counter = 0,
#                         baseline_sl607_counter = 0,
#                         -- Reset shift baseline JSON fields (CRITICAL - these are used for production calculation)
#                         baseline_shift_a_start = NULL,
#                         baseline_shift_b_start = NULL,
#                         baseline_shift_c_start = NULL
#                     WHERE status = 'InProgress'
#                 """)
#                 sql_updated_count = cursor.rowcount
#                 conn.commit()
#                 print(f"✅ FALLBACK UPDATE successful: {sql_updated_count} order(s) updated using raw connection")
#                 sys.stdout.flush()

#                 # 2️⃣ Reset baselines for all Pending
#                 print("🔄 FALLBACK: Resetting baselines for all Pending orders...")
#                 cursor.execute(reset_baselines_sql_str)
#                 conn.commit()
#                 print("✅ FALLBACK: BASELINES RESET after STOP")
#                 sys.stdout.flush()

#                 cursor.close()
#             finally:
#                 conn.close()
#         except Exception as fallback_error:
#             print(f"❌ FALLBACK also failed: {fallback_error}")
#             import traceback
#             traceback.print_exc()
#             sql_updated_count = 0

#     # Set db_updated_count from SQL result
#     db_updated_count = sql_updated_count
#     print(f"🔍 Database update completed. Updated {db_updated_count} order(s). Now stopping workers...")
#     sys.stdout.flush()

#     # Stop all validation workers (after DB update)
#     print("🔍 Stopping validation workers...")
#     sys.stdout.flush()
#     with VALIDATION_LOCK:
#         active_orders = list(VALIDATION_STATES.keys())
#         print(f"🔍 Found {len(active_orders)} active orders in VALIDATION_STATES")
#         sys.stdout.flush()
#         for po_number in active_orders:
#             if po_number in VALIDATION_STATES:
#                 del VALIDATION_STATES[po_number]
#                 print(f"🛑 Cleared validation state for order: {po_number}")
#             stopped_orders.append(po_number)
#             sys.stdout.flush()

#     print(f"✅ Workers stopped: {len(stopped_orders)} worker(s), validation states cleared")
#     sys.stdout.flush()

#     # ORM fallback: keep as-is (only status + baseline_fixed_flags)
#     try:
#         if ProcessOrder is not None:
#             print("✅ ProcessOrder model is available, proceeding with ORM database update")
#             print("🔍 Opening database session...")
#             with _db_session() as db:
#                 try:
#                     test_count = db.query(ProcessOrder).count()
#                     print(f"🔍 Database connection test: Found {test_count} total orders in PostgreSQL")
#                 except Exception as test_error:
#                     print(f"❌ Database connection test failed: {test_error}")
#                     raise test_error

#                 print("🔍 Querying InProgress orders from database...")
#                 inprogress_orders = db.query(ProcessOrder).filter(
#                     ProcessOrder.status == "InProgress"
#                 ).all()

#                 if len(inprogress_orders) == 0:
#                     print("⚠️ No orders found with exact 'InProgress' status, checking case variations...")
#                     all_orders = db.query(ProcessOrder).all()
#                     inprogress_variants = [
#                         o for o in all_orders if o.status and "progress" in o.status.lower()
#                     ]
#                     print(f"🔍 Found {len(inprogress_variants)} order(s) with 'progress' in status: {[o.status for o in inprogress_variants[:5]]}")
#                     if inprogress_variants:
#                         inprogress_orders = inprogress_variants

#                 print(f"🔍 Found {len(inprogress_orders)} InProgress order(s) in database to update")

#                 if len(inprogress_orders) == 0 and stopped_orders:
#                     print("⚠️ No InProgress orders found by status, trying to update by order_id from stopped workers...")
#                     for po_number in stopped_orders:
#                         order = db.query(ProcessOrder).filter(
#                             ProcessOrder.order_id == po_number
#                         ).first()
#                         # ✅ CRITICAL: Only update InProgress orders, NOT Validated orders
#                         # Validated orders are already completed and should not be changed to Pending
#                         if order and order.status == "InProgress":
#                             inprogress_orders.append(order)
#                             print(f"🔍 Found order {po_number} with status '{order.status}' to update")
#                         elif order and order.status == "Validated":
#                             print(f"⏭️ Skipping Validated order {po_number} - already completed, not changing to Pending")

#                 if len(inprogress_orders) == 0:
#                     print("⚠️ No orders to update - all orders may already be Pending or no InProgress orders exist")
#                 else:
#                     for order in inprogress_orders:
#                         old_status = order.status
#                         order_id = order.order_id
                        
#                         # ✅ CRITICAL: Skip Validated orders - they are already completed
#                         # Only update InProgress orders to Pending
#                         if old_status == "Validated":
#                             print(f"⏭️ Skipping Validated order {order_id} - already completed, not changing to Pending")
#                             continue

#                         order.status = "Pending"

#                         # Reset baseline_fixed_flags
#                         if order.baseline_fixed_flags:
#                             baseline_fixed_flags = order.baseline_fixed_flags.copy() if isinstance(order.baseline_fixed_flags, dict) else {}
#                             for key in list(baseline_fixed_flags.keys()):
#                                 baseline_fixed_flags[key] = False
#                             order.baseline_fixed_flags = baseline_fixed_flags
#                         else:
#                             order.baseline_fixed_flags = {}

#                         # ✅ CRITICAL: Reset ALL baseline values to 0
#                         # PACKING: Bag counter baselines
#                         order.baseline_sl601_counter = 0.0
#                         order.baseline_sl602_counter = 0.0
#                         order.baseline_sl603_counter = 0.0
#                         order.baseline_sl606_counter = 0.0
#                         order.baseline_sl607_counter = 0.0
                        
#                         # MILLING: Flour/Bran output baselines
#                         order.baseline_wg101 = 0.0
#                         order.baseline_wg201 = 0.0
#                         order.baseline_wg202 = 0.0
#                         order.baseline_wg301 = 0.0
#                         order.baseline_wg302 = 0.0
#                         order.baseline_wg501 = 0.0
#                         order.baseline_wg502 = 0.0
#                         order.baseline_wg503 = 0.0
                        
#                         # WATER DOSING METER baselines
#                         order.baseline_dm101 = 0.0
#                         order.baseline_dm102 = 0.0
#                         order.baseline_dm201 = 0.0
#                         order.baseline_dm202 = 0.0
#                         order.baseline_dm203 = 0.0
                        
#                         # ✅ CRITICAL: Reset shift baseline JSON fields (these are used for production calculation)
#                         order.baseline_shift_a_start = None
#                         order.baseline_shift_b_start = None
#                         order.baseline_shift_c_start = None

#                         order.updated_at = datetime.now()
#                         db.add(order)
#                         db_updated_count += 1
#                         print(f"🛑 DB updating: Order {order_id} (ID: {order.id}) status '{old_status}' → 'Pending', baseline flags, baseline values, and shift baselines reset")

#                 if db_updated_count > 0:
#                     try:
#                         db.flush()
#                         print(f"✅ Database flush successful: {db_updated_count} order(s) flushed")
#                     except Exception as flush_error:
#                         print(f"❌ Database flush failed: {flush_error}")
#                         import traceback
#                         traceback.print_exc()
#                         db.rollback()
#                         raise flush_error

#                     try:
#                         db.commit()
#                         print(f"✅ Database commit successful: {db_updated_count} order(s) committed to Pending status")
#                         order_ids_list = [o.order_id for o in inprogress_orders]
#                         if order_ids_list:
#                             verify_orders = db.query(ProcessOrder).filter(
#                                 ProcessOrder.status == "Pending",
#                                 ProcessOrder.order_id.in_(order_ids_list)
#                             ).count()
#                             print(f"✅ Verification: {verify_orders} of {db_updated_count} order(s) confirmed as Pending in database")
#                         else:
#                             print("⚠️ No order IDs to verify")
#                     except Exception as commit_error:
#                         print(f"❌ Database commit failed: {commit_error}")
#                         import traceback
#                         traceback.print_exc()
#                         db.rollback()
#                         raise commit_error
#                 else:
#                     print(f"⚠️ ORM update found 0 orders to update (SQL already updated {db_updated_count} orders)")
#         else:
#             print("❌ ProcessOrder model not available - ORM update skipped")
#             print(f"ℹ️ SQL update already attempted: {db_updated_count} order(s) updated")
#     except Exception as e:
#         print(f"❌ CRITICAL ERROR updating database during stop: {e}")
#         import traceback
#         print("=" * 80)
#         print("FULL TRACEBACK:")
#         traceback.print_exc()
#         print("=" * 80)
#         return jsonify({
#             "success": True,
#             "message": f"Auto-validator stopped (workers stopped, but DB update had errors: {str(e)})",
#             "stopped_orders": stopped_orders,
#             "stopped_count": len(stopped_orders),
#             "db_updated_count": db_updated_count,
#             "warning": f"Database update failed: {str(e)}"
#         })

#     print(f"🔍 Database update process completed. Updated {db_updated_count} order(s)")
#     print(f"✅ Auto-validator stopped completely. Stopped {len(stopped_orders)} worker(s), updated {db_updated_count} order(s) in DB")
#     print("=" * 80)
#     print("🛑 STOP AUTO-VALIDATOR ENDPOINT COMPLETED")
#     print("=" * 80)

#     response_data = {
#         "success": True,
#         "message": f"Auto-validator stopped successfully. Updated {db_updated_count} order(s) to Pending.",
#         "stopped_orders": stopped_orders,
#         "stopped_count": len(stopped_orders),
#         "db_updated_count": db_updated_count
#     }

#     print(f"🔍 Returning response: {response_data}")
#     return jsonify(response_data)


# @orders_bp.route("/priority", methods=["GET", "POST"])
# def priority_endpoint():
#     if ProcessOrder is None:
#         return jsonify({"error": "ProcessOrder model not available"}), 500
#     if request.method == "GET":
#         try:
#             with _db_session() as db:
#                 orders = db.query(ProcessOrder).all()
#                 priorities = {order.id: get_attr_safe(order, "priority", 0) for order in orders}
#             return jsonify(priorities)
#         except Exception as e:
#             print(f"❌ Error fetching priorities: {e}")
#             return jsonify({"error": str(e)}), 500
#     else:
#         try:
#             data = request.get_json()
#             if not data or not isinstance(data, dict):
#                 return jsonify({"error": "Invalid request body. Expected JSON mapping of order IDs to priorities."}), 400
#             with _db_session() as db:
#                 updated_count = 0
#                 errors = []
#                 for order_id_str, priority in data.items():
#                     try:
#                         order_id = int(order_id_str)
#                         priority = int(priority)
#                         order = db.query(ProcessOrder).filter(ProcessOrder.id == order_id).first()
#                         if order:
#                             set_attr_safe(order, "priority", priority)
#                             updated_count += 1
#                         else:
#                             errors.append(f"Order ID {order_id} not found")
#                     except Exception as e:
#                         errors.append(f"Invalid input for {order_id_str}: {e}")
#                 db.commit()
#             return jsonify({"success": True, "updated_count": updated_count, "errors": errors if errors else None, "message": f"Updated priorities for {updated_count} order(s)"})
#         except Exception as e:
#             print(f"❌ Error updating priorities: {e}")
#             import traceback
#             traceback.print_exc()
#             return jsonify({"error": f"Failed to update priorities: {str(e)}"}), 500

# @orders_bp.route("/palletizer-mapping", methods=["GET", "POST", "OPTIONS"])
# def palletizer_mapping():
#     from models.palletizer_mapping import PalletizerMapping

#     # Handle CORS preflight
#     if request.method == "OPTIONS":
#         response = jsonify({})
#         response.headers.add("Access-Control-Allow-Origin", "*")
#         response.headers.add("Access-Control-Allow-Headers", "Content-Type")
#         response.headers.add("Access-Control-Allow-Methods", "GET, POST, OPTIONS")
#         return response

#     if request.method == "GET":
#         # GET: Fetch all palletizer mappings
#         with _db_session() as db:
#             mappings = db.query(PalletizerMapping).order_by(PalletizerMapping.version.asc()).all()
#             result = []
#             for mapping in mappings:
#                 result.append({
#                     "id": mapping.id,
#                     "version": mapping.version,
#                     "palletizer": mapping.palletizer,
#                     "bag_size_kg": float(mapping.bag_size_kg) if mapping.bag_size_kg else 0.0,
#                     "bags_per_pallet": int(mapping.bags_per_pallet) if mapping.bags_per_pallet else 0,
#                     "kg_per_pallet": float(mapping.kg_per_pallet) if mapping.kg_per_pallet else 0.0,
#                 })
#             return jsonify(result)
    
#     # POST: Create or update palletizer mapping
#     data = request.json or {}
#     version = data.get("version", "").strip().upper()
#     palletizer = data.get("palletizer")
#     bag_size = data.get("bag_size_kg")
#     bags_per_pallet = data.get("bags_per_pallet")
#     kg_per_pallet = data.get("kg_per_pallet")

#     if not version or not palletizer:
#         return jsonify({"success": False, "message": "Version and palletizer required"}), 400
    
#     with _db_session() as db:
#         existing = db.query(PalletizerMapping).filter(
#             PalletizerMapping.version == version
#         ).first()

#         if existing:
#             # UPDATE mapping
#             existing.palletizer = palletizer
#             existing.bag_size_kg = bag_size
#             existing.bags_per_pallet = bags_per_pallet
#             existing.kg_per_pallet = kg_per_pallet
#             db.commit()
#             return jsonify({"success": True, "message": "Mapping updated", "mode": "update"})

#         # INSERT new row
#         new_row = PalletizerMapping(
#             version=version,
#             palletizer=palletizer,
#             bag_size_kg=bag_size,
#             bags_per_pallet=bags_per_pallet,
#             kg_per_pallet=kg_per_pallet
#         )
#         db.add(new_row)
#         db.commit()

#         return jsonify({"success": True, "message": "Mapping created", "mode": "create"})


from __future__ import annotations
from typing import Dict, Any, List, Optional, Mapping
from datetime import datetime
import threading
import time
import re
import ast
import sys

from flask import Blueprint, request, jsonify
from werkzeug.exceptions import BadRequest, NotFound
from sqlalchemy.orm import sessionmaker
import threading

# Services
from services.scale_service import (
    get_multiple_scada_readings,   # noqa: F401
    capture_baseline_readings,
    calculate_deltas,
    MILLING_FIELDS,  # ✅ ADD THIS
    INPUT_FIELDS,     # ✅ ADD THIS
)
from services.sap_confirmation import SAPConfirmationService
from services.error_logger import log_order_error
from services.auth_service import optional_auth
from services.system_logger import system_logger
from services.scale_lock_service import (
    lock_scales,
    release_scales,
    is_scale_available,
    check_and_promote_waiting_orders,
    add_to_queue,
    remove_from_queue,
    get_scale_owner,
    get_scale_usage_status,
    get_lock_status_for_order,
    check_scale_conflicts_for_order,
    register_order_version,
    unregister_order_version,
    get_orders_with_same_version,
    get_orders_using_scale,
    set_order_running,
)

# Database
from database import postgres_engine
from utils.shifts import get_current_shift, get_next_shift, is_shift_ended
from utils.vpn_check import check_vpn_connection
from models.shift_master import ShiftMaster
from models.offline_confirmation import OfflineConfirmation

try:
    from models.process_order_pg import ProcessOrderPG as ProcessOrder
    print("✅ ProcessOrder model imported successfully")
except Exception as e:
    print(f"❌ Failed to import ProcessOrder model: {e}")
    ProcessOrder = None


PostgresSessionLocal = sessionmaker(
    bind=postgres_engine, autoflush=False, autocommit=False, future=True
)


def _db_session():
    return PostgresSessionLocal()


def _mapping_db_session():
    """Return a session bound to the PostgreSQL DB for milling mappings."""
    return PostgresSessionLocal()


orders_bp = Blueprint("orders", __name__, url_prefix="/api/orders")

# Module-level dictionary to track last calculated production from baseline for each shift
# Key: (po_number, shift_code) -> last_total_production_from_baseline
_last_shift_production_cache = {}

# ✅ CRITICAL: Track maximum weight seen for each shift to prevent reverts
# Key: (po_number, shift_code) -> maximum_weight_seen
_max_shift_weight_cache = {}

# ✅ CRITICAL: Track last delta value for PACKING orders to prevent confirmed_qty accumulation
# Key: po_number -> last_delta_value
# This ensures we only add delta increases, not recalculate from preserved each cycle
_last_delta_cache_packing = {}

# ✅ CRITICAL: Track last total shift weights sum for MILLING orders to prevent confirmed_qty accumulation
# Key: po_number -> last_total_shift_weights_sum
# This ensures we only add increases, not recalculate from preserved each cycle
_last_total_cache_milling = {}

# =============================================================================
# SPEC-CONFORMANT CLASSIFICATION MAPPINGS
# =============================================================================

PL_TO_SCADA = {
    "PL601": "PL601_TOT",
    "PL602": "PL602_TOT",
    "PL603": "PL603_TOT",
    "PL606": "SL606_TOT",
    "PL607": "SL607_TOT",
}

def _is_pl_palletizer(tag: str) -> bool:
    """
    Check if a SCADA tag is a PL palletizer (needs conversion) or SL (direct bags).
    PL palletizers: PL601_TOT, PL602_TOT, PL603_TOT → convert pallets to bags
    SL equipment: SL606_TOT, SL607_TOT → already in bags, no conversion
    """
    tag_upper = str(tag or "").upper()
    # PL palletizers need conversion
    return tag_upper in ["PL601_TOT", "PL602_TOT", "PL603_TOT"]

def _get_bags_per_pallet_from_palletizer_type(tag: str) -> float:
    """
    Get bags per pallet based on palletizer type (PL601, PL602, etc.)
    This is used as a fallback when version-specific lookup fails or gives incorrect values.
    """
    tag_upper = str(tag or "").upper()
    
    # Map palletizer types to standard bags per pallet
    # PL601 and PL602 typically use 32 bags per pallet
    if "PL601" in tag_upper:
        return 32.0
    elif "PL602" in tag_upper:
        return 32.0
    elif "PL603" in tag_upper:
        # PL603 might be different, check database first, but default to 32
        return 32.0
    else:
        return 1.0  # Unknown palletizer, no conversion

def _convert_packing_delta_to_bags(tag: str, delta: float, packing_info: Dict) -> float:
    """
    Convert PACKING delta to bags.
    - PL palletizers (PL601_TOT, PL602_TOT, PL603_TOT): convert pallets to bags
    - SL equipment (SL606_TOT, SL607_TOT): also convert using bag_size_kg from version mapping
    
    For packing orders: SCADA sends pallet/count, multiply by bag_size_kg from version mapping.
    Example: 1 pallet × bag_size_kg (32) = 32 bags
    """
    tag_upper = str(tag or "").upper()
    
    # ✅ FIX: Both PL and SL equipment should use bag_size_kg from version mapping
    # Get from packing_info (which comes from palletizer_mapping table)
    bags_per_pallet = float(packing_info.get("bags_per_pallet", 0) or 0)
    bag_size_kg = float(packing_info.get("bag_size_kg", 0) or 0)
    
    # ✅ FIX: ALWAYS use bag_size_kg for conversion (priority 1) for both PL and SL
    # bag_size_kg represents the number of bags per pallet for this version
    if bag_size_kg > 1:
        # Use bag_size_kg as the multiplier (pallets × bag_size_kg = bags)
        conversion_factor = bag_size_kg
        print(f"🔍 [{tag_upper}] Using bag_size_kg ({bag_size_kg}) as multiplier from version mapping")
    elif bags_per_pallet > 1:
        # Fallback to bags_per_pallet if bag_size_kg is invalid
        conversion_factor = bags_per_pallet
        print(f"⚠️ [{tag_upper}] bag_size_kg invalid, using bags_per_pallet ({bags_per_pallet}) from database")
    else:
        # Final fallback: for PL palletizers, use palletizer standard; for SL, use 1 (no conversion)
        if _is_pl_palletizer(tag_upper):
            conversion_factor = _get_bags_per_pallet_from_palletizer_type(tag_upper)
            print(f"⚠️ [{tag_upper}] Both bag_size_kg and bags_per_pallet invalid, using palletizer standard ({conversion_factor})")
        else:
            # SL equipment fallback: if no bag_size_kg, return as-is (assume already in bags)
            conversion_factor = 1.0
            print(f"⚠️ [{tag_upper}] No bag_size_kg found, returning delta as-is (assumed already in bags)")
    
    result = delta * conversion_factor
    print(f"🔍 [{tag_upper}] Conversion: delta={delta} × {conversion_factor} = {result} bags")
    return result

# =============================================================================
# MILLING PV SPECS - Version-specific formulas and equipment
# =============================================================================
# Based on "Confirmed Weight Scale" column from material version mapping table
# MILLING PV SPECS - corrected from spreadsheet
# =============================================================================
# ⚠️ DEPRECATED: HARDCODED MILLING MAPPINGS
# =============================================================================
# These dictionaries are NO LONGER USED - all milling mappings are now stored
# in the database table `milling_version_mappings` and accessed via the
# MillingVersionMapping model.
#
# To add/update milling mappings, use the API endpoint:
# POST /api/milling-mapping
#
# These are kept here temporarily for reference/migration purposes only.
# =============================================================================

# DEPRECATED: Use milling_version_mappings table instead
# MILLING_PV_SPECS = {
#     "LWSM": {"scales": ["WG101", "WG302", "DM101", "DM102"], "formula": "(WG101-WG302)+(DM101+DM102)"},
#     "IWSM": {"scales": ["WG101", "WG302"], "formula": "(WG101-WG302)"},
#     "SWSM": {"scales": ["WG101", "WG302"], "formula": "(WG101-WG302)"},
#     "CWIM": {"scales": ["WG201", "WG301", "DM201", "DM202", "DM203"], "formula": "(WG201-WG301)+(DM201+DM202+DM203)"},
#     "CWLM": {"scales": ["WG201", "WG301", "DM201", "DM202", "DM203"], "formula": "(WG201-WG301)+(DM201+DM202+DM203)"},
#     "CWMM": {"scales": ["WG201", "WG301", "DM201", "DM202", "DM203"], "formula": "(WG201-WG301)+(DM201+DM202+DM203)"},
#     "CWSM": {"scales": ["WG201", "WG301", "DM201", "DM202", "DM203"], "formula": "(WG201-WG301)+(DM201+DM202+DM203)"},
#     "BKF1": {"scales": ["WG501"], "formula": "WG501"},
#     "CKF1": {"scales": ["WG502"], "formula": "WG502"},
#     "IWF1": {"scales": ["WG502"], "formula": "WG502"},
#     "IWF2": {"scales": ["WG502"], "formula": "WG502"},
#     "BRF1": {"scales": ["WG501"], "formula": "WG501"},
#     "BRF2": {"scales": ["WG502"], "formula": "WG502"},
#     "BRF3": {"scales": ["WG501"], "formula": "WG501"},
#     "MMCF": {"scales": ["WG502"], "formula": "WG502"},
# }

# DEPRECATED: Use milling_version_mappings table instead
# MILLING_PV_MAPPING_SPEC = {v: spec["scales"] for v, spec in MILLING_PV_SPECS.items()}

# DEPRECATED: No longer used - overrides should be managed via DB
# AUTH_MILLING_PV_OVERRIDES: Dict[str, List[str]] = {}

# DEPRECATED: Use milling_version_mappings table (scale1, scale2, scale3 columns) instead
# MILLING_BYPRODUCT_MAPPING = {
#     "LWSM": {"scale1": "WG302", "scale2": None, "scale3": None},
#     "IWSM": {"scale1": "WG302", "scale2": None, "scale3": None},
#     "SWSM": {"scale1": "WG302", "scale2": None, "scale3": None},
#     "CWIM": {"scale1": "WG301", "scale2": None, "scale3": None},
#     "CWLM": {"scale1": "WG301", "scale2": None, "scale3": None},
#     "CWMM": {"scale1": "WG301", "scale2": None, "scale3": None},
#     "CWSM": {"scale1": "WG301", "scale2": None, "scale3": None},
#     "BKF1": {"scale1": "WG503", "scale2": None, "scale3": None},
#     "CKF1": {"scale1": "WG501", "scale2": "WG503", "scale3": None},
#     "IWF1": {"scale1": "WG501", "scale2": "WG503", "scale3": None},
#     "IWF2": {"scale1": "WG501", "scale2": "WG503", "scale3": None},
#     "BRF1": {"scale1": "WG503", "scale2": None, "scale3": None},
#     "BRF2": {"scale1": "WG501", "scale2": "WG503", "scale3": None},
#     "BRF3": {"scale1": "WG501", "scale2": "WG503", "scale3": None},
#     "MMCF": {"scale1": "WG501", "scale2": "WG503", "scale3": None},
# }

# =============================================================================
# GLOBALS & CONSTANTS
# =============================================================================

import threading

# NEW: Track multiple orders in parallel
VALIDATION_STATES = {}  # Key: ponumber, Value: {isrunning, thread, progresspct, status}
VALIDATION_LOCK = threading.Lock()

# Global master switch for auto-validator
AUTO_VALIDATOR_MASTER = {"isrunning": False}


def is_auto_validator_enabled() -> bool:
    """Return True if master auto-validator is ON."""
    return AUTO_VALIDATOR_MASTER.get("isrunning", False)

# Helper functions to safely access multi-order state
def get_order_validation_state(ponumber: str):
    """Get validation state for a specific order"""
    with VALIDATION_LOCK:
        return VALIDATION_STATES.get(ponumber, {
            "isrunning": False,
            "thread": None,
            "progresspct": 0,
            "status": "idle"
        })

def set_order_validation_state(ponumber: str, state: dict):
    """Set validation state for a specific order"""
    with VALIDATION_LOCK:
        if ponumber not in VALIDATION_STATES:
            VALIDATION_STATES[ponumber] = {}
        VALIDATION_STATES[ponumber].update(state)

def remove_order_validation_state(ponumber: str):
    """Remove validation state when order completes"""
    with VALIDATION_LOCK:
        VALIDATION_STATES.pop(ponumber, None)

def is_order_validating(ponumber: str) -> bool:
    """Check if specific order is currently validating"""
    state = get_order_validation_state(ponumber)
    return state.get("isrunning", False)

TOLERANCE_PCT = 0.0
WORKER_SLEEP_SECONDS = 60


# =============================================================================
# SAFE ATTRIBUTE ACCESS
# =============================================================================

def get_attr_safe(obj, attr: str, default=None):
    try:
        return getattr(obj, attr, default)
    except Exception:
        return default


def set_attr_safe(obj, attr: str, value):
    try:
        setattr(obj, attr, value)
    except Exception:
        pass


def update_last_confirmed_qty(order) -> None:
    """
    Update last_confirmed_qty column with the sum of confirmed_shift_a, confirmed_shift_b, confirmed_shift_c.
    This represents what has been confirmed to SAP.
    """
    confirmed_shift_a = float(get_attr_safe(order, "confirmed_shift_a", 0.0) or 0.0)
    confirmed_shift_b = float(get_attr_safe(order, "confirmed_shift_b", 0.0) or 0.0)
    confirmed_shift_c = float(get_attr_safe(order, "confirmed_shift_c", 0.0) or 0.0)
    
    total_confirmed = confirmed_shift_a + confirmed_shift_b + confirmed_shift_c
    set_attr_safe(order, "last_confirmed_qty", total_confirmed)
    
    print(f"📊 Updated last_confirmed_qty: {total_confirmed:.2f} (A={confirmed_shift_a:.2f}, B={confirmed_shift_b:.2f}, C={confirmed_shift_c:.2f})")


# =============================================================================
# HELPERS
# =============================================================================

def _translate_pl_to_scada(pl_list: List[str]) -> List[str]:
    return [PL_TO_SCADA[p] for p in pl_list if p in PL_TO_SCADA]


def _resolve_milling_streams(version: str) -> Optional[List[str]]:
    """
    DEPRECATED: Returns scales list from DB-based milling_version_mappings.
    For backward compatibility only - prefer using classify_order() instead.
    """
    from models.milling_version_mapping import MillingVersionMapping
    
    v = (version or "").upper().strip()
    
    try:
        with _mapping_db_session() as db:
            mapping = (
                db.query(MillingVersionMapping)
                  .filter(MillingVersionMapping.version == v)
                  .first()
            )
    except Exception:
        return None
    
    if mapping:
        return mapping.scales or []
    
    return None


def _resolve_milling_streams_and_formula(version: str) -> Optional[Dict[str, Any]]:
    """
    DEPRECATED: Return confirmed-weight scales + formula for a milling PV from DB.
    For backward compatibility only - prefer using classify_order() instead.
    """
    from models.milling_version_mapping import MillingVersionMapping
    
    v = (version or "").upper().strip()
    
    try:
        with _mapping_db_session() as db:
            mapping = (
                db.query(MillingVersionMapping)
                  .filter(MillingVersionMapping.version == v)
                  .first()
            )
    except Exception:
        return None
    
    if not mapping:
        return None
    
    # always return a fresh list
    return {
        "scales": list(mapping.scales or []),
        "formula": mapping.formula or "",
    }


def _capture_byproduct_baselines(version: str, baselines: Dict[str, float], order=None) -> Dict[str, float]:
    """
    Capture baseline SCADA readings for all byproduct scales for a given version.
    ALWAYS stores SCADA value for byproduct scales, even if it's 0 or already in baselines.
    This ensures byproduct scale quantities are correctly stored.
    
    Args:
        version: Order version (e.g., "LWSM", "CKF1")
        baselines: Existing baselines dict (will be updated with byproduct scales)
        order: Optional ProcessOrder object to reset baseline_fixed_flags for byproduct scales
    
    Returns:
        Updated baselines dict with byproduct scales included
    """
    from services.scale_service import get_scada_reading
    from models.milling_version_mapping import MillingVersionMapping
    
    version_upper = (version or "").upper().strip()
    
    if not version_upper:
        print(f"⚠️ [byproduct_baselines] Version is empty, skipping byproduct baseline capture")
        return baselines
    
    # Get byproduct scales from DB
    try:
        with _mapping_db_session() as db:
            mapping = (
                db.query(MillingVersionMapping)
                  .filter(MillingVersionMapping.version == version_upper)
                  .first()
            )
    except Exception as e:
        print(f"⚠️ [byproduct_baselines] Error querying byproduct mapping for '{version_upper}': {e}")
        return baselines
    
    if not mapping:
        print(f"⚠️ [byproduct_baselines] No mapping found for version '{version_upper}', skipping byproduct baselines")
        return baselines
    
    # Build byproduct scales dict from DB mapping
    byp_scales = {
        "scale1": mapping.scale1,
        "scale2": mapping.scale2,
        "scale3": mapping.scale3
    }
    
    # ✅ FIX: Capture baseline for each byproduct scale (scale1, scale2, scale3)
    # ALWAYS capture, even if tag is already in baselines (may be both main and byproduct scale)
    for scale_key in ["scale1", "scale2", "scale3"]:
        tag = byp_scales.get(scale_key)
        if tag:
            # ✅ ALWAYS get fresh SCADA reading for byproduct scale
            scada_val = get_scada_reading(tag)
            
            # ✅ FIX: ALWAYS store SCADA value, even if it's 0 (0 is a valid baseline)
            if scada_val is None:
                scada_val = 0.0
            
            # ✅ FIX: Override existing baseline if this is a byproduct scale
            # (Even if tag is also in main equipment list, byproduct baseline takes precedence)
            baselines[tag] = float(scada_val)
            print(f"📌 Byproduct baseline saved: {tag} = {scada_val:.2f} (overriding any existing baseline)")
            
            # ✅ FIX: Reset baseline_fixed_flags for byproduct scales to allow fresh capture
            if order:
                baseline_fixed_flags = get_attr_safe(order, "baseline_fixed_flags", {}) or {}
                if not isinstance(baseline_fixed_flags, dict):
                    baseline_fixed_flags = {}
                tag_key = tag.lower()
                # Reset flag so byproduct baseline can be stored fresh
                baseline_fixed_flags[tag_key] = False
                set_attr_safe(order, "baseline_fixed_flags", baseline_fixed_flags)
    
    return baselines


def _set_byproduct_scales(order, version: str, baselines: Dict[str, float]) -> None:
    """
    Set byproduct scales (scale1, scale2) and initialize their quantities to 0
    when order validation starts. Baselines are captured separately for delta calculations.
    Only applies to MILLING orders.
    
    Note: scale3 was removed from milling_version_mappings in Jan 2026.
    
    Args:
        order: ProcessOrder object
        version: Order version (e.g., "LWSM", "CKF1")
        baselines: Dictionary of baseline readings from SCADA (tag -> value)
                   Should include both main equipment and byproduct scales
    """
    from models.milling_version_mapping import MillingVersionMapping
    
    version_upper = (version or "").upper().strip()
    
    if not version_upper:
        print(f"⚠️ [set_byproduct_scales] Version is empty, clearing byproduct scales")
        # Clear scales if version is empty
        set_attr_safe(order, "scale1", None)
        set_attr_safe(order, "scale1_qty", 0.0)
        set_attr_safe(order, "scale2", None)
        set_attr_safe(order, "scale2_qty", 0.0)
        set_attr_safe(order, "scale3", None)
        set_attr_safe(order, "scale3_qty", 0.0)
        return
    
    # Get byproduct scales from DB (MSSQL - same as API routes)
    try:
        with _mapping_db_session() as db:
            mapping = (
                db.query(MillingVersionMapping)
                  .filter(MillingVersionMapping.version == version_upper)
                  .first()
            )
    except Exception as e:
        print(f"⚠️ [set_byproduct_scales] Error querying byproduct mapping for '{version_upper}': {e}")
        # Clear scales if error
        set_attr_safe(order, "scale1", None)
        set_attr_safe(order, "scale1_qty", 0.0)
        set_attr_safe(order, "scale2", None)
        set_attr_safe(order, "scale2_qty", 0.0)
        set_attr_safe(order, "scale3", None)
        set_attr_safe(order, "scale3_qty", 0.0)
        return
    
    if not mapping:
        print(f"⚠️ [set_byproduct_scales] No byproduct scales defined for version '{version_upper}'")
        # Clear scales if no mapping exists
        set_attr_safe(order, "scale1", None)
        set_attr_safe(order, "scale1_qty", 0.0)
        set_attr_safe(order, "scale2", None)
        set_attr_safe(order, "scale2_qty", 0.0)
        set_attr_safe(order, "scale3", None)
        set_attr_safe(order, "scale3_qty", 0.0)
        return
    
    scale1_tag = mapping.scale1
    scale2_tag = mapping.scale2
    scale3_tag = mapping.scale3
    
    # Assign scale names to order
    set_attr_safe(order, "scale1", scale1_tag)
    set_attr_safe(order, "scale2", scale2_tag)
    set_attr_safe(order, "scale3", scale3_tag)
    
    # ✅ Get baseline readings from baselines dict (now includes byproduct scales)
    scale1_baseline = float(baselines.get(scale1_tag, 0.0) or 0.0) if scale1_tag else 0.0
    scale2_baseline = float(baselines.get(scale2_tag, 0.0) or 0.0) if scale2_tag else 0.0
    scale3_baseline = float(baselines.get(scale3_tag, 0.0) or 0.0) if scale3_tag else 0.0
    
    # ✅ FIX: Initialize byproduct quantities to 0 at order start
    # Quantities accumulate during production, baselines are for delta calculation only
    print(f"🔧🔧🔧 [SET-BYPRODUCT-SCALES-RESET] Resetting scale_qty values to 0 for order - THIS SHOULD ONLY HAPPEN ON BRAND NEW ORDERS!")
    set_attr_safe(order, "scale1_qty", 0.0)
    set_attr_safe(order, "scale2_qty", 0.0)
    set_attr_safe(order, "scale3_qty", 0.0)
    
    print(f"✅ [set_byproduct_scales] Byproduct scales set for {version_upper}: "
          f"scale1={scale1_tag} (baseline={scale1_baseline:.2f}, qty=0.00), "
          f"scale2={scale2_tag} (baseline={scale2_baseline:.2f}, qty=0.00), "
          f"scale3={scale3_tag} (baseline={scale3_baseline:.2f}, qty=0.00)")


# =============================================================================
# SAFE FORMULA EVALUATOR
# =============================================================================

# Python 3.8+ uses ast.Constant instead of ast.Num
ALLOWED_AST_NODES = (
    ast.Expression, ast.BinOp, ast.UnaryOp, ast.Constant,
    ast.Add, ast.Sub, ast.Mult, ast.Div, ast.Pow,
    ast.USub, ast.UAdd, ast.Load, ast.Call, ast.Mod, ast.FloorDiv,
    ast.Tuple, ast.List, ast.Subscript, ast.Index
)
# Python < 3.8 compatibility (ast.Num was deprecated)
try:
    ALLOWED_AST_NODES = ALLOWED_AST_NODES + (ast.Num,)
except AttributeError:
    pass  # ast.Num doesn't exist in Python 3.8+


def _is_safe_ast(node: ast.AST) -> bool:
    """Return True if node and all subnodes are permitted (no names, no attributes)."""
    for n in ast.walk(node):
        # Allow numeric constants (ast.Constant) and arithmetic operators
        if not isinstance(n, ALLOWED_AST_NODES):
            return False
    return True


def evaluate_formula_using_deltas(formula: str, deltas: Mapping[str, float]) -> float:
    """
    Safely evaluate a formula string where tokens like 'WG201' are replaced by numeric delta values.
    Allowed operators: + - * / and parentheses.
    
    Args:
        formula: Formula string like "(WG201-WG301)+(DM201+DM202+DM203)"
        deltas: Mapping of tag names to delta values, e.g., {"WG201": 40.0, "WG301": 5.0, ...}
    
    Returns:
        Evaluated result as float (0.0 if evaluation fails)
    """
    if not formula:
        return 0.0

    # Replace tags (WG201, DM201, etc.) with numeric literals.
    # Use word boundary to avoid partial replacements.
    expr = formula.strip()

    # Replace each tag token by a numeric literal from deltas (use 0.0 default)
    # Example: "(WG201-WG301)+(DM201+DM202+DM203)" => "(40.0-5.0)+(0.0+0.0+0.0)"
    def _tag_repl(match):
        tag = match.group(0)
        val = float(deltas.get(tag, 0.0) or 0.0)
        # Use repr to keep numeric formatting safe
        return repr(val)

    # Match tokens consisting of letters+digits like WG201, DM202, etc.
    expr = re.sub(r'\b[A-Za-z]{1,5}\d{1,4}\b', _tag_repl, expr)

    # Now validate expression only contains digits, ., whitespace, arithmetic symbols and parentheses
    if re.search(r'[A-Za-z_]', expr):
        # if any alpha remains, it's unsafe
        print(f"⚠️ Unsafe tokens in formula after substitution: {formula} -> {expr}")
        return 0.0

    # Parse to AST and ensure it's safe (only arithmetic)
    try:
        node = ast.parse(expr, mode='eval')
        if not _is_safe_ast(node):
            print(f"⚠️ Unsafe expression in formula: {formula}")
            return 0.0
        result = eval(compile(node, "<formula>", mode="eval"), {"__builtins__": {}})
        return float(result)
    except Exception as e:
        # fallback - log and return 0.0 to avoid crashing production
        print(f"⚠️ Failed to evaluate formula '{formula}' with deltas {deltas}: {e}")
        return 0.0

def classify_order(order) -> Dict[str, Any]:
    """
    Classification logic for MILLING & PACKING:

    - MILLING (fully dynamic):
        ✔ Scales from milling_version_mappings.scales
        ✔ Formula from milling_version_mappings.formula
        ✔ Byproduct scale1/2/3 from milling_version_mappings

    - PACKING (unchanged):
        ✔ PL → SCADA mapping
        ✔ Bag size, pallets info
    """

    material_code = str(order.material or "").strip()
    version = (order.version or "").upper().strip()
    
    # ✅ FIX: Strip "V" prefix from version if present (e.g., "VBKL1" -> "BKL1")
    # The "V" prefix indicates "version" but the actual version code in database is without it
    version_clean = version
    if version.startswith("V") and len(version) > 1:
        version_clean = version[1:]  # Remove "V" prefix
        print(f"🔍 [classify_order] Stripped 'V' prefix from version: '{version}' -> '{version_clean}'")

    result = {
        "order_type": None,
        "equipment": [],     # Main confirmed-weight scales
        "formula": "",
        "version": version_clean,  # Use cleaned version in result
        "byproduct": {},     # scale1/scale2/scale3
        "packing_info": {},
        "error": None
    }

    # ---------------------------------------------------------
    # MATERIAL PREFIX → MILLING / PACKING
    # ---------------------------------------------------------
    material_stripped = material_code.lstrip("0")
    if len(material_stripped) < 2:
        result["error"] = f"Invalid material code: {material_code}"
        return result

    prefix = material_stripped[:2]

    if prefix == "13":
        result["order_type"] = "MILLING"
    elif prefix == "14":
        result["order_type"] = "PACKING"
    else:
        result["error"] = f"Unknown material prefix: {prefix}"
        return result

    # =========================================================
    #             ✔✔✔ MILLING — NOW 100% DYNAMIC
    # =========================================================
    if result["order_type"] == "MILLING":
        from models.milling_version_mapping import MillingVersionMapping

        # Validate version is not empty
        if not version_clean:
            result["error"] = f"Version is empty or missing for order"
            print(f"❌ [classify_order] Version is empty for material {material_code}")
            return result

        try:
            with _mapping_db_session() as db:
                mapping = (
                    db.query(MillingVersionMapping)
                      .filter(MillingVersionMapping.version == version_clean)  # ✅ Use version_clean
                      .first()
                )
        except Exception as e:
            error_msg = f"Database error querying milling mapping for version '{version_clean}' (original: '{version}'): {e}"
            print(f"❌ [classify_order] {error_msg}")
            result["error"] = error_msg
            return result

        if not mapping:
            error_msg = f"No milling mapping found for version '{version_clean}' (original: '{version}'). Please add it via /api/milling-mapping"
            print(f"❌ [classify_order] {error_msg}")
            result["error"] = error_msg
            return result

        # ---------------------------
        # MAIN SCALE LIST
        # ---------------------------
        scales_raw = mapping.scales
        
        # ✅ CRITICAL FIX: Ensure scales is a proper list, not a JSON string
        # SQLAlchemy JSON columns should auto-deserialize, but handle edge cases
        if scales_raw is None:
            result["equipment"] = []
        elif isinstance(scales_raw, str):
            import json
            try:
                result["equipment"] = json.loads(scales_raw)
                print(f"🔧 [classify_order] Parsed scales string as JSON: {result['equipment']}")
            except json.JSONDecodeError:
                # If it's a comma-separated string, split it
                result["equipment"] = [s.strip() for s in scales_raw.split(",") if s.strip()]
                print(f"🔧 [classify_order] Parsed scales as comma-separated: {result['equipment']}")
        elif isinstance(scales_raw, list):
            result["equipment"] = scales_raw
        else:
            result["equipment"] = [scales_raw] if scales_raw else []

        # ---------------------------
        # FORMULA
        # ---------------------------
        result["formula"] = mapping.formula or ""

        # ---------------------------
        # BYPRODUCT scale1/2/3
        # ---------------------------
        result["byproduct"] = {
            "scale1": mapping.scale1,
            "scale2": mapping.scale2,
            "scale3": mapping.scale3
        }

        return result

    # =========================================================
    #                   PACKING (UNCHANGED)
    # =========================================================
    try:
        from models.palletizer_mapping import PalletizerMapping

        with _db_session() as db:
            mapping = db.query(PalletizerMapping).filter(
                PalletizerMapping.version == version_clean  # ✅ Use version_clean
            ).first()

        if not mapping:
            result["error"] = f"No palletizer mapping found for version {version_clean} (original: {version})"
            return result

        # Convert palletizer code → SCADA PL tag
        result["equipment"] = _translate_pl_to_scada([mapping.palletizer])
        result["formula"] = ""

        result["packing_info"] = {
            "bag_size_kg": float(mapping.bag_size_kg or 0),
            "bags_per_pallet": float(mapping.bags_per_pallet or 0),  # ✅ FIX: Use float, not int
            "kg_per_pallet": float(mapping.kg_per_pallet or 0),
            "description": f"{version_clean} → {mapping.palletizer}"
        }

    except Exception as e:
        print(f"❌ Error querying palletizer mapping for {version_clean} (original: {version}): {e}")
        result["error"] = f"Database error: {e}"
        return result

    return result

def get_all_scales_for_order(order, classification: Dict, include_byproduct: bool = False) -> List[str]:
    """
    Get all scales this order needs to lock.
    
    Args:
        order: ProcessOrder instance
        classification: Order classification dict
        include_byproduct: Whether to include byproduct scales (scale1/2/3).
                           Default False so we only lock the actual tracked equipment.
    
    Returns:
        List of scale tags (uppercase, stripped, no duplicates)
    """
    scales = set()
    
    # Always add the main equipment scales (these drive confirmed weight / production)
    equipment = classification.get("equipment", []) or []
    
    # ✅ CRITICAL FIX: Ensure equipment is a proper list, not a JSON string
    # If it's a string (e.g., '["WG501", "WG502"]'), parse it as JSON
    if isinstance(equipment, str):
        import json
        try:
            equipment = json.loads(equipment)
            print(f"🔧 [get_all_scales_for_order] Parsed equipment string as JSON: {equipment}")
        except json.JSONDecodeError:
            # If it's a comma-separated string, split it
            equipment = [s.strip() for s in equipment.split(",") if s.strip()]
            print(f"🔧 [get_all_scales_for_order] Parsed equipment as comma-separated: {equipment}")
    
    # Ensure equipment is a list
    if not isinstance(equipment, list):
        equipment = [equipment] if equipment else []
    
    for tag in equipment:
        if tag and isinstance(tag, str):
            scales.add(tag.upper().strip())
    
    if include_byproduct:
        # ✅ CRITICAL FIX (Dec 13, 2025): Include byproduct scales from BOTH sources:
        # 1. From ORDER object (for InProgress orders where scale1/2/3 are already set)
        # 2. From CLASSIFICATION (for all orders - this is the source of truth from DB mapping)
        
        # Source 1: Order object (runtime values)
        for scale_key in ["scale1", "scale2", "scale3"]:
            tag = get_attr_safe(order, scale_key)
            if tag:
                scales.add(tag.upper().strip())
                print(f"   🔧 [{order.order_id}] Added byproduct from order.{scale_key}: {tag}")
        
        # Source 2: Classification byproduct (from milling_version_mappings DB)
        # This ensures we get byproduct scales even for Pending orders
        byproduct = classification.get("byproduct", {}) or {}
        for scale_key in ["scale1", "scale2", "scale3"]:
            tag = byproduct.get(scale_key)
            if tag:
                scales.add(tag.upper().strip())
                print(f"   🔧 [{order.order_id}] Added byproduct from classification.{scale_key}: {tag}")
    
    result_scales = list(scales)
    print(f"📦 [get_all_scales_for_order] {order.order_id}: equipment={equipment}, byproduct={classification.get('byproduct')}, all_scales={result_scales}")
    return result_scales

def release_scales_and_start_waiting_orders(po_number: str, order, classification: Dict, db) -> None:
    """
    Release scales for a completed order and automatically start waiting orders.
    
    Enhanced with Scale Locking (Dec 12, 2025):
    - Unregisters order version for duplicate detection cleanup
    - Uses priority-based promotion for waiting orders
    
    Args:
        po_number: Order ID that completed
        order: ProcessOrder object
        classification: Order classification dict
        db: Database session
    """
    try:
        version = get_attr_safe(order, "version", "").upper().strip()
        order_type = classification.get("order_type")
        
        # Release ALL scales locked by this order (not just the scales it currently uses)
        # This ensures we release scales even if byproduct scales changed or were cleared
        # Pass None to release_scales to release all scales for this order
        released = release_scales(po_number, None)
        print(f"🔓 [Release-{po_number}] Released all scales for this order: {released}")
        
        # Unregister version for duplicate detection cleanup
        if version and order_type:
            unregister_order_version(po_number, version, order_type)
            print(f"🔓 [Release-{po_number}] Unregistered version {version} ({order_type})")
        
        # Also get scales for this order for logging purposes
        # ✅ Include byproduct scales in release check
        all_scales_for_order = get_all_scales_for_order(order, classification, include_byproduct=True)
        if all_scales_for_order:
            print(f"🔍 [Release-{po_number}] Order uses scales: {all_scales_for_order}")
            
            # Remove from queue if it was queued
            remove_from_queue(po_number)
            
            # ✅ CRITICAL FIX (Jan 27, 2026): Use conflict-group-aware promotion
            # Check which orders should be promoted based on conflict group priority
            print(f"🔍 [Release-{po_number}] Scales released. Checking for next priority order to promote...")
            
            # Remove the completed order from queue first
            remove_from_queue(po_number)
            
            # Get all pending orders and detect conflict groups
            all_pending = db.query(ProcessOrder).filter(ProcessOrder.status == "Pending").all()
            if all_pending:
                orders_data = []
                for pending_order in all_pending:
                    pending_classification = classify_order(pending_order)
                    if not pending_classification.get("error"):
                        all_scales = get_all_scales_for_order(pending_order, pending_classification, include_byproduct=True)
                        orders_data.append({
                            "order_id": pending_order.order_id,
                            "version": get_attr_safe(pending_order, "version", ""),
                            "scales": all_scales,
                            "order_type": pending_classification.get("order_type"),
                            "priority": get_attr_safe(pending_order, "hercules_priority", 999) or get_attr_safe(pending_order, "priority", 999) or 999,
                            "status": pending_order.status
                        })
                
                # Detect conflict groups
                if orders_data:
                    from services.scale_lock_service import get_conflict_groups_for_orders
                    conflict_info = get_conflict_groups_for_orders(orders_data)
                    
                    # Find orders that can run (priority=1 in their conflict group AND scales are free)
                    promoted_orders = []
                    for pending_order in all_pending:
                        pending_po = pending_order.order_id
                        order_conflict = conflict_info["order_conflict_info"].get(pending_po, {})
                        
                        # Only promote if it's priority=1 in its conflict group (or has no conflicts)
                        can_run = not order_conflict.get("has_conflict") or order_conflict.get("can_run", False)
                        
                        if can_run:
                            # Check if scales are actually available
                            pending_classification = classify_order(pending_order)
                            if not pending_classification.get("error"):
                                all_scales = get_all_scales_for_order(pending_order, pending_classification, include_byproduct=True)
                                priority = get_attr_safe(pending_order, "hercules_priority") or get_attr_safe(pending_order, "priority") or 100
                                version = get_attr_safe(pending_order, "version", "").upper().strip()
                                order_type = pending_classification.get("order_type")
                                
                                # Try to lock scales
                                has_conflict, locked, _, _ = lock_scales(pending_po, all_scales, priority, version, order_type)
                                
                                if not has_conflict and len(locked) == len(all_scales):
                                    # Successfully locked - this order can be promoted
                                    promoted_orders.append(pending_po)
                                    add_to_queue(pending_po, all_scales, priority, version, order_type)
                                    update_queue_status(pending_po, "RUNNING")
                                    print(f"✅ [Release-{po_number}] Promoting {pending_po} (conflict_group_priority={order_conflict.get('group_priority', 1)})")
                else:
                    promoted_orders = []
            else:
                promoted_orders = []
            
            if promoted_orders:
                print(f"🚀 [Release-{po_number}] Promoted {len(promoted_orders)} waiting order(s) by conflict group priority: {promoted_orders}")
                for promoted_po_number in promoted_orders:
                    try:
                        # Get the order and start validation
                        promoted_order = db.query(ProcessOrder).filter(
                            ProcessOrder.order_id == promoted_po_number
                        ).first()
                        if promoted_order:
                            # ✅ C31-T32: Also start Pending orders that were waiting for scales
                            # When scales become available, waiting orders might still be "Pending"
                            # Change them to "InProgress" so they can start
                            if promoted_order.status == "Pending":
                                set_attr_safe(promoted_order, "status", "InProgress")
                                db.add(promoted_order)
                                db.commit()
                                print(f"📋 [Release-{po_number}] Changed waiting order {promoted_po_number} status: Pending → InProgress")
                            
                            # Now check if order is InProgress (either originally or just changed)
                            if promoted_order.status == "InProgress":
                                promoted_classification = classify_order(promoted_order)
                                if not promoted_classification.get("error"):
                                    # Capture baselines for promoted order (now that scales are available)
                                    promoted_equipment = promoted_classification.get("equipment", [])
                                    
                                    # ✅ Initialize promoted_baselines to None in case equipment is empty
                                    promoted_baselines = None
                                    
                                    # ✅ CRITICAL FIX (Jan 22, 2026): Enhanced baseline capture for auto-started orders
                                    # Match the robustness of init_and_start_order_worker to ensure baselines are captured correctly
                                    if promoted_equipment:
                                        print(f"🔄 [Release-{po_number}] Capturing baselines for promoted order {promoted_po_number}...")
                                        
                                        # 1️⃣ Clear SCADA cache to get fresh values (not stale from previous order)
                                        try:
                                            from services.scale_service import clear_scada_cache
                                            clear_scada_cache()
                                            print(f"✅ [Release-{po_number}] SCADA cache cleared for {promoted_po_number}")
                                        except Exception as e:
                                            print(f"⚠️ [Release-{po_number}] Could not clear SCADA cache: {e}")
                                        
                                        # 2️⃣ Wait for SCADA values to settle after previous order completed
                                        import time
                                        print(f"⏳ [Release-{po_number}] Waiting for SCADA values to settle...")
                                        time.sleep(1.0)  # 1 second delay for SCADA to stabilize
                                        
                                        # 3️⃣ Take multiple baseline readings to ensure stable values
                                        baselines_1 = capture_baseline_readings(promoted_equipment)
                                        time.sleep(0.3)
                                        baselines_2 = capture_baseline_readings(promoted_equipment)
                                        time.sleep(0.3)
                                        baselines_3 = capture_baseline_readings(promoted_equipment)
                                        
                                        # Use the most recent reading (should be most stable)
                                        promoted_baselines = baselines_3 if baselines_3 else (baselines_2 if baselines_2 else baselines_1)
                                        
                                        if promoted_baselines:
                                            print(f"✅ [Release-{po_number}] Captured baselines (3rd reading): {promoted_baselines}")
                                            
                                            # 4️⃣ NOW reset and set baselines (only after successful capture)
                                            # First reset to ensure clean state, then immediately set captured values
                                            for tag in promoted_equipment:
                                                set_attr_safe(promoted_order, f"baseline_{tag.lower()}", 0.0)
                                            
                                            for tag, value in promoted_baselines.items():
                                                set_attr_safe(promoted_order, f"baseline_{tag.lower()}", float(value or 0.0))
                                        else:
                                            print(f"⚠️ [Release-{po_number}] Failed to capture baselines for {promoted_po_number} after 3 attempts!")
                                            # Don't reset baselines to 0 - leave them as-is to avoid breaking delta calculation
                                    
                                    if promoted_baselines:
                                        
                                        # Handle MILLING byproduct scales
                                        if promoted_classification.get("order_type") == "MILLING":
                                            version = (get_attr_safe(promoted_order, "version") or "").strip().upper()
                                            
                                            # ✅ FIX: Check if byproduct tags are already set (RESTART scenario)
                                            # If tags are set, preserve quantities and only reset baselines
                                            existing_scale1 = get_attr_safe(promoted_order, "scale1", None)
                                            existing_scale2 = get_attr_safe(promoted_order, "scale2", None)
                                            existing_scale3 = get_attr_safe(promoted_order, "scale3", None)
                                            byproduct_tags_already_set = (
                                                (existing_scale1 is not None and existing_scale1 != "") or
                                                (existing_scale2 is not None and existing_scale2 != "") or
                                                (existing_scale3 is not None and existing_scale3 != "")
                                            )
                                            
                                            if byproduct_tags_already_set:
                                                # RESTART: Preserve quantities, only reset baselines to current SCADA
                                                print(f"🔒 [Release-{po_number}] Promoted order {promoted_po_number} byproduct tags set - preserving quantities")
                                                from services.scale_service import get_scada_reading
                                                for scale_tag in [existing_scale1, existing_scale2, existing_scale3]:
                                                    if scale_tag:
                                                        current_reading = float(get_scada_reading(scale_tag) or 0.0)
                                                        promoted_baselines[scale_tag] = current_reading
                                                        set_attr_safe(promoted_order, f"baseline_{scale_tag.lower()}", current_reading)
                                                        print(f"   📌 Reset baseline to CURRENT SCADA: {scale_tag} = {current_reading:.2f}")
                                            else:
                                                # BRAND NEW: Capture fresh baselines and initialize byproduct scales
                                                promoted_baselines = _capture_byproduct_baselines(version, promoted_baselines, order=promoted_order)
                                                for tag, val in promoted_baselines.items():
                                                    set_attr_safe(promoted_order, f"baseline_{tag.lower()}", float(val or 0.0))
                                                _set_byproduct_scales(promoted_order, version, promoted_baselines)
                                        
                                        # ✅ CRITICAL FIX (Jan 22, 2026): Handle PACKING orders
                                        # For PACKING orders, baseline is read from scale1_qty column, NOT baseline_{tag}
                                        # Must set scale1/scale1_qty for baseline to work correctly
                                        elif promoted_classification.get("order_type") == "PACKING":
                                            if promoted_equipment:
                                                tag = promoted_equipment[0]
                                                baseline_value = float(promoted_baselines.get(tag, 0.0) or 0.0)
                                                set_attr_safe(promoted_order, "scale1", tag)
                                                set_attr_safe(promoted_order, "scale1_qty", baseline_value)
                                                print(f"📦 [Release-{po_number}] PACKING: Set scale1={tag}, scale1_qty={baseline_value:.2f} for {promoted_po_number}")
                                            else:
                                                set_attr_safe(promoted_order, "scale1", None)
                                                set_attr_safe(promoted_order, "scale1_qty", 0.0)
                                            # Clear unused scales for PACKING
                                            set_attr_safe(promoted_order, "scale2", None)
                                            set_attr_safe(promoted_order, "scale2_qty", 0.0)
                                            set_attr_safe(promoted_order, "scale3", None)
                                            set_attr_safe(promoted_order, "scale3_qty", 0.0)
                                        
                                        # Initialize shift
                                        plant = get_attr_safe(promoted_order, "plant", "3130")
                                        department = "MILLING" if promoted_classification.get("order_type") == "MILLING" else "PACKING"
                                        shift_row = get_current_shift(plant, department, db)
                                        current_shift = shift_row.shift_code if shift_row else "A"
                                        set_attr_safe(promoted_order, "current_shift", current_shift)
                                        set_attr_safe(promoted_order, "shift_start_time", datetime.now())
                                        
                                        # Set shift baselines
                                        if promoted_classification.get("order_type") == "MILLING":
                                            set_attr_safe(
                                                promoted_order,
                                                f"baseline_shift_{current_shift.lower()}_start",
                                                promoted_baselines,
                                            )
                                        else:
                                            shift_baseline_dict = {}
                                            for tag in promoted_equipment:
                                                shift_baseline_dict[tag] = float(promoted_baselines.get(tag, 0.0) or 0.0)
                                            set_attr_safe(
                                                promoted_order,
                                                f"baseline_shift_{current_shift.lower()}_start",
                                                shift_baseline_dict,
                                            )
                                        
                                        set_attr_safe(promoted_order, f"baseline_shift_{current_shift.lower()}_time", datetime.now())
                                        
                                        db.add(promoted_order)
                                        db.commit()
                                        
                                        print(f"✅ [Release-{po_number}] Captured baselines for promoted order {promoted_po_number}")
                                    
                                # ✅ CRITICAL: Add brief delay before starting promoted order
                                # This ensures the paused order's worker has fully stopped
                                # and there's no overlap in scale access
                                import time
                                time.sleep(0.5)  # 500ms delay for safety
                                print(f"⏳ [Release-{po_number}] Starting promoted order {promoted_po_number} after safety delay...")
                                
                                # Start validation thread for promoted order
                                validation_thread = threading.Thread(
                                    target=auto_validation_worker,
                                    args=(promoted_po_number, promoted_classification),
                                    daemon=True,
                                    name=f"Validation-{promoted_po_number}",
                                )
                                set_order_validation_state(promoted_po_number, {
                                    "isrunning": True,
                                    "thread": validation_thread,
                                    "progress_pct": 0,
                                    "status": "running",
                                    "started_at": datetime.now().isoformat()
                                })
                                validation_thread.start()
                                # Remove from queue since validation has started
                                remove_from_queue(promoted_po_number)
                                print(f"🚀 [Release-{po_number}] Started validation thread for promoted order {promoted_po_number}")
                    except Exception as e:
                        print(f"⚠️ [Release-{po_number}] Failed to start promoted order {promoted_po_number}: {e}")
                        import traceback
                        traceback.print_exc()
        else:
            print(f"⚠️ [Release-{po_number}] No scales to release for this order")
    except Exception as e:
        print(f"⚠️ [Release-{po_number}] Error releasing scales: {e}")
        import traceback
        traceback.print_exc()

def _get_baseline_for_tag(order, tag: str) -> float:
    """
    Helper function to get baseline value for a scale tag.
    For PL/SL scales (PACKING), baseline is stored in scale1_qty/scale2_qty/scale3_qty.
    For WG/DM scales (MILLING), baseline is stored in baseline_{tag} attributes.
    """
    tag_upper = tag.upper()
    
    # ✅ ONLY use scale1_qty/scale2_qty/scale3_qty for PL/SL palletizer scales
    # WG/DM scales ALWAYS use baseline_{tag} attributes
    if tag_upper.startswith("PL") or tag_upper.startswith("SL"):
        scale1_tag = str(get_attr_safe(order, 'scale1', '') or '').upper()
        scale2_tag = str(get_attr_safe(order, 'scale2', '') or '').upper()
        scale3_tag = str(get_attr_safe(order, 'scale3', '') or '').upper()
        
        if tag_upper == scale1_tag:
            return float(get_attr_safe(order, 'scale1_qty', 0.0) or 0.0)
        elif tag_upper == scale2_tag:
            return float(get_attr_safe(order, 'scale2_qty', 0.0) or 0.0)
        elif tag_upper == scale3_tag:
            return float(get_attr_safe(order, 'scale3_qty', 0.0) or 0.0)
    
    # WG/DM scales use baseline_{tag} attributes
    baseline_attr = f"baseline_{tag.lower()}"
    return float(get_attr_safe(order, baseline_attr, 0.0) or 0.0)

def get_current_production(order, classification: Dict, db=None, force_fresh_baseline: bool = False, use_shift_baselines: bool = True) -> Dict[str, Any]:
    """
    ✅ FIXED: Use SHIFT baselines (not global baselines) for accurate production tracking
    
    Args:
        use_shift_baselines: If True, use shift-specific baselines (for worker)
                            If False, use global baselines (for manual checks)
    """
    from services.scale_service import get_scada_reading, calculate_deltas
    
    # ✅ CRITICAL: Refresh order to ensure we have latest baseline values from database
    # This ensures we read fresh shift baselines, not stale cached values
    if db is not None:
        try:
            db.refresh(order)
        except Exception:
            pass  # If refresh fails, continue with current order state
    
    main_equipment = classification.get("equipment", []) or []
    if not main_equipment:
        return {"error": "No main equipment mapped", "total": 0.0}
    
    order_type = classification.get("order_type")
    packing_info = classification.get("packing_info", {}) or {}
    
    # ================================================================
    # ✅ CRITICAL FIX: Use SHIFT baselines (not global baselines)
    # This ensures production is calculated from shift start, preserving
    # previous production when order is restarted
    # ================================================================
    baselines_main = {}
    
    if use_shift_baselines:
        # ✅ Use shift-specific baselines (for worker - accurate after restart)
        current_shift = get_attr_safe(order, "current_shift", "A")
        shift_baseline_field = f"baseline_shift_{current_shift.lower()}_start"
        shift_baselines = get_attr_safe(order, shift_baseline_field, None)
        
        if shift_baselines and isinstance(shift_baselines, dict):
            # ✅ CRITICAL FIX: Handle both simple dict format {'TAG': float} and nested dict format {'TAG': {'current': float}}
            # Extract current values if nested dict format is detected
            baselines_main = {}
            for tag in main_equipment:
                if tag in shift_baselines:
                    value = shift_baselines[tag]
                    # Handle nested dict format {'current': val, 'delta': val}
                    if isinstance(value, dict):
                        current_val = float(value.get('current', 0.0) or 0.0)
                    else:
                        current_val = float(value or 0.0)
                    baselines_main[tag] = current_val
                else:
                    # Tag not in shift baselines, use global baseline as fallback
                    # ✅ FIX: For PL/SL scales, baseline is stored in scale1_qty/scale2_qty/scale3_qty
                    baselines_main[tag] = _get_baseline_for_tag(order, tag)
            print(f"✅ Using SHIFT baselines for production calculation: {baselines_main}")
        else:
            # Fallback to global baselines if shift baselines not found
            print(f"⚠️ Shift baselines not found, falling back to global baselines")
            for tag in main_equipment:
                # ✅ FIX: For PL/SL scales, baseline is stored in scale1_qty/scale2_qty/scale3_qty
                baselines_main[tag] = _get_baseline_for_tag(order, tag)
    else:
        # Use global baselines (for manual checks or initial setup)
        for tag in main_equipment:
            # ✅ FIX: For PL/SL scales, baseline is stored in scale1_qty/scale2_qty/scale3_qty
            baselines_main[tag] = _get_baseline_for_tag(order, tag)
    
    # ================================================================
    # Calculate deltas from baselines
    # ================================================================
    deltas_main = calculate_deltas(main_equipment, baselines_main, order, db=db)
    per_tag_delta_main = {tag: float(info.get("delta", 0.0) or 0.0) for tag, info in deltas_main.items()}
    
    # ✅ FIX: Use sum_dm_readings_for_order for DM water meters
    # DM tags are 30-sec averages on PLC side, so we must SUM all readings in the time window,
    # rather than using the delta/accumulation logic which misses readings between polls.
    try:
        from services.scale_service import sum_dm_readings_for_order
        
        for tag in main_equipment:
            if tag.startswith("DM"):
                # Calculate correct sum from database
                dm_sum = sum_dm_readings_for_order(tag, order)
                
                # Update values used for formula evaluation
                per_tag_delta_main[tag] = dm_sum
                
                # Update values returned to UI/Frontend
                if tag in deltas_main:
                    deltas_main[tag]["delta"] = dm_sum
                    # Note: We keep 'current' as is (instantaneous flow rate), but 'delta' becomes the total volume
                    print(f"💧 [get_current_production] Replaced DM delta for {tag} with SUM: {dm_sum} (Type: {type(dm_sum)})")
    except Exception as e:
        print(f"⚠️ [get_current_production] Error calculating DM sums: {e}")

    
    # ================================================================
    # Calculate total production
    # ================================================================
    if order_type == "MILLING" and classification.get("formula"):
        formula = classification["formula"]
        total_main = evaluate_formula_using_deltas(formula, per_tag_delta_main)
    else:
        total_main = sum(per_tag_delta_main.values())
    
    # Convert to bags if PACKING
    if order_type == "PACKING":
        packing_info = classification.get("packing_info", {})
        total_bags = 0.0
        
        for tag in main_equipment:
            delta = per_tag_delta_main.get(tag, 0.0)
            bags = _convert_packing_delta_to_bags(tag, delta, packing_info)
            total_bags += bags
        
        total_main = total_bags
    
    # ============================================================
    # ✅ REMOVED: Logic that was hiding deltas for brand-new orders
    # This was causing values to reset to 0 after showing correctly for 1-2 seconds
    # Now all production values are shown properly from the start
    # ============================================================
    # NOTE: The previous logic was hiding small deltas (< 2.0 kg) for brand-new orders
    # to prevent SCADA settling issues. However, this caused the UI to show correct
    # values briefly, then reset them to 0, which was confusing.
    # 
    # After reset, baselines are correctly captured as 0.0 (reset-adjusted),
    # so there's no need to hide deltas anymore. All production should be visible.
    # ============================================================
    
    # ================================================================
    # Get byproduct baselines (if MILLING)
    # ================================================================
    byp_tags = [get_attr_safe(order, "scale1"), get_attr_safe(order, "scale2"), get_attr_safe(order, "scale3")]
    byp_tags = [t for t in byp_tags if t]
    byproduct_baselines = {tag: float(get_attr_safe(order, f"baseline_{tag.lower()}", 0.0) or 0.0) for tag in byp_tags}
    
    return {
        "total": total_main,
        "deltas": deltas_main,
        "baselines": baselines_main,
        "per_scale": per_tag_delta_main,
        "byproduct_baselines": byproduct_baselines,
    }

def check_order_completion(order, classification: Dict) -> Dict[str, Any]:
    """
    Check if order is complete. Uses confirmed_qty which is already updated by the worker.
    ✅ CRITICAL: The worker already updates confirmed_qty = preserved_confirmed_qty + total_production
    So we just need to check if confirmed_qty >= target_qty
    """
    # ✅ CRITICAL: Use confirmed_qty directly (worker already updates it correctly)
    # The worker calculates: display_total = preserved_confirmed_qty + total_production
    # And sets: confirmed_qty = min(display_total, target_qty)
    # So confirmed_qty is already the total production (capped at target)
    existing_confirmed = float(get_attr_safe(order, "confirmed_qty", 0.0) or 0.0)
    
    # Get fresh production for variance calculation
    if get_attr_safe(order, "shift_end_time"):
    # Do NOT take SCADA deltas after shift end (would double count)
        new_production = 0.0
    else:
        prod_info = get_current_production(order, classification)
        new_production = float(prod_info.get("total", 0.0) or 0.0)
    # new_production = float(prod_info.get("total", 0.0) or 0.0) if not prod_info.get("error") else 0.0
    
    order_type = classification["order_type"]
    if order_type == "MILLING":
        target_qty = float(get_attr_safe(order, "expected_weight") or get_attr_safe(order, "quantity") or 0.0)
        unit = "KG"
    else:
        # ✅ CRITICAL FIX (Jan 23, 2026): PACKING quantity is already stored in BAGS
        # Only SCADA delta needs conversion (pallets → bags), NOT the target quantity
        target_qty = float(get_attr_safe(order, "quantity") or 0.0)
        print(f"🔍 [check_order_completion] PACKING target: {target_qty} bags (quantity already in bags)")
        unit = "BAG"
    
    if target_qty == 0:
        return {"is_complete": False, "error": "Invalid target quantity"}
    
    # ✅ C31-T25: Use actual shift weights sum for total_actual (not confirmed_qty which is capped at target).
    # For PACKING, confirmed_qty is min(scada_total, target) so overflow was always 0 when production
    # exceeded target. Shift weights hold real production; overflow = max(0, shift_weights_sum - target).
    shift_weights_sum = (
        float(get_attr_safe(order, "weight_shift_a", 0.0) or 0.0)
        + float(get_attr_safe(order, "weight_shift_b", 0.0) or 0.0)
        + float(get_attr_safe(order, "weight_shift_c", 0.0) or 0.0)
    )
    total_actual = shift_weights_sum
    
    overall_variance = total_actual - target_qty
    overall_variance_pct = (overall_variance / target_qty) * 100.0 if target_qty > 0 else 0.0
    
    # ✅ CRITICAL: Check completion using both methods:
    # 1. total_actual >= target_qty (includes latest production)
    # 2. confirmed_qty >= target_qty (worker already capped it at target)
    # Order is complete if either condition is true
    is_complete = (total_actual >= target_qty) or (existing_confirmed >= target_qty)
    
    # ✅ OVERFLOW CALCULATION: Calculate overflow for transfer to next order of same type
    # Overflow = production beyond target (will be transferred to next order of same type)
    overflow = max(0.0, total_actual - target_qty)
    
    # Log completion check for debugging
    if existing_confirmed >= target_qty * 0.99:  # Log when close to completion
        print(f"🔍 [Completion Check] confirmed_qty={existing_confirmed:.2f}, target={target_qty:.2f}, total_actual={total_actual:.2f}, is_complete={is_complete}, overflow={overflow:.2f}")
    
    return {
        "is_complete": is_complete,
        "actual_qty": round(total_actual, 3),  # Report actual (not capped)
        "target_qty": round(target_qty, 3),
        "variance": round(overall_variance, 3),
        "variance_pct": round(overall_variance_pct, 2),
        "overflow": round(overflow, 3),  # Report overflow for storage
        "unit": unit
    }
def update_order_scales(order, deltas: Dict) -> None:
    """
    Update scale quantities.

    ✔ MILLING:
        - DO NOT update byproduct scale quantities.
        - Byproduct scale1/2/3 quantities are captured ONCE at order start.

    ✔ PACKING:
        - Convert pallets -> bags
        - Update scale1/2/3 quantities dynamically
    """

    order_type = (get_attr_safe(order, "order_type", "") or "").strip().upper()

    # --------------------------------------------------------
    # MILLING — DO NOT UPDATE BYPRODUCT QUANTITIES
    # --------------------------------------------------------
    if order_type == "MILLING":
        # Do NOT update byproduct scale quantities here.
        # scale1_qty, scale2_qty, scale3_qty store the CONFIRMED amount sent to SAP.
        # They are only updated during SAP confirmation (manual_confirm_from_progress).
        # The delta for display is calculated on-the-fly in byproduct_details.
        return

    # --------------------------------------------------------
    # PACKING — UPDATE SCALE QUANTITIES (PALLETS → BAGS)
    # --------------------------------------------------------
    if order_type == "PACKING":
        classification = classify_order(order)
        packing_info = classification.get("packing_info", {})
        # ✅ COMMENTED OUT: SCADA now sends bags directly, not palletizers
        # Use bags_per_pallet (e.g., 32 bags per palletizer) for conversion
        # Support fractional palletizers: 0.5 palletizer = 16 bags, 0.3 = 9.6 bags, etc.
        # bags_per_pallet = float(packing_info.get("bags_per_pallet") or 1)
        # if bags_per_pallet == 0:
        #     bags_per_pallet = float(packing_info.get("bag_size_kg") or 1)

        scale1_tag = str(get_attr_safe(order, "scale1") or "").upper()
        scale2_tag = str(get_attr_safe(order, "scale2") or "").upper()
        scale3_tag = str(get_attr_safe(order, "scale3") or "").upper()

        for tag, delta_info in deltas.items():
            # Get raw delta (pallets for PL, bags for SL)
            raw_delta = float(delta_info.get("delta", 0.0) or 0.0)
            
            # Convert to bags: PL palletizers need conversion, SL already in bags
            bags = _convert_packing_delta_to_bags(tag, raw_delta, packing_info)
            
            if bags <= 0:
                continue
                
            tag_cmp = str(tag or "").upper()

            if tag_cmp == scale1_tag:
                set_attr_safe(order, "scale1_qty", bags)
            elif tag_cmp == scale2_tag:
                set_attr_safe(order, "scale2_qty", bags)
            elif tag_cmp == scale3_tag:
                set_attr_safe(order, "scale3_qty", bags)

        return


def serialize_order(row: Any) -> Dict[str, Any]:
    def format_datetime(dt):
        if dt is None:
            return None
        if hasattr(dt, 'isoformat'):
            return dt.isoformat()
        return str(dt)

    # ✅ CRITICAL FIX (Jan 23, 2026): Calculate target based on order type
    # MILLING: target = expected_weight or quantity (KG)
    # PACKING: target = quantity (already in BAGS - do NOT convert)
    # NOTE: SCADA delta needs conversion (pallets → bags), but order.quantity is already in bags
    order_type = (get_attr_safe(row, "order_type") or "").strip().upper()
    raw_quantity = float(get_attr_safe(row, "quantity") or 0)
    expected_weight = float(get_attr_safe(row, "expected_weight") or 0)
    
    if order_type == "MILLING":
        target = expected_weight if expected_weight > 0 else raw_quantity
        uom = "KG"
    elif order_type == "PACKING":
        # ✅ PACKING: quantity is already stored in BAGS (not pallets)
        # Only SCADA delta needs conversion from pallets to bags, NOT the target
        target = raw_quantity
        uom = "BAG"
    else:
        target = raw_quantity
        uom = get_attr_safe(row, "unit") or get_attr_safe(row, "uom") or ""

    return {
        "id": get_attr_safe(row, "id"),
        "po_number": get_attr_safe(row, "order_id"),
        "material": get_attr_safe(row, "material"),
        "version": get_attr_safe(row, "version"),
        "batch": get_attr_safe(row, "batch"),
        "quantity": get_attr_safe(row, "quantity"),
        "unit": get_attr_safe(row, "unit") or get_attr_safe(row, "uom"),
        "status": get_attr_safe(row, "status", "Pending"),
        "priority": get_attr_safe(row, "hercules_priority", 0) or get_attr_safe(row, "priority", 0),
        "priority_id": get_attr_safe(row, "priority_id", None),
        "expected_weight": get_attr_safe(row, "expected_weight"),
        "confirmed_qty": get_attr_safe(row, "confirmed_qty"),
        "last_confirmed_qty": get_attr_safe(row, "last_confirmed_qty", 0),
        "is_final_sent": get_attr_safe(row, "is_final_sent", False),
        "validation_method": get_attr_safe(row, "validation_method"),
        "order_type": get_attr_safe(row, "order_type"),
        "confirmed_text": get_attr_safe(row, "confirmed_text"),
        "created_at": format_datetime(get_attr_safe(row, "created_at")),
        "scale1": get_attr_safe(row, "scale1"),
        "scale1_qty": get_attr_safe(row, "scale1_qty"),
        "scale2": get_attr_safe(row, "scale2"),
        "scale2_qty": get_attr_safe(row, "scale2_qty"),
        "scale3": get_attr_safe(row, "scale3"),
        "scale3_qty": get_attr_safe(row, "scale3_qty"),
        # ✅ NEW: Calculated target for frontend (already converted for packing)
        "target": target,
        "uom": uom,
    }


# =============================================================================
# SHIFT HELPERS (unchanged except where needed)
# =============================================================================



def calculate_shift_weight(order, shift: str, classification: Dict, db=None) -> float:
    """
    Calculate total production weight for a specific shift.
    
    ✅ CRITICAL: Always uses the latest baseline from database to prevent using stale baselines after restart.
    
    Returns:
        - MILLING: Weight in KG (from formula or sum of deltas)
        - PACKING: Count in PALLETS (will be converted to bags later)
    """
    try:
        equipment = classification["equipment"]
        formula = classification.get("formula", "")
        order_type = classification.get("order_type")
        po_number = get_attr_safe(order, "order_id", "UNKNOWN")

        if not equipment:
            return 0.0

        # ✅ CRITICAL: Refresh order from database to ensure we have latest baseline values
        # This is especially important after restart when baseline was just updated
        if db is not None:
            try:
                db.refresh(order)
                print(f"✅ [{po_number}] calculate_shift_weight: Refreshed order from database to get latest baseline")
            except Exception as e:
                print(f"⚠️ [{po_number}] calculate_shift_weight: Failed to refresh order: {e}")

        # Get baseline for this shift
        baseline_field = f"baseline_shift_{shift.lower()}_start"
        shift_baselines = get_attr_safe(order, baseline_field, None)
        
        # ✅ CRITICAL DEBUG: Log baseline source to help troubleshoot
        if shift_baselines:
            print(f"🔍 [{po_number}] calculate_shift_weight: Using shift baseline from {baseline_field}: {shift_baselines}")
        else:
            print(f"⚠️ [{po_number}] calculate_shift_weight: No shift baseline found in {baseline_field}, will use global baseline")

        # If we have shift-specific baselines, use them
        if shift_baselines and isinstance(shift_baselines, dict):
            # ✅ CRITICAL FIX: Handle both simple dict format {'TAG': float} and nested dict format {'TAG': {'current': float}}
            # Extract current values if nested dict format is detected
            baselines = {}
            for tag in equipment:
                if tag in shift_baselines:
                    value = shift_baselines[tag]
                    # Handle nested dict format {'current': val, 'delta': val}
                    if isinstance(value, dict):
                        current_val = float(value.get('current', 0.0) or 0.0)
                    else:
                        current_val = float(value or 0.0)
                    baselines[tag] = current_val
                else:
                    # Tag not in shift baselines, use global baseline as fallback
                    baseline_attr = f"baseline_{tag.lower()}"
                    baselines[tag] = float(get_attr_safe(order, baseline_attr, 0.0) or 0.0)
            baseline_source = "shift_baselines"
        else:
            # Fallback to regular baselines (shouldn't happen in normal flow)
            baselines = {}
            for tag in equipment:
                baseline_attr = f"baseline_{tag.lower()}"
                baselines[tag] = float(get_attr_safe(order, baseline_attr, 0.0) or 0.0)
            baseline_source = "regular_baselines"
            print(f"⚠️ [{po_number}] calculate_shift_weight: No shift baselines found for shift {shift}, using regular baselines")

        # ✅ ADD DEBUG: Print baselines
        if int(time.time()) % 30 == 0:
            print(f"🔍 [{po_number}] Baselines from {baseline_source}: {baselines}")

        # Compute deltas
        deltas = calculate_deltas(equipment, baselines, order=order, db=None)
        per_tag_delta = {tag: float(deltas[tag].get("delta", 0.0) or 0.0) for tag in equipment}

        # ✅ FIX: Use sum_dm_readings_for_order for DM water meters
        # DM tags are 30-sec averages on PLC side, so we must SUM all readings in the time window,
        # rather than using the delta/accumulation logic which misses readings between polls.
        try:
            from services.scale_service import sum_dm_readings_for_order
            
            for tag in equipment:
                if tag.startswith("DM"):
                    # Calculate correct sum from database
                    dm_sum = sum_dm_readings_for_order(tag, order)
                    
                    # Update values used for formula evaluation
                    per_tag_delta[tag] = dm_sum
                    
                    # Update values returned in deltas dict
                    if tag in deltas:
                        deltas[tag]["delta"] = dm_sum
                        # Note: We keep 'current' as is (instantaneous flow rate), but 'delta' becomes the total volume
                        print(f"💧 [calculate_shift_weight] Replaced DM delta for {tag} with SUM: {dm_sum} (Type: {type(dm_sum)})")
        except Exception as e:
            print(f"⚠️ [calculate_shift_weight] Error calculating DM sums: {e}")

        # ✅ ADD DEBUG: Print deltas
        if int(time.time()) % 30 == 0:
            print(f"🔍 [{po_number}] Deltas: {per_tag_delta}")

        # ---- MILLING ---- use formula (same as live production)
        if order_type == "MILLING" and formula:
            result = evaluate_formula_using_deltas(formula, per_tag_delta)
            
            # ✅ CRITICAL DEBUG: Check if result is reasonable
            sum_of_deltas = sum(per_tag_delta.values())
            if int(time.time()) % 30 == 0:
                print(f"🔍 [{po_number}] calculate_shift_weight MILLING:")
                print(f"  Formula: {formula}")
                print(f"  Deltas: {per_tag_delta}")
                print(f"  Formula result: {result:.2f} KG")
                print(f"  Sum of deltas: {sum_of_deltas:.2f}")
                if sum_of_deltas > 0:
                    ratio = result / sum_of_deltas
                    print(f"  Ratio (formula/sum): {ratio:.2f}")
                    if ratio > 5.0:
                        print(f"  ⚠️ WARNING: Formula result is {ratio:.1f}x larger than sum of deltas - possible multiplication issue!")
                else:
                    print(f"  Ratio: N/A (sum of deltas is 0)")
            
            return result

        # ---- PACKING ---- convert pallets to bags for PL, keep SL as-is
        if order_type == "PACKING":
            packing_info = classification.get("packing_info", {})
            total_bags = 0.0
            
            for tag in equipment:
                delta = per_tag_delta.get(tag, 0.0)
                bags = _convert_packing_delta_to_bags(tag, delta, packing_info)
                total_bags += bags
            
            result = total_bags
            # Debug logging for PACKING
            if int(time.time()) % 30 == 0:
                print(f"🔍 [{po_number}] calculate_shift_weight PACKING: deltas={per_tag_delta}, result={result:.2f} bags (from {baseline_source})")
            return result
        
        # Fallback (shouldn't reach here for PACKING)
        result = sum(per_tag_delta.values())
        return result

    except Exception as e:
        po_number = get_attr_safe(order, "order_id", "UNKNOWN")
        print(f"❌ [{po_number}] Error calculating shift weight: {e}")
        import traceback
        traceback.print_exc()
        return 0.0




# def end_shift_and_confirm(order, current_shift: str, classification: Dict, sap_service, force_final: bool = False) -> Dict[str, Any]:
#     """
#     ✅ FIXED: End shift and send remaining production to SAP.
    
#     Key fixes:
#     - DON'T update confirmed_qty (auto-validator handles it)
#     - DON'T use last_confirmed_qty (not needed)
#     - Only send REMAINING production (weight_shift_X - confirmed_shift_X)
#     - Track confirmations in confirmed_shift_X columns
#     """
#     try:
#         shift_weight = calculate_shift_weight(order, current_shift, classification)
        
#         order_type = classification["order_type"]
#         if order_type == "MILLING":
#             target = float(get_attr_safe(order, "expected_weight") or get_attr_safe(order, "quantity") or 0.0)
#             shift_weight_stored = shift_weight
#             uom = "KG"
#         else:
#             # PACKING: Convert pallets to bags
#             target = float(get_attr_safe(order, "quantity") or 0.0)
#             packing_info = classification.get("packing_info", {})
#             bags_per_pallet = packing_info.get("bag_size_kg", 1)
#             shift_weight_stored = shift_weight * bags_per_pallet
#             uom = "BAG"
        
#         # ✅ CRITICAL: Store shift production in weight_shift_X (ACCUMULATE, don't overwrite)
#         # When restarting in the same shift, we need to add to existing weight, not replace it
#         try:
#             shift_field = f"weight_shift_{current_shift.lower()}"
#             # ✅ Read existing shift weight (may have production from before restart)
#             existing_shift_weight = float(get_attr_safe(order, shift_field, 0.0) or 0.0)
            
#             # ✅ Accumulate: Add new production to existing shift weight
#             accumulated_shift_weight = existing_shift_weight + shift_weight_stored
#             set_attr_safe(order, shift_field, accumulated_shift_weight)
#             set_attr_safe(order, "shift_end_time", datetime.now())
            
#             if existing_shift_weight > 0.0:
#                 print(f"✅ Shift {current_shift}: Accumulated weight {existing_shift_weight:.2f} + new {shift_weight_stored:.2f} = {accumulated_shift_weight:.2f} {uom}")
#             else:
#             print(f"✅ Shift {current_shift}: Produced {shift_weight_stored:.2f} {uom}")
#         except Exception as e:
#             print(f"⚠️ Failed to record shift weight: {e}")
        
#         # ================================================================
#         # ✅ CHECK REMAINING PRODUCTION (deduplication)
#         # ================================================================
#         shift_weight_field = f"weight_shift_{current_shift.lower()}"
#         confirmed_field = f"confirmed_shift_{current_shift.lower()}"
        
#         total_shift_production = float(get_attr_safe(order, shift_weight_field, 0.0) or 0.0)
#         already_confirmed_for_shift = float(get_attr_safe(order, confirmed_field, 0.0) or 0.0)
        
#         remaining_shift_production = total_shift_production - already_confirmed_for_shift
        
#         # ================================================================
#         # ✅ CALCULATE TOTAL CONFIRMED TO SAP (from all shifts)
#         # ================================================================
#         confirmed_shift_a = float(get_attr_safe(order, "confirmed_shift_a", 0.0) or 0.0)
#         confirmed_shift_b = float(get_attr_safe(order, "confirmed_shift_b", 0.0) or 0.0)
#         confirmed_shift_c = float(get_attr_safe(order, "confirmed_shift_c", 0.0) or 0.0)
        
#         total_confirmed_to_sap = confirmed_shift_a + confirmed_shift_b + confirmed_shift_c
        
#         print(f"📊 Total confirmed to SAP: {total_confirmed_to_sap:.2f} {uom}")
#         print(f"   Shift A: {confirmed_shift_a:.2f}, Shift B: {confirmed_shift_b:.2f}, Shift C: {confirmed_shift_c:.2f}")
        
#         # ================================================================
#         # ✅ CALCULATE REMAINING TO TARGET
#         # ================================================================
#         remaining_to_target = target - total_confirmed_to_sap
        
#         # ✅ CRITICAL: If force_final=True (order is complete), always send final confirmation
#         # even if there's no remaining shift production or already fully confirmed
#         if force_final:
#             if remaining_to_target > 0:
#                 # Order is complete but not fully confirmed to SAP - send remaining as final confirmation
#                 confirm_qty = remaining_to_target
#                 print(f"🔔 FORCE FINAL: Order complete, sending remaining {confirm_qty:.2f} {uom} as final confirmation")
#             else:
#                 # Order is complete and already fully confirmed to SAP - send 0 quantity with final flag
#                 # This ensures the final_confirmation flag is set in SAP
#                 confirm_qty = 0.0
#                 print(f"🔔 FORCE FINAL: Order complete and already fully confirmed to SAP. Sending final confirmation flag with 0 quantity.")
#         elif remaining_shift_production <= 0:
#             # No remaining shift production and not forcing final
#             if remaining_to_target <= 0:
#                 print(f"✅ Shift {current_shift} fully confirmed. Order already fully confirmed to SAP.")
#                 plant = get_attr_safe(order, "plant", "3130")
#                 department = "MILLING" if order_type == "MILLING" else "PACKING"
#                 with _db_session() as db:
#                     next_shift_row = get_next_shift(current_shift, plant, department, db)
#                     next_shift = next_shift_row.shift_code if next_shift_row else "A"
#                 return {
#                     "success": True,
#                     "order_complete": False,
#                     "next_shift": next_shift,
#                     "confirmed_qty": 0.0,
#                     "message": f"Shift {current_shift} already fully confirmed"
#                 }
#             else:
#                 # Shift is confirmed but order not fully confirmed to SAP - use remaining to target
#                 confirm_qty = remaining_to_target
#                 print(f"⚠️ Shift {current_shift} confirmed but order not fully confirmed to SAP. Sending remaining {confirm_qty:.2f} {uom}")
#         else:
#             # Normal case: send remaining shift production (up to target)
#         confirm_qty = min(remaining_shift_production, remaining_to_target)
        
#         # ✅ CRITICAL: If force_final=True, always send even if confirm_qty is 0 (to set final flag)
#         if confirm_qty <= 0 and not force_final:
#             print(f"⚠️ No new production to confirm in Shift {current_shift}")
#             plant = get_attr_safe(order, "plant", "3130")
#             department = "MILLING" if order_type == "MILLING" else "PACKING"
#             with _db_session() as db:
#                 next_shift_row = get_next_shift(current_shift, plant, department, db)
#                 next_shift = next_shift_row.shift_code if next_shift_row else "A"
#             return {
#                 "success": True,
#                 "order_complete": False,
#                 "next_shift": next_shift,
#                 "confirmed_qty": 0.0,
#                 "message": "No new confirmation needed"
#             }
        
#         print(f"📤 Sending to SAP: {confirm_qty:.2f} {uom}")
#         print(f"   (Shift total: {total_shift_production:.2f}, Already sent: {already_confirmed_for_shift:.2f})")
        
#         new_total_confirmed_to_sap = total_confirmed_to_sap + confirm_qty
#         # ✅ CRITICAL: If force_final=True, always set final_confirmation flag
#         is_final_confirmation = force_final or (new_total_confirmed_to_sap >= target)

#         print(f"🔍 Final check: {new_total_confirmed_to_sap:.2f} >= {target:.2f} = {is_final_confirmation} (force_final={force_final})")
        
#         # ================================================================
#         # ✅ BUILD SAP PAYLOAD
#         # ✅ CRITICAL: Always include byproduct scales (even if order not validated)
#         # ================================================================
#         # ✅ CRITICAL: Refresh order to get latest scale values from database
#         # This ensures we have the most up-to-date scale values
#         try:
#             # If order is in a session, refresh it
#             if hasattr(order, '__session__') or hasattr(order, '_sa_instance_state'):
#                 # Order is already in a session, we can't refresh here
#                 # But we can ensure we read the latest values
#                 pass
#         except:
#             pass
        
#         # ✅ CRITICAL: Read scale values with proper defaults
#         # Ensure byproduct scales are always included, even if None or 0
#         scale1_tag = get_attr_safe(order, "scale1") or ""
#         scale1_qty_val = float(get_attr_safe(order, "scale1_qty", 0.0) or 0.0)
#         scale2_tag = get_attr_safe(order, "scale2") or ""
#         scale2_qty_val = float(get_attr_safe(order, "scale2_qty", 0.0) or 0.0)
#         scale3_tag = get_attr_safe(order, "scale3") or ""
#         scale3_qty_val = float(get_attr_safe(order, "scale3_qty", 0.0) or 0.0)
        
#         print(f"📊 [SAP Payload] Byproduct scales: scale1={scale1_tag} ({scale1_qty_val:.2f}), scale2={scale2_tag} ({scale2_qty_val:.2f}), scale3={scale3_tag} ({scale3_qty_val:.2f})")
        
#         order_data = {
#             'po_number': order.order_id,
#             'confirmed_weight': confirm_qty,  # ✅ Only remaining
#             'last_confirmed_qty': 0,  # For SAP reference
#             'total_qty': target,
#             'material': get_attr_safe(order, "material"),
#             'version': get_attr_safe(order, "version"),
#             'material_desc': get_attr_safe(order, "material_desc"),
#             'batch': get_attr_safe(order, "batch"),
#             'uom': uom,
#             'plant': get_attr_safe(order, "plant"),
#             'created_at': get_attr_safe(order, "created_at"),
#             'shift': current_shift,
#             'validation_method': 'Automatic',
#             'confirmed_text': f'Auto: {"FINAL " if is_final_confirmation else ""}Shift {current_shift} End - {confirm_qty:.2f} {uom}',
#             'scrap': get_attr_safe(order, "scrap", 0) or 0,
#             # ✅ CRITICAL: Always include byproduct scales (even if empty/None)
#             # This ensures they appear in SAP payload for mid-shift and end-shift confirmations
#             'scale1': scale1_tag,
#             'scale1_qty': scale1_qty_val,
#             'scale2': scale2_tag,
#             'scale2_qty': scale2_qty_val,
#             'scale3': scale3_tag,
#             'scale3_qty': scale3_qty_val,
#             'final_confirmation': "X" if is_final_confirmation else ""
#         }
        
#         # ================================================================
#         # ✅ SEND TO SAP
#         # ================================================================
#         sap_result = sap_service.push_confirmation([order_data], 'online')
        
#         if sap_result.get('success'):
#             # ================================================================
#             # ✅ UPDATE DATABASE (DON'T touch confirmed_qty!)
#             # ================================================================
            
#             # Update confirmed_shift_X to accumulate what was sent
#             new_shift_confirmed = already_confirmed_for_shift + confirm_qty
#             set_attr_safe(order, confirmed_field, new_shift_confirmed)
            
#             print(f"✅ Updated {confirmed_field} from {already_confirmed_for_shift:.2f} to {new_shift_confirmed:.2f}")
            
#             # ✅ DON'T update confirmed_qty - auto-validator handles it
#             # ✅ DON'T update last_confirmed_qty - we don't use it anymore
            
#             # Handle overflow (if shift produced more than target)
#             overflow = max(0, new_total_confirmed_to_sap - target)
#             if overflow > 0:
#                 set_attr_safe(order, "overflow_weight", overflow)
#                 print(f"⚠️ Overflow: {overflow:.2f} {uom}")
            
#             # ================================================================
#             # ✅ CHECK ORDER COMPLETION (based on SAP confirmations)
#             # ================================================================
#             if new_total_confirmed_to_sap >= target:
#                 set_attr_safe(order, "is_target_reached", True)
#                 set_attr_safe(order, "status", "Validated")
#                 set_attr_safe(order, "validation_method", "Automatic")
#                 set_attr_safe(order, "is_final_sent", True)
                
#                 print(f"✅ ORDER COMPLETE: {new_total_confirmed_to_sap:.2f}/{target:.2f} {uom}")
#                 print(f"   Shift A: {confirmed_shift_a:.2f}, Shift B: {confirmed_shift_b:.2f}, Shift C: {confirmed_shift_c:.2f}")
                
#                 return {
#                     "success": True,
#                     "order_complete": True,
#                     "confirmed_qty": confirm_qty,
#                     "message": f"Order completed in shift {current_shift}"
#                 }
#             else:
#                 # Order not complete - get next shift
#                 plant = get_attr_safe(order, "plant", "3130")
#                 department = "MILLING" if order_type == "MILLING" else "PACKING"
                
#                 with _db_session() as db:
#                     next_shift_row = get_next_shift(current_shift, plant, department, db)
#                     next_shift = next_shift_row.shift_code if next_shift_row else "A"
                
#                 print(f"✅ Shift {current_shift} ended. Confirmed {confirm_qty:.2f} {uom}. Next: {next_shift}")
#                 print(f"   Progress: {new_total_confirmed_to_sap:.2f}/{target:.2f} {uom} ({(new_total_confirmed_to_sap/target*100):.1f}%)")
                
#                 return {
#                     "success": True,
#                     "order_complete": False,
#                     "next_shift": next_shift,
#                     "confirmed_qty": confirm_qty,
#                     "message": f"Shift {current_shift} completed"
#                 }
#         else:
#             error_msg = sap_result.get('message', 'Unknown SAP error')
#             print(f"❌ SAP Failed: {error_msg}")
#             return {
#                 "success": False,
#                 "message": f"SAP confirmation failed: {error_msg}",
#                 "confirmed_qty": 0.0,
#                 "order_complete": False
#             }
    
#     except Exception as e:
#         print(f"❌ Error ending shift: {e}")
#         import traceback
#         traceback.print_exc()
#         return {
#             "success": False,
#             "message": str(e),
#             "confirmed_qty": 0.0,
#             "order_complete": False
#         }

def end_shift_and_confirm(order, current_shift: str, classification: Dict, sap_service, force_final: bool = False) -> Dict[str, Any]:
    """
    End shift and send remaining production to SAP.
    
    CRITICAL RULES:
    1. NEVER modify weight_shift_X (only READ it)
    2. Only send ACTUAL production (not target)
    3. Track confirmations in confirmed_shift_X
    """
    try:
        po_number = get_attr_safe(order, "order_id", "UNKNOWN")
        
        # ================================================================
        # ✅ DETERMINE ORDER TYPE AND TARGET
        # ================================================================
        order_type = classification["order_type"]
        if order_type == "MILLING":
            target = float(get_attr_safe(order, "expected_weight") or get_attr_safe(order, "quantity") or 0.0)
            uom = "KG"
        else:
            # ✅ CRITICAL FIX (Jan 23, 2026): PACKING quantity is already in BAGS
            # Only SCADA delta needs conversion (pallets → bags), NOT the target
            target = float(get_attr_safe(order, "quantity") or 0.0)
            uom = "BAG"
        
        # ================================================================
        # ✅ READ EXISTING SHIFT PRODUCTION (DON'T MODIFY!)
        # ================================================================
        shift_field = f"weight_shift_{current_shift.lower()}"
        total_shift_production = float(get_attr_safe(order, shift_field, 0.0) or 0.0)
        
        # ❌ DELETE ANY CODE THAT DOES THIS:
        # set_attr_safe(order, shift_field, anything)  # NEVER MODIFY weight_shift_X here!
        
        # ✅ Just mark shift end time
        set_attr_safe(order, "shift_end_time", datetime.now())
        
        print(f"✅ [{po_number}] Shift {current_shift} actual production = {total_shift_production:.2f} {uom}")
        print(f"   Target = {target:.2f} {uom}")
        
        # ❌ CRITICAL CHECK: Make sure we're using ACTUAL production, not target!
        if total_shift_production == target and total_shift_production > 0:
            print(f"⚠️ [{po_number}] WARNING: Shift production exactly equals target!")
            print(f"   This might indicate a bug where target is being used instead of actual production")
            print(f"   Verify weight_shift_{current_shift.lower()} in database is correct")
        
        # ================================================================
        # ✅ CHECK REMAINING PRODUCTION (deduplication)
        # ================================================================
        confirmed_field = f"confirmed_shift_{current_shift.lower()}"
        already_confirmed_for_shift = float(get_attr_safe(order, confirmed_field, 0.0) or 0.0)
        
        # ✅ CRITICAL: Use ACTUAL production, not target!
        remaining_shift_production = total_shift_production - already_confirmed_for_shift
        
        print(f"   Total shift production: {total_shift_production:.2f}")
        print(f"   Already confirmed: {already_confirmed_for_shift:.2f}")
        print(f"   Remaining to send: {remaining_shift_production:.2f}")
        
        # ================================================================
        # ✅ CALCULATE TOTAL CONFIRMED TO SAP (from all shifts)
        # ================================================================
        confirmed_shift_a = float(get_attr_safe(order, "confirmed_shift_a", 0.0) or 0.0)
        confirmed_shift_b = float(get_attr_safe(order, "confirmed_shift_b", 0.0) or 0.0)
        confirmed_shift_c = float(get_attr_safe(order, "confirmed_shift_c", 0.0) or 0.0)
        
        total_confirmed_to_sap = confirmed_shift_a + confirmed_shift_b + confirmed_shift_c
        
        print(f"📊 Total confirmed to SAP: {total_confirmed_to_sap:.2f} {uom}")
        print(f"   Shift A: {confirmed_shift_a:.2f}, Shift B: {confirmed_shift_b:.2f}, Shift C: {confirmed_shift_c:.2f}")
        
        # ================================================================
        # ✅ CALCULATE REMAINING TO TARGET
        # ================================================================
        remaining_to_target = target - total_confirmed_to_sap
        
        # ================================================================
        # ✅ DETERMINE CONFIRMATION QUANTITY
        # Use ACTUAL production (remaining_shift_production), not target!
        # ================================================================
        # ✅ Check if order is validated - only send final confirmation for validated orders
        order_status = get_attr_safe(order, "status", "").strip()
        is_validated = order_status in ("Validated", "Completed")
        
        if force_final:
            # ✅ For validated orders: send remaining to target (target - already_sent)
            # Example: target=500, already_sent=160, send=340
            if remaining_to_target > 0:
                # ✅ CRITICAL: For validated orders, send remaining_to_target directly
                # Don't limit by shift production - validated orders may have been validated mid-shift
                confirm_qty = remaining_to_target
                print(f"🔔 FORCE FINAL (Validated Order): Sending remaining {confirm_qty:.2f} {uom} (target={target:.2f}, already_sent={total_confirmed_to_sap:.2f})")
            else:
                confirm_qty = 0.0
                print(f"🔔 FORCE FINAL: Already at target, sending 0 with final flag")
        elif remaining_shift_production <= 0:
            if remaining_to_target <= 0:
                # Already confirmed
                print(f"✅ Shift {current_shift} fully confirmed")
                plant = get_attr_safe(order, "plant", "3130")
                department = "MILLING" if order_type == "MILLING" else "PACKING"
                with _db_session() as db:
                    next_shift_row = get_next_shift(current_shift, plant, department, db)
                    next_shift = next_shift_row.shift_code if next_shift_row else "A"
                return {
                    "success": True,
                    "order_complete": False,
                    "next_shift": next_shift,
                    "confirmed_qty": 0.0,
                    "message": f"Shift {current_shift} already confirmed"
                }
            else:
                # Shift confirmed but order not complete
                # ❌ DON'T send remaining_to_target if there's no production!
                confirm_qty = 0.0
                print(f"⚠️ Shift {current_shift} has no remaining production")
        else:
            # ✅ CRITICAL: Send ACTUAL production, capped at remaining target
            confirm_qty = min(remaining_shift_production, remaining_to_target)
            print(f"📤 Normal confirmation: {confirm_qty:.2f} {uom}")
            print(f"   (min of remaining_production={remaining_shift_production:.2f}, remaining_target={remaining_to_target:.2f})")
        
        # ✅ Check if there's anything to send
        if confirm_qty <= 0 and not force_final:
            print(f"⚠️ No production to confirm in Shift {current_shift}")
            plant = get_attr_safe(order, "plant", "3130")
            department = "MILLING" if order_type == "MILLING" else "PACKING"
            with _db_session() as db:
                next_shift_row = get_next_shift(current_shift, plant, department, db)
                next_shift = next_shift_row.shift_code if next_shift_row else "A"
            return {
                "success": True,
                "order_complete": False,
                "next_shift": next_shift,
                "confirmed_qty": 0.0,
                "message": "No new confirmation needed"
            }
        
        # ================================================================
        # ✅ BUILD SAP PAYLOAD
        # ================================================================
        # ✅ CRITICAL FIX: Cap confirm_qty to never exceed target (exclude overflow)
        # Ensure the total confirmed (including this confirmation) never exceeds target
        # Overflow should NOT be included in confirmations
        remaining_to_target_before_send = max(0, target - total_confirmed_to_sap)
        confirm_qty_capped = min(confirm_qty, remaining_to_target_before_send)
        
        # ✅ CRITICAL: Never send overflow - only send up to target
        if confirm_qty_capped < confirm_qty:
            print(f"⚠️ CAPPED confirm_qty from {confirm_qty:.2f} to {confirm_qty_capped:.2f} to not exceed target {target:.2f} (excluding overflow)")
            print(f"   (total_confirmed_to_sap={total_confirmed_to_sap:.2f}, remaining={remaining_to_target_before_send:.2f})")
        
        # ✅ Double-check: Ensure we never send more than remaining to target
        if confirm_qty_capped > remaining_to_target_before_send:
            confirm_qty_capped = remaining_to_target_before_send
            print(f"🔒 FORCE CAPPED: confirm_qty limited to remaining_to_target: {confirm_qty_capped:.2f}")
        
        new_total_confirmed_to_sap = total_confirmed_to_sap + confirm_qty_capped
        # ✅ CRITICAL: Only mark as final confirmation if:
        # 1. force_final=True (validated order), OR
        # 2. Order status is "Validated" AND we're reaching target, OR
        # 3. We're reaching/exceeding target
        is_final_confirmation = force_final or (is_validated and new_total_confirmed_to_sap >= target) or (new_total_confirmed_to_sap >= target)
        
        print(f"📤 Sending to SAP: {confirm_qty_capped:.2f} {uom}")
        print(f"   (Shift total: {total_shift_production:.2f}, Already sent: {already_confirmed_for_shift:.2f})")
        print(f"🔍 Final check: {new_total_confirmed_to_sap:.2f} >= {target:.2f} = {is_final_confirmation} (force_final={force_final})")
        
        # Read scale values
        scale1_tag = get_attr_safe(order, "scale1") or ""
        scale1_qty_val = float(get_attr_safe(order, "scale1_qty", 0.0) or 0.0)
        scale2_tag = get_attr_safe(order, "scale2") or ""
        scale2_qty_val = float(get_attr_safe(order, "scale2_qty", 0.0) or 0.0)
        scale3_tag = get_attr_safe(order, "scale3") or ""
        scale3_qty_val = float(get_attr_safe(order, "scale3_qty", 0.0) or 0.0)
        
        print(f"📊 [SAP Payload] Byproduct scales: scale1={scale1_tag} ({scale1_qty_val:.2f}), scale2={scale2_tag} ({scale2_qty_val:.2f}), scale3={scale3_tag} ({scale3_qty_val:.2f})")
        
        order_data = {
            'po_number': order.order_id,
            'confirmed_weight': confirm_qty_capped,
            'last_confirmed_qty': 0,
            'total_qty': target,
            'material': get_attr_safe(order, "material"),
            'version': get_attr_safe(order, "version"),
            'material_desc': get_attr_safe(order, "material_desc"),
            'batch': get_attr_safe(order, "batch"),
            'uom': uom,
            'plant': get_attr_safe(order, "plant"),
            'created_at': get_attr_safe(order, "created_at"),
            'shift': current_shift,
            'validation_method': 'Automatic',
            'confirmed_text': f'Auto: {"FINAL " if is_final_confirmation else ""}Shift {current_shift} End - {confirm_qty_capped:.2f} {uom}',
            'scrap': get_attr_safe(order, "scrap", 0) or 0,
            'scale1': scale1_tag,
            'scale1_qty': scale1_qty_val,
            'scale2': scale2_tag,
            'scale2_qty': scale2_qty_val,
            'scale3': scale3_tag,
            'scale3_qty': scale3_qty_val,
            'final_confirmation': "X" if is_final_confirmation else ""
        }
        
        # ================================================================
        # ✅ CHECK VPN CONNECTION BEFORE SAP CALL
        # Skip VPN check if using mock mode (demo server)
        # ================================================================
        # ✅ Read mock mode from database settings (not environment variable)
        try:
            from models.system_settings import is_mock_sap_enabled
            mock_mode = is_mock_sap_enabled()
        except Exception:
            mock_mode = True  # Default to mock mode for safety
        
        if mock_mode:
            # Mock mode: Skip VPN check, always send to demo server
            vpn_status = {"connected": True, "message": "Mock mode - using demo server"}
        else:
            # Real SAP mode: Check VPN connection
            vpn_status = check_vpn_connection()
        
        if not vpn_status.get("connected"):
            # VPN is disconnected - store for offline confirmation
            order_status = (get_attr_safe(order, "status") or "").upper()
            print(f"⚠️ [{po_number}] VPN disconnected during shift change - storing for offline confirmation (status: {order_status})")
            
            try:
                with _db_session() as offline_db:
                    import json
                    from sqlalchemy import func
                    
                    # ✅ CRITICAL FIX: Check for existing pending offline confirmation for this order
                    # If exists, UPDATE it by accumulating values instead of creating duplicates
                    po_num_stripped = str(order.order_id).lstrip('0')
                    existing_offline = offline_db.query(OfflineConfirmation).filter(
                        func.ltrim(OfflineConfirmation.order_id, '0') == po_num_stripped,
                        OfflineConfirmation.status == 'pending'
                    ).first()
                    
                    if existing_offline:
                        # ✅ UPDATE existing record - accumulate values
                        old_weight = existing_offline.confirmed_weight or 0
                        accumulated_weight = old_weight + confirm_qty_capped
                        existing_offline.confirmed_weight = accumulated_weight
                        existing_offline.scrap = (existing_offline.scrap or 0) + float(get_attr_safe(order, "scrap", 0) or 0)
                        # Update SAP payload with accumulated values
                        order_data['confirmed_weight'] = accumulated_weight
                        existing_offline.sap_payload = order_data
                        # ✅ Keep existing confirmed_text - don't overwrite user's manual notes
                        # existing_offline.confirmed_text is preserved as-is
                        offline_db.commit()
                        print(f"✅ [{po_number}] UPDATED existing offline confirmation: {old_weight:.2f} + {confirm_qty_capped:.2f} = {accumulated_weight:.2f}")
                    else:
                        # Create new offline record
                        offline_record = OfflineConfirmation(
                            order_id=order.order_id,
                            process_order_id=order.id,
                            material=get_attr_safe(order, "material"),
                            version=get_attr_safe(order, "version"),
                            confirmed_weight=confirm_qty_capped,
                            total_qty=target,
                            uom=uom,
                            plant=get_attr_safe(order, "plant"),
                            batch=get_attr_safe(order, "batch") or "",
                            shift=current_shift,
                            scrap=float(get_attr_safe(order, "scrap", 0) or 0),
                            confirmed_text=order_data.get('confirmed_text', ''),
                            sap_payload=order_data,
                            validation_method='Automatic',
                            status='pending'
                        )
                        offline_db.add(offline_record)
                        offline_db.commit()
                        print(f"✅ [{po_number}] Created NEW offline confirmation: {confirm_qty_capped:.2f}")
            except Exception as offline_err:
                print(f"❌ [{po_number}] Failed to store offline confirmation: {offline_err}")
                import traceback
                traceback.print_exc()
            
            # Return success with offline flag - don't fail the shift change
            return {
                "success": True,
                "offline_queued": True,
                "order_complete": False,
                "confirmed_qty": confirm_qty_capped,
                "message": f"VPN disconnected - confirmation queued for offline send ({confirm_qty_capped:.2f} {uom})"
            }
        
        # ================================================================
        # ✅ SEND TO SAP (VPN is connected)
        # ================================================================
        sap_result = sap_service.push_confirmation([order_data], 'online')
        
        if sap_result.get('success'):
            # ================================================================
            # ✅ UPDATE DATABASE (Only confirmed_shift_X, NOT weight_shift_X)
            # ================================================================
            # ✅ Use capped value for database update too
            new_shift_confirmed = already_confirmed_for_shift + confirm_qty_capped
            set_attr_safe(order, confirmed_field, new_shift_confirmed)
            
            # ✅ Update last_confirmed_qty with total of all shift confirmations
            # This represents what has been confirmed to SAP
            confirmed_shift_a_after = float(get_attr_safe(order, "confirmed_shift_a", 0.0) or 0.0)
            confirmed_shift_b_after = float(get_attr_safe(order, "confirmed_shift_b", 0.0) or 0.0)
            confirmed_shift_c_after = float(get_attr_safe(order, "confirmed_shift_c", 0.0) or 0.0)
            total_confirmed_after = confirmed_shift_a_after + confirmed_shift_b_after + confirmed_shift_c_after
            set_attr_safe(order, "last_confirmed_qty", total_confirmed_after)
            
            print(f"✅ Updated {confirmed_field} from {already_confirmed_for_shift:.2f} to {new_shift_confirmed:.2f}")
            print(f"📊 Updated last_confirmed_qty: {total_confirmed_after:.2f} (A={confirmed_shift_a_after:.2f}, B={confirmed_shift_b_after:.2f}, C={confirmed_shift_c_after:.2f})")
            
            # ✅ OVERFLOW STORAGE: Store overflow for transfer to next order of same type
            # ✅ DISABLED FOR PACKING: Packing orders do NOT carry overflow bags to next order
            overflow = max(0, new_total_confirmed_to_sap - target)
            if overflow > 0 and order_type != "PACKING":
                set_attr_safe(order, "overflow_weight", overflow)
                print(f"💾 [SAP] Stored overflow: {overflow:.2f} {uom} for next {order_type} order")
            elif overflow > 0 and order_type == "PACKING":
                print(f"⏭️ [SAP] PACKING overflow {overflow:.2f} {uom} discarded (not carried to next order)")
            
            # ================================================================
            # ✅ CHECK ORDER COMPLETION
            # ================================================================
            if new_total_confirmed_to_sap >= target:
                set_attr_safe(order, "is_target_reached", True)
                # ✅ Feb 5, 2026: Use "Completed" when order reaches 100% tracking
                # "Validated" is reserved for after successful SAP confirmation
                set_attr_safe(order, "status", "Completed")
                set_attr_safe(order, "validation_method", "Automatic")
                set_attr_safe(order, "is_final_sent", True)
                # ✅ FIX (Jan 23, 2026): Set confirmed_qty to target when order is completed
                set_attr_safe(order, "confirmed_qty", target)
                
                print(f"✅ ORDER COMPLETE: {new_total_confirmed_to_sap:.2f}/{target:.2f} {uom}")
                
                return {
                    "success": True,
                    "order_complete": True,
                    "confirmed_qty": confirm_qty,
                    "message": f"Order completed in shift {current_shift}"
                }
            else:
                # Get next shift
                plant = get_attr_safe(order, "plant", "3130")
                department = "MILLING" if order_type == "MILLING" else "PACKING"
                
                with _db_session() as db:
                    next_shift_row = get_next_shift(current_shift, plant, department, db)
                    next_shift = next_shift_row.shift_code if next_shift_row else "A"
                
                print(f"✅ Shift {current_shift} ended. Confirmed {confirm_qty:.2f} {uom}. Next: {next_shift}")
                print(f"   Progress: {new_total_confirmed_to_sap:.2f}/{target:.2f} {uom}")
                
                return {
                    "success": True,
                    "order_complete": False,
                    "next_shift": next_shift,
                    "confirmed_qty": confirm_qty,
                    "message": f"Shift {current_shift} completed"
                }
        else:
            error_msg = sap_result.get('message', 'Unknown SAP error')
            print(f"❌ SAP Failed: {error_msg}")
            return {
                "success": False,
                "message": f"SAP confirmation failed: {error_msg}",
                "confirmed_qty": 0.0,
                "order_complete": False
            }
    
    except Exception as e:
        po_number = get_attr_safe(order, "order_id", "UNKNOWN")
        print(f"❌ [{po_number}] Error ending shift: {e}")
        import traceback
        traceback.print_exc()
        return {
            "success": False,
            "message": str(e),
            "confirmed_qty": 0.0,
            "order_complete": False
        }

def init_and_start_order_worker(db, order, classification, is_manual_start=False):
    """
    FINAL: Always reset SCADA equipment baseline columns on (re)start.
    Preserves confirmed_qty. Does NOT skip baseline reset just because shift baselines exist.
    
    Enhanced with Scale Locking (Dec 12, 2025):
    - Registers order version for duplicate detection
    - Locks scales with priority-based conflict resolution
    - Adds order to queue for visibility
    
    Args:
        is_manual_start: True if started via manual Start button, False if started via auto-validation
    """

    po_number = order.order_id
    order_type = classification.get("order_type")
    version = get_attr_safe(order, "version", "").upper().strip()
    priority = get_attr_safe(order, "hercules_priority", 100) or get_attr_safe(order, "priority", 100) or 100
    equipment = classification.get("equipment", []) or []

    # =============================================================================
    # SCALE LOCKING: Register order and lock scales with priority
    # =============================================================================
    print(f"🔐 [{po_number}] Registering order for scale locking: type={order_type}, version={version}, priority={priority}")
    
    # Register order version for duplicate detection
    if version and order_type:
        register_order_version(po_number, version, order_type)
    
    # Add to queue with full details
    add_to_queue(po_number, equipment, priority, version, order_type)
    
    # Lock scales with priority checking
    if equipment:
        has_conflict, locked_scales, conflict_details, preempted_orders = lock_scales(
            po_number, equipment, priority, version, order_type
        )
        
        # ✅ Handle preempted orders - signal them to pause
        if preempted_orders:
            print(f"⚠️ [{po_number}] Higher priority - preempting orders: {preempted_orders}")
            for preempted_po in preempted_orders:
                # Signal the preempted order's worker to stop
                set_order_validation_state(preempted_po, {"isrunning": False})
                print(f"🛑 [{po_number}] Signaled order {preempted_po} to stop (preempted by higher priority)")
                # ✅ C31-T29: Also update database status to Pending (was only in-memory, UI showed InProgress)
                preempted_order = db.query(ProcessOrder).filter(ProcessOrder.order_id == preempted_po).first()
                if preempted_order:
                    set_attr_safe(preempted_order, "status", "Pending")
                    db.add(preempted_order)
                    db.commit()
                    print(f"📋 [{po_number}] Set preempted order {preempted_po} status to Pending in database")
        
        if has_conflict:
            print(f"⚠️ [{po_number}] Scale conflict detected but proceeding (partial lock allowed)")
            print(f"   Locked: {locked_scales}")
            print(f"   Conflicts: {conflict_details}")
        else:
            print(f"✅ [{po_number}] All {len(locked_scales)} scales locked successfully: {locked_scales}")
    
    # Mark order as RUNNING in queue
    set_order_running(po_number)

    # --- 1. Preserve confirmed_qty AND byproduct quantities (never reset) ---
    db.refresh(order)
    confirmed_qty_so_far = float(order.confirmed_qty if hasattr(order, 'confirmed_qty') and order.confirmed_qty is not None else 0.0)
    set_attr_safe(order, "confirmed_qty", confirmed_qty_so_far)
    print(f"✅ [{po_number}] Preserved confirmed_qty on (re)start: {confirmed_qty_so_far:.2f}")
    print(f"🔧🔧🔧 [BYPRODUCT-FIX-DEC21] init_and_start_order_worker executing for {po_number}")
    
    # ✅ CRITICAL FIX: Also preserve byproduct quantities (like confirmed_qty, never reset)
    # Read them from database NOW before any modifications happen
    preserved_scale1_qty = float(get_attr_safe(order, "scale1_qty", 0.0) or 0.0)
    preserved_scale2_qty = float(get_attr_safe(order, "scale2_qty", 0.0) or 0.0)
    preserved_scale3_qty = float(get_attr_safe(order, "scale3_qty", 0.0) or 0.0)
    if preserved_scale1_qty > 0 or preserved_scale2_qty > 0 or preserved_scale3_qty > 0:
        print(f"✅ [{po_number}] Preserved byproduct quantities on (re)start:")
        print(f"   scale1_qty: {preserved_scale1_qty:.4f}")
        print(f"   scale2_qty: {preserved_scale2_qty:.4f}")
        print(f"   scale3_qty: {preserved_scale3_qty:.4f}")
    
    # =============================================================================
    # ✅ DEFINE TARGET before overflow handling (Jan 22, 2026)
    # Need target value to cap overflow at target quantity
    # ✅ CRITICAL FIX (Jan 23, 2026): PACKING quantity is already in BAGS
    # =============================================================================
    if order_type == "MILLING":
        target = float(get_attr_safe(order, "expected_weight") or get_attr_safe(order, "quantity") or 0.0)
    else:
        # PACKING: quantity is already in BAGS - do NOT convert
        target = float(get_attr_safe(order, "quantity") or 0.0)
        print(f"🔍 [{po_number}] PACKING target: {target} bags (quantity already in bags)")
    
    # =============================================================================
    # ✅ OVERFLOW APPLICATION: Transfer overflow from DIFFERENT validated orders of same type
    # MILLING overflow → next MILLING order only
    # ✅ DISABLED FOR PACKING: Packing orders do NOT receive overflow bags from previous orders
    # =============================================================================
    overflow_applied = 0.0
    temp_overflow_for_shift = 0.0
    
    # ✅ Only apply overflow for MILLING orders (PACKING does not carry overflow)
    if order_type != "PACKING":
        # Find overflow from validated orders of the SAME TYPE (but different PO number)
        # ✅ C31-T27: Only transfer overflow from AUTO-validated orders, not manual
        # Manual validation = user controls, no overflow transfer
        # Auto validation = system handles overflow transfer automatically
        print(f"🔍 [{po_number}] Searching for overflow from validated {order_type} orders...")
        
        completed_with_overflow_list = db.query(ProcessOrder).filter(
            ProcessOrder.status.in_(["Validated", "Completed"]),
            ProcessOrder.validation_method == "Automatic",  # ✅ C31-T27: Only auto-validated orders
            ProcessOrder.overflow_weight > 0,
            ProcessOrder.order_type == order_type,  # CRITICAL: Match by order type
            ProcessOrder.order_id != po_number  # CRITICAL: Don't apply overflow from same order
        ).order_by(ProcessOrder.id.desc()).all()
        
        print(f"🔍 [{po_number}] Found {len(completed_with_overflow_list)} validated {order_type} orders with overflow")
        for candidate in completed_with_overflow_list:
            print(f"   📋 {candidate.order_id}: overflow={get_attr_safe(candidate, 'overflow_weight', 0):.2f}, validation_method={get_attr_safe(candidate, 'validation_method', 'UNKNOWN')}")
        
        completed_with_overflow = None
        for candidate in completed_with_overflow_list:
            # First match by type is sufficient
            completed_with_overflow = candidate
            break
        
        if completed_with_overflow:
            overflow_weight = float(get_attr_safe(completed_with_overflow, "overflow_weight", 0.0) or 0.0)
            if overflow_weight > 0:
                overflow_applied = overflow_weight
                
                # ✅ Apply overflow to confirmed_qty
                # Update the confirmed_qty_so_far variable so it's reflected in later logic
                # ✅ CRITICAL FIX (Jan 22, 2026): Cap confirmed_qty at target
                # Overflow can be larger than target, but confirmed_qty must NEVER exceed target
                confirmed_qty_capped = min(overflow_applied, target) if target > 0 else overflow_applied
                confirmed_qty_so_far = confirmed_qty_capped
                set_attr_safe(order, "confirmed_qty", confirmed_qty_capped)
                
                print(f"🌊 [{po_number}] Found overflow from order {completed_with_overflow.order_id}: {overflow_weight:.2f}")
                if confirmed_qty_capped < overflow_applied:
                    print(f"🌊 [{po_number}] Overflow ({overflow_applied:.2f}) exceeds target ({target:.2f}), capping confirmed_qty to {confirmed_qty_capped:.2f}")
                print(f"🌊 [{po_number}] Applied overflow to confirmed_qty: {confirmed_qty_capped:.2f}")
                
                # ✅ ALSO apply overflow to current shift's weight column
                # We need to know which shift we're in first, so this will be done after shift detection
                # Store capped overflow for later use (shift weight should also not exceed target)
                # ✅ CRITICAL FIX (Jan 22, 2026): Use capped value for shift weight too
                temp_overflow_for_shift = confirmed_qty_capped
                
                # Clear overflow from source order
                set_attr_safe(completed_with_overflow, "overflow_weight", 0.0)
                
                # ✅ CRITICAL: Add BOTH orders to session before commit
                db.add(order)  # Target order with overflow applied
                db.add(completed_with_overflow)  # Source order with overflow cleared
                db.commit()
                db.refresh(order)  # Refresh to ensure changes are persisted
                
                print(f"✅ [{po_number}] Applied main product overflow {overflow_applied:.2f} from {completed_with_overflow.order_id} (same type: {order_type})")
        else:
            print(f"✅ [{po_number}] No main product overflow found from other {order_type} orders")
    else:
        # PACKING orders do not carry over overflow
        print(f"⏭️ [{po_number}] PACKING order - overflow carry-over disabled (starting fresh)")
    
    # 💥 CRITICAL FIX: CLEAR ALL OLD SHIFT BASELINES FOR NEW ORDER
    # This ensures worker uses fresh baselines, not old shift baselines from previous order
    print(f"🧹 [{po_number}] Clearing ALL old shift baselines for fresh start...")
    for s in ["a", "b", "c"]:
        set_attr_safe(order, f"baseline_shift_{s}_start", {})
        set_attr_safe(order, f"baseline_shift_{s}_time", None)
        print(f"🧹 [{po_number}] Cleared baseline_shift_{s}_start and baseline_shift_{s}_time")
    
    # ✅ CRITICAL: Commit shift baseline clearing to database immediately
    db.add(order)
    db.flush()
    db.commit()
    db.refresh(order)
    print(f"✅ [{po_number}] Shift baseline clearing committed to database")
    
    # 💥 CRITICAL FIX: CLEAR ALL PRODUCTION CACHES FOR ALL SHIFTS
    # This ensures worker starts fresh without any cached values from previous order
    # ✅ CRITICAL: ALWAYS clear cache unconditionally - use pop() to avoid KeyError
    # This ensures we remove any stale cache from deleted orders with the same PO number
    print(f"🧹 [{po_number}] Clearing ALL production caches for all shifts...")
    for s in ["a", "b", "c"]:
        cache_key = (po_number, s)
        # Use pop() with default to safely remove cache even if it doesn't exist
        old_prod_cache = _last_shift_production_cache.pop(cache_key, None)
        if old_prod_cache is not None:
            print(f"🧹 [{po_number}] Cleared _last_shift_production_cache for shift {s.upper()} (had value: {old_prod_cache:.2f})")
        old_max_cache = _max_shift_weight_cache.pop(cache_key, None)
        if old_max_cache is not None:
            print(f"🧹 [{po_number}] Cleared _max_shift_weight_cache for shift {s.upper()} (had value: {old_max_cache:.2f})")
    
    print(f"✅ [{po_number}] All shift baselines and production caches cleared for fresh start")

    # --- 2. Fetch equipment/scada baselines ---
    order_type = classification.get("order_type")
    equipment = classification.get("equipment", []) or []
    if not equipment:
        print(f"❌ [{po_number}] No equipment mapped")
        return

    # ✅ CRITICAL FIX: Reset ALL baseline columns to 0 first to ensure clean state
    # This prevents old baseline values from interfering with new order baselines
    print(f"🔄 [{po_number}] Resetting all baseline columns to 0 before capturing fresh SCADA values...")
    # PACKING: Bag counter baselines
    set_attr_safe(order, "baseline_sl601_counter", 0.0)
    set_attr_safe(order, "baseline_sl602_counter", 0.0)
    set_attr_safe(order, "baseline_sl603_counter", 0.0)
    set_attr_safe(order, "baseline_sl606_counter", 0.0)
    set_attr_safe(order, "baseline_sl607_counter", 0.0)
    # MILLING: Flour/Bran output baselines
    set_attr_safe(order, "baseline_wg101", 0.0)
    set_attr_safe(order, "baseline_wg201", 0.0)
    set_attr_safe(order, "baseline_wg202", 0.0)
    set_attr_safe(order, "baseline_wg301", 0.0)
    set_attr_safe(order, "baseline_wg302", 0.0)
    set_attr_safe(order, "baseline_wg501", 0.0)
    set_attr_safe(order, "baseline_wg502", 0.0)
    set_attr_safe(order, "baseline_wg503", 0.0)
    # WATER DOSING METER baselines
    set_attr_safe(order, "baseline_dm101", 0.0)
    set_attr_safe(order, "baseline_dm102", 0.0)
    set_attr_safe(order, "baseline_dm201", 0.0)
    set_attr_safe(order, "baseline_dm202", 0.0)
    set_attr_safe(order, "baseline_dm203", 0.0)
    
    # ✅ CRITICAL: Flush baseline reset to database BEFORE capturing fresh SCADA values
    db.add(order)
    db.flush()
    
    # ✅ VERIFY: Refresh order to confirm baselines were reset
    db.refresh(order)
    print(f"✅ [{po_number}] All baseline columns reset to 0 and flushed to database")

    # 💥 CRITICAL FIX: CLEAR SCADA CACHE BEFORE CAPTURING BASELINES
    # This ensures we get FRESH SCADA values, not stale cached values from previous order
    print(f"🧹 [{po_number}] Clearing SCADA cache before capturing baselines...")
    try:
        from services.scale_service import clear_scada_cache
        clear_scada_cache()
        print(f"✅ [{po_number}] SCADA cache cleared")
    except Exception as e:
        print(f"⚠️ [{po_number}] Could not clear SCADA cache: {e}")
    
    # ✅ CRITICAL: Wait after clearing cache to ensure fresh values are available
    time.sleep(0.3)

    # ✅ CRITICAL: Longer delay before capturing baselines to ensure SCADA values have settled
    # This is especially important when starting a new order immediately after previous one completes
    # The delay ensures we capture truly fresh baselines, not residual values from previous order
    # Increased delay to 1.0s to ensure previous order's SCADA values have fully cleared
    # Take multiple readings to ensure we get stable, fresh values
    print(f"⏳ [{po_number}] Waiting for SCADA values to settle before capturing baselines...")
    time.sleep(1.0)
    
    # ✅ CRITICAL: Take multiple baseline readings to ensure we get truly fresh values
    # First reading might still have residual values from previous order
    baselines_1 = capture_baseline_readings(equipment)
    time.sleep(0.5)  # Wait between readings
    baselines_2 = capture_baseline_readings(equipment)
    time.sleep(0.5)  # Wait again
    baselines_3 = capture_baseline_readings(equipment)
    
    # Use the most recent reading (should be most stable)
    baselines = baselines_3 if baselines_3 else (baselines_2 if baselines_2 else baselines_1)
    
    if not baselines:
        print(f"❌ [{po_number}] Failed to capture baselines - SCADA may be unavailable for equipment: {equipment}")
        # Release scales since we're failing
        release_scales(po_number, None)
        remove_from_queue(po_number)
        raise Exception(f"Failed to capture baselines for {order_type} order {po_number} - equipment: {equipment}")
    
    print(f"✅ [{po_number}] Captured baseline (3rd reading, most stable): {baselines}")

    # 🚦🚦🚦 ALWAYS SET MAIN BASELINE COLUMNS, UNCONDITIONALLY 🚦🚦🚦
    for tag, val in baselines.items():
        set_attr_safe(order, f"baseline_{tag.lower()}", float(val or 0.0))
    print(f"✅ [{po_number}] Main equipment baseline columns set with fresh SCADA values: {baselines}")

    # -- Shift and basic order state setup --
    plant = get_attr_safe(order, "plant", "3130")
    department = "MILLING" if order_type == "MILLING" else "PACKING"
    shift_row = get_current_shift(plant, department, db)
    current_shift = shift_row.shift_code if shift_row else "A"
    set_attr_safe(order, "current_shift", current_shift)
    set_attr_safe(order, "shift_start_time", datetime.now())
    set_attr_safe(order, "order_type", order_type)
    set_attr_safe(order, "status", "InProgress")
    # ✅ C31-T27: Set validation_method based on how order was started
    validation_method_to_set = "Manual" if is_manual_start else "Automatic"
    set_attr_safe(order, "validation_method", validation_method_to_set)
    print(f"🔧 [{po_number}] init_and_start_order_worker: is_manual_start={is_manual_start}, validation_method={validation_method_to_set}")
    
    # ✅ Apply overflow to current shift's weight column (now that we know the shift)
    # ✅ CRITICAL FIX: For brand new orders, SET (not ADD) the shift weight to overflow
    # This prevents double-counting when stale shift weight data exists
    if temp_overflow_for_shift > 0:
        shift_weight_field = f"weight_shift_{current_shift.lower()}"
        existing_shift_weight = float(get_attr_safe(order, shift_weight_field, 0.0) or 0.0)
        
        # Check if this was a brand new order (confirmed_qty_so_far was 0 before overflow applied)
        # Note: confirmed_qty_so_far is now equal to overflow_applied after line 7592
        # So we check if confirmed_qty_so_far == temp_overflow_for_shift (brand new) vs > (restarted)
        if confirmed_qty_so_far == temp_overflow_for_shift:
            # Brand new order - SET shift weight to overflow only, ignore any stale existing weight
            set_attr_safe(order, shift_weight_field, temp_overflow_for_shift)
            print(f"🌊 [{po_number}] Applied overflow to {shift_weight_field}: SET to {temp_overflow_for_shift:.2f} (brand new order, ignoring stale {existing_shift_weight:.2f})")
        else:
            # Restarted order with existing production - ADD overflow to preserved weight
            new_shift_weight = existing_shift_weight + temp_overflow_for_shift
            set_attr_safe(order, shift_weight_field, new_shift_weight)
            print(f"🌊 [{po_number}] Applied overflow to {shift_weight_field}: {existing_shift_weight:.2f} + {temp_overflow_for_shift:.2f} = {new_shift_weight:.2f} (restarted order)")
        
        # Commit the shift weight change
        db.add(order)
        db.commit()
        db.refresh(order)
        
        # ✅ Verify the shift weight was saved
        verified_shift_weight = float(get_attr_safe(order, shift_weight_field, 0.0) or 0.0)
        print(f"✅ [{po_number}] Verified {shift_weight_field} in DB: {verified_shift_weight:.2f}")

    # ✅ CRITICAL: Set FRESH shift baseline (old ones were cleared above)
    # This ensures worker uses fresh baseline, not old shift baseline from previous order
    print(f"✅ [{po_number}] Setting FRESH shift baseline for shift {current_shift.upper()}: {baselines}")
    set_attr_safe(order, f"baseline_shift_{current_shift.lower()}_start", baselines)
    set_attr_safe(order, f"baseline_shift_{current_shift.lower()}_time", datetime.now())
    
    # ✅ CRITICAL: Commit shift baseline immediately to ensure it's persisted before worker starts
    db.add(order)
    db.flush()
    db.commit()
    db.refresh(order)
    print(f"✅ [{po_number}] Fresh shift baseline committed to database")
    
    # ✅ CRITICAL FIX: For brand new orders, update shift baseline to current SCADA immediately
    # This absorbs any timing delta between baseline capture and worker start
    # Do this immediately at order start, not wait for first worker cycle
    if confirmed_qty_so_far == 0.0:
        # Longer delay to let SCADA values fully settle after baseline capture
        # This ensures we get truly current values, not residual from previous order
        # Increased to 1.0s to ensure SCADA values have fully settled
        print(f"⏳ [{po_number}] Waiting for SCADA values to settle before final baseline update...")
        time.sleep(1.0)
        # Get current SCADA readings to update baseline (absorbs timing delta)
        # Take multiple readings to ensure we get stable, fresh values
        current_scada_for_baseline_1 = get_multiple_scada_readings(equipment)
        time.sleep(0.5)  # Delay between readings
        current_scada_for_baseline_2 = get_multiple_scada_readings(equipment)
        time.sleep(0.5)  # Delay again
        current_scada_for_baseline_3 = get_multiple_scada_readings(equipment)
        # Use the most recent reading (should be most stable and fresh)
        current_scada_for_baseline = current_scada_for_baseline_3 if current_scada_for_baseline_3 else (current_scada_for_baseline_2 if current_scada_for_baseline_2 else current_scada_for_baseline_1)
        if current_scada_for_baseline:
            # Extract current values (floats) from SCADA readings dict
            updated_baseline_dict = {}
            for tag in equipment:
                if tag in current_scada_for_baseline:
                    reading = current_scada_for_baseline[tag]
                    if isinstance(reading, dict):
                        current_val = float(reading.get('current', 0.0) or 0.0)
                    else:
                        current_val = float(reading or 0.0)
                    
                    # ✅ CRITICAL: For brand new orders, ALWAYS update baseline to current SCADA
                    # This absorbs any timing delta, regardless of how high current is
                    # The only exception is if current is suspiciously high (10x+) which indicates it's definitely from previous order
                    initial_baseline = float(baselines.get(tag, 0.0) or 0.0)
                    if initial_baseline > 0.0 and current_val > initial_baseline * 10.0:
                        # Current value is extremely high (10x+) - definitely from previous order
                        # Use initial baseline instead to avoid false deltas
                        print(f"⚠️ [{po_number}] {tag}: Current SCADA ({current_val:.2f}) is extremely high vs initial baseline ({initial_baseline:.2f}) - using initial baseline to avoid false delta")
                        updated_baseline_dict[tag] = initial_baseline
                    else:
                        # Always use current SCADA value to absorb timing delta
                        # Even if it's higher than initial baseline, it's likely just a timing difference
                        updated_baseline_dict[tag] = current_val
                        if current_val != initial_baseline:
                            print(f"✅ [{po_number}] {tag}: Updating baseline from {initial_baseline:.2f} to {current_val:.2f} to absorb timing delta")
                else:
                    # Fallback to original baseline if tag not in current readings
                    updated_baseline_dict[tag] = float(baselines.get(tag, 0.0) or 0.0)
            
            # ✅ CRITICAL: Update BOTH shift baseline JSON AND individual baseline columns
            # The UI reads from individual baseline columns (baseline_wg201, etc.) for delta calculation
            # So we must update both to ensure deltas show correctly
            print(f"🔄 [{po_number}] Updating baselines - BEFORE: shift_baseline={get_attr_safe(order, f'baseline_shift_{current_shift.lower()}_start', {})}")
            for tag in equipment:
                baseline_attr = f"baseline_{tag.lower()}"
                old_val = float(get_attr_safe(order, baseline_attr, 0.0) or 0.0)
                new_val = float(updated_baseline_dict.get(tag, 0.0) or 0.0)
                if old_val != new_val:
                    print(f"   {tag}: baseline_{tag.lower()} = {old_val:.2f} → {new_val:.2f}")
            
            set_attr_safe(order, f"baseline_shift_{current_shift.lower()}_start", updated_baseline_dict)
            set_attr_safe(order, f"baseline_shift_{current_shift.lower()}_time", datetime.now())
            
            # Update individual baseline columns so UI shows correct deltas
            for tag, val in updated_baseline_dict.items():
                set_attr_safe(order, f"baseline_{tag.lower()}", float(val or 0.0))
            
            db.add(order)
            db.flush()
            db.commit()  # ✅ CRITICAL: Commit immediately so UI reads correct baselines
            db.refresh(order)
            
            # Verify the update
            print(f"✅ [{po_number}] Brand new order - updated shift baseline AND individual baseline columns to absorb timing delta")
            print(f"   AFTER commit: shift_baseline={get_attr_safe(order, f'baseline_shift_{current_shift.lower()}_start', {})}")
            for tag in equipment:
                baseline_attr = f"baseline_{tag.lower()}"
                final_val = float(get_attr_safe(order, baseline_attr, 0.0) or 0.0)
                print(f"   {tag}: baseline_{tag.lower()} = {final_val:.2f} (should match {updated_baseline_dict.get(tag, 0.0):.2f})")
    
    # ✅ CRITICAL FIX: For brand new orders, ensure shift weights start at 0
    # This prevents showing false production from timing differences between baseline capture and first worker cycle
    # Only reset if this is a brand new order (confirmed_qty = 0 and all shift weights = 0)
    if confirmed_qty_so_far == 0.0:
        # Check if shift weights are already 0 (brand new order)
        existing_weight_a = float(get_attr_safe(order, "weight_shift_a", 0.0) or 0.0)
        existing_weight_b = float(get_attr_safe(order, "weight_shift_b", 0.0) or 0.0)
        existing_weight_c = float(get_attr_safe(order, "weight_shift_c", 0.0) or 0.0)
        
        if existing_weight_a == 0.0 and existing_weight_b == 0.0 and existing_weight_c == 0.0:
            # Brand new order - explicitly set all shift weights to 0 to ensure clean start
            set_attr_safe(order, "weight_shift_a", 0.0)
            set_attr_safe(order, "weight_shift_b", 0.0)
            set_attr_safe(order, "weight_shift_c", 0.0)
            print(f"✅ [{po_number}] Brand new order - initialized all shift weights to 0")

    # -- Byproduct/Packing assignment as usual --
    if order_type == "MILLING":
        version = get_attr_safe(order, "version", "").strip().upper()
        
        # ✅ CRITICAL FIX: Check if byproduct scale TAGS are already set
        # If scale tags are set, byproducts were already captured on FIRST START - preserve them
        # This ensures byproducts are captured ONLY on first start, not on restart/pause
        existing_scale1 = get_attr_safe(order, "scale1", None)
        existing_scale2 = get_attr_safe(order, "scale2", None)
        existing_scale3 = get_attr_safe(order, "scale3", None)
        
        # ✅ CRITICAL FIX: Use PRESERVED quantities captured at function start, not current order values
        # The order object may have been modified/refreshed during setup, losing the byproduct quantities
        existing_scale1_qty = preserved_scale1_qty
        existing_scale2_qty = preserved_scale2_qty
        existing_scale3_qty = preserved_scale3_qty
        
        # ✅ FIX: Only check if byproduct TAGS are set (not quantities or confirmed_qty)
        # If tags are set, byproducts were already captured on first start - ALWAYS preserve
        byproduct_tags_already_set = (
            (existing_scale1 is not None and existing_scale1 != "") or
            (existing_scale2 is not None and existing_scale2 != "") or
            (existing_scale3 is not None and existing_scale3 != "")
        )
        
        if byproduct_tags_already_set:
            # RESTART/PAUSED scenario: Byproduct scales already configured, preserve them
            # This preserves byproducts even if confirmed_qty is 0 (order was paused before any production)
            print(f"🔒 [{po_number}] Byproduct scale tags already set - RESTORING preserved values")
            print(f"   scale1: {existing_scale1} ({existing_scale1_qty:.4f})")
            print(f"   scale2: {existing_scale2} ({existing_scale2_qty:.4f})")
            print(f"   scale3: {existing_scale3} ({existing_scale3_qty:.4f})")
            
            # ✅ CRITICAL: Actually RESTORE the preserved quantities to the order object
            # These may have been lost during the multiple commit/refresh cycles
            set_attr_safe(order, "scale1_qty", existing_scale1_qty)
            set_attr_safe(order, "scale2_qty", existing_scale2_qty)
            set_attr_safe(order, "scale3_qty", existing_scale3_qty)
            print(f"   ✅ Byproduct quantities RESTORED to order object")
            
            # ✅ CRITICAL FIX: Reset byproduct baselines to CURRENT SCADA readings on restart
            # This ensures delta only shows NEW production since restart, not total since order start
            # Without this fix, baseline was 0 (reset on pause), making delta = current = incorrect!
            from services.scale_service import get_scada_reading
            for scale_tag in [existing_scale1, existing_scale2, existing_scale3]:
                if scale_tag:
                    # Get CURRENT SCADA reading as new baseline (not old value from DB which is 0)
                    current_reading = float(get_scada_reading(scale_tag) or 0.0)
                    baselines[scale_tag] = current_reading
                    set_attr_safe(order, f"baseline_{scale_tag.lower()}", current_reading)
                    print(f"   📌 Reset baseline to CURRENT SCADA: {scale_tag} = {current_reading:.2f}")
            
            print(f"   ✅ Byproduct baselines reset to current SCADA readings for accurate delta tracking")
        else:
            # BRAND NEW order: No byproduct tags set yet - capture fresh baselines from SCADA
            print(f"🆕 [{po_number}] BRAND NEW order - no byproduct tags set - capturing baselines fresh")
            byproduct_baselines = _capture_byproduct_baselines(version, baselines, order=order)
            for tag, value in byproduct_baselines.items():
                set_attr_safe(order, f"baseline_{tag.lower()}", float(value or 0.0))
            _set_byproduct_scales(order, version, byproduct_baselines)
            print(f"✅ [{po_number}] Byproduct scales captured and set for brand new order")
    elif order_type == "PACKING":
        if equipment:
            tag = equipment[0]
            set_attr_safe(order, "scale1", tag)
            set_attr_safe(order, "scale1_qty", float(baselines.get(tag, 0.0) or 0.0))
        else:
            set_attr_safe(order, "scale1", None)
            set_attr_safe(order, "scale1_qty", 0.0)
        set_attr_safe(order, "scale2", None)
        set_attr_safe(order, "scale2_qty", 0.0)
        set_attr_safe(order, "scale3", None)
        set_attr_safe(order, "scale3_qty", 0.0)

    db.add(order)
    db.commit()
    print(f"✅ [{po_number}] All baseline columns and order state committed to DB.")
    
    # =============================================================================
    # BYPRODUCT SCALE OVERFLOW: Apply overflow for byproduct scales (scale1, scale2, scale3)
    # =============================================================================
    # When a previous order's byproduct quantity was manually overridden (reduced),
    # the difference is stored in scale_overflows table. Apply it to this order.
    # ✅ Apply overflow to BOTH MILLING and PACKING orders during auto-validation
    if order_type in ("MILLING", "PACKING"):
        scale1_tag = get_attr_safe(order, "scale1", None)
        scale2_tag = get_attr_safe(order, "scale2", None)
        scale3_tag = get_attr_safe(order, "scale3", None)
        
        byproduct_overflow_applied = []
        
        for scale_idx, scale_tag in enumerate([scale1_tag, scale2_tag, scale3_tag], 1):
            if not scale_tag:
                continue
            
            try:
                # Check for overflow in scale_overflows table
                result = db.execute(text("""
                    SELECT overflow_qty FROM scale_overflows 
                    WHERE scale_tag = :tag AND overflow_qty > 0
                """), {"tag": scale_tag}).fetchone()
                
                if result and result[0] > 0:
                    overflow_qty = float(result[0])
                    scale_qty_field = f"scale{scale_idx}_qty"
                    current_scale_qty = float(get_attr_safe(order, scale_qty_field, 0.0) or 0.0)
                    new_scale_qty = current_scale_qty + overflow_qty
                    
                    # Apply overflow to the byproduct scale quantity
                    set_attr_safe(order, scale_qty_field, new_scale_qty)
                    
                    # Clear the overflow from the table
                    db.execute(text("""
                        UPDATE scale_overflows SET overflow_qty = 0, last_updated = NOW()
                        WHERE scale_tag = :tag
                    """), {"tag": scale_tag})
                    
                    byproduct_overflow_applied.append(f"{scale_tag}: +{overflow_qty:.4f}")
                    print(f"🌊 [{po_number}] Applied byproduct overflow to scale{scale_idx} ({scale_tag}): {current_scale_qty:.4f} + {overflow_qty:.4f} = {new_scale_qty:.4f}")
            except Exception as ovf_err:
                print(f"⚠️ [{po_number}] Error applying byproduct overflow for {scale_tag}: {ovf_err}")
        
        if byproduct_overflow_applied:
            db.add(order)
            db.commit()
            db.refresh(order)
            print(f"✅ [{po_number}] Applied byproduct overflows: {', '.join(byproduct_overflow_applied)}")
        else:
            print(f"✅ [{po_number}] No byproduct overflow found for scales")

    # --- Start auto-validation worker thread, as usual ---
    # ✅ OPTIMIZED: Reduced from 1.5s to 0.5s to allow faster multi-order starts
    # The baseline is committed above, 0.5s should be sufficient for propagation
    print(f"⏳ [{po_number}] Waiting 0.5 seconds for baseline to propagate...")
    time.sleep(0.5)  # Reduced delay for faster multi-order startup
    
    print(f"✅ [{po_number}] Starting validation thread...")
    thread = threading.Thread(
        target=auto_validation_worker,
        args=(po_number, classification),
        daemon=True,
        name=f"Validation-{po_number}"
    )
    set_order_validation_state(po_number, {
        "isrunning": True,  # ✅ CRITICAL: Must match the key checked in is_order_validating()
        "thread": thread,
        "progress_pct": 0
    })
    thread.start()
    
    # ✅ CRITICAL: Verify worker thread actually started
    time.sleep(0.05)  # Reduced from 0.1s to 0.05s
    if thread.is_alive():
        print(f"✅ [{po_number}] Worker thread started and is ALIVE - will process confirmed_qty updates")
    else:
        print(f"❌ [{po_number}] CRITICAL: Worker thread started but is NOT ALIVE! This will prevent confirmed_qty updates!")
    
    # ✅ CRITICAL: Verify is_order_validating returns True
    if is_order_validating(po_number):
        print(f"✅ [{po_number}] is_order_validating() = True - worker should be running")
    else:
        print(f"❌ [{po_number}] CRITICAL: is_order_validating() = False! Worker might not be running!")
    
    print(f"✅ [{po_number}] Worker thread initialization complete")

def _schedule_next_orders_after_completion():
    """
    Called by a worker when an order completes normally.
    Uses conflict group detection to start ALL eligible orders from different scale groups.
    
    This allows multiple orders to run simultaneously if they use different scales.
    Within each conflict group, only the highest priority order runs.
    """
    print("=" * 80)
    print("🔁 [SCHEDULER] ========== SCHEDULER CALLED (CONFLICT-GROUP-AWARE) ==========")
    print("=" * 80)
    
    if not is_auto_validator_enabled() or ProcessOrder is None:
        print("🔁 [SCHEDULER] ❌ Skipping - auto-validator not enabled or ProcessOrder not available")
        print(f"   is_auto_validator_enabled()={is_auto_validator_enabled()}, ProcessOrder={ProcessOrder is not None}")
        return

    print("🔁 [SCHEDULER] ✅ Starting conflict-group-aware scheduler...")
    
    # Wait for previous order cleanup and SCADA values to settle
    print("⏳ [SCHEDULER] Waiting for previous order cleanup...")
    time.sleep(2.0)
    
    # Import scale lock service functions
    from services.scale_lock_service import (
        get_conflict_groups_for_orders,
        lock_scales,
        add_to_queue,
        set_order_running,
        release_scales
    )
    
    with _db_session() as db:
        from sqlalchemy import func
        
        # Get all InProgress orders (sorted by priority)
        inprogress_orders = db.query(ProcessOrder).filter(
            ProcessOrder.status == "InProgress"
        ).order_by(func.coalesce(ProcessOrder.hercules_priority, 999).asc()).all()
        
        # Filter to only orders with active workers
        active_inprogress = []
        for o in inprogress_orders:
            po_num = get_attr_safe(o, "order_id", "UNKNOWN")
            if is_order_validating(po_num):
                active_inprogress.append(o)
            else:
                print(f"⚠️ [SCHEDULER] Order {po_num} is InProgress but worker not running")
        
        # Get all Pending orders (sorted by priority)
        pending_orders = db.query(ProcessOrder).filter(
            ProcessOrder.status == "Pending"
        ).order_by(func.coalesce(ProcessOrder.hercules_priority, 999).asc()).all()
        
        print(f"🔁 [SCHEDULER] Found {len(active_inprogress)} InProgress (with workers), {len(pending_orders)} Pending orders")
        
        if not pending_orders:
            print("🔁 [SCHEDULER] No pending orders to start")
            print("=" * 80)
            return
        
        # Build conflict data for ALL orders (InProgress + Pending)
        orders_data_for_conflict = []
        order_classifications = {}
        order_objects = {}
        
        # Add InProgress orders
        for order in active_inprogress:
            po_number = order.order_id
            classification = classify_order(order)
            if classification.get("error"):
                continue
            
            order_classifications[po_number] = classification
            order_objects[po_number] = order
            all_scales = get_all_scales_for_order(order, classification, include_byproduct=True)
            
            orders_data_for_conflict.append({
                "order_id": po_number,
                "version": get_attr_safe(order, "version", ""),
                "scales": all_scales,
                "order_type": classification.get("order_type"),
                "priority": get_attr_safe(order, "hercules_priority", 999) or get_attr_safe(order, "priority", 999) or 999,
                "status": order.status
            })
        
        # Add Pending orders
        for order in pending_orders:
            po_number = order.order_id
            classification = classify_order(order)
            if classification.get("error"):
                print(f"❌ [SCHEDULER] Classification error for {po_number}: {classification['error']}")
                continue
            
            order_classifications[po_number] = classification
            order_objects[po_number] = order
            all_scales = get_all_scales_for_order(order, classification, include_byproduct=True)
            
            orders_data_for_conflict.append({
                "order_id": po_number,
                "version": get_attr_safe(order, "version", ""),
                "scales": all_scales,
                "order_type": classification.get("order_type"),
                "priority": get_attr_safe(order, "hercules_priority", 999) or get_attr_safe(order, "priority", 999) or 999,
                "status": order.status
            })
        
        # Detect conflict groups across ALL orders
        conflict_info = get_conflict_groups_for_orders(orders_data_for_conflict)
        print(f"🔁 [SCHEDULER] Detected {len(conflict_info['conflict_groups'])} conflict group(s)")
        
        for group in conflict_info["conflict_groups"]:
            print(f"   📊 Group {group['group_id']}: orders={group['orders']}, shared_scales={group['shared_scales']}")
        
        started_count = 0
        waiting_count = 0
        
        # ✅ Jan 30, 2026: STRICT PRIORITY ENFORCEMENT
        # Only start orders from the HIGHEST priority group (lowest priority number)
        # Find the minimum priority among ALL ACTIVE orders (InProgress + Pending)
        # This ensures Priority 5 cannot start while Priority 1 is still running
        min_priority = 999
        for order in active_inprogress + pending_orders:
            p = int(get_attr_safe(order, "hercules_priority", 999) or get_attr_safe(order, "priority", 999) or 999)
            if p < min_priority:
                min_priority = p
        
        print(f"🔁 [SCHEDULER] Highest priority group: {min_priority} (from {len(active_inprogress)} running + {len(pending_orders)} pending)")
        print(f"🔁 [SCHEDULER] Processing {len(pending_orders)} pending orders (only priority {min_priority} will start)...")
        
        for order in pending_orders:
            po_number = order.order_id
            
            # Skip if already validating
            if is_order_validating(po_number):
                print(f"⏭️ [SCHEDULER] {po_number} already validating - skip")
                continue
            
            # Skip if classification failed
            if po_number not in order_classifications:
                continue
            
            classification = order_classifications[po_number]
            order_type = classification.get("order_type")
            all_scales = get_all_scales_for_order(order, classification, include_byproduct=True)
            priority = int(get_attr_safe(order, "hercules_priority", 999) or get_attr_safe(order, "priority", 999) or 999)
            version = get_attr_safe(order, "version", "").upper().strip()
            
            # ✅ Jan 30, 2026: SCALE-BASED START (not priority-based)
            # Orders with FREE scales can start regardless of priority
            # Priority only matters within same-scale conflict groups
            # (Removed strict priority enforcement)
            
            # Check conflict info - only start if can_run=True (priority 1 in its group)
            order_conflict = conflict_info["order_conflict_info"].get(po_number, {"has_conflict": False})
            
            if order_conflict.get("has_conflict") and not order_conflict.get("can_run", True):
                waiting_for = order_conflict.get("waiting_for", [])
                print(f"⏸️ [SCHEDULER] {po_number} (priority {priority}) waiting - blocked by {waiting_for}")
                waiting_count += 1
                continue
            
            # This order can run - try to lock scales
            has_conflict, locked_scales, conflict_details, preempted = lock_scales(
                po_number, all_scales, priority, version, order_type
            )
            
            # Add to queue
            add_to_queue(po_number, all_scales, priority, version, order_type)
            
            if has_conflict:
                print(f"⏸️ [SCHEDULER] {po_number} scales already locked: {conflict_details}")
                waiting_count += 1
                continue
            
            # Scales locked - start the order
            print(f"🔁 [SCHEDULER] ✅ Starting {order_type} order {po_number} (priority {priority})")
            
            try:
                # Stop any existing worker
                if is_order_validating(po_number):
                    set_order_validation_state(po_number, {"isrunning": False})
                    time.sleep(0.3)
                
                # Mark as running in scale lock queue
                set_order_running(po_number)
                
                # Refresh and start
                db.refresh(order)
                
                # Small delay for SCADA values
                time.sleep(0.5)
                
                # Start the order - manual start via Start button
                init_and_start_order_worker(db, order, classification, is_manual_start=True)
                
                # Verify started
                db.refresh(order)
                final_status = get_attr_safe(order, "status", "UNKNOWN")
                if final_status == "InProgress" and is_order_validating(po_number):
                    print(f"✅ [SCHEDULER] Successfully started {po_number}")
                    started_count += 1
                else:
                    print(f"⚠️ [SCHEDULER] {po_number} may not have started correctly: status={final_status}")
                    release_scales(po_number, all_scales)
                    
            except Exception as e:
                print(f"❌ [SCHEDULER] Failed to start {po_number}: {e}")
                import traceback
                traceback.print_exc()
                release_scales(po_number, all_scales)
        
        # Summary
        print(f"🔁 [SCHEDULER] ========== SCHEDULER COMPLETE ==========")
        print(f"🔁 [SCHEDULER] Summary:")
        print(f"   - Started: {started_count} order(s)")
        print(f"   - Waiting: {waiting_count} order(s)")
        print(f"   - Already running: {len(active_inprogress)} order(s)")
        print(f"   - Conflict groups: {len(conflict_info['conflict_groups'])}")
        print("=" * 80)


# =============================================================================
# TEST ENDPOINT: Manually trigger scheduler (for debugging)
# =============================================================================
@orders_bp.route("/auto-validator/test-scheduler", methods=["POST"])
def test_scheduler():
    """
    Test endpoint to manually trigger the scheduler.
    This helps debug why orders are not starting automatically.
    """
    try:
        from backend.database import get_db
        db = next(get_db())
        print("=" * 80)
        print("🧪 [TEST] Manually triggering scheduler...")
        print("=" * 80)
        _schedule_next_orders_after_completion()
        return jsonify({
            "success": True,
            "message": "Scheduler triggered successfully. Check console logs for details."
        })
    except Exception as e:
        print(f"❌ [TEST] Error triggering scheduler: {e}")
        import traceback
        traceback.print_exc()
        return jsonify({
            "success": False,
            "error": str(e)
        }), 500


# =============================================================================
# TEST ENDPOINT: Manually trigger shift auto-confirmation (for debugging)
# =============================================================================
@orders_bp.route("/auto-validator/test-shift-confirm", methods=["POST"])
def test_shift_confirm():
    """
    Test endpoint to manually trigger the shift auto-confirmation.
    This helps debug why shift-end confirmations are not triggering.
    """
    try:
        from services.shift_auto_confirm import auto_push_shift_confirmation
        print("=" * 80)
        print("🧪 [TEST] Manually triggering shift auto-confirmation...")
        print("=" * 80)
        auto_push_shift_confirmation()
        return jsonify({
            "success": True,
            "message": "Shift auto-confirmation triggered. Check console logs for details."
        })
    except Exception as e:
        print(f"❌ [TEST] Error triggering shift auto-confirmation: {e}")
        import traceback
        traceback.print_exc()
        return jsonify({
            "success": False,
            "error": str(e)
        }), 500


# =============================================================================
# DIAGNOSTIC ENDPOINT: Check shift schedule and current status
# =============================================================================
@orders_bp.route("/auto-validator/shift-status", methods=["GET"])
def get_shift_status():
    """
    Diagnostic endpoint to show shift schedule, current time, and which shifts have ended.
    Helps debug shift auto-confirmation issues.
    """
    try:
        from datetime import datetime
        from models.shift_master import ShiftMaster
        
        with PostgresSessionLocal() as db:
            shifts = db.query(ShiftMaster).order_by(ShiftMaster.department, ShiftMaster.sort_order).all()
            
            now = datetime.now()
            current_time = now.time()
            
            shift_data = []
            for shift in shifts:
                # Calculate if shift has ended
                shift_end_datetime = datetime.combine(now.date(), shift.end_time)
                shift_start_datetime = datetime.combine(now.date(), shift.start_time)
                
                # Handle overnight shifts
                if shift.start_time > shift.end_time:
                    if current_time < shift.end_time:
                        # Before midnight portion - shift ends today
                        pass
                    else:
                        # After midnight portion - compare to yesterday's start
                        shift_end_datetime = datetime.combine(now.date(), shift.end_time)
                
                time_since_end = (now - shift_end_datetime).total_seconds()
                has_ended = time_since_end >= 120  # 2 min buffer
                time_until_end = -time_since_end  # Negative if ended
                
                # Check if shift is ending soon (within 5 min)
                is_ending_soon = 0 <= time_until_end <= 300
                
                # Check if this is the currently active shift
                is_active = False
                if shift.start_time < shift.end_time:
                    # Same-day shift
                    is_active = shift.start_time <= current_time < shift.end_time
                else:
                    # Overnight shift
                    is_active = current_time >= shift.start_time or current_time < shift.end_time
                
                shift_data.append({
                    "plant": shift.plant,
                    "department": shift.department,
                    "shift_code": shift.shift_code,
                    "start_time": str(shift.start_time),
                    "end_time": str(shift.end_time),
                    "is_active": is_active,
                    "has_ended": has_ended,
                    "is_ending_soon": is_ending_soon,
                    "minutes_since_end": round(time_since_end / 60, 1) if time_since_end > 0 else None,
                    "minutes_until_end": round(time_until_end / 60, 1) if time_until_end > 0 else None
                })
            
            return jsonify({
                "success": True,
                "current_time": now.isoformat(),
                "current_time_only": str(current_time),
                "shifts": shift_data
            })
    except Exception as e:
        print(f"❌ Error getting shift status: {e}")
        import traceback
        traceback.print_exc()
        return jsonify({
            "success": False,
            "error": str(e)
        }), 500


# =============================================================================
# AUTO-VALIDATOR WORKER (keeps previous behavior but uses corrected totals)
# =============================================================================
def auto_validation_worker(po_number: str, classification: Dict):
    """
    ✅ FINAL: Robust auto-validator 
    - confirmed_qty is always the sum of all shift weights, never double-counted, never reset.
    - Shift weights and confirmed_qty stay correct across stops, restarts, and shift changes.
    - Works for any SCADA/plant restarts — no manual fixing ever needed.
    """
    print(f"✅ [Worker-{po_number}] Auto-validator worker started")
    sap_service = SAPConfirmationService()
    WORKER_WAIT = 1
    order_completed_normally = False
    first_cycle = True

    try:
        while True:
            # Stop check
            if not is_order_validating(po_number):
                if not first_cycle:
                    print(f"🛑 [Worker-{po_number}] Stop signal - exiting")
                    break
                else:
                    print(f"⚠️ [Worker-{po_number}] is_order_validating() false on first cycle - ignoring")
            first_cycle = False

            try:
                # ✅ CRITICAL: Log that worker is running for this order
                # This helps identify if worker is running for all orders or just the first one
                print(f"🔄 [Worker-{po_number}] Worker cycle starting - checking order status and processing production...")
                
                with _db_session() as db:
                    current_order = db.query(ProcessOrder).filter(
                        ProcessOrder.order_id == po_number
                    ).first()

                    if not current_order:
                        print(f"❌ [Worker-{po_number}] Order not found - exiting")
                        break

                    # ✅ CRITICAL: Check order status - if validated, stop worker immediately
                    order_status = get_attr_safe(current_order, "status", "").strip().upper()
                    if order_status == "VALIDATED":
                        print(f"✅ [Worker-{po_number}] Order is Validated - stopping worker (no SAP confirmation until shift end)")
                        order_completed_normally = True
                        break
                    elif order_status == "PENDING":
                        # ✅ FIX: Stop worker when order is paused (auto-validator stopped)
                        print(f"🛑 [Worker-{po_number}] Order status is PENDING - stopping worker")
                        break
                    elif order_status != "INPROGRESS":
                        print(f"⏳ [Worker-{po_number}] Status is {order_status}, waiting...")
                        time.sleep(WORKER_WAIT)
                        continue
                    
                    # ✅ CRITICAL: Log that we're processing this order
                    print(f"✅ [Worker-{po_number}] Order is InProgress - processing production cycle...")

                    order_type = classification.get("order_type")
                    equipment = classification.get("equipment", []) or []

                    # Target and UOM
                    if order_type == "MILLING":
                        target_qty = float(get_attr_safe(current_order, "expected_weight") or 0.0)
                        uom = "KG"
                    else:
                        # ✅ CRITICAL FIX (Jan 23, 2026): PACKING quantity is already in BAGS
                        # Only SCADA delta needs conversion (pallets → bags), NOT the target
                        target_qty = float(get_attr_safe(current_order, "quantity") or 0.0)
                        uom = "BAG"

                    # ------- SHIFT CHANGE LOGIC --------
                    shift_changed = False
                    if order_type in ["MILLING", "PACKING"]:
                        plant = get_attr_safe(current_order, "plant", "3130")
                        department = "MILLING" if order_type == "MILLING" else "PACKING"
                        shift_row = get_current_shift(plant, department, db)
                        realtime_shift = shift_row.shift_code if shift_row else "A"
                        stored_shift = get_attr_safe(current_order, "current_shift", None)

                        if stored_shift is None:
                            print(f"🆕 [Worker-{po_number}] Initializing shift {realtime_shift}")
                            shift_baselines = capture_baseline_readings(equipment)
                            if shift_baselines:
                                set_attr_safe(current_order, f"baseline_shift_{realtime_shift.lower()}_start", shift_baselines)
                                set_attr_safe(current_order, f"baseline_shift_{realtime_shift.lower()}_time", datetime.now())
                            set_attr_safe(current_order, "current_shift", realtime_shift)
                            set_attr_safe(current_order, "shift_start_time", datetime.now())
                            db.commit()
                        elif stored_shift != realtime_shift:
                            print(f"🔄 [Worker-{po_number}] Shift change {stored_shift} → {realtime_shift}")
                            
                            # ✅ CRITICAL: Check if order is already validated
                            # If validated, DO NOT send to SAP here - wait for shift-end auto confirmation
                            order_status = get_attr_safe(current_order, "status", "").strip().upper()
                            is_validated = order_status == "VALIDATED"
                            
                            # ✅ CRITICAL FIX (Dec 12, 2025): Do NOT send SAP from worker
                            # SAP confirmations should ONLY happen at:
                            # 1. Shift end (via shift_auto_confirm.py)
                            # 2. Manual push (via /push-confirmation endpoint)
                            # Worker should only track production, not send to SAP
                            print(f"📋 [Worker-{po_number}] Shift change {stored_shift} → {realtime_shift} detected")
                            print(f"📋 [Worker-{po_number}] NOT sending SAP here - will be handled by shift_auto_confirm at shift end")
                            
                            # Just update shift flags for tracking, don't send to SAP
                            # (shift_auto_confirm.py will handle SAP sending at actual shift end)
                            
                            # ❌ OLD COMMENT WAS WRONG HERE:
                            # "DO NOT reset shift baselines" is what causes weight_shift_b = 10

                            # ✅ NEW: capture fresh baselines for the NEW shift
                            new_shift_baselines = capture_baseline_readings(equipment)
                            if new_shift_baselines:
                                set_attr_safe(
                                    current_order,
                                    f"baseline_shift_{realtime_shift.lower()}_start",
                                    new_shift_baselines,
                                )
                                set_attr_safe(
                                    current_order,
                                    f"baseline_shift_{realtime_shift.lower()}_time",
                                    datetime.now(),
                                )
                                print(f"✅ [Worker-{po_number}] Set fresh baselines for shift {realtime_shift}: {new_shift_baselines}")
                            else:
                                print(f"⚠️ [Worker-{po_number}] Failed to capture baselines for new shift {realtime_shift} — keeping previous ones")
                            
                            # Update current shift marker
                            set_attr_safe(current_order, "current_shift", realtime_shift)
                            set_attr_safe(current_order, "shift_start_time", datetime.now())
                            db.commit()
                            shift_changed = True

                        if shift_changed:
                            print(f"⏭️ [Worker-{po_number}] Skipping to next cycle after shift change")
                            time.sleep(WORKER_WAIT)
                            continue

                    # ----- PRODUCTION AND SHIFT WEIGHTS -----
                    # ✅ CRITICAL: Shift weights are preserved and accumulated
                    # Refresh order from DB to ensure we have latest shift weights (including preserved values)
                    db.refresh(current_order)
                    
                    # Read current shift weights BEFORE any calculations (these are preserved from before restart)
                    weight_a_before = float(get_attr_safe(current_order, "weight_shift_a", 0.0) or 0.0)
                    weight_b_before = float(get_attr_safe(current_order, "weight_shift_b", 0.0) or 0.0)
                    weight_c_before = float(get_attr_safe(current_order, "weight_shift_c", 0.0) or 0.0)
                    print(f"🔍 [Worker-{po_number}] Current shift weights from DB: A={weight_a_before:.2f}, B={weight_b_before:.2f}, C={weight_c_before:.2f} {uom}")
                    
                    # Only update the currently active shift
                    current_shift = get_attr_safe(current_order, "current_shift", "A").lower()
                    print(f"🔍 [Worker-{po_number}] Active shift: {current_shift.upper()}")
                    
                    skip_cycle_due_to_lock = False
                    for code in ["a", "b", "c"]:
                        shift_field = f"weight_shift_{code}"
                        try:
                            # ✅ CRITICAL: Get existing shift weight from database (preserved from before restart)
                            existing_shift_weight_db = float(get_attr_safe(current_order, shift_field, 0.0) or 0.0)
                            
                            # ✅ CRITICAL: Track maximum weight seen to prevent reverts
                            # Use the maximum of DB value and cached maximum to prevent decreases
                            cache_key_weight = (po_number, code)
                            max_weight_seen = _max_shift_weight_cache.get(cache_key_weight, 0.0)
                            existing_shift_weight = max(existing_shift_weight_db, max_weight_seen)
                            
                            # If DB value is higher than cached max, update the cache
                            if existing_shift_weight_db > max_weight_seen:
                                _max_shift_weight_cache[cache_key_weight] = existing_shift_weight_db
                                print(f"🔍 [Worker-{po_number}] Shift {code.upper()}: Updated max weight cache to {existing_shift_weight_db:.2f} (was {max_weight_seen:.2f})")
                            
                            # Only update shift if currently active
                            if current_shift == code:
                                print(f"🔍 [Worker-{po_number}] Calculating production for Shift {code.upper()} (existing weight={existing_shift_weight:.2f} {uom})")
                                
                                # ✅ CRITICAL: SCALE LOCK CHECK - Only process weight if all scales are locked by this order
                                # This ensures priority-based scale locking works correctly
                                # Lower priority orders (higher priority number) must wait until scales are released
                                if equipment:
                                    # Ensure equipment is a proper list
                                    if isinstance(equipment, str):
                                        import json
                                        try:
                                            equipment = json.loads(equipment)
                                        except json.JSONDecodeError:
                                            equipment = [s.strip() for s in equipment.split(",") if s.strip()]
                                    if not isinstance(equipment, list):
                                        equipment = [equipment] if equipment else []
                                    
                                    # Check if all required scales are locked by this order
                                    all_scales_locked = True
                                    locked_by_other = []
                                    for scale in equipment:
                                        if not scale:
                                            continue
                                        scale_upper = scale.upper().strip()
                                        scale_owner = get_scale_owner(scale_upper)
                                        
                                        if scale_owner is None:
                                            # Scale is free - no conflict, proceed with processing
                                            # This might happen if order started before locking was implemented
                                            # ✅ FIX: Free scales are OK - only block when locked by ANOTHER order
                                            print(f"ℹ️ [Worker-{po_number}] Scale {scale_upper} is free (not locked) - proceeding anyway (no conflict)")
                                            # Don't set all_scales_locked = False - free scales are OK
                                        elif scale_owner != po_number:
                                            # Scale is locked by another order - this order must wait
                                            all_scales_locked = False
                                            locked_by_other.append(f"{scale_upper} (by {scale_owner})")
                                            print(f"🔒 [Worker-{po_number}] Scale {scale_upper} is locked by order {scale_owner} - skipping weight processing")
                                    
                                    if not all_scales_locked:
                                        if locked_by_other:
                                            print(f"⏸️ [Worker-{po_number}] Scales locked by other orders: {', '.join(locked_by_other)} - SKIPPING weight processing (waiting for scales)")
                                        else:
                                            print(f"⏸️ [Worker-{po_number}] Not all scales are locked - SKIPPING weight processing")
                                        # Skip the entire worker cycle - don't process any weights or confirmed_qty
                                        skip_cycle_due_to_lock = True
                                        break
                                    else:
                                        print(f"✅ [Worker-{po_number}] All scales locked by this order - proceeding with weight processing")
                                
                                # Calculate TOTAL production from shift baseline to current SCADA
                                # This is the total production in this shift since the baseline was captured
                                # ✅ CRITICAL: This should return the DELTA (current - baseline), not the absolute current value
                                # ✅ CRITICAL: Pass db to ensure calculate_shift_weight refreshes order and uses latest baseline
                                total_production_from_baseline = calculate_shift_weight(current_order, code.upper(), classification, db=db)
                                
                                # ✅ SAFETY CHECK: If total_production_from_baseline is suspiciously large (close to current SCADA reading),
                                # it might indicate that the baseline wasn't set correctly or we're using absolute values instead of deltas.
                                # Log a warning but continue - the increment calculation should handle this.
                                if total_production_from_baseline > 1000.0 and existing_shift_weight == 0.0:
                                    print(f"⚠️ [Worker-{po_number}] Shift {code.upper()}: WARNING - total_production_from_baseline ({total_production_from_baseline:.2f}) is very large. This might indicate baseline wasn't set correctly or we're using absolute SCADA reading instead of delta.")
                                
                                if order_type == "MILLING":
                                    total_production = total_production_from_baseline
                                else:
                                    # PACKING: total_production_from_baseline is already in bags
                                    # because calculate_shift_weight now converts PL palletizers to bags
                                    # and keeps SL as bags, so we can use it directly
                                    total_production = total_production_from_baseline
                                
                                print(f"🔍 [Worker-{po_number}] Shift {code.upper()}: total_production from baseline = {total_production:.2f} {uom}")
                                
                                # ✅ CRITICAL: Track last calculated production to prevent double-counting
                                # Key: (po_number, shift_code) -> last_total_production
                                cache_key = (po_number, code)
                                last_total_production = _last_shift_production_cache.get(cache_key, 0.0)
                                
                                # ✅ CRITICAL FIX: Detect if baseline changed after restart
                                # When order is restarted, baseline is updated but cache might still have old value
                                # We need to detect this and reset the cache to prevent double-counting
                                baseline_changed_after_restart = False
                                
                                # ✅ CRITICAL: If existing_shift_weight > 0, it means order was restarted
                                # In this case, total_production is calculated from NEW baseline
                                # If cache has old value (last_total_production > total_production), reset it
                                if existing_shift_weight > 0.0:
                                    if last_total_production > total_production:
                                        # Cache has old value from before restart - reset it
                                        print(f"🚨 [Worker-{po_number}] Shift {code.upper()}: CRITICAL - Baseline changed after restart!")
                                        print(f"   existing_weight={existing_shift_weight:.2f}, cache={last_total_production:.2f}, current={total_production:.2f}")
                                        print(f"   Cache has old value from before restart - resetting cache")
                                        baseline_changed_after_restart = True
                                        _last_shift_production_cache[cache_key] = 0.0
                                        last_total_production = 0.0
                                        print(f"✅ [Worker-{po_number}] Shift {code.upper()}: Cache reset to 0 after detecting baseline change")
                                    elif last_total_production > 0.0 and total_production < last_total_production * 0.5:
                                        # Production dropped significantly - baseline was reset
                                        print(f"🚨 [Worker-{po_number}] Shift {code.upper()}: CRITICAL - Baseline changed after restart!")
                                        print(f"   existing_weight={existing_shift_weight:.2f}, cache={last_total_production:.2f}, current={total_production:.2f}")
                                        print(f"   Production dropped significantly - baseline was reset, clearing cache")
                                        baseline_changed_after_restart = True
                                        _last_shift_production_cache[cache_key] = 0.0
                                        last_total_production = 0.0
                                        print(f"✅ [Worker-{po_number}] Shift {code.upper()}: Cache reset to 0 after detecting baseline change")
                                    elif last_total_production == 0.0:
                                        # Cache is already cleared (was cleared on restart) - this is correct
                                        print(f"✅ [Worker-{po_number}] Shift {code.upper()}: Cache is 0 (was cleared on restart) - correct state")
                                
                                # ✅ CRITICAL FIX: Detect first cycle scenarios
                                # Check if this is a brand new order (confirmed_qty = 0 and all shift weights = 0)
                                confirmed_qty_check = float(get_attr_safe(current_order, "confirmed_qty", 0.0) or 0.0)
                                weight_a_check = float(get_attr_safe(current_order, "weight_shift_a", 0.0) or 0.0)
                                weight_b_check = float(get_attr_safe(current_order, "weight_shift_b", 0.0) or 0.0)
                                weight_c_check = float(get_attr_safe(current_order, "weight_shift_c", 0.0) or 0.0)
                                is_truly_brand_new = (confirmed_qty_check == 0.0 and weight_a_check == 0.0 and weight_b_check == 0.0 and weight_c_check == 0.0)
                                
                                # ✅ CRITICAL: For brand new orders, FORCE clear cache to prevent inheriting values from deleted orders
                                # This is especially important if the new order has the same PO number as a deleted order
                                if is_truly_brand_new and last_total_production > 0.0:
                                    print(f"🚨 [Worker-{po_number}] Shift {code.upper()}: Brand new order but cache has old value ({last_total_production:.2f})!")
                                    print(f"   This might be from a deleted order - FORCING cache clear")
                                    _last_shift_production_cache[cache_key] = 0.0
                                    last_total_production = 0.0
                                    print(f"✅ [Worker-{po_number}] Shift {code.upper()}: Cache force cleared for brand new order")
                                
                                # ✅ CRITICAL: Also clear max weight cache for brand new orders
                                if is_truly_brand_new and cache_key in _max_shift_weight_cache:
                                    max_weight_value = _max_shift_weight_cache[cache_key]
                                    if max_weight_value > 0.0:
                                        print(f"🚨 [Worker-{po_number}] Shift {code.upper()}: Brand new order but max weight cache has old value ({max_weight_value:.2f})!")
                                        print(f"   This might be from a deleted order - FORCING cache clear")
                                        del _max_shift_weight_cache[cache_key]
                                        print(f"✅ [Worker-{po_number}] Shift {code.upper()}: Max weight cache force cleared for brand new order")
                                
                                is_first_cycle_after_restart = (last_total_production == 0.0 and existing_shift_weight > 0.0) or baseline_changed_after_restart
                                is_first_cycle_brand_new = (last_total_production == 0.0 and existing_shift_weight == 0.0 and is_truly_brand_new)
                                
                                # ✅ CRITICAL DEBUG: Log first cycle detection
                                print(f"🔍 [Worker-{po_number}] Shift {code.upper()}: First cycle detection - is_first_cycle_after_restart={is_first_cycle_after_restart}, is_first_cycle_brand_new={is_first_cycle_brand_new}, is_truly_brand_new={is_truly_brand_new}, last_total_production={last_total_production:.2f}, existing_shift_weight={existing_shift_weight:.2f}, total_production={total_production:.2f}")
                                
                                # ✅ CRITICAL: If existing_weight > 0 but cache is wrong, force reset
                                # This handles cases where cache wasn't cleared properly on restart
                                if existing_shift_weight > 0.0 and last_total_production > total_production and not baseline_changed_after_restart:
                                    # Cache has old value but we didn't detect baseline change - force reset
                                    print(f"🚨 [Worker-{po_number}] Shift {code.upper()}: FORCE RESET - existing_weight={existing_shift_weight:.2f} but cache={last_total_production:.2f} > current={total_production:.2f}")
                                    print(f"   Cache wasn't cleared properly - forcing reset")
                                    _last_shift_production_cache[cache_key] = 0.0
                                    last_total_production = 0.0
                                    baseline_changed_after_restart = True
                                    print(f"✅ [Worker-{po_number}] Shift {code.upper()}: Cache force reset to 0")
                                
                                if is_first_cycle_after_restart:
                                    print(f"🔍 [Worker-{po_number}] Shift {code.upper()}: First cycle after restart - existing_weight={existing_shift_weight:.2f} preserved, total_production={total_production:.2f} (NEW production to be added)")
                                elif is_first_cycle_brand_new:
                                    # ✅ IMPROVED LOGIC: For a brand-new order, only ignore SMALL deltas (< 2.0 kg)
                                    # Small deltas are likely SCADA settling from previous order.
                                    # LARGE deltas (> 2.0 kg) are real production and should be counted.
                                    #
                                    # So we:
                                    #   - If total_production <= 2.0 kg: ignore it (SCADA settling), cache it, keep weight at 0
                                    #   - If total_production > 2.0 kg: count it as real production, set weight = total_production

                                    noise_threshold = 2.0  # 2.0 kg threshold - anything smaller is likely noise/settling

                                    if total_production <= noise_threshold:
                                        # Small production - likely SCADA settling, ignore it
                                        print(
                                            f"🔍 [Worker-{po_number}] Shift {code.upper()}: "
                                            f"Brand NEW order, first cycle - total_production={total_production:.2f} "
                                            f"(small delta, treating as SCADA settling, NOT counting for this order)"
                                        )

                                        # Initialize caches to this starting offset
                                        _last_shift_production_cache[cache_key] = total_production
                                        _max_shift_weight_cache[cache_key_weight] = 0.0

                                        # Explicitly force shift weight to 0 for a fresh order
                                        if hasattr(current_order, shift_field):
                                            setattr(current_order, shift_field, 0.0)
                                        else:
                                            set_attr_safe(current_order, shift_field, 0.0)
                                        print(
                                            f"🔒 [Worker-{po_number}] Shift {code.upper()} SET to 0.0 "
                                            f"(brand new order, first cycle ignored – next cycles will only count NEW production)"
                                        )
                                        
                                        # ✅ CRITICAL: Even though we're skipping this cycle, ensure confirmed_qty is 0
                                        # This prevents any stale confirmed_qty from previous orders
                                        # For automatically started orders, this ensures clean start
                                        if hasattr(current_order, "confirmed_qty"):
                                            current_order.confirmed_qty = 0.0
                                        else:
                                            set_attr_safe(current_order, "confirmed_qty", 0.0)
                                        
                                        # ✅ CRITICAL: Commit shift weight and confirmed_qty immediately
                                        # This ensures they're persisted even though we're using continue
                                        try:
                                            db.add(current_order)
                                            db.flush()
                                            db.commit()
                                            
                                            # ✅ CRITICAL: Verify commit by querying database directly
                                            db.refresh(current_order)
                                            verified_weight = float(get_attr_safe(current_order, shift_field, 0.0) or 0.0)
                                            verified_confirmed = float(get_attr_safe(current_order, "confirmed_qty", 0.0) or 0.0)
                                            
                                            # Also query directly from database to double-check
                                            verify_order = db.query(ProcessOrder).filter(ProcessOrder.order_id == po_number).first()
                                            if verify_order:
                                                direct_weight = float(get_attr_safe(verify_order, shift_field, 0.0) or 0.0)
                                                direct_confirmed = float(get_attr_safe(verify_order, "confirmed_qty", 0.0) or 0.0)
                                                if direct_weight != 0.0 or direct_confirmed != 0.0:
                                                    print(f"⚠️ [Worker-{po_number}] WARNING: Direct query shows weight={direct_weight:.2f}, confirmed={direct_confirmed:.2f} but we set both to 0.0!")
                                                else:
                                                    print(f"✅ [Worker-{po_number}] Shift {code.upper()} and confirmed_qty committed and verified in database (both set to 0.0)")
                                            else:
                                                print(f"⚠️ [Worker-{po_number}] Could not verify commit - order not found in direct query")
                                        except Exception as e:
                                            print(f"⚠️ [Worker-{po_number}] Failed to commit shift weight and confirmed_qty: {e}")
                                            import traceback
                                            traceback.print_exc()
                                            db.rollback()

                                        # Skip normal accumulation logic for this first cycle
                                        continue
                                    else:
                                        # Large production - this is REAL production, count it!
                                        print(
                                            f"🔍 [Worker-{po_number}] Shift {code.upper()}: "
                                            f"Brand NEW order, first cycle - total_production={total_production:.2f} "
                                            f"(REAL production detected, counting it)"
                                        )

                                        # Initialize caches to current production
                                        _last_shift_production_cache[cache_key] = total_production
                                        _max_shift_weight_cache[cache_key_weight] = total_production

                                        # Set shift weight directly to total_production (this is real production)
                                        if hasattr(current_order, shift_field):
                                            setattr(current_order, shift_field, total_production)
                                        else:
                                            set_attr_safe(current_order, shift_field, total_production)
                                        print(
                                            f"✅ [Worker-{po_number}] Shift {code.upper()} SET to {total_production:.2f} "
                                            f"(brand new order, first cycle - real production counted)"
                                        )

                                        # ✅ CRITICAL: Also update confirmed_qty immediately to match shift weight
                                        # This ensures "Current" shows the production right away
                                        # ✅ CRITICAL FIX (Jan 23, 2026): PACKING quantity is already in BAGS
                                        if order_type == "MILLING":
                                            target_qty = float(get_attr_safe(current_order, "expected_weight") or 0.0)
                                        else:
                                            # PACKING: quantity is already in BAGS - do NOT convert
                                            target_qty = float(get_attr_safe(current_order, "quantity") or 0.0)
                                        display_total = min(total_production, target_qty)
                                        if hasattr(current_order, "confirmed_qty"):
                                            current_order.confirmed_qty = display_total
                                        else:
                                            set_attr_safe(current_order, "confirmed_qty", display_total)
                                        print(
                                            f"✅ [Worker-{po_number}] confirmed_qty SET to {display_total:.2f} "
                                            f"(brand new order, first cycle - matching shift weight, target={target_qty:.2f})"
                                        )

                                        # ✅ CRITICAL: Flush and commit immediately to ensure weight and confirmed_qty are persisted
                                        # This is necessary because we're using 'continue' which skips the normal commit
                                        # ✅ CRITICAL: Use direct commit with refresh to ensure values are actually in database
                                        try:
                                            db.add(current_order)
                                            db.flush()
                                            db.commit()
                                            # ✅ CRITICAL: Refresh to verify commit worked
                                            db.refresh(current_order)
                                            # Verify the values were actually committed
                                            verified_weight = float(get_attr_safe(current_order, shift_field, 0.0) or 0.0)
                                            verified_confirmed = float(get_attr_safe(current_order, "confirmed_qty", 0.0) or 0.0)
                                            if abs(verified_weight - total_production) > 0.01 or abs(verified_confirmed - display_total) > 0.01:
                                                print(f"⚠️ [Worker-{po_number}] WARNING: Commit verification failed! weight={verified_weight:.2f} (expected {total_production:.2f}), confirmed={verified_confirmed:.2f} (expected {display_total:.2f})")
                                                # Retry commit
                                                if hasattr(current_order, shift_field):
                                                    setattr(current_order, shift_field, total_production)
                                                if hasattr(current_order, "confirmed_qty"):
                                                    current_order.confirmed_qty = display_total
                                                db.add(current_order)
                                                db.commit()
                                                db.refresh(current_order)
                                                print(f"✅ [Worker-{po_number}] Retry commit completed")
                                            else:
                                                print(f"✅ [Worker-{po_number}] Shift {code.upper()} weight and confirmed_qty committed and verified: weight={verified_weight:.2f}, confirmed={verified_confirmed:.2f} {uom}")
                                        except Exception as e:
                                            print(f"⚠️ [Worker-{po_number}] Failed to commit shift weight and confirmed_qty: {e}")
                                            import traceback
                                            traceback.print_exc()
                                            db.rollback()

                                        # Skip normal accumulation logic since we already set the weight and confirmed_qty
                                        continue
                                
                                # Calculate increment: only add new production since last cycle
                                # ✅ CRITICAL FIX: After restart, baseline is reset, so total_production is calculated from NEW baseline
                                # If existing_shift_weight > 0, it means we have production from BEFORE restart (from OLD baseline)
                                # We need to preserve existing_weight and only add NEW production from NEW baseline
                                # The cache should be reset to 0 on restart, but if it wasn't, we need to handle it here
                                
                                # ✅ CRITICAL: Detect if this is after restart (baseline was reset)
                                # If existing_weight > 0 but total_production is calculated from new baseline,
                                # we need to reset cache and treat all current production as new
                                if existing_shift_weight > 0.0:
                                    # Order was restarted - existing_weight is from old baseline, total_production is from new baseline
                                    # We should preserve existing_weight and add only NEW production (increment from new baseline)
                                    # But if cache has old value, increment calculation will be wrong
                                    
                                    # ✅ CRITICAL: If cache has old value (last_total_production > total_production),
                                    # it means baseline was reset but cache wasn't cleared - reset it now
                                    if last_total_production > total_production:
                                        print(f"🚨 [Worker-{po_number}] Shift {code.upper()}: CRITICAL - Cache has old value after restart!")
                                        print(f"   existing_weight={existing_shift_weight:.2f}, cache={last_total_production:.2f}, current={total_production:.2f}")
                                        print(f"   Baseline was reset - clearing cache and treating all current production as new")
                                        _last_shift_production_cache[cache_key] = 0.0
                                        last_total_production = 0.0
                                        production_increment = total_production  # All current production is new from new baseline
                                        print(f"✅ [Worker-{po_number}] Shift {code.upper()}: Cache reset, increment={production_increment:.2f} (all new from new baseline)")
                                    elif last_total_production == 0.0:
                                        # Cache is already 0 (was cleared on restart) - all current production is new
                                        production_increment = total_production
                                        print(f"🔍 [Worker-{po_number}] Shift {code.upper()}: After restart - cache=0, increment={production_increment:.2f} (all new from new baseline)")
                                    else:
                                        # Cache has value but it's less than total_production - normal increment
                                        production_increment = total_production - last_total_production
                                        print(f"🔍 [Worker-{po_number}] Shift {code.upper()}: Normal increment - cache={last_total_production:.2f}, current={total_production:.2f}, increment={production_increment:.2f}")
                                else:
                                    # No existing weight - normal increment calculation
                                    production_increment = total_production - last_total_production
                                
                                # ✅ DEBUG: Log cache state for troubleshooting
                                if last_total_production > 0.0:
                                    print(f"🔍 [Worker-{po_number}] Shift {code.upper()}: CACHE STATE - last_total={last_total_production:.2f} (from cache), current_total={total_production:.2f}, increment={production_increment:.2f} {uom}")
                                print(f"🔍 [Worker-{po_number}] Shift {code.upper()}: existing_weight={existing_shift_weight:.2f}, last_total={last_total_production:.2f}, current_total={total_production:.2f}, increment={production_increment:.2f} {uom}")
                                
                                # ✅ SAFETY CHECK: If increment is suspiciously large compared to existing weight,
                                # it might indicate double-counting. Log a warning but still process.
                                if existing_shift_weight > 0 and production_increment > existing_shift_weight * 2:
                                    print(f"⚠️ [Worker-{po_number}] Shift {code.upper()}: Large increment detected! existing={existing_shift_weight:.2f}, increment={production_increment:.2f} - possible double-counting?")
                                
                                # ✅ CRITICAL: Only accumulate if there's new production (increment > 0)
                                # This prevents double-counting by only adding the increment, not the total
                                # NEVER decrease shift weight - it should only increase or stay the same
                                # ✅ CRITICAL: If total_production > 0 but increment is 0 or negative, it means cache is wrong
                                # Force update shift weight to total_production if it's higher than existing
                                if total_production > existing_shift_weight and production_increment <= 0.01:
                                    print(f"🚨 [Worker-{po_number}] Shift {code.upper()}: CRITICAL - total_production={total_production:.2f} > existing_weight={existing_shift_weight:.2f} but increment={production_increment:.2f} <= 0.01!")
                                    print(f"   This means cache is wrong or production wasn't counted. FORCING update to {total_production:.2f}")
                                    # Force update shift weight to total_production
                                    if hasattr(current_order, shift_field):
                                        setattr(current_order, shift_field, total_production)
                                    else:
                                        set_attr_safe(current_order, shift_field, total_production)
                                    
                                    # ✅ CRITICAL: Commit immediately to ensure it's persisted
                                    try:
                                        db.add(current_order)
                                        db.flush()
                                        db.commit()
                                        db.refresh(current_order)
                                        print(f"✅ [Worker-{po_number}] Shift {code.upper()} FORCED to {total_production:.2f} {uom} and COMMITTED to database")
                                    except Exception as e:
                                        print(f"⚠️ [Worker-{po_number}] Failed to commit forced shift weight: {e}")
                                        import traceback
                                        traceback.print_exc()
                                    
                                    _last_shift_production_cache[cache_key] = total_production
                                    _max_shift_weight_cache[cache_key_weight] = total_production
                                    
                                    # Skip normal accumulation since we already set and committed the weight
                                    continue
                                
                                if production_increment > 0.01:
                                    # ✅ CRITICAL: Before adding increment, verify it's reasonable
                                    # If increment is suspiciously large compared to existing weight, it might be wrong
                                    # This can happen if cache wasn't cleared properly after restart
                                    if existing_shift_weight > 0.0 and production_increment > existing_shift_weight:
                                        print(f"🚨 [Worker-{po_number}] Shift {code.upper()}: WARNING - Increment ({production_increment:.2f}) > existing_weight ({existing_shift_weight:.2f})!")
                                        print(f"   This might indicate cache wasn't cleared properly after restart")
                                        print(f"   Checking if this is first cycle after restart...")
                                        
                                        # If this is first cycle after restart, increment should equal total_production
                                        # If not, something is wrong - reset cache and recalculate
                                        if not is_first_cycle_after_restart and last_total_production > 0.0:
                                            print(f"🚨 [Worker-{po_number}] Shift {code.upper()}: Cache has old value! Resetting cache and recalculating increment")
                                            _last_shift_production_cache[cache_key] = 0.0
                                            production_increment = total_production  # All current production is new
                                            print(f"✅ [Worker-{po_number}] Shift {code.upper()}: Cache reset, increment recalculated to {production_increment:.2f}")
                                    
                                    # Add only the increment to existing weight
                                    accumulated_shift_weight = existing_shift_weight + production_increment
                                    
                                    # ✅ CRITICAL: Ensure we never decrease (safety check)
                                    if accumulated_shift_weight < existing_shift_weight:
                                        print(f"⚠️ [Worker-{po_number}] Shift {code.upper()}: Prevented decrease! Keeping {existing_shift_weight:.2f} instead of {accumulated_shift_weight:.2f} {uom}")
                                        accumulated_shift_weight = existing_shift_weight
                                    
                                    # ✅ CRITICAL: Use MAX to ensure shift weight never decreases
                                    # This protects against any edge cases where calculations might go wrong
                                    final_shift_weight = max(existing_shift_weight, accumulated_shift_weight)
                                    
                                    # ✅ CRITICAL: Ensure final weight is never less than maximum seen
                                    final_shift_weight = max(final_shift_weight, max_weight_seen)
                                    
                                    # ✅ CRITICAL: Update max weight cache
                                    if final_shift_weight > max_weight_seen:
                                        _max_shift_weight_cache[cache_key_weight] = final_shift_weight
                                    
                                    # ✅ CRITICAL FIX (Dec 12, 2025): FINAL CHECK - shift weight can ONLY INCREASE
                                    # Read current DB value one more time to ensure we never decrease
                                    current_db_weight = float(get_attr_safe(current_order, shift_field, 0.0) or 0.0)
                                    if final_shift_weight < current_db_weight:
                                        print(f"🛑 [Worker-{po_number}] Shift {code.upper()}: BLOCKED DECREASE! Keeping {current_db_weight:.2f} instead of {final_shift_weight:.2f}")
                                        final_shift_weight = current_db_weight
                                    
                                    # ✅ CRITICAL: Use direct assignment to ensure shift weight is set
                                    if hasattr(current_order, shift_field):
                                        setattr(current_order, shift_field, final_shift_weight)
                                    else:
                                        set_attr_safe(current_order, shift_field, final_shift_weight)
                                    
                                    # ✅ CRITICAL: Commit shift weight immediately to ensure it's persisted
                                    # This is especially important for new production - it must be committed!
                                    try:
                                        db.add(current_order)
                                        db.flush()
                                        db.commit()
                                        db.refresh(current_order)
                                        print(f"✅ [Worker-{po_number}] Shift {code.upper()} UPDATED to {final_shift_weight:.2f} {uom} and COMMITTED to database")
                                    except Exception as e:
                                        print(f"⚠️ [Worker-{po_number}] Failed to commit shift weight update: {e}")
                                        import traceback
                                        traceback.print_exc()
                                        db.rollback()
                                    
                                    # ✅ CRITICAL: Always update cache IMMEDIATELY after calculating increment
                                    # This ensures cache stays in sync with actual production from baseline
                                    # This prevents double-counting on subsequent cycles
                                    # ✅ CRITICAL: Update cache BEFORE logging to ensure it's set for next cycle
                                    _last_shift_production_cache[cache_key] = total_production
                                    if is_first_cycle_after_restart:
                                        print(f"🔍 [Worker-{po_number}] Shift {code.upper()}: Cache initialized to {total_production:.2f} after restart (existing_weight={existing_shift_weight:.2f} preserved)")
                                    
                                    if final_shift_weight > existing_shift_weight:
                                        print(f"✅ [Worker-{po_number}] Shift {code.upper()} UPDATED: {existing_shift_weight:.2f} + {production_increment:.2f} = {final_shift_weight:.2f} {uom} (cache updated to {total_production:.2f})")
                                    else:
                                        print(f"🔒 [Worker-{po_number}] Shift {code.upper()} PRESERVED: {final_shift_weight:.2f} {uom} (MAX safeguard prevented change, but cache updated to {total_production:.2f})")
                                elif production_increment < -0.01:
                                    # Production decreased - could be:
                                    # 1. SCADA reading went down temporarily (temporary glitch) - don't update cache
                                    # 2. Baseline was reset after restart (baseline change) - MUST update cache
                                    
                                    # ✅ CRITICAL: If existing_weight > 0 and increment is very negative,
                                    # it likely means baseline was reset but we didn't detect it earlier
                                    # In this case, we MUST update cache to current production
                                    if existing_shift_weight > 0.0 and abs(production_increment) > existing_shift_weight * 0.5:
                                        # Very large negative increment - likely baseline reset
                                        print(f"🚨 [Worker-{po_number}] Shift {code.upper()}: Large negative increment ({production_increment:.2f}) detected!")
                                        print(f"   existing_weight={existing_shift_weight:.2f}, cache={last_total_production:.2f}, current={total_production:.2f}")
                                        print(f"   This likely means baseline was reset - updating cache to current production")
                                        _last_shift_production_cache[cache_key] = total_production
                                        print(f"✅ [Worker-{po_number}] Shift {code.upper()}: Cache updated to {total_production:.2f} after detecting baseline reset")
                                    else:
                                        # Small negative increment - likely temporary SCADA glitch
                                        # DO NOT update cache - keep last_total_production as is
                                        print(f"⚠️ [Worker-{po_number}] Shift {code.upper()}: Production decreased ({production_increment:.2f}), preserving weight and cache (likely temporary SCADA glitch)")
                                    
                                    # DO NOT decrease shift weight - preserve existing (use MAX to be safe)
                                    final_shift_weight = max(existing_shift_weight, max_weight_seen, 0.0)  # Never decrease below max seen
                                    # ✅ CRITICAL: Update max weight cache if needed
                                    if final_shift_weight > max_weight_seen:
                                        _max_shift_weight_cache[cache_key_weight] = final_shift_weight
                                    print(f"🔒 [Worker-{po_number}] Shift {code.upper()}: Weight preserved at {final_shift_weight:.2f} {uom} (max_seen={max_weight_seen:.2f})")
                                    # ✅ CRITICAL: Use direct assignment to ensure shift weight is set
                                    if hasattr(current_order, shift_field):
                                        setattr(current_order, shift_field, final_shift_weight)
                                    else:
                                        set_attr_safe(current_order, shift_field, final_shift_weight)
                                    
                                    # ✅ CRITICAL: Flush shift weight immediately
                                    try:
                                        db.add(current_order)
                                        db.flush()
                                    except Exception as e:
                                        print(f"⚠️ [Worker-{po_number}] Failed to flush shift weight: {e}")
                                    # Cache remains unchanged - don't update it with lower value
                                else:
                                    # No new production (increment ≈ 0), preserve existing weight
                                    # ✅ CRITICAL: Always preserve existing weight, never overwrite with lower value
                                    # ✅ CRITICAL FIX: If total_production is significantly higher than existing weight,
                                    # it means production wasn't counted properly. Force update!
                                    if total_production > existing_shift_weight + 1.0:  # At least 1kg difference
                                        print(f"🚨 [Worker-{po_number}] Shift {code.upper()}: CRITICAL - total_production={total_production:.2f} > existing_weight={existing_shift_weight:.2f} but increment={production_increment:.2f} ≈ 0!")
                                        print(f"   Production wasn't counted! FORCING update to {total_production:.2f}")
                                        final_shift_weight = total_production
                                        # ✅ CRITICAL: Use direct assignment to ensure shift weight is set
                                        if hasattr(current_order, shift_field):
                                            setattr(current_order, shift_field, final_shift_weight)
                                        else:
                                            set_attr_safe(current_order, shift_field, final_shift_weight)
                                        
                                        # ✅ CRITICAL: Commit immediately to ensure it's persisted
                                        try:
                                            db.add(current_order)
                                            db.flush()
                                            db.commit()
                                            db.refresh(current_order)
                                            print(f"✅ [Worker-{po_number}] Shift {code.upper()} FORCED to {final_shift_weight:.2f} {uom} and COMMITTED to database")
                                        except Exception as e:
                                            print(f"⚠️ [Worker-{po_number}] Failed to commit forced shift weight: {e}")
                                            import traceback
                                            traceback.print_exc()
                                            db.rollback()
                                        
                                        _last_shift_production_cache[cache_key] = total_production
                                        _max_shift_weight_cache[cache_key_weight] = total_production
                                    else:
                                        # Normal case: no new production, preserve existing
                                        final_shift_weight = max(existing_shift_weight, max_weight_seen, 0.0)  # Never decrease below max seen
                                        # ✅ CRITICAL: Update max weight cache if needed
                                        if final_shift_weight > max_weight_seen:
                                            _max_shift_weight_cache[cache_key_weight] = final_shift_weight
                                        
                                        # ✅ CRITICAL: Use direct assignment to ensure shift weight is set
                                        if hasattr(current_order, shift_field):
                                            setattr(current_order, shift_field, final_shift_weight)
                                        else:
                                            set_attr_safe(current_order, shift_field, final_shift_weight)
                                        
                                        # ✅ CRITICAL: Commit shift weight immediately to ensure it's persisted
                                        # This is especially important for preserved weights - they must be committed!
                                        # Even if the value didn't change, we need to commit to ensure database has the latest value
                                        try:
                                            db.add(current_order)
                                            db.flush()
                                            db.commit()
                                            db.refresh(current_order)
                                            print(f"✅ [Worker-{po_number}] Shift {code.upper()} PRESERVED at {final_shift_weight:.2f} {uom} and COMMITTED to database")
                                        except Exception as e:
                                            print(f"⚠️ [Worker-{po_number}] Failed to commit preserved shift weight: {e}")
                                            import traceback
                                            traceback.print_exc()
                                            db.rollback()
                                        
                                        if existing_shift_weight > 0:
                                            print(f"🔒 [Worker-{po_number}] Shift {code.upper()} PRESERVED: {final_shift_weight:.2f} {uom} (no new production, max_seen={max_weight_seen:.2f})")
                                        # ✅ CRITICAL: Only update cache if total_production >= last_total_production
                                        # This prevents cache from being updated with lower values that could cause issues
                                        if total_production >= last_total_production:
                                            _last_shift_production_cache[cache_key] = total_production
                                        else:
                                            print(f"🔒 [Worker-{po_number}] Shift {code.upper()}: Cache preserved at {last_total_production:.2f} (total_production={total_production:.2f} is lower)")
                            else:
                                # Inactive shift - preserve weight (don't recalculate)
                                if existing_shift_weight > 0:
                                    print(f"🔒 [Worker-{po_number}] Shift {code.upper()} (inactive): Preserving weight={existing_shift_weight:.2f} {uom}")
                            # For inactive shifts, weight is preserved (not recalculated)
                        except Exception as e:
                            print(f"⚠️ [Worker-{po_number}] Failed to update {shift_field}: {e}")
                            import traceback
                            traceback.print_exc()
                    
                    if skip_cycle_due_to_lock:
                        print(f"⏸️ [Worker-{po_number}] Skipping full cycle due to scale lock conflict")
                        time.sleep(WORKER_WAIT)
                        continue

                    # ✅ CRITICAL FINAL SAFEGUARD: After all shift weight updates, check if production exists but weights are still 0
                    # This catches cases where first cycle logic didn't run or production wasn't counted
                    db.refresh(current_order)
                    final_weight_a = float(get_attr_safe(current_order, "weight_shift_a", 0.0) or 0.0)
                    final_weight_b = float(get_attr_safe(current_order, "weight_shift_b", 0.0) or 0.0)
                    final_weight_c = float(get_attr_safe(current_order, "weight_shift_c", 0.0) or 0.0)
                    final_weights_sum = final_weight_a + final_weight_b + final_weight_c
                    
                    # Check if we have production from SCADA but shift weights are 0
                    # This means production wasn't counted - force update!
                    if final_weights_sum == 0.0:
                        # Recalculate total production from current SCADA to see if we missed it
                        try:
                            current_shift_for_check = get_attr_safe(current_order, "current_shift", "A").lower()
                            if current_shift_for_check == code:
                                # This is the active shift - check if we have production
                                if total_production > 2.0:  # Real production detected
                                    print(f"🚨 [Worker-{po_number}] CRITICAL FINAL CHECK: Shift {code.upper()} has production={total_production:.2f} but weight is still 0!")
                                    print(f"   FORCING shift weight update to {total_production:.2f}")
                                    set_attr_safe(current_order, shift_field, total_production)
                                    # Update cache with correct key format (same as used elsewhere)
                                    cache_key_final = (po_number, code)
                                    cache_key_weight_final = (po_number, code)  # Same format as line 6521
                                    _last_shift_production_cache[cache_key_final] = total_production
                                    _max_shift_weight_cache[cache_key_weight_final] = total_production
                                    print(f"✅ [Worker-{po_number}] Shift {code.upper()} FINALLY FORCED to {total_production:.2f} {uom}")
                        except Exception as e:
                            print(f"⚠️ [Worker-{po_number}] Error in final safeguard check: {e}")
                    
                    # ✅ CRITICAL: Refresh order to get latest shift weights after individual commits
                    # Since we're now committing shift weights immediately when they're updated,
                    # we just need to refresh to get the latest committed values
                    # This ensures confirmed_qty calculation uses the most recent values from database
                    # ✅ CRITICAL: For automatically started orders, this refresh is ESSENTIAL
                    # Without it, confirmed_qty calculation might use stale shift weight values
                    db.refresh(current_order)
                    
                    # ✅ CRITICAL: Double-check that shift weights are actually in the database
                    # If they're still 0 after refresh, it means the individual commits didn't work
                    weight_a_check = float(get_attr_safe(current_order, "weight_shift_a", 0.0) or 0.0)
                    weight_b_check = float(get_attr_safe(current_order, "weight_shift_b", 0.0) or 0.0)
                    weight_c_check = float(get_attr_safe(current_order, "weight_shift_c", 0.0) or 0.0)
                    if weight_a_check == 0.0 and weight_b_check == 0.0 and weight_c_check == 0.0:
                        print(f"⚠️ [Worker-{po_number}] WARNING: All shift weights are 0 after refresh! This might indicate commits didn't work.")
                        print(f"   Check logs above for commit errors.")

                    # ✅ CRITICAL: Read shift weights from order object after flush and refresh
                    # The flush ensures updates are in the session, and refresh ensures we have the latest values
                    # We'll commit these updates at the end of the cycle
                    weight_a = float(get_attr_safe(current_order, "weight_shift_a", 0.0) or 0.0)
                    weight_b = float(get_attr_safe(current_order, "weight_shift_b", 0.0) or 0.0)
                    weight_c = float(get_attr_safe(current_order, "weight_shift_c", 0.0) or 0.0)
                    
                    print(f"🔍 [Worker-{po_number}] Shift weights after update: A={weight_a:.2f}, B={weight_b:.2f}, C={weight_c:.2f} {uom}")
                    
                    # ✅ CRITICAL FIX: For PACKING orders, use current delta directly instead of accumulated shift weights
                    # This ensures confirmed_qty matches the delta shown in UI (SCADA now sends bags directly)
                    if order_type == "PACKING":
                        # ✅ CRITICAL: Refresh order BEFORE reading confirmed_qty to get preserved value from before pause
                        db.refresh(current_order)
                        old_confirmed_for_packing = float(get_attr_safe(current_order, "confirmed_qty", 0.0) or 0.0)
                        
                        # ✅ CRITICAL: For PACKING orders after manual confirmation, check if shift weights are also 0
                        # If both confirmed_qty and shift weights are 0, it means manual confirmation just happened
                        weight_a_check = float(get_attr_safe(current_order, "weight_shift_a", 0.0) or 0.0)
                        weight_b_check = float(get_attr_safe(current_order, "weight_shift_b", 0.0) or 0.0)
                        weight_c_check = float(get_attr_safe(current_order, "weight_shift_c", 0.0) or 0.0)
                        shift_weights_all_zero = (weight_a_check == 0.0 and weight_b_check == 0.0 and weight_c_check == 0.0)
                        
                        # Get current production delta directly from SCADA (matches what UI shows)
                        # ✅ CRITICAL: Force refresh to ensure we get the latest baseline after manual confirmation
                        db.refresh(current_order)
                        current_prod_info = get_current_production(current_order, classification, db=db, use_shift_baselines=True)
                        current_delta = float(current_prod_info.get("total", 0.0) or 0.0)
                        
                        # ✅ C31-T26 FIX: DISABLED worker boundary detection
                        # The C31-T26 formula in calculate_deltas() handles 100K rollover naturally:
                        # - When counter > baseline but wrapped (e.g., baseline=99998, current=1)
                        # - raw_delta is negative, C31-T26 calculates: delta = current + (100000 - baseline)
                        # - This gives the correct total (e.g., 1 + 2 = 3 pallets)
                        # - Formula continues to work as counter increases (4, 5, 6...)
                        #
                        # We do NOT reset baseline because:
                        # 1. C31-T26 works correctly without baseline updates
                        # 2. Resetting baseline would make delta start from 0, losing production history
                        # 3. The formula naturally handles the wrapped counter
                        #
                        # Old code that reset baseline has been removed to prevent conflicts.
                        
                        # ✅ C31-T26 FIX: For PACKING orders, use shift_weight as source of truth
                        # shift_weight is calculated by shift_live_update using the correct delta logic
                        # It handles the rollover correctly and is updated every poll cycle
                        
                        db.refresh(current_order)
                        current_confirmed_in_db = float(get_attr_safe(current_order, "confirmed_qty", 0.0) or 0.0)
                        
                        # Get shift weight from shift_live_update (PRIMARY source of truth)
                        current_shift = get_attr_safe(current_order, "current_shift", "A").upper()
                        shift_weight_field = f"weight_shift_{current_shift.lower()}"
                        shift_weight = float(get_attr_safe(current_order, shift_weight_field, 0.0) or 0.0)
                        
                        # ✅ SIMPLE LOGIC: confirmed_qty should match shift_weight
                        # shift_live_update calculates weight correctly using calculate_deltas()
                        # which handles the 100K rollover properly with C31-T26 fix
                        
                        # ✅ C31-T26 FIX: Smart handling using delta INCREASE tracking
                        # The key insight:
                        # - delta from calculate_deltas() is the TOTAL from current baseline
                        # - We need to track how much delta INCREASED since last cycle
                        # - Add only the INCREASE to confirmed_qty (not full delta each time)
                        #
                        # This handles both scenarios correctly:
                        # 1. Normal operation: delta increases 1, 2, 3... we add the increase
                        # 2. After restart: delta starts from 0, we add the increase
                        # 3. After rollover: C31-T26 gives correct total, we use it
                        
                        if current_delta > 0:
                            # Track last delta for this order
                            last_delta = _last_delta_cache_packing.get(po_number, 0.0)
                            
                            # ✅ CRITICAL FIX (Jan 23, 2026): Detect restart by checking if confirmed_qty > delta
                            # OLD BUG: Condition `baseline_used < 5000` failed when baseline was large (e.g., 61646)
                            # FIX: If confirmed_qty exists and is larger than current delta, we're in restart scenario
                            # This handles:
                            # - Initial start: confirmed_qty=0, delta=12 → use delta directly
                            # - After restart: confirmed_qty=3296, delta=12 → add delta to confirmed_qty
                            if current_confirmed_in_db > 0 and current_confirmed_in_db > current_delta:
                                # Post-restart: baseline was re-captured, delta is small relative to existing production
                                # Track delta increase and add to confirmed
                                
                                # ✅ FIX: If current delta is much smaller than cache, cache is STALE
                                # Reset cache so first production after restart counts correctly
                                if last_delta > 0 and current_delta < last_delta * 0.5:
                                    print(f"🔄 [Worker-{po_number}] Stale cache detected: delta={current_delta:.2f} < cache={last_delta:.2f}, resetting")
                                    last_delta = 0.0
                                
                                delta_increase = max(0.0, current_delta - last_delta)
                                
                                if delta_increase > 0.1:  # Meaningful increase
                                    scada_total = current_confirmed_in_db + delta_increase
                                    print(f"➕ [Worker-{po_number}] PACKING RESTART: {current_confirmed_in_db:.2f} + {delta_increase:.2f} = {scada_total:.2f}")
                                else:
                                    scada_total = current_confirmed_in_db
                                    print(f"✅ [Worker-{po_number}] PACKING RESTART: no change (delta_increase={delta_increase:.2f})")
                                
                                # Update cache
                                _last_delta_cache_packing[po_number] = current_delta
                            else:
                                # Initial start or delta caught up to confirmed_qty: use delta directly
                                scada_total = current_delta
                                # Reset cache since we're using delta directly
                                _last_delta_cache_packing[po_number] = 0.0
                                print(f"✅ [Worker-{po_number}] PACKING INITIAL: confirmed_qty = {scada_total:.2f} (delta=total)")
                        else:
                            # No production yet - keep existing
                            scada_total = current_confirmed_in_db
                            print(f"🔒 [Worker-{po_number}] PACKING: preserving confirmed_qty = {scada_total:.2f} (delta=0)")
                    else:
                        # ✅ MILLING: Use same delta-tracking logic as PACKING
                        # Get the current confirmed_qty from DB (this is our base)
                        db.refresh(current_order)
                        current_confirmed_in_db = float(get_attr_safe(current_order, "confirmed_qty", 0.0) or 0.0)
                        
                        # Calculate current total shift weights sum
                        current_total_shift_weights = weight_a + weight_b + weight_c
                        
                        # ✅ CRITICAL: Get the last total shift weights sum we tracked for this order
                        last_total = _last_total_cache_milling.get(po_number, None)
                        
                        # ✅ CRITICAL FIX: Initialize cache on first cycle to match shift weights if not set
                        # This prevents double-counting when confirmed_qty already has the correct value
                        if last_total is None:
                            # First cycle - initialize cache to match current shift weights
                            # This ensures we only track NEW increases from this point forward
                            _last_total_cache_milling[po_number] = current_total_shift_weights
                            last_total = current_total_shift_weights
                            print(f"🔍 [Worker-{po_number}] MILLING: First cycle - initialized cache to {last_total:.2f} to match shift weights (confirmed_qty={current_confirmed_in_db:.2f})")
                        
                        # ✅ CRITICAL FIX: If confirmed_qty already matches shift weights, don't add again
                        # This prevents double-counting when confirmed_qty was already updated correctly
                        if abs(current_confirmed_in_db - current_total_shift_weights) < 0.01:
                            # confirmed_qty already matches shift weights - no need to add
                            scada_total = current_confirmed_in_db
                            # Update cache to track current total
                            _last_total_cache_milling[po_number] = current_total_shift_weights
                            print(f"🔍 [Worker-{po_number}] MILLING: confirmed_qty already matches shift weights ({current_confirmed_in_db:.2f}) - no change needed")
                        else:
                            # Calculate the increase (only count new production)
                            total_increase = max(0.0, current_total_shift_weights - last_total)
                            
                            # ✅ CRITICAL FIX: Only add the increase to current confirmed_qty
                            # This prevents accumulation from recalculating from preserved shift weights
                            if total_increase > 0.01:  # At least 0.01 kg increase (prevents tiny drift)
                                # Total has increased - add only the increase to current confirmed_qty
                                scada_total = current_confirmed_in_db + total_increase
                                # Update the cache with current total for next cycle
                                _last_total_cache_milling[po_number] = current_total_shift_weights
                                print(f"🔍 [Worker-{po_number}] MILLING: Total increased - adding {total_increase:.2f} to {current_confirmed_in_db:.2f} = {scada_total:.2f} (current_total={current_total_shift_weights:.2f}, last_total={last_total:.2f})")
                            else:
                                # No increase - keep current value
                                scada_total = current_confirmed_in_db
                                # Update cache even if no increase (to track current total)
                                _last_total_cache_milling[po_number] = current_total_shift_weights
                                print(f"🔍 [Worker-{po_number}] MILLING: No total increase - keeping: {current_confirmed_in_db:.2f} (current_total={current_total_shift_weights:.2f}, last_total={last_total:.2f}, increase={total_increase:.2f})")
                    
                    display_total = min(scada_total, target_qty)
                    overflow = max(scada_total - target_qty, 0.0)

                    # ✅ CRITICAL: Refresh order AGAIN before reading confirmed_qty to ensure we have the latest value
                    # This is especially important for restarted orders where confirmed_qty might have been updated
                    # in a previous cycle but the object might be stale
                    db.refresh(current_order)
                    old_confirmed = float(get_attr_safe(current_order, "confirmed_qty", 0.0) or 0.0)
                    print(f"🔍 [Worker-{po_number}] Read old_confirmed from database after refresh: {old_confirmed:.2f} {uom}")
                    
                    print(f"🔍 [Worker-{po_number}] Calculated totals: scada_total={scada_total:.2f}, display_total={display_total:.2f}, old_confirmed={old_confirmed:.2f} {uom}")
                    
                    # ✅ CRITICAL FIX: confirmed_qty should ALWAYS follow shift weights
                    # If shift weights are > 0, confirmed_qty MUST be updated to match
                    # Only block if ALL shift weights are 0 AND scada_total is small (< 2.0 kg) - this is SCADA settling
                    shift_weights_sum = weight_a + weight_b + weight_c
                    is_brand_new_still_zero = (old_confirmed == 0.0 and weight_a == 0.0 and weight_b == 0.0 and weight_c == 0.0)
                    
                    if is_brand_new_still_zero and scada_total > 0.0 and scada_total <= 2.0:
                        # Brand new order, first cycle - shift weights still 0 and scada_total is small (SCADA settling)
                        # Keep confirmed_qty at 0 (this is just noise, not real production)
                        print(f"🔒 [Worker-{po_number}] Brand new order first cycle - keeping confirmed_qty at 0.0 (shift weights=0, scada_total={scada_total:.2f} is SCADA settling, will count from next cycle)")
                        final_confirmed = 0.0
                    elif shift_weights_sum > 0.0:
                        # ✅ CRITICAL: Shift weights are > 0, so confirmed_qty MUST match display_total
                        # This handles both new orders (old_confirmed=0) and existing orders (old_confirmed>0)
                        # ✅ CRITICAL FIX: For restarted orders, ALWAYS update to display_total if shift weights increased
                        # Don't use max() here - we want to update even if old_confirmed is higher (shouldn't happen, but be safe)
                        # The safeguard at line 6811 will prevent decreases
                        if display_total > old_confirmed:
                            # Production increased - update confirmed_qty
                            final_confirmed = display_total
                            print(f"✅ [Worker-{po_number}] confirmed_qty updating: {old_confirmed:.2f} → {final_confirmed:.2f} (scada_total={scada_total:.2f}, shift weights: A={weight_a:.2f}, B={weight_b:.2f}, C={weight_c:.2f})")
                        elif display_total == old_confirmed:
                            # No change - keep existing
                            final_confirmed = old_confirmed
                            print(f"🔍 [Worker-{po_number}] confirmed_qty unchanged: {old_confirmed:.2f} (scada_total={scada_total:.2f}, shift weights: A={weight_a:.2f}, B={weight_b:.2f}, C={weight_c:.2f})")
                        else:
                            # display_total < old_confirmed (shouldn't happen, but use max to prevent decrease)
                            final_confirmed = max(old_confirmed, display_total)
                            print(f"⚠️ [Worker-{po_number}] confirmed_qty preserved: {final_confirmed:.2f} (display_total={display_total:.2f} < old_confirmed={old_confirmed:.2f}, preventing decrease)")
                        
                        # ✅ CRITICAL: Double-check - if shift weights increased but confirmed_qty didn't, force update
                        if shift_weights_sum > old_confirmed and final_confirmed <= old_confirmed:
                            print(f"🚨 [Worker-{po_number}] CRITICAL: shift_weights_sum={shift_weights_sum:.2f} > old_confirmed={old_confirmed:.2f} but final_confirmed={final_confirmed:.2f} - FORCING update!")
                            final_confirmed = display_total
                    elif scada_total > 2.0:
                        # Shift weights are 0 but scada_total is large (real production detected)
                        # This shouldn't happen if first cycle logic worked, but if it does, count it!
                        print(f"⚠️ [Worker-{po_number}] Shift weights=0 but scada_total={scada_total:.2f} is large (real production), counting it!")
                        final_confirmed = display_total
                    else:
                        # old_confirmed is 0, shift weights are 0, scada_total is small - keep at 0
                        final_confirmed = 0.0
                        print(f"🔍 [Worker-{po_number}] No production detected - keeping confirmed_qty at 0.0 (scada_total={scada_total:.2f}, shift weights: A={weight_a:.2f}, B={weight_b:.2f}, C={weight_c:.2f})")
                    
                    # ✅ CRITICAL FIX (Dec 12, 2025): confirmed_qty can ONLY INCREASE, never decrease
                    # This is the GOLDEN RULE - production tracking must be monotonically increasing
                    new_production_value = display_total
                    
                    # Only update if new value is GREATER than existing
                    if new_production_value > old_confirmed:
                        final_confirmed = new_production_value
                        print(f"✅ [Worker-{po_number}] Increasing confirmed_qty: {old_confirmed:.2f} → {final_confirmed:.2f}")
                    else:
                        final_confirmed = old_confirmed  # PRESERVE existing value - never decrease
                        print(f"🔒 [Worker-{po_number}] Preserving confirmed_qty: {old_confirmed:.2f} (new calc {new_production_value:.2f} is not higher)")
                    
                    # ✅ CRITICAL FIX (Jan 22, 2026): Cap confirmed_qty at target_qty
                    # Even if old_confirmed was incorrectly above target (from overflow transfer or bug),
                    # confirmed_qty should NEVER exceed target. Overflow is tracked separately.
                    if target_qty > 0 and final_confirmed > target_qty:
                        print(f"⚠️ [Worker-{po_number}] CAPPING confirmed_qty: {final_confirmed:.2f} → {target_qty:.2f} (was above target)")
                        final_confirmed = target_qty
                    
                    # ✅ CRITICAL: Set confirmed_qty - this MUST happen for ALL orders, EVERY cycle
                    # No conditions, no exceptions - if shift weights show production, confirmed_qty must be set
                    # This is especially critical for orders after the first one that are automatically started
                    print(f"🔍 [Worker-{po_number}] Setting confirmed_qty: old={old_confirmed:.2f}, new={final_confirmed:.2f}, shift_weights_sum={shift_weights_sum:.2f}, display_total={display_total:.2f}")
                    
                    # ✅ CRITICAL: Use direct assignment as primary method, set_attr_safe as fallback
                    # This ensures confirmed_qty is ALWAYS set, even if set_attr_safe has issues
                    if hasattr(current_order, "confirmed_qty"):
                        current_order.confirmed_qty = final_confirmed
                        print(f"✅ [Worker-{po_number}] confirmed_qty set via direct assignment: {final_confirmed:.2f}")
                    else:
                        print(f"⚠️ [Worker-{po_number}] confirmed_qty attribute not found, using set_attr_safe")
                        set_attr_safe(current_order, "confirmed_qty", final_confirmed)
                    
                    # ✅ CRITICAL: Double-check that confirmed_qty was actually set
                    # Sometimes set_attr_safe might not work if the attribute doesn't exist or has issues
                    try:
                        test_confirmed = float(get_attr_safe(current_order, "confirmed_qty", 0.0) or 0.0)
                        if abs(test_confirmed - final_confirmed) > 0.01:
                            print(f"⚠️ [Worker-{po_number}] WARNING: confirmed_qty not set correctly! Expected {final_confirmed:.2f} but got {test_confirmed:.2f}")
                            # Try direct assignment
                            if hasattr(current_order, "confirmed_qty"):
                                current_order.confirmed_qty = final_confirmed
                                print(f"✅ [Worker-{po_number}] Fixed confirmed_qty using direct assignment: {final_confirmed:.2f}")
                    except Exception as e:
                        print(f"⚠️ [Worker-{po_number}] Error checking confirmed_qty: {e}")
                    
                    # ✅ CRITICAL: Always log confirmed_qty updates for debugging
                    if abs(final_confirmed - old_confirmed) > 0.0001:  # Log only if there's a meaningful change
                        if final_confirmed > old_confirmed:
                            print(f"📌 [Worker-{po_number}] ✅ confirmed_qty UPDATED: {old_confirmed:.2f} → {final_confirmed:.2f}/{target_qty:.2f} (sum of shifts: A={weight_a:.2f}, B={weight_b:.2f}, C={weight_c:.2f})")
                        elif final_confirmed < old_confirmed:
                            print(f"🔒 [Worker-{po_number}] confirmed_qty preserved at {final_confirmed:.2f} (prevented decrease from {old_confirmed:.2f} to {display_total:.2f})")
                    else:
                        # Log even if no change, to confirm the value is being set
                        if shift_weights_sum > 0.0:
                            print(f"🔍 [Worker-{po_number}] confirmed_qty = {final_confirmed:.2f}/{target_qty:.2f} (no change, shift weights: A={weight_a:.2f}, B={weight_b:.2f}, C={weight_c:.2f})")
                    
                    # ✅ CRITICAL: Add order to session and commit confirmed_qty immediately
                    # This ensures the value is persisted to database right away, not waiting for end of cycle
                    # This is especially important for automatically started orders and restarted orders
                    # ✅ CRITICAL: ALWAYS add order to session, even if it's already there
                    # This ensures confirmed_qty changes are tracked by SQLAlchemy
                    # ✅ CRITICAL: For restarted orders, we MUST commit even if final_confirmed == old_confirmed
                    # This ensures the database has the latest value, especially after restart
                    db.add(current_order)
                    db.flush()
                    
                    # ✅ CRITICAL: Commit confirmed_qty immediately to ensure it's stored in database
                    # This prevents the issue where confirmed_qty is 0 until order restart
                    # ✅ CRITICAL: For automatically started orders and restarted orders, this commit is ESSENTIAL
                    # Without it, confirmed_qty will remain stale even though shift weights are correct
                    # ✅ CRITICAL: Commit EVERY cycle when shift weights > 0, even if confirmed_qty didn't change
                    # This ensures database always has the latest value, especially for restarted orders
                    try:
                        db.commit()
                        if abs(final_confirmed - old_confirmed) > 0.01:
                            print(f"✅ [Worker-{po_number}] ✅✅✅ confirmed_qty UPDATED and committed: {old_confirmed:.2f} → {final_confirmed:.2f} ✅✅✅")
                        else:
                            print(f"✅ [Worker-{po_number}] ✅✅✅ confirmed_qty committed (no change): {final_confirmed:.2f} (shift_weights_sum={shift_weights_sum:.2f}) ✅✅✅")
                    except Exception as e:
                        print(f"⚠️ [Worker-{po_number}] ⚠️⚠️⚠️ FAILED to commit confirmed_qty: {e} ⚠️⚠️⚠️")
                        import traceback
                        traceback.print_exc()
                        db.rollback()
                        # ✅ CRITICAL: Retry commit after rollback
                        try:
                            # Re-read shift weights to ensure we have latest values
                            db.refresh(current_order)
                            weight_a_retry = float(get_attr_safe(current_order, "weight_shift_a", 0.0) or 0.0)
                            weight_b_retry = float(get_attr_safe(current_order, "weight_shift_b", 0.0) or 0.0)
                            weight_c_retry = float(get_attr_safe(current_order, "weight_shift_c", 0.0) or 0.0)
                            shift_weights_sum_retry = weight_a_retry + weight_b_retry + weight_c_retry
                            display_total_retry = min(shift_weights_sum_retry, target_qty)
                            
                            # Force update confirmed_qty to match shift weights
                            current_order.confirmed_qty = display_total_retry
                            db.add(current_order)
                            db.commit()
                            print(f"✅ [Worker-{po_number}] confirmed_qty committed on retry: {display_total_retry:.2f} (recalculated from shift weights)")
                        except Exception as e2:
                            print(f"❌ [Worker-{po_number}] CRITICAL: Retry commit also failed: {e2}")
                    
                    # ✅ CRITICAL: Verify confirmed_qty was set correctly after commit
                    db.refresh(current_order)
                    verified_confirmed = float(get_attr_safe(current_order, "confirmed_qty", 0.0) or 0.0)
                    if abs(verified_confirmed - final_confirmed) > 0.01:
                        print(f"⚠️ [Worker-{po_number}] WARNING: confirmed_qty mismatch after commit! Set to {final_confirmed:.2f} but database shows {verified_confirmed:.2f}")
                        # Try to fix it
                        set_attr_safe(current_order, "confirmed_qty", final_confirmed)
                        db.add(current_order)
                        db.commit()
                        db.refresh(current_order)
                        verified_confirmed = float(get_attr_safe(current_order, "confirmed_qty", 0.0) or 0.0)
                        if abs(verified_confirmed - final_confirmed) > 0.01:
                            print(f"❌ [Worker-{po_number}] CRITICAL: confirmed_qty still wrong after retry! Database shows {verified_confirmed:.2f}, expected {final_confirmed:.2f}")
                        else:
                            print(f"✅ [Worker-{po_number}] confirmed_qty fixed after retry: {verified_confirmed:.2f}")
                    else:
                        print(f"✅ [Worker-{po_number}] confirmed_qty verified in database: {verified_confirmed:.2f}")
                    
                    # ✅ CRITICAL FIX (Dec 12, 2025): Final safeguard - only INCREASE confirmed_qty
                    # NEVER force confirmed_qty to a lower value, even if display_total is different
                    if shift_weights_sum > 0.0:
                        final_verified = float(get_attr_safe(current_order, "confirmed_qty", 0.0) or 0.0)
                        # Only update if display_total is HIGHER than current confirmed_qty
                        if display_total > final_verified:
                            print(f"✅ [Worker-{po_number}] FINAL CHECK: Increasing confirmed_qty {final_verified:.2f} → {display_total:.2f}")
                            current_order.confirmed_qty = display_total
                            db.add(current_order)
                            db.commit()
                            db.refresh(current_order)
                            final_check = float(get_attr_safe(current_order, "confirmed_qty", 0.0) or 0.0)
                            print(f"✅ [Worker-{po_number}] Final confirmed_qty update successful: {final_check:.2f}")
                        else:
                            # Preserve existing - never decrease
                            print(f"🔒 [Worker-{po_number}] FINAL CHECK: Preserving confirmed_qty at {final_verified:.2f} (display_total={display_total:.2f} is not higher)")
                    
                    # ✅ OVERFLOW STORAGE: Store overflow for transfer to next order of same type
                    if overflow > 0:
                        set_attr_safe(current_order, "overflow_weight", overflow)
                        validation_method = get_attr_safe(current_order, "validation_method", "UNKNOWN")
                        print(f"💾 [Worker-{po_number}] Stored overflow: {overflow:.2f} for next {order_type} order")
                        print(f"   📋 validation_method={validation_method} (must be 'Automatic' for overflow transfer to work)")

                    # PACKING PER SCALE
                    try:
                        if order_type == "PACKING":
                            deltas_main = {}  # (Fill with your normal scale-deltas logic)
                            update_order_scales(current_order, deltas_main)
                    except Exception as e:
                        print(f"⚠️ [Worker-{po_number}] update_order_scales: {e}")

                    # ✅ CRITICAL FIX (Jan 23, 2026): Check completion BEFORE updating UI status
                    # This prevents progress from continuing to increase after target is reached for packing orders
                    completion = check_order_completion(current_order, classification)
                    
                    # ✅ CRITICAL FIX: For packing orders, ensure display_total is capped at target_qty
                    # Once target is reached, display_total should never increase further
                    if order_type == "PACKING" and completion.get("is_complete", False):
                        # Order is complete - cap display_total at target_qty to prevent further increases
                        display_total = min(display_total, target_qty)
                        print(f"🔒 [Worker-{po_number}] PACKING order complete - capping display_total at {target_qty:.2f} {uom}")

                    # UI STATUS
                    progress = min(100.0, (display_total / target_qty) * 100.0 if target_qty > 0 else 0.0)
                    set_order_validation_state(po_number, {
                        "isrunning": True,  # ✅ CRITICAL: Must match the key checked in is_order_validating()
                        "progress_pct": progress,
                        "current_production": display_total,
                        "target": target_qty,
                        "status": "running",
                        "unit": uom,
                    })

                    # COMPLETION (already checked above, but handle here)
                    if completion.get("is_complete", False):
                        print(f"🏁 [Worker-{po_number}] ORDER COMPLETE!")
                        order_type_completed = classification.get("order_type", "UNKNOWN")
                        print(f"🔍 [Worker-{po_number}] Completed order type: {order_type_completed}")
                        
                        # ✅ CRITICAL CHANGE: Do NOT send to SAP when order is validated
                        # Only mark as Validated - let shift-end auto confirm OR manual push handle SAP sending
                        # DO NOT set shift_end_time - this prevents auto-trigger on validation
                        # SAP confirmation only happens at actual shift end or manual push
                        print(f"📋 [Worker-{po_number}] Order validated - will be sent to SAP at shift end or manual push only")
                        print(f"📋 [Worker-{po_number}] NOT setting shift_end_time to prevent auto-trigger - will wait for actual shift end")
                        
                        # ✅ DO NOT set shift_end_time - this would trigger auto-confirm immediately
                        # Only actual shift end should trigger auto-confirm
                        # current_shift = get_attr_safe(current_order, "current_shift", None)
                        # if current_shift:
                        #     set_attr_safe(current_order, "shift_end_time", datetime.now())
                        #     print(f"📅 [Worker-{po_number}] Set shift_end_time for shift {current_shift}")
                        
                        # ✅ CRITICAL: Keep current_shift so shift-end auto confirmation knows which shift to process
                        # DO NOT clear current_shift - this allows shift-end auto confirmation to find the order
                        current_shift_at_validation = get_attr_safe(current_order, "current_shift", None)
                        if current_shift_at_validation:
                            print(f"📋 [Worker-{po_number}] Keeping current_shift={current_shift_at_validation} so shift-end auto confirmation can process it")
                        
                        # ✅ Feb 5, 2026: Use "Completed" when order reaches 100% tracking
                        # "Validated" is reserved for after successful SAP confirmation
                        set_attr_safe(current_order, "status", "Completed")
                        # ✅ FIX (Jan 22, 2026): Set validation_method based on how order COMPLETED, not started
                        # If order completes during auto-validation, mark as "Automatic" for overflow transfer
                        # Overflow only transfers from orders with validation_method == "Automatic"
                        if is_auto_validator_enabled():
                            set_attr_safe(current_order, "validation_method", "Automatic")
                            print(f"✅ [Worker-{po_number}] Set validation_method=Automatic (completed during auto-validation)")
                        else:
                            # Manual completion - keep as Manual (no overflow transfer)
                            set_attr_safe(current_order, "validation_method", "Manual")
                            print(f"✅ [Worker-{po_number}] Set validation_method=Manual (completed outside auto-validation)")
                        set_attr_safe(current_order, "is_target_reached", True)
                        # ✅ Set is_final_sent=False so shift-end auto confirm knows to send final confirmation
                        set_attr_safe(current_order, "is_final_sent", False)
                        # ✅ FIX (Jan 23, 2026): Set confirmed_qty to target when order is completed
                        # This ensures "Current" column shows the correct value for completed orders
                        set_attr_safe(current_order, "confirmed_qty", target_qty)
                        print(f"✅ [Worker-{po_number}] Set confirmed_qty={target_qty:.2f} (target) on completion")
                        # ✅ DO NOT clear current_shift - shift-end auto confirmation needs it
                        # set_attr_safe(current_order, "current_shift", None)
                        
                        # ✅ CRITICAL: Commit order status change immediately
                        db.add(current_order)
                        db.commit()
                        db.refresh(current_order)
                        
                        # ✅ CRITICAL: Verify status was updated
                        final_status = get_attr_safe(current_order, "status", "UNKNOWN")
                        print(f"✅ [Worker-{po_number}] Order status updated to: {final_status}")
                        
                        if final_status != "Completed":
                            print(f"⚠️ [Worker-{po_number}] WARNING: Status is {final_status}, expected Completed!")
                        
                        # =============================================================================
                        # SCALE LOCKING: Release scales when order completes
                        # =============================================================================
                        release_scales_and_start_waiting_orders(po_number, current_order, classification, db)
                        
                        # ✅ CRITICAL: Stop worker state immediately so scheduler doesn't think order is still running
                        # Also prevents any further shift change detection that would trigger SAP confirmation
                        print(f"🛑 [Worker-{po_number}] Stopping worker state immediately - order validated, no SAP confirmation until shift end")
                        set_order_validation_state(po_number, {"isrunning": False})
                        
                        # ✅ CRITICAL: Wait a moment for state to propagate
                        time.sleep(0.5)
                        
                        order_completed_normally = True
                        print(f"✅ [Worker-{po_number}] Order validated - worker stopped. SAP confirmation will be sent at shift end or manual push only")
                        break
                    db.commit()

            except Exception as e:
                print(f"❌ [Worker-{po_number}] Error in cycle: {e}")
                import traceback
                traceback.print_exc()
                time.sleep(WORKER_WAIT)
                continue
            time.sleep(WORKER_WAIT)

        print(f"🏁 [Worker-{po_number}] Worker loop exited")

    except Exception as e:
        print(f"❌ [Worker-{po_number}] Fatal error: {e}")
        import traceback
        traceback.print_exc()

    finally:
        try:
            remove_order_validation_state(po_number)
        except Exception:
            pass
        print(f"🛑 [Worker-{po_number}] Auto-validator stopped")
        if order_completed_normally and is_auto_validator_enabled():
            try:
                print(f"🔁 [Worker-{po_number}] Order completed normally - triggering scheduler to start next order")
                print(f"🔍 [Worker-{po_number}] order_completed_normally={order_completed_normally}, is_auto_validator_enabled()={is_auto_validator_enabled()}")
                print(f"🔍 [Worker-{po_number}] Order type that completed: {classification.get('order_type', 'UNKNOWN') if 'classification' in locals() else 'UNKNOWN'}")
                
                # ✅ CRITICAL: Ensure worker state is fully cleared before scheduler runs
                # Sometimes the state might not be fully cleared yet
                set_order_validation_state(po_number, {"isrunning": False})
                time.sleep(0.5)  # Wait for state to propagate
                
                _schedule_next_orders_after_completion()
                print(f"✅ [Worker-{po_number}] Scheduler completed")
            except Exception as e:
                print(f"⚠️ [Worker-{po_number}] ⚠️⚠️⚠️ FAILED to schedule next order: {e} ⚠️⚠️⚠️")
                import traceback
                traceback.print_exc()
        else:
            reason = []
            if not order_completed_normally:
                reason.append("order_completed_normally=False")
            if not is_auto_validator_enabled():
                reason.append("auto_validator not enabled")
            print(f"🔍 [Worker-{po_number}] Not triggering scheduler: {', '.join(reason) if reason else 'unknown reason'}")

# =============================================================================
# API ENDPOINTS
# =============================================================================

@orders_bp.route("", methods=["GET"])
def list_orders():
    if ProcessOrder is None:
        return jsonify([])
    status = request.args.get("status")
    statuses = request.args.get("statuses")
    with _db_session() as db:
        q = db.query(ProcessOrder)
        if statuses:
            status_list = [s.strip() for s in statuses.split(",")]
            q = q.filter(ProcessOrder.status.in_(status_list))
        elif status and status != "All":
            q = q.filter(ProcessOrder.status == status)
        rows = q.order_by(ProcessOrder.hercules_priority.asc(), ProcessOrder.id.asc()).all()
    return jsonify([serialize_order(r) for r in rows])

@orders_bp.route("/<string:po_number>/start", methods=["POST"])
def start_order(po_number: str):
    """
    Start validation for a specific order.
    ✅ Supports parallel validation (per-order threads).
    ✅ Ensures by-product scales (scale1/2/3 + *_qty) are stored for MILLING.
    ✅ On restart after STOP: uses FRESH baselines, preserves confirmed_qty.
    """
    if ProcessOrder is None:
        raise BadRequest("ProcessOrder model not available")

    with _db_session() as db:
        order = db.query(ProcessOrder).filter(
            ProcessOrder.order_id == po_number
        ).first()

        if not order:
            raise NotFound(f"Order {po_number} not found")

        # ✅ CRITICAL: Refresh order from database to get latest values
        db.refresh(order)
        
        # ✅ CRITICAL FIX: Preserve byproduct quantities IMMEDIATELY after refresh
        # These may be lost during subsequent modifications and commits
        preserved_scale1_qty_start = float(get_attr_safe(order, "scale1_qty", 0.0) or 0.0)
        preserved_scale2_qty_start = float(get_attr_safe(order, "scale2_qty", 0.0) or 0.0)
        preserved_scale3_qty_start = float(get_attr_safe(order, "scale3_qty", 0.0) or 0.0)
        if preserved_scale1_qty_start > 0 or preserved_scale2_qty_start > 0 or preserved_scale3_qty_start > 0:
            print(f"✅ [{po_number}] Preserved byproduct quantities on start:")
            print(f"   scale1_qty: {preserved_scale1_qty_start:.4f}")
            print(f"   scale2_qty: {preserved_scale2_qty_start:.4f}")
            print(f"   scale3_qty: {preserved_scale3_qty_start:.4f}")
        
        # ✅ CRITICAL: Check order status first - if status is Pending, clear any stale validation state
        order_status = get_attr_safe(order, "status", "").strip()
        if order_status == "Pending":
            # Order is Pending, so it should NOT be validating - clear any stale validation state
            if is_order_validating(po_number):
                print(f"⚠️ [Start-{po_number}] Order status is Pending but validation state shows running - clearing stale state")
                set_order_validation_state(po_number, {"isrunning": False})
        elif order_status in ("Validated", "Completed"):
            # Order is already completed/validated - cannot start
            return jsonify({
                "success": False,
                "message": f"Order {po_number} is already validated and cannot be restarted"
            }), 400
        elif order_status != "InProgress":
            # Order is not in a valid state to start
            return jsonify({
                "success": False,
                "message": f"Cannot start order with status '{order_status}'. Order must be Pending or InProgress."
            }), 400
        
        # ✅ Check validation state only if order is InProgress
        # If order is Pending, we already cleared stale state above
        if order_status == "InProgress" and is_order_validating(po_number):
            return jsonify({
                "success": False,
                "message": f"Order {po_number} is already being validated"
            }), 400
        
        # ✅ CRITICAL: Clear production cache for this order on restart
        # This ensures we start tracking from 0 after baseline is captured
        # ✅ CRITICAL: For brand new orders (after deleting old order), ALWAYS clear cache
        # This prevents new orders from inheriting cached values from deleted orders
        # ✅ CRITICAL: ALWAYS clear cache unconditionally - don't check if it exists
        # This ensures we remove any stale cache from deleted orders with the same PO number
        for shift_code in ["a", "b", "c"]:
            cache_key = (po_number, shift_code)
            # ✅ CRITICAL: ALWAYS clear cache - use pop() with default to avoid KeyError
            # This ensures we remove cache even if it exists from a deleted order
            old_cache_value = _last_shift_production_cache.pop(cache_key, None)
            if old_cache_value is not None:
                print(f"🧹 [Start-{po_number}] Cleared production cache for shift {shift_code.upper()} (had value: {old_cache_value:.2f})")
            else:
                # Cache doesn't exist - this is fine, but log it for brand new orders
                print(f"🔍 [Start-{po_number}] No production cache found for shift {shift_code.upper()} (will be initialized fresh)")
            
            # ✅ CRITICAL: Also clear max weight cache for brand new orders
            # Only initialize max weight cache if we have preserved weight (restart scenario)
            weight_field = f"weight_shift_{shift_code}"
            preserved_weight = float(get_attr_safe(order, weight_field, 0.0) or 0.0)
            if preserved_weight > 0.0:
                # Restart scenario - initialize max weight cache from preserved weight
                # But first, clear any existing cache to ensure clean state
                old_max_cache = _max_shift_weight_cache.pop(cache_key, None)
                if old_max_cache is not None and old_max_cache != preserved_weight:
                    print(f"🧹 [Start-{po_number}] Cleared old max weight cache for shift {shift_code.upper()} (had value: {old_max_cache:.2f}, will use preserved: {preserved_weight:.2f})")
                _max_shift_weight_cache[cache_key] = preserved_weight
                print(f"🔍 [Start-{po_number}] Initialized max weight cache for shift {shift_code.upper()} to {preserved_weight:.2f}")
            else:
                # Brand new order - ALWAYS clear max weight cache if it exists (from deleted order)
                old_max_cache = _max_shift_weight_cache.pop(cache_key, None)
                if old_max_cache is not None:
                    print(f"🧹 [Start-{po_number}] Cleared max weight cache for shift {shift_code.upper()} (had value: {old_max_cache:.2f} from deleted order)")
                else:
                    print(f"🔍 [Start-{po_number}] No max weight cache for shift {shift_code.upper()} (brand new order)")
        
        # ✅ CRITICAL: Read confirmed_qty IMMEDIATELY after refreshing (before any modifications)
        # Read directly from the order object to ensure we get the actual database value
        preserved_confirmed_qty = float(order.confirmed_qty if hasattr(order, 'confirmed_qty') and order.confirmed_qty is not None else 0.0)
        if preserved_confirmed_qty > 0.0:
            print(f"🔍 [{po_number}] Found existing confirmed_qty in DB: {preserved_confirmed_qty} - will preserve on restart")
        else:
            print(f"🔍 [{po_number}] confirmed_qty is 0 or None in DB - will set to 0 for new order")
        
        # ✅ CRITICAL: Preserve shift weights (DO NOT reset them!)
        preserved_weight_a = float(get_attr_safe(order, "weight_shift_a", 0.0) or 0.0)
        preserved_weight_b = float(get_attr_safe(order, "weight_shift_b", 0.0) or 0.0)
        preserved_weight_c = float(get_attr_safe(order, "weight_shift_c", 0.0) or 0.0)
        if preserved_weight_a > 0.0 or preserved_weight_b > 0.0 or preserved_weight_c > 0.0:
            print(f"🔍 [{po_number}] Found existing shift weights in DB: A={preserved_weight_a:.2f}, B={preserved_weight_b:.2f}, C={preserved_weight_c:.2f} - will preserve on restart")
        else:
            print(f"🔍 [{po_number}] All shift weights are 0 in DB - new order")

        # Allow re-init ONLY if InProgress but scales are empty (legacy fix)
        if order.status == "InProgress":
            has_scales = any([
                get_attr_safe(order, "scale1"),
                get_attr_safe(order, "scale2"),
                get_attr_safe(order, "scale3"),
            ])
            if has_scales:
                return jsonify({
                    "success": False,
                    "message": "Order already InProgress with scales set"
                }), 400
            else:
                print(f"♻️ Re-initialising InProgress order {po_number} (scale1/2/3 were empty)")

        # Debug: Log order details before classification
        order_version = (get_attr_safe(order, "version") or "").strip().upper()
        order_material = str(get_attr_safe(order, "material") or "").strip()
        print(f"🔍 [Start-{po_number}] Classifying order: version='{order_version}', material='{order_material}'")
        
        classification = classify_order(order)
        if classification.get("error"):
            error_msg = classification['error']
            print(f"❌ [Start-{po_number}] Classification failed: {error_msg}")
            raise BadRequest(f"Classification failed: {error_msg}")

        equipment = classification.get("equipment", [])
        if not equipment:
            raise BadRequest("No equipment mapped for this order")

        order_type_new = classification["order_type"]
        set_attr_safe(order, "order_type", order_type_new)

        # =============================================================================
        # ✅ Jan 30, 2026: SCALE-BASED START (not priority-based)
        # Orders with FREE scales can start regardless of priority
        # Priority only matters within same-scale conflict groups
        # (Removed strict priority enforcement - priority 5 with free scales can start)
        # =============================================================================

        # =============================================================================
        # SCALE LOCKING: Check if scales are available before starting validation
        # =============================================================================
        # Get all scales for this order (equipment + byproduct scales)
        # Use get_all_scales_for_order to ensure we get:
        # - Main equipment scales from classification
        # - Byproduct scales from classification (for new orders)
        # - Byproduct scales from order object (for restarted orders where scale1/2/3 are already set)
        # ✅ CRITICAL: Include byproduct scales to prevent conflicts when orders share byproduct scales
        all_scales = get_all_scales_for_order(order, classification, include_byproduct=True)
        
        # Try to lock all scales
        print(f"🔒 [{po_number}] Attempting to lock scales: {all_scales}")
        priority = int(get_attr_safe(order, "hercules_priority", 100) or get_attr_safe(order, "priority", 100) or 100)
        version = get_attr_safe(order, "version", "").upper().strip()
        has_conflict, locked_scales, conflict_details, preempted_orders = lock_scales(
            po_number, all_scales, priority, version, order_type_new
        )
        
        # ✅ CRITICAL FIX: Add manually started order to queue immediately
        # This ensures it participates in conflict detection and lock management
        add_to_queue(po_number, all_scales, priority, version, order_type_new)
        
        # ✅ Handle preempted orders - signal them to pause
        if preempted_orders:
            print(f"⚠️ [{po_number}] Higher priority - preempting orders: {preempted_orders}")
            for preempted_po in preempted_orders:
                # Signal the preempted order's worker to stop
                set_order_validation_state(preempted_po, {"isrunning": False})
                print(f"🛑 [{po_number}] Signaled order {preempted_po} to stop (preempted by higher priority)")
                # ✅ C31-T29: Also update database status to Pending (was only in-memory, UI showed InProgress)
                preempted_order = db.query(ProcessOrder).filter(ProcessOrder.order_id == preempted_po).first()
                if preempted_order:
                    set_attr_safe(preempted_order, "status", "Pending")
                    db.add(preempted_order)
                    db.commit()
                    print(f"📋 [{po_number}] Set preempted order {preempted_po} status to Pending in database")
        
        # Check if ALL scales were locked successfully
        all_scales_locked = not has_conflict and len(locked_scales) == len(all_scales)
        
        if conflict_details:
            print(f"⚠️ [{po_number}] Scale conflicts detected: {conflict_details}")
        
        if not all_scales_locked:
            # ✅ CRITICAL FIX: Scales are locked by another order - DO NOT start, keep as Pending
            # This prevents scale tracking inaccuracy from multiple orders reading same scales
            print(f"🛑 [{po_number}] BLOCKED: Scales are locked by another order. Keeping status as Pending.")
            print(f"   Required scales: {all_scales}")
            print(f"   Conflict details: {conflict_details}")
            
            # Release any partially locked scales (we need all or nothing)
            if locked_scales:
                release_scales(po_number, locked_scales)
                print(f"🔓 [{po_number}] Released partially locked scales: {locked_scales}")
            
            # DO NOT change status - keep order as Pending
            # DO NOT add to queue - order must wait for higher priority to complete
            # The frontend will show this order with a priority number indicating its position
            
            return jsonify({
                "success": False,
                "po_number": po_number,
                "status": "Pending",
                "order_type": order_type_new,
                "equipment": equipment,
                "message": f"Cannot start - scales are locked by another order. Please wait for higher priority orders to complete first.",
                "scales_locked": True,
                "conflict_details": conflict_details,
                "required_scales": all_scales
            }), 409  # 409 Conflict
        
        print(f"✅ [{po_number}] All scales locked successfully: {locked_scales}")
        
        # ✅ CRITICAL FIX: Mark order as running in queue
        # This ensures get_scale_usage_status() and other endpoints see it as RUNNING
        set_order_running(po_number)
        
        # ✅ CRITICAL FIX: Detect restart by checking if byproduct tags are already set
        # On restart, we should NOT reset byproduct baselines - they need to be preserved
        existing_scale1_tag = get_attr_safe(order, "scale1", None)
        existing_scale2_tag = get_attr_safe(order, "scale2", None)
        existing_scale3_tag = get_attr_safe(order, "scale3", None)
        is_restart_with_byproducts = (
            (existing_scale1_tag is not None and existing_scale1_tag != "") or
            (existing_scale2_tag is not None and existing_scale2_tag != "") or
            (existing_scale3_tag is not None and existing_scale3_tag != "")
        )
        if is_restart_with_byproducts:
            print(f"📌 [{po_number}] RESTART detected - will preserve byproduct baselines")
        
        # ✅ CRITICAL: FIRST reset ALL baseline columns to 0 to ensure clean slate
        print(f"🔄 [{po_number}] Resetting all baseline columns to 0 before capturing fresh SCADA values...")
        # PACKING: Bag counter baselines
        set_attr_safe(order, "baseline_sl601_counter", 0.0)
        set_attr_safe(order, "baseline_sl602_counter", 0.0)
        set_attr_safe(order, "baseline_sl603_counter", 0.0)
        set_attr_safe(order, "baseline_sl606_counter", 0.0)
        set_attr_safe(order, "baseline_sl607_counter", 0.0)
        # MILLING: Flour/Bran output baselines
        set_attr_safe(order, "baseline_wg101", 0.0)
        set_attr_safe(order, "baseline_wg201", 0.0)
        set_attr_safe(order, "baseline_wg202", 0.0)
        set_attr_safe(order, "baseline_wg301", 0.0)
        set_attr_safe(order, "baseline_wg302", 0.0)
        set_attr_safe(order, "baseline_wg501", 0.0)
        # ✅ CRITICAL FIX: Only reset byproduct baselines on FIRST start, not restart
        if not is_restart_with_byproducts:
            set_attr_safe(order, "baseline_wg502", 0.0)
            set_attr_safe(order, "baseline_wg503", 0.0)
        else:
            # Preserve existing byproduct baselines on restart
            preserved_wg502 = float(get_attr_safe(order, "baseline_wg502", 0.0) or 0.0)
            preserved_wg503 = float(get_attr_safe(order, "baseline_wg503", 0.0) or 0.0)
            print(f"📌 [{po_number}] Preserving byproduct baselines: WG502={preserved_wg502:.2f}, WG503={preserved_wg503:.2f}")
        # WATER DOSING METER baselines
        set_attr_safe(order, "baseline_dm101", 0.0)
        set_attr_safe(order, "baseline_dm102", 0.0)
        set_attr_safe(order, "baseline_dm201", 0.0)
        set_attr_safe(order, "baseline_dm202", 0.0)
        set_attr_safe(order, "baseline_dm203", 0.0)
        
        # ✅ CRITICAL: Commit baseline reset to database BEFORE capturing fresh SCADA values
        db.add(order)
        db.flush()  # Flush to ensure reset is in database before SCADA capture
        
        # ✅ VERIFY: Refresh order to confirm baselines were reset/preserved in database
        db.refresh(order)
        baseline_wg502_check = float(get_attr_safe(order, "baseline_wg502", 0.0) or 0.0)
        baseline_wg501_check = float(get_attr_safe(order, "baseline_wg501", 0.0) or 0.0)
        if is_restart_with_byproducts:
            print(f"✅ [{po_number}] Main baselines reset, byproduct baselines preserved")
        else:
            print(f"✅ [{po_number}] All baseline columns reset to 0 and flushed to database")
        print(f"🔍 [{po_number}] Verification: baseline_wg502={baseline_wg502_check}, baseline_wg501={baseline_wg501_check}")

        # ✅ CAPTURE FRESH SCADA BASELINES (always new on start!)
        # 💥 CRITICAL FIX: Use robust multi-reading capture logic (copied from init_and_start_order_worker)
        # This ensures we get truly fresh values after a pause, even if SCADA is slow to update
        print(f"🧹 [{po_number}] Clearing SCADA cache before capturing baselines...")
        try:
            from services.scale_service import clear_scada_cache
            clear_scada_cache()
            print(f"✅ [{po_number}] SCADA cache cleared")
        except Exception as e:
            print(f"⚠️ [{po_number}] Could not clear SCADA cache: {e}")
        
        # ✅ CRITICAL: Wait after clearing cache
        import time
        time.sleep(0.3)
        
        # ✅ CRITICAL: Longer delay to ensure SCADA values have settled
        print(f"⏳ [{po_number}] Waiting for SCADA values to settle before capturing baselines...")
        time.sleep(1.0)
        
        # ✅ CRITICAL: Take multiple baseline readings to ensure we get truly fresh values
        # First reading might still have residual values
        baselines_1 = capture_baseline_readings(equipment)
        time.sleep(0.5)
        baselines_2 = capture_baseline_readings(equipment)
        time.sleep(0.5)
        baselines_3 = capture_baseline_readings(equipment)
        
        # Use the most recent reading (should be most stable)
        baselines = baselines_3 if baselines_3 else (baselines_2 if baselines_2 else baselines_1)
        
        if not baselines:
            raise BadRequest("Failed to capture SCADA baselines (all attempts empty)")

        for tag in equipment:
            baselines.setdefault(tag, 0.0)

        # Initialize shift
        plant = get_attr_safe(order, "plant", "3130")
        department = "MILLING" if order_type_new == "MILLING" else "PACKING"
        shift_row = get_current_shift(plant, department, db)
        current_shift = shift_row.shift_code if shift_row else "A"
        set_attr_safe(order, "current_shift", current_shift)
        set_attr_safe(order, "shift_start_time", datetime.now())

        # ✅ OVERWRITE ALL baseline_* COLUMNS WITH FRESH SCADA VALUES
        print(f"📊 [{po_number}] Setting fresh SCADA baselines: {baselines}")
        
        # ✅ Apply Overflow from Previous Order if available (Feature 4.5)
        from models.scale_overflow import ScaleOverflow
        
        for tag, value in baselines.items():
            baseline_val = float(value or 0.0)
            
            # Check for overflow
            try:
                overflow_record = db.query(ScaleOverflow).filter(ScaleOverflow.scale_tag == tag).first()
                if overflow_record and overflow_record.overflow_qty > 0:
                    overflow = overflow_record.overflow_qty
                    print(f"🌊 [{po_number}] Found overflow for {tag}: {overflow:.2f}")
                    # Apply overflow: Reduce baseline (so calculation shows higher current)
                    # New Baseline = Actual Baseline - Overflow
                    baseline_val = max(0.0, baseline_val - overflow)
                    print(f"🌊 [{po_number}] Applied overflow. New baseline for {tag}: {baseline_val:.2f}")
                    
                    # Clear overflow
                    overflow_record.overflow_qty = 0.0
                    db.add(overflow_record)
            except Exception as ovf_err:
                print(f"⚠️ [{po_number}] Error checking overflow for {tag}: {ovf_err}")
            
            set_attr_safe(order, f"baseline_{tag.lower()}", baseline_val)
            # Update the local baselines dict so subsequent logic (shift baselines) uses the adjusted values
            baselines[tag] = baseline_val
            print(f"  ✅ baseline_{tag.lower()} = {baseline_val}")

        # ✅ CRITICAL: MARK ALL BASELINES AS "FIXED" TO PREVENT RE-CAPTURE
        baseline_fixed_flags = {tag.lower(): True for tag in equipment}
        set_attr_safe(order, "baseline_fixed_flags", baseline_fixed_flags)

        # Handle MILLING vs PACKING scale setup
        if order_type_new == "MILLING":
            version = (get_attr_safe(order, "version") or "").strip().upper()
            
            # ✅ CRITICAL FIX: Check if byproduct scale TAGS are already set
            # If scale tags are set, byproducts were already captured on FIRST START - preserve them
            # This ensures byproducts are captured ONLY on first start, not on restart/pause
            existing_scale1 = get_attr_safe(order, "scale1", None)
            existing_scale2 = get_attr_safe(order, "scale2", None)
            existing_scale3 = get_attr_safe(order, "scale3", None)
            
            # ✅ CRITICAL FIX: Use PRESERVED quantities captured at function start, not current order values
            # The order object may have been modified/refreshed during setup, losing the byproduct quantities
            existing_scale1_qty = preserved_scale1_qty_start
            existing_scale2_qty = preserved_scale2_qty_start
            existing_scale3_qty = preserved_scale3_qty_start
            
            # ✅ FIX: Only check if byproduct TAGS are set (not quantities or confirmed_qty)
            # If tags are set, byproducts were already captured on first start - ALWAYS preserve
            byproduct_tags_already_set = (
                (existing_scale1 is not None and existing_scale1 != "") or
                (existing_scale2 is not None and existing_scale2 != "") or
                (existing_scale3 is not None and existing_scale3 != "")
            )
            
            if byproduct_tags_already_set:
                # RESTART/PAUSED scenario: Byproduct scales already configured, preserve them
                # This preserves byproducts even if confirmed_qty is 0 (order was paused before any production)
                print(f"🔒 [{po_number}] Byproduct scale tags already set - RESTORING preserved values")
                print(f"   scale1: {existing_scale1} ({existing_scale1_qty:.4f})")
                print(f"   scale2: {existing_scale2} ({existing_scale2_qty:.4f})")
                print(f"   scale3: {existing_scale3} ({existing_scale3_qty:.4f})")
                
                # ✅ CRITICAL: Actually RESTORE the preserved quantities to the order object
                # These may have been lost during the multiple commit/refresh cycles
                set_attr_safe(order, "scale1_qty", existing_scale1_qty)
                set_attr_safe(order, "scale2_qty", existing_scale2_qty)
                set_attr_safe(order, "scale3_qty", existing_scale3_qty)
                print(f"   ✅ Byproduct quantities RESTORED to order object")
                
                # ✅ CRITICAL FIX: Reset byproduct baselines to CURRENT SCADA readings on restart
                # This ensures delta only shows NEW production since restart, not total since order start
                # Without this fix, baseline was 0 (reset on pause), making delta = current = incorrect!
                from services.scale_service import get_scada_reading
                for scale_tag in [existing_scale1, existing_scale2, existing_scale3]:
                    if scale_tag:
                        # Get CURRENT SCADA reading as new baseline (not old value from DB which is 0)
                        current_reading = float(get_scada_reading(scale_tag) or 0.0)
                        baselines[scale_tag] = current_reading
                        set_attr_safe(order, f"baseline_{scale_tag.lower()}", current_reading)
                        print(f"   📌 Reset baseline to CURRENT SCADA: {scale_tag} = {current_reading:.2f}")
                
                print(f"   ✅ Byproduct baselines reset to current SCADA readings for accurate delta tracking")
            else:
                # BRAND NEW order: No byproduct tags set yet - capture fresh baselines from SCADA
                print(f"🆕 [{po_number}] BRAND NEW order - no byproduct tags set - capturing baselines fresh")
                print(f"🛠 Setting by-product scales for {po_number} / {version}")
                
                # Capture byproduct baselines (overrides if same tag)
                baselines = _capture_byproduct_baselines(version, baselines, order=order)

                # Save all baselines (main + byproduct)
                for tag, val in baselines.items():
                    set_attr_safe(order, f"baseline_{tag.lower()}", float(val or 0.0))

                _set_byproduct_scales(order, version, baselines)
                print(f"✅ [{po_number}] Byproduct scales captured and set for brand new order")

            # ✅ CRITICAL: Always capture fresh shift baselines on restart
            # This allows us to track NEW production after restart
            # Shift WEIGHTS are preserved (not reset), so we accumulate: old_weight + new_production
            set_attr_safe(
                order,
                f"baseline_shift_{current_shift.lower()}_start",
                baselines,
            )
            # ✅ Store baseline capture time for tracking
            set_attr_safe(order, f"baseline_shift_{current_shift.lower()}_time", datetime.now())
            print(f"✅ [{po_number}] Set fresh shift baselines for shift {current_shift} (shift weight preserved for accumulation)")

            # ✅ Also mark byproduct scales as fixed
            all_tags = set(equipment)
            for scale_key in ["scale1", "scale2", "scale3"]:
                tag = get_attr_safe(order, scale_key)
                if tag:
                    all_tags.add(tag)
            updated_flags = {tag.lower(): True for tag in all_tags}
            set_attr_safe(order, "baseline_fixed_flags", updated_flags)

        else:
            # PACKING logic (unchanged)
            pallet_equipment = equipment
            if pallet_equipment:
                tag = pallet_equipment[0]
                set_attr_safe(order, "scale1", tag)
                set_attr_safe(order, "scale1_qty", float(baselines.get(tag, 0.0) or 0.0))
            else:
                set_attr_safe(order, "scale1", None)
                set_attr_safe(order, "scale1_qty", 0.0)

            # Clear extra scales
            for i in [2, 3]:
                set_attr_safe(order, f"scale{i}", None)
                set_attr_safe(order, f"scale{i}_qty", 0.0)

            # ✅ CRITICAL: Always capture fresh shift baselines on restart
            # This allows us to track NEW production after restart
            # Shift WEIGHTS are preserved (not reset), so we accumulate: old_weight + new_production
            # ✅ FIX: Create shift baseline dict with ALL pallet equipment tags (not just first one)
            shift_baseline_dict = {}
            if pallet_equipment:
                for tag in pallet_equipment:
                    shift_baseline_dict[tag] = float(baselines.get(tag, 0.0) or 0.0)
            
            set_attr_safe(
                order,
                f"baseline_shift_{current_shift.lower()}_start",
                shift_baseline_dict,
            )
            # ✅ Store baseline capture time for tracking
            set_attr_safe(order, f"baseline_shift_{current_shift.lower()}_time", datetime.now())
            print(f"✅ [{po_number}] Set fresh PACKING shift baselines for shift {current_shift}: {shift_baseline_dict} (shift weight preserved for accumulation)")

        # ✅ CRITICAL: Get order status BEFORE any modifications (for brand new order check)
        current_status_before = get_attr_safe(order, "status", "Pending")
        
        # ✅ CRITICAL: Detect if this is a brand new order (after deleting old order)
        # Brand new orders should have all values = 0 and status = Pending
        is_brand_new_order = (
            preserved_confirmed_qty == 0.0 and 
            preserved_weight_a == 0.0 and 
            preserved_weight_b == 0.0 and 
            preserved_weight_c == 0.0 and
            current_status_before == "Pending"
        )
        
        # ✅ CRITICAL: For brand new orders, FORCE clear all caches to prevent inheriting values from deleted orders
        # This is especially important if the new order has the same PO number as a deleted order
        if is_brand_new_order:
            print(f"🆕 [{po_number}] Brand new order detected - FORCING cache clear to prevent inheriting values from deleted orders")
            for shift_code in ["a", "b", "c"]:
                cache_key = (po_number, shift_code)
                # ✅ CRITICAL: Use pop() to force delete from both caches, even if they don't exist
                # This ensures we remove any stale cache from deleted orders
                old_prod_cache = _last_shift_production_cache.pop(cache_key, None)
                if old_prod_cache is not None:
                    print(f"🧹 [Start-{po_number}] FORCED clear production cache for shift {shift_code.upper()} (removed value: {old_prod_cache:.2f} from deleted order)")
                old_max_cache = _max_shift_weight_cache.pop(cache_key, None)
                if old_max_cache is not None:
                    print(f"🧹 [Start-{po_number}] FORCED clear max weight cache for shift {shift_code.upper()} (removed value: {old_max_cache:.2f} from deleted order)")
            print(f"✅ [{po_number}] All caches cleared for brand new order - will start fresh")
        
        # --- Overflow & auto-validation logic ---
        # ✅ C31-T27: Manual start does NOT transfer overflow
        # Overflow transfer only applies to AUTO validation flow
        # Manual start (1-by-1) = user explicitly controls each order
        # User can manually manage overflow if needed
        overflow_applied = 0.0
        print(f"✅ [{po_number}] Manual start - no overflow transfer (C31-T27)")
        
        # =============================================================================
        # BYPRODUCT SCALE OVERFLOW: Apply overflow for byproduct scales (scale1, scale2, scale3)
        # =============================================================================
        # When a previous order's byproduct quantity was manually overridden (reduced),
        # the difference is stored in scale_overflows table. Apply it to this order.
        # ✅ UPDATED: Apply overflow to BOTH MILLING and PACKING orders
        if order_type_new in ("MILLING", "PACKING"):
            scale1_tag = get_attr_safe(order, "scale1", None)
            scale2_tag = get_attr_safe(order, "scale2", None)
            scale3_tag = get_attr_safe(order, "scale3", None)
            
            byproduct_overflow_applied = []
            
            for scale_idx, scale_tag in enumerate([scale1_tag, scale2_tag, scale3_tag], 1):
                if not scale_tag:
                    continue
                    
                try:
                    # Check for overflow in scale_overflows table
                    result = db.execute(text("""
                        SELECT overflow_qty FROM scale_overflows 
                        WHERE scale_tag = :tag AND overflow_qty > 0
                    """), {"tag": scale_tag}).fetchone()
                    
                    if result and result[0] > 0:
                        overflow_qty = float(result[0])
                        scale_qty_field = f"scale{scale_idx}_qty"
                        current_scale_qty = float(get_attr_safe(order, scale_qty_field, 0.0) or 0.0)
                        new_scale_qty = current_scale_qty + overflow_qty
                        
                        # Apply overflow to the byproduct scale quantity
                        set_attr_safe(order, scale_qty_field, new_scale_qty)
                        
                        # Clear the overflow from the table
                        db.execute(text("""
                            UPDATE scale_overflows SET overflow_qty = 0, last_updated = NOW()
                            WHERE scale_tag = :tag
                        """), {"tag": scale_tag})
                        
                        byproduct_overflow_applied.append(f"{scale_tag}: +{overflow_qty:.4f}")
                        print(f"🌊 [{po_number}] Applied {order_type_new} byproduct overflow for {scale_tag}: {current_scale_qty:.4f} + {overflow_qty:.4f} = {new_scale_qty:.4f}")
                        
                except Exception as e:
                    print(f"⚠️ [{po_number}] Error applying byproduct overflow for {scale_tag}: {e}")
            
            if byproduct_overflow_applied:
                db.commit()
                print(f"✅ [{po_number}] {order_type_new} byproduct overflow applied: {', '.join(byproduct_overflow_applied)}")
            else:
                print(f"ℹ️ [{po_number}] No {order_type_new} byproduct overflow to apply")

        # ✅ CRITICAL: Preserve confirmed_qty if it exists (for restarted orders)
        # Overflow handling: if overflow is applied, it's already set above
        set_attr_safe(order, "status", "InProgress")
        # ✅ C31-T27: Manual start via Start button = Manual validation method
        set_attr_safe(order, "validation_method", "Manual")
        print(f"🔧 [{po_number}] Manual start via Start button - setting validation_method=Manual")
        
        # ✅ CRITICAL: Reset delta cache for PACKING orders on restart
        # This ensures we track delta from 0 when order restarts
        order_type_new = classification.get("order_type", "")
        if order_type_new == "PACKING":
            _last_delta_cache_packing[po_number] = 0.0
            print(f"🔄 [{po_number}] Reset last_delta cache for PACKING order (restart detected)")
        
        # ✅ CRITICAL: Reset shift production cache for MILLING orders on restart
        # This ensures we track production from 0 when order restarts (baseline was reset)
        if order_type_new == "MILLING":
            # Reset cache for all shifts (a, b, c)
            for shift_code in ["a", "b", "c"]:
                cache_key = (po_number, shift_code)
                old_cache_value = _last_shift_production_cache.pop(cache_key, None)
                if old_cache_value is not None:
                    print(f"🔄 [{po_number}] Reset shift production cache for shift {shift_code.upper()} (had value: {old_cache_value:.2f} kg)")
                else:
                    print(f"🔄 [{po_number}] Reset shift production cache for shift {shift_code.upper()} (restart detected)")
            
            # ✅ CRITICAL: Also reset total cache for MILLING orders
            # This ensures we track total from current shift weights sum when order restarts
            current_total = float(get_attr_safe(order, "weight_shift_a", 0.0) or 0.0) + \
                           float(get_attr_safe(order, "weight_shift_b", 0.0) or 0.0) + \
                           float(get_attr_safe(order, "weight_shift_c", 0.0) or 0.0)
            _last_total_cache_milling[po_number] = current_total
            print(f"🔄 [{po_number}] Reset last_total cache for MILLING order to current shift weights sum: {current_total:.2f} kg (restart detected)")

        if overflow_applied == 0.0:
            # Use the preserved confirmed_qty value we read at the start
            # NEVER reset confirmed_qty if it has a value - only set to 0 for brand new orders
            if preserved_confirmed_qty > 0.0:
                # ✅ CRITICAL: Explicitly preserve the existing confirmed_qty for restarted orders
                # This MUST be set BEFORE any other operations that might affect confirmed_qty
                set_attr_safe(order, "confirmed_qty", preserved_confirmed_qty)
                print(f"✅ [{po_number}] PRESERVING confirmed_qty: {preserved_confirmed_qty} (DO NOT RESET)")
                # Verify it was set correctly
                verify_qty = float(order.confirmed_qty if hasattr(order, 'confirmed_qty') and order.confirmed_qty is not None else 0.0)
                if verify_qty != preserved_confirmed_qty:
                    print(f"⚠️ [{po_number}] WARNING: confirmed_qty mismatch! Expected {preserved_confirmed_qty}, got {verify_qty}")
                    # Force set it again
                    set_attr_safe(order, "confirmed_qty", preserved_confirmed_qty)
                    print(f"✅ [{po_number}] Force-set confirmed_qty to {preserved_confirmed_qty}")
                else:
                    print(f"✅ [{po_number}] Verified: confirmed_qty correctly set to {verify_qty}")
            else:
                # Brand new order, set to 0
                # ✅ CRITICAL: Force set to 0 even if database has stale value from deleted order
                set_attr_safe(order, "confirmed_qty", 0.0)
                print(f"ℹ️ [{po_number}] Setting confirmed_qty to 0.0 for brand new order (force clear any stale values)")
                
                # ✅ CRITICAL: Also ensure all shift weights are 0 for brand new orders
                # This prevents inheriting values from deleted orders
                set_attr_safe(order, "weight_shift_a", 0.0)
                set_attr_safe(order, "weight_shift_b", 0.0)
                set_attr_safe(order, "weight_shift_c", 0.0)
                print(f"🧹 [{po_number}] Force cleared all shift weights to 0.0 for brand new order")
        else:
            print(f"✅ Keeping overflow in confirmed_qty: {overflow_applied}")
        
        # ✅ CRITICAL: Preserve shift weights - but DON'T overwrite if overflow was applied to a shift!
        # Shift weights accumulate production across restarts
        if overflow_applied > 0:
            # Overflow was applied - get the current shift's weight which now includes overflow
            current_shift_for_overflow = get_attr_safe(order, "current_shift", "A").upper().lower()
            
            # Preserve other shifts, but keep the current shift's overflow
            if current_shift_for_overflow == "a":
                # Keep weight_shift_a as-is (has overflow), preserve others
                set_attr_safe(order, "weight_shift_b", preserved_weight_b)
                set_attr_safe(order, "weight_shift_c", preserved_weight_c)
                print(f"✅ [{po_number}] Keeping overflow in weight_shift_a, preserving B={preserved_weight_b:.2f}, C={preserved_weight_c:.2f}")
            elif current_shift_for_overflow == "b":
                set_attr_safe(order, "weight_shift_a", preserved_weight_a)
                # Keep weight_shift_b as-is (has overflow)
                set_attr_safe(order, "weight_shift_c", preserved_weight_c)
                print(f"✅ [{po_number}] Preserving A={preserved_weight_a:.2f}, keeping overflow in weight_shift_b, preserving C={preserved_weight_c:.2f}")
            else:  # "c"
                set_attr_safe(order, "weight_shift_a", preserved_weight_a)
                set_attr_safe(order, "weight_shift_b", preserved_weight_b)
                # Keep weight_shift_c as-is (has overflow)
                print(f"✅ [{po_number}] Preserving A={preserved_weight_a:.2f}, B={preserved_weight_b:.2f}, keeping overflow in weight_shift_c")
        else:
            # No overflow applied - preserve all shift weights normally
            set_attr_safe(order, "weight_shift_a", preserved_weight_a)
            set_attr_safe(order, "weight_shift_b", preserved_weight_b)
            set_attr_safe(order, "weight_shift_c", preserved_weight_c)
            if preserved_weight_a > 0.0 or preserved_weight_b > 0.0 or preserved_weight_c > 0.0:
                print(f"✅ [{po_number}] PRESERVING shift weights: A={preserved_weight_a:.2f}, B={preserved_weight_b:.2f}, C={preserved_weight_c:.2f} (DO NOT RESET)")

        # Auto-validate if overflow >= target
        order_auto_validated = False
        if overflow_applied > 0:
            target_qty = float(
                get_attr_safe(order, "expected_weight") or get_attr_safe(order, "quantity") or 0.0
            ) if order_type_new == "MILLING" else float(get_attr_safe(order, "quantity") or 0.0)
            unit = "KG" if order_type_new == "MILLING" else "BAG"

            if target_qty > 0 and overflow_applied >= target_qty:
                # ✅ FIXED: Don't calculate or accumulate shift weight here
                # The auto-validator worker already tracks weight_shift_X in real-time
                # ✅ DO NOT set shift_end_time - prevents auto-trigger on validation
                # SAP confirmation only happens at actual shift end or manual push
                current_shift_at_validation = get_attr_safe(order, "current_shift", None)
                if current_shift_at_validation:
                    print(f"📋 [Start-{po_number}] Order validated from overflow - NOT setting shift_end_time (will wait for actual shift end)")
                    print(f"📋 [Start-{po_number}] Keeping current_shift={current_shift_at_validation} so shift-end auto confirmation can process it")
                # ✅ DO NOT set shift_end_time - this would trigger auto-confirm immediately
                # set_attr_safe(order, "shift_end_time", datetime.now())
                
                # ✅ Feb 5, 2026: Use "Completed" when order reaches 100% tracking
                # "Validated" is reserved for after successful SAP confirmation
                set_attr_safe(order, "status", "Completed")
                set_attr_safe(order, "is_final_sent", False)
                # ✅ DO NOT clear current_shift - shift-end auto confirmation needs it
                # set_attr_safe(order, "current_shift", None)
                set_attr_safe(order, "validation_method", "Automatic")
                set_attr_safe(order, "confirmed_qty", target_qty)
                # ✅ CRITICAL FIX (Dec 12, 2025): Do NOT auto-set confirmed_text
                # confirmed_text should ONLY be entered by user in manual/offline mode
                # set_attr_safe(order, "confirmed_text", f"Auto: Target met instantly from overflow...")
                excess = overflow_applied - target_qty
                # ✅ CRITICAL FIX (Dec 12, 2025): Do NOT store overflow - cap at target
                # set_attr_safe(order, "overflow_weight", max(0.0, excess))
                order_auto_validated = True
                
                # Release scales and start waiting orders
                release_scales_and_start_waiting_orders(po_number, order, classification, db)

        if not order_auto_validated:
            set_attr_safe(order, "is_final_sent", False)

        db.add(order)
        db.commit()
        
        # ✅ CRITICAL: Verify preserved confirmed_qty and shift weights were committed correctly
        db.refresh(order)
        final_confirmed_qty = float(order.confirmed_qty if hasattr(order, 'confirmed_qty') and order.confirmed_qty is not None else 0.0)
        final_weight_a = float(get_attr_safe(order, "weight_shift_a", 0.0) or 0.0)
        final_weight_b = float(get_attr_safe(order, "weight_shift_b", 0.0) or 0.0)
        final_weight_c = float(get_attr_safe(order, "weight_shift_c", 0.0) or 0.0)
        
        if preserved_confirmed_qty > 0.0 and overflow_applied == 0.0:
            if final_confirmed_qty != preserved_confirmed_qty:
                print(f"❌ [{po_number}] ERROR: confirmed_qty not preserved after commit! Expected {preserved_confirmed_qty:.2f}, got {final_confirmed_qty:.2f}")
                # Force set it again
                set_attr_safe(order, "confirmed_qty", preserved_confirmed_qty)
                db.add(order)
                db.commit()
                print(f"✅ [{po_number}] Fixed: confirmed_qty set to {preserved_confirmed_qty:.2f}")
            else:
                print(f"✅ [{po_number}] Verified: confirmed_qty={final_confirmed_qty:.2f} correctly committed to database")
        
        # Verify shift weights were preserved
        if preserved_weight_a > 0.0 or preserved_weight_b > 0.0 or preserved_weight_c > 0.0:
            if final_weight_a != preserved_weight_a or final_weight_b != preserved_weight_b or final_weight_c != preserved_weight_c:
                print(f"❌ [{po_number}] ERROR: Shift weights not preserved after commit!")
                print(f"   Expected: A={preserved_weight_a:.2f}, B={preserved_weight_b:.2f}, C={preserved_weight_c:.2f}")
                print(f"   Got: A={final_weight_a:.2f}, B={final_weight_b:.2f}, C={final_weight_c:.2f}")
                # Force set them again
                set_attr_safe(order, "weight_shift_a", preserved_weight_a)
                set_attr_safe(order, "weight_shift_b", preserved_weight_b)
                set_attr_safe(order, "weight_shift_c", preserved_weight_c)
                db.add(order)
                db.commit()
                print(f"✅ [{po_number}] Fixed: Shift weights restored")
            else:
                print(f"✅ [{po_number}] Verified: Shift weights preserved correctly: A={final_weight_a:.2f}, B={final_weight_b:.2f}, C={final_weight_c:.2f}")

        final_status = get_attr_safe(order, "status", "InProgress")

        if not order_auto_validated:
            validation_thread = threading.Thread(
                target=auto_validation_worker,
                args=(po_number, classification),
                daemon=True,
                name=f"Validation-{po_number}",
            )
            set_order_validation_state(po_number, {
                "isrunning": True,
                "thread": validation_thread,
                "progress_pct": 0,
                "status": "running",
                "started_at": datetime.now().isoformat()
            })
            validation_thread.start()
            print(f"🚀 Started validation thread for {po_number}")

    return jsonify({
        "success": True,
        "po_number": po_number,
        "status": final_status,
        "order_type": classification["order_type"],
        "equipment": equipment,
        "formula": classification.get("formula", ""),
        "baselines": baselines,
        "auto_validated": order_auto_validated,
    })

@orders_bp.route("/<string:po_number>/validate", methods=["POST"])
@optional_auth
def validate_order(po_number: str):
    if ProcessOrder is None:
        raise BadRequest("ProcessOrder model not available")

    with _db_session() as db:
        order = db.query(ProcessOrder).filter(
            ProcessOrder.order_id == po_number
        ).first()

        if not order:
            raise NotFound(f"Order {po_number} not found")

        if order.status != "InProgress":
            return jsonify({
                "success": False,
                "message": f"Cannot validate order with status '{order.status}'"
            }), 400

        classification = classify_order(order)
        if classification.get("error"):
            raise BadRequest(f"Classification failed: {classification['error']}")

        completion = check_order_completion(order, classification)
        if completion.get("error"):
            raise BadRequest(f"Validation failed: {completion['error']}")

        if completion["is_complete"]:
            # ✅ FIXED: Don't calculate or accumulate shift weight here
            # The auto-validator worker already tracks weight_shift_X in real-time
            # DO NOT set shift_end_time - this prevents auto-trigger on validation
            # SAP confirmation only happens at actual shift end or manual push
            print(f"📋 [Validate-{po_number}] Order validated - will be sent to SAP at shift end or manual push only")
            print(f"📋 [Validate-{po_number}] NOT setting shift_end_time to prevent auto-trigger - will wait for actual shift end")
            
            # ✅ DO NOT set shift_end_time - this would trigger auto-confirm immediately
            # Only actual shift end should trigger auto-confirm
            # current_shift = get_attr_safe(order, "current_shift", None)
            # if current_shift:
            #     set_attr_safe(order, "shift_end_time", datetime.now())

            # ✅ Feb 5, 2026: Use "Completed" when order reaches 100% tracking
            # "Validated" is reserved for after successful SAP confirmation
            set_attr_safe(order, "status", "Completed")
            set_attr_safe(order, "validation_method", "Manual")
            # ✅ FIX (Jan 23, 2026): Set confirmed_qty to target when order is completed
            # This ensures "Current" column shows the correct value for completed orders
            set_attr_safe(order, "confirmed_qty", completion["target_qty"])
            print(f"📋 [Validate-{po_number}] Set confirmed_qty={completion['target_qty']:.2f} (target) on manual completion")

            # ✅ CRITICAL: Keep current_shift so shift-end auto confirmation knows which shift to process
            # DO NOT clear current_shift - this allows shift-end auto confirmation to find the order
            # Only clear it after shift-end auto confirmation has processed it
            current_shift = get_attr_safe(order, "current_shift", None)
            if current_shift:
                print(f"📋 [Validate-{po_number}] Keeping current_shift={current_shift} so shift-end auto confirmation can process it")
            
            # Let shift_auto_confirm send SAP (only at actual shift end) OR manual push
            set_attr_safe(order, "is_final_sent", False)
            # ✅ DO NOT set shift_end_time here - prevents auto-trigger on validation
            # set_attr_safe(order, "shift_end_time", datetime.now())
            # ✅ DO NOT clear current_shift - shift-end auto confirmation needs it
            # set_attr_safe(order, "current_shift", None)

            # ✅ C31-T27: Manual validation does NOT calculate overflow
            # Overflow only applies to auto-validation when production continues beyond target
            # Manual validation = user explicitly controls when order is complete
            
            # Release scales and start waiting orders
            release_scales_and_start_waiting_orders(po_number, order, classification, db)
            
            # ✅ CRITICAL: Stop validation worker for this order if running
            print(f"🛑 [Validate-{po_number}] Stopping validation worker...")
            set_order_validation_state(po_number, {"isrunning": False})
            
            # ✅ CRITICAL: Wait for worker to fully stop before proceeding
            # This ensures the scheduler doesn't think there's still an order in progress
            import time
            time.sleep(1.0)  # Wait 1 second for worker to stop
            print(f"✅ [Validate-{po_number}] Worker stopped, proceeding with validation...")
            
            # ✅ CRITICAL FIX: Capture final SCADA readings at validation time and store them
            # This ensures that when viewing a validated order, we show the correct final values
            # We preserve the original baseline (used during production) and store final SCADA readings
            print(f"🔄 [Validate-{po_number}] Capturing final SCADA readings at validation time...")
            try:
                from services.scale_service import clear_scada_cache, get_multiple_scada_readings
                # ✅ CRITICAL: Clear SCADA cache multiple times to ensure truly fresh values
                clear_scada_cache()
                import time
                time.sleep(0.2)
                clear_scada_cache()  # Clear again to be sure
                print(f"✅ [Validate-{po_number}] SCADA cache cleared (twice) before capturing final readings")
            except Exception as e:
                print(f"⚠️ [Validate-{po_number}] Could not clear SCADA cache: {e}")
                get_multiple_scada_readings = None
                import time
            
            # ✅ CRITICAL: Wait longer for fresh SCADA values to ensure we get the latest readings
            # This is especially important if SCADA values are still updating
            time.sleep(0.5)
            
            # Get equipment list for this order
            equipment = classification.get("equipment", [])
            if equipment and get_multiple_scada_readings:
                # ✅ CRITICAL: Take multiple readings to ensure we get the most recent/final value
                # First reading might still be cached or slightly stale
                print(f"🔍 [Validate-{po_number}] Taking multiple SCADA readings to ensure final values...")
                final_readings_1 = get_multiple_scada_readings(equipment, force_fresh=True)
                time.sleep(0.3)
                final_readings_2 = get_multiple_scada_readings(equipment, force_fresh=True)
                time.sleep(0.3)
                final_readings_3 = get_multiple_scada_readings(equipment, force_fresh=True)
                
                # Use the most recent reading (should be the final value)
                final_readings = final_readings_3 if final_readings_3 else (final_readings_2 if final_readings_2 else final_readings_1)
                
                print(f"🔍 [Validate-{po_number}] Final SCADA readings captured (3 attempts):")
                for tag in equipment:
                    if tag in final_readings:
                        reading_data = final_readings[tag]
                        if isinstance(reading_data, dict):
                            val = reading_data.get("current", 0.0)
                        else:
                            val = reading_data
                        print(f"   {tag}: {val}")
                
                if final_readings:
                    print(f"✅ [Validate-{po_number}] Captured final SCADA readings: {final_readings}")
                    
                    # ✅ CRITICAL: Update baseline to final SCADA reading at validation time
                    # This ensures that when viewing a validated order, baseline = final SCADA reading
                    # Deltas will be calculated as: current_SCADA - baseline (which will be 0 or very small for validated orders)
                    # NOTE: We do NOT store deltas in scale_qty - scale_qty is ONLY for byproduct scales at order start
                    print(f"🔄 [Validate-{po_number}] Updating baseline columns to final SCADA readings...")
                    for tag, reading_data in final_readings.items():
                        baseline_attr = f"baseline_{tag.lower()}"
                        if isinstance(reading_data, dict):
                            final_current = float(reading_data.get("current", 0.0) or 0.0)
                        else:
                            final_current = float(reading_data or 0.0)
                        
                        old_baseline = float(get_attr_safe(order, baseline_attr, 0.0) or 0.0)
                        set_attr_safe(order, baseline_attr, final_current)
                        if old_baseline != final_current:
                            print(f"   ✅ {tag}: baseline updated from {old_baseline:.2f} to {final_current:.2f} (final SCADA reading)")
                        else:
                            print(f"   ✓ {tag}: baseline already correct at {final_current:.2f}")
                    
                    # ✅ CRITICAL: Flush baseline updates before commit to ensure they're saved
                    db.add(order)
                    db.flush()
                    print(f"✅ [Validate-{po_number}] Baseline updates flushed to database")
                    
                    # Also update shift baseline if current_shift exists
                    if current_shift:
                        final_baselines_dict = {}
                        for tag, reading_data in final_readings.items():
                            if isinstance(reading_data, dict):
                                final_baselines_dict[tag] = float(reading_data.get("current", 0.0) or 0.0)
                            else:
                                final_baselines_dict[tag] = float(reading_data or 0.0)
                        
                        set_attr_safe(
                            order,
                            f"baseline_shift_{current_shift.lower()}_start",
                            final_baselines_dict
                        )
                        print(f"✅ [Validate-{po_number}] Updated shift baseline for shift {current_shift}")
                    
                    print(f"✅ [Validate-{po_number}] Final SCADA readings captured and stored at validation time")
                else:
                    print(f"⚠️ [Validate-{po_number}] Failed to capture final SCADA readings, keeping existing values")
            else:
                print(f"⚠️ [Validate-{po_number}] No equipment found or get_multiple_scada_readings unavailable, skipping final reading capture")
        else:
            set_attr_safe(order, "status", "Validation_Failed")
            set_attr_safe(order, "confirmed_qty", completion["actual_qty"])
            set_attr_safe(
                order,
                "confirmed_text",
                f"Target not reached: {completion['actual_qty']:.2f}/"
                f"{completion['target_qty']:.2f} {completion['unit']}"
            )

        db.add(order)
        db.commit()
        
        # ✅ CRITICAL: Refresh order to ensure baseline updates are fully persisted
        # This ensures the validated order's baseline values are correctly saved before scheduler starts
        db.refresh(order)
        
        # ✅ CRITICAL: Verify baseline values were actually saved correctly
        if completion["is_complete"] and equipment:
            print(f"🔍 [Validate-{po_number}] Verifying baseline values after commit...")
            for tag in equipment:
                baseline_attr = f"baseline_{tag.lower()}"
                saved_baseline = float(get_attr_safe(order, baseline_attr, 0.0) or 0.0)
                print(f"   {tag}: saved baseline = {saved_baseline:.2f}")
        
        print(f"✅ [Validate-{po_number}] Order refreshed after commit - baseline values verified and persisted")
        
        # ✅ CRITICAL: Add a small delay to ensure database changes are fully propagated
        # This prevents race conditions where the scheduler might read stale baseline values
        import time
        time.sleep(0.5)
        
        # ✅ CRITICAL: Trigger scheduler to start next priority order of same type (after commit)
        # Only if order was successfully validated and auto-validator is enabled
        if completion["is_complete"] and is_auto_validator_enabled():
            try:
                order_type_validated = classification.get("order_type", "UNKNOWN")
                print(f"🔁 [Manual Validate-{po_number}] Order type: {order_type_validated}, triggering scheduler to start next priority order")
                print(f"🔍 [Manual Validate-{po_number}] Conditions: is_complete={completion['is_complete']}, is_auto_validator_enabled()={is_auto_validator_enabled()}")
                
                # ✅ CRITICAL: Wait a bit more to ensure worker thread has fully exited
                # This prevents the scheduler from thinking there's still an order in progress
                time.sleep(0.5)
                
                _schedule_next_orders_after_completion()
                print(f"✅ [Manual Validate-{po_number}] Scheduler completed")
            except Exception as e:
                print(f"⚠️ [Manual Validate-{po_number}] Failed to schedule next order: {e}")
                import traceback
                traceback.print_exc()
        else:
            print(f"🔍 [Manual Validate-{po_number}] Not triggering scheduler: is_complete={completion.get('is_complete', False)}, is_auto_validator_enabled()={is_auto_validator_enabled()}")

    # Admin activity log: who validated which order
    try:
        operator = (getattr(request, 'current_user', None) or {}).get('username', 'Unknown')
        system_logger.log_event(
            source='Operator',
            action='Validated order',
            status='Success',
            operator=operator,
            details=f'PO {po_number}',
            metadata={'po_number': po_number}
        )
    except Exception as log_err:
        print(f"⚠️ Failed to log validate to activity: {log_err}")

    return jsonify({
        "success": True,
        "po_number": po_number,
        "order_type": classification["order_type"],
        "validation_result": completion,
        "order_status": order.status
    })

@orders_bp.route("/<int:order_id>/reject", methods=["POST"])
@optional_auth
def reject_order(order_id: int):
    if ProcessOrder is None:
        raise BadRequest("ProcessOrder model not available")
    try:
        data = request.get_json() or {}
        remarks = data.get("remarks", "")
        rejected_by = data.get("rejected_by", "")
        po_number = None
        with _db_session() as db:
            order = db.query(ProcessOrder).filter(ProcessOrder.id == order_id).first()
            if not order:
                raise NotFound(f"Order with ID {order_id} not found")
            if order.status != "InProgress":
                return jsonify({"success": False, "message": f"Cannot reject order with status '{order.status}'. Only InProgress orders can be rejected."}), 400
            po_number = get_attr_safe(order, "order_id", "")
            set_attr_safe(order, "status", "Rejected")
            set_attr_safe(order, "validation_method", "Manual")
            rejection_text = f"Rejected: {remarks}"
            if rejected_by:
                rejection_text += f" (by {rejected_by})"
            set_attr_safe(order, "confirmed_text", rejection_text)
            # Check if this order is currently being validated and stop it
            if is_order_validating(po_number):
                remove_order_validation_state(po_number)
                print(f"🛑 Order {po_number} rejected - Auto-validator will move to next priority order")
            db.add(order)
            db.commit()
            
            # ✅ Log rejection to error_log table
            try:
                po_clean = str(po_number).lstrip("0") if po_number else ""
                log_order_error(
                    po_number=po_clean,
                    error_type="validation_rejected",
                    error_message=rejection_text,
                    payload={
                        "order_id": order_id,
                        "po_number": po_number,
                        "remarks": remarks,
                        "rejected_by": rejected_by,
                        "order_status": "Rejected",
                        "timestamp": datetime.now().isoformat()
                    },
                    source="manual_rejection"
                )
                print(f"📌 Rejection logged to error_log for PO {po_clean}")
            except Exception as log_err:
                print(f"⚠️ Failed to log rejection to error_log: {log_err}")
                # Don't fail the rejection if logging fails
            # Admin activity log
            try:
                operator = (getattr(request, 'current_user', None) or {}).get('username', 'Unknown')
                system_logger.log_event(
                    source='Operator',
                    action='Rejected order',
                    status='Success',
                    operator=operator,
                    details=f'PO {po_number or order_id}, order_id={order_id}',
                    metadata={'po_number': po_number, 'order_id': order_id}
                )
            except Exception as log_err:
                print(f"⚠️ Failed to log reject to activity: {log_err}")
        return jsonify({"success": True, "po_number": po_number or f"ID-{order_id}", "order_id": order_id, "status": "Rejected", "message": f"Order {po_number or f'ID-{order_id}'} rejected successfully. Auto-validator will move to next order if running."})
    except NotFound as e:
        return jsonify({"error": str(e)}), 404
    except BadRequest as e:
        return jsonify({"error": str(e)}), 400
    except Exception as e:
        print(f"❌ Error rejecting order: {e}")
        import traceback
        traceback.print_exc()
        return jsonify({"error": f"Failed to reject order: {str(e)}"}), 500


@orders_bp.route("/<string:po_number>/stop", methods=["POST"])
@optional_auth
def stop_order(po_number: str):
    """
    Pause (stop) an order validation.
    
    ✅ CRITICAL: This endpoint now:
    1. Stops the worker FIRST and waits for it to finish
    2. Captures final SCADA reading to ensure confirmed_qty is accurate
    3. Logs all values for audit trail (for SAP sync purposes)
    4. Only releases scales AFTER confirmed_qty is saved
    5. Resets baselines (but preserves confirmed_qty and shift weights)
    """
    if ProcessOrder is None:
        raise BadRequest("ProcessOrder model not available")
    with _db_session() as db:
        order = db.query(ProcessOrder).filter(ProcessOrder.order_id == po_number).first()
        if not order:
            raise NotFound(f"Order {po_number} not found")
        if order.status != "InProgress":
            return jsonify({
                "success": False,
                "message": f"Cannot stop order with status '{order.status}'. Only InProgress orders can be stopped."
            }), 400

        # =============================================================================
        # ✅ STEP 1: SIGNAL WORKER TO STOP FIRST (before any other operations)
        # =============================================================================
        print(f"🛑 [Stop-{po_number}] Signaling worker to stop...")
        set_order_validation_state(po_number, {"isrunning": False})
        
        # ✅ CRITICAL: Wait for worker to fully stop before proceeding
        # This ensures the worker has committed its final confirmed_qty update
        # Using 1.5 seconds (slightly longer than validate_order's 1.0s for safety)
        import time
        time.sleep(1.5)
        print(f"✅ [Stop-{po_number}] Worker stopped, proceeding with pause...")
        
        # ✅ STEP 2: Refresh order from database to get the latest values from worker's final commit
        db.refresh(order)
        
        # =============================================================================
        # ✅ STEP 3: CAPTURE AND LOG current values BEFORE modifications (AUDIT TRAIL)
        # This is critical for SAP sync - we need to know exactly what was produced
        # =============================================================================
        preserved_confirmed_qty = float(get_attr_safe(order, "confirmed_qty", 0.0) or 0.0)
        preserved_weight_a = float(get_attr_safe(order, "weight_shift_a", 0.0) or 0.0)
        preserved_weight_b = float(get_attr_safe(order, "weight_shift_b", 0.0) or 0.0)
        preserved_weight_c = float(get_attr_safe(order, "weight_shift_c", 0.0) or 0.0)
        current_shift = get_attr_safe(order, "current_shift", "A")
        
        print(f"📋 [Stop-{po_number}] ═══════════════════════════════════════════════")
        print(f"📋 [Stop-{po_number}] PAUSE AUDIT LOG (values preserved for SAP sync):")
        print(f"📋 [Stop-{po_number}]   ├─ confirmed_qty: {preserved_confirmed_qty:.2f}")
        print(f"📋 [Stop-{po_number}]   ├─ weight_shift_a: {preserved_weight_a:.2f}")
        print(f"📋 [Stop-{po_number}]   ├─ weight_shift_b: {preserved_weight_b:.2f}")
        print(f"📋 [Stop-{po_number}]   ├─ weight_shift_c: {preserved_weight_c:.2f}")
        print(f"📋 [Stop-{po_number}]   ├─ current_shift: {current_shift}")
        print(f"📋 [Stop-{po_number}]   └─ TOTAL SHIFT WEIGHTS: {preserved_weight_a + preserved_weight_b + preserved_weight_c:.2f}")
        print(f"📋 [Stop-{po_number}] ═══════════════════════════════════════════════")
        
        # =============================================================================
        # ✅ STEP 4: CAPTURE FINAL SCADA READING (in case worker stopped mid-cycle)
        # This ensures confirmed_qty reflects the actual production at pause time
        # =============================================================================
        classification = classify_order(order)
        final_confirmed_qty = preserved_confirmed_qty  # Default to preserved value
        
        if not classification.get("error"):
            order_type = classification.get("order_type")
            equipment = classification.get("equipment", [])
            
            if equipment and current_shift:
                try:
                    # Calculate current production from shift baseline using live SCADA
                    current_production = calculate_shift_weight(order, current_shift, classification, db=db)
                    shift_field = f"weight_shift_{current_shift.lower()}"
                    stored_shift_weight = float(get_attr_safe(order, shift_field, 0.0) or 0.0)
                    
                    # If current SCADA shows more production than stored, update it
                    if current_production > stored_shift_weight + 0.01:  # Small tolerance for float comparison
                        print(f"🔄 [Stop-{po_number}] Capturing final SCADA production before pause:")
                        print(f"🔄 [Stop-{po_number}]   ├─ Current SCADA production: {current_production:.2f}")
                        print(f"🔄 [Stop-{po_number}]   ├─ Stored shift weight: {stored_shift_weight:.2f}")
                        print(f"🔄 [Stop-{po_number}]   └─ Delta (new production): {current_production - stored_shift_weight:.2f}")
                        
                        # Update shift weight to current SCADA value
                        set_attr_safe(order, shift_field, current_production)
                        
                        # Recalculate total weight with updated shift
                        if current_shift.lower() == "a":
                            total_weight = current_production + preserved_weight_b + preserved_weight_c
                        elif current_shift.lower() == "b":
                            total_weight = preserved_weight_a + current_production + preserved_weight_c
                        else:  # shift C
                            total_weight = preserved_weight_a + preserved_weight_b + current_production
                        
                        # Update confirmed_qty (capped at target)
                        target_qty = float(get_attr_safe(order, "expected_weight") or get_attr_safe(order, "quantity") or 0.0)
                        final_confirmed_qty = min(total_weight, target_qty) if target_qty > 0 else total_weight
                        
                        set_attr_safe(order, "confirmed_qty", final_confirmed_qty)
                        
                        print(f"✅ [Stop-{po_number}] Updated values from final SCADA reading:")
                        print(f"✅ [Stop-{po_number}]   ├─ {shift_field}: {current_production:.2f}")
                        print(f"✅ [Stop-{po_number}]   └─ confirmed_qty: {final_confirmed_qty:.2f}")
                        
                        # Commit the updated values immediately
                        db.add(order)
                        db.commit()
                        db.refresh(order)
                        print(f"✅ [Stop-{po_number}] Final SCADA values committed to database")
                    else:
                        print(f"✅ [Stop-{po_number}] Stored values are current (no SCADA update needed)")
                        
                except Exception as e:
                    print(f"⚠️ [Stop-{po_number}] Could not capture final SCADA reading: {e}")
                    import traceback
                    traceback.print_exc()
                    # Continue with preserved values - don't fail the pause operation
            
            # =============================================================================
            # ✅ STEP 4b: CAPTURE AND STORE BYPRODUCT DELTAS (preserve like confirmed_qty)
            # This ensures byproduct quantities are accumulated across pause/restart cycles
            # =============================================================================
            print(f"🔧🔧🔧 [BYPRODUCT-FIX-DEC21] stop_order STEP 4b executing for {po_number}, order_type={order_type}")
            if order_type == "MILLING":
                from services.scale_service import get_scada_reading
                
                scale1_tag = get_attr_safe(order, "scale1", None)
                scale2_tag = get_attr_safe(order, "scale2", None)
                scale3_tag = get_attr_safe(order, "scale3", None)
                
                print(f"📦 [Stop-{po_number}] Capturing byproduct deltas...")
                
                # Capture and accumulate byproduct deltas
                if scale1_tag:
                    stored1 = float(get_attr_safe(order, "scale1_qty", 0.0) or 0.0)
                    baseline1 = float(get_attr_safe(order, f"baseline_{scale1_tag.lower()}", 0.0) or 0.0)
                    current1 = float(get_scada_reading(scale1_tag) or 0.0)
                    delta1 = max(0.0, current1 - baseline1)
                    accumulated1 = stored1 + delta1
                    set_attr_safe(order, "scale1_qty", accumulated1)
                    print(f"📦 [Stop-{po_number}]   scale1 ({scale1_tag}): stored={stored1:.4f} + delta={delta1:.4f} = {accumulated1:.4f}")
                    
                if scale2_tag:
                    stored2 = float(get_attr_safe(order, "scale2_qty", 0.0) or 0.0)
                    baseline2 = float(get_attr_safe(order, f"baseline_{scale2_tag.lower()}", 0.0) or 0.0)
                    current2 = float(get_scada_reading(scale2_tag) or 0.0)
                    delta2 = max(0.0, current2 - baseline2)
                    accumulated2 = stored2 + delta2
                    set_attr_safe(order, "scale2_qty", accumulated2)
                    print(f"📦 [Stop-{po_number}]   scale2 ({scale2_tag}): stored={stored2:.4f} + delta={delta2:.4f} = {accumulated2:.4f}")
                    
                if scale3_tag:
                    stored3 = float(get_attr_safe(order, "scale3_qty", 0.0) or 0.0)
                    baseline3 = float(get_attr_safe(order, f"baseline_{scale3_tag.lower()}", 0.0) or 0.0)
                    current3 = float(get_scada_reading(scale3_tag) or 0.0)
                    delta3 = max(0.0, current3 - baseline3)
                    accumulated3 = stored3 + delta3
                    set_attr_safe(order, "scale3_qty", accumulated3)
                    print(f"📦 [Stop-{po_number}]   scale3 ({scale3_tag}): stored={stored3:.4f} + delta={delta3:.4f} = {accumulated3:.4f}")
                
                # ✅ CRITICAL FIX: Commit byproduct quantities IMMEDIATELY
                # This ensures they are persisted to database before any other operations
                # that might refresh the order object and lose uncommitted changes
                db.add(order)
                db.commit()
                db.refresh(order)
                
                # Verify the values were saved correctly
                saved_scale1_qty = float(get_attr_safe(order, "scale1_qty", 0.0) or 0.0)
                saved_scale2_qty = float(get_attr_safe(order, "scale2_qty", 0.0) or 0.0)
                saved_scale3_qty = float(get_attr_safe(order, "scale3_qty", 0.0) or 0.0)
                print(f"✅ [Stop-{po_number}] Byproduct quantities COMMITTED to database:")
                print(f"   scale1_qty: {saved_scale1_qty:.4f}")
                print(f"   scale2_qty: {saved_scale2_qty:.4f}")
                print(f"   scale3_qty: {saved_scale3_qty:.4f}")
            
            # =============================================================================
            # ✅ STEP 5: On PAUSE - only release scales (do NOT auto-start next order)
            # Next order remains available for user to start manually via Start button.
            # =============================================================================
            released = release_scales(po_number, None)
            version = get_attr_safe(order, "version", "").upper().strip()
            order_type = classification.get("order_type")
            if version and order_type:
                unregister_order_version(po_number, version, order_type)
            remove_from_queue(po_number)
            print(f"🔓 [Stop-{po_number}] Released scales (next order available for manual start, not auto-started)")

        # ✅ STEP 6: Set status to Pending
        set_attr_safe(order, "status", "Pending")
        
        # ✅ STEP 7: Remove from queue if it was queued
        remove_from_queue(po_number)

        # ✅ STEP 8: Reset baseline_fixed_flags so new baselines are captured on restart
        baseline_fixed_flags = get_attr_safe(order, "baseline_fixed_flags", {}) or {}
        for key in list(baseline_fixed_flags.keys()):
            baseline_fixed_flags[key] = False
        set_attr_safe(order, "baseline_fixed_flags", baseline_fixed_flags)

        # ✅ STEP 9: Reset ALL baseline column values to 0
        # NOTE: confirmed_qty and weight_shift_* are PRESERVED (not reset)
        # PACKING: Bag counter baselines
        set_attr_safe(order, "baseline_sl601_counter", 0.0)
        set_attr_safe(order, "baseline_sl602_counter", 0.0)
        set_attr_safe(order, "baseline_sl603_counter", 0.0)
        set_attr_safe(order, "baseline_sl606_counter", 0.0)
        set_attr_safe(order, "baseline_sl607_counter", 0.0)
        
        # MILLING: Flour/Bran output baselines
        set_attr_safe(order, "baseline_wg101", 0.0)
        set_attr_safe(order, "baseline_wg201", 0.0)
        set_attr_safe(order, "baseline_wg202", 0.0)
        set_attr_safe(order, "baseline_wg301", 0.0)
        set_attr_safe(order, "baseline_wg302", 0.0)
        set_attr_safe(order, "baseline_wg501", 0.0)
        set_attr_safe(order, "baseline_wg502", 0.0)
        set_attr_safe(order, "baseline_wg503", 0.0)
        
        # WATER DOSING METER baselines
        set_attr_safe(order, "baseline_dm101", 0.0)
        set_attr_safe(order, "baseline_dm102", 0.0)
        set_attr_safe(order, "baseline_dm201", 0.0)
        set_attr_safe(order, "baseline_dm202", 0.0)
        set_attr_safe(order, "baseline_dm203", 0.0)
        
        # ✅ CRITICAL: Reset shift baseline JSON fields (these are used for production calculation)
        set_attr_safe(order, "baseline_shift_a_start", None)
        set_attr_safe(order, "baseline_shift_b_start", None)
        set_attr_safe(order, "baseline_shift_c_start", None)

        # =============================================================================
        # ✅ Jan 30, 2026: PUSH PAUSED ORDER TO END OF QUEUE
        # When pausing, move the order to the back of the priority queue
        # This ensures the NEXT order starts, not the paused one again
        # =============================================================================
        order_type = classification.get("order_type") if classification else None
        swapped_with_order = None
        
        if is_auto_validator_enabled():
            from sqlalchemy import func
            paused_priority = int(get_attr_safe(order, "hercules_priority", 999) or get_attr_safe(order, "priority", 999) or 999)
            
            # Find the max hercules_priority among ALL Pending/InProgress orders
            max_priority_result = db.query(func.max(ProcessOrder.hercules_priority)).filter(
                ProcessOrder.status.in_(["Pending", "InProgress"]),
                ProcessOrder.order_id != po_number
            ).scalar()
            max_priority = int(max_priority_result or 1)
            
            # Push paused order to back of queue (max + 1)
            new_priority = max_priority + 1
            
            print(f"🔄 [Stop-{po_number}] PUSHING TO BACK OF QUEUE:")
            print(f"🔄 [Stop-{po_number}]   Current hercules_priority: {paused_priority}")
            print(f"🔄 [Stop-{po_number}]   Max hercules_priority in queue: {max_priority}")
            print(f"🔄 [Stop-{po_number}]   New hercules_priority: {new_priority}")
            
            set_attr_safe(order, "hercules_priority", new_priority)
            print(f"✅ [Stop-{po_number}] Paused order moved to priority {new_priority} (back of queue)")
        else:
            print(f"🔄 [Stop-{po_number}] Auto-validator OFF - priority unchanged")

        # ✅ SINGLE COMMIT: All changes (status, baselines, priority swap) committed together
        # This prevents race conditions where auto-validator sees partial state
        db.add(order)
        db.commit()
        print(f"✅ [{po_number}] Reset all baseline values to 0 and shift baselines to NULL")
        print(f"✅ [{po_number}] Preserved: confirmed_qty={final_confirmed_qty:.2f}, shift weights remain in database")
        if swapped_with_order:
            print(f"✅ [{po_number}] Priority swapped with {swapped_with_order} - committed to database")

        # On PAUSE: do NOT trigger scheduler - next order stays Pending for manual start
        # User will start the next order manually via the Start button when ready.
        print(f"🔓 [Stop-{po_number}] Pause complete. Next order(s) available for manual start.")

    # Admin activity log
    try:
        operator = (getattr(request, 'current_user', None) or {}).get('username', 'Unknown')
        system_logger.log_event(
            source='Operator',
            action='Paused order',
            status='Success',
            operator=operator,
            details=f'PO {po_number}',
            metadata={'po_number': po_number}
        )
    except Exception as log_err:
        print(f"⚠️ Failed to log pause to activity: {log_err}")

    return jsonify({
        "success": True,
        "po_number": po_number,
        "status": "Pending",
        "message": f"Order {po_number} paused. Production preserved: {final_confirmed_qty:.2f}. Scales released.",
        "preserved_confirmed_qty": final_confirmed_qty,
        "preserved_weight_a": preserved_weight_a,
        "preserved_weight_b": preserved_weight_b,
        "preserved_weight_c": preserved_weight_c
    })

def _split_baseline_into_hi_lo(baseline_value: float) -> tuple:
    """
    Split a baseline value into HI and LO parts (same logic as emulator).
    
    Examples:
        - 10.87 -> (1, 0.87) or similar based on splitting logic
        - 100.40 -> (10, 0.40) or (100, 0.40) depending on format
    
    Returns:
        (baseline_hi, baseline_lo) tuple
    """
    # Convert to string to work with digits
    value_str = f"{baseline_value:.10f}".rstrip('0').rstrip('.')
    
    # Handle negative values
    is_negative = baseline_value < 0
    if is_negative:
        value_str = value_str[1:]  # Remove minus sign
    
    # Split integer and decimal parts
    if '.' in value_str:
        int_part, dec_part = value_str.split('.', 1)
    else:
        int_part = value_str
        dec_part = ""
    
    # Split integer part into HI and LO
    int_len = len(int_part)
    if int_len == 0:
        hi_int = "0"
        lo_int = "0"
    elif int_len == 1:
        # Single digit: HI=0, LO=digit
        hi_int = "0"
        lo_int = int_part
    elif int_len == 2:
        # Two digits: split each digit
        hi_int = int_part[0]
        lo_int = int_part[1]
    else:
        # Three or more digits: split roughly in half
        # For even length: split exactly in half
        # For odd length: give one extra digit to LO
        split_point = int_len // 2
        if int_len % 2 == 1:
            split_point += 1  # Give extra digit to LO for odd lengths
        hi_int = int_part[:split_point] if split_point > 0 else "0"
        lo_int = int_part[split_point:] if split_point < int_len else "0"
    
    # Reconstruct HI and LO
    # HI: high-order digits (integer)
    hi_value = float(hi_int) if hi_int else 0.0
    
    # LO: low-order digits + decimal part
    if dec_part:
        lo_value = float(lo_int + "." + dec_part) if lo_int else float("0." + dec_part)
    else:
        lo_value = float(lo_int) if lo_int else 0.0
    
    # Apply negative sign if needed
    if is_negative:
        hi_value = -hi_value
        lo_value = -lo_value
    
    return (hi_value, lo_value)

@orders_bp.route("/<string:po_number>/progress", methods=["GET"])
def get_progress(po_number: str):
    if ProcessOrder is None:
        raise NotFound("ProcessOrder model not available")

    try:
        with _db_session() as db:
            # 1️⃣ Fetch order safely
            order = db.query(ProcessOrder).filter(ProcessOrder.order_id == po_number).first()
            if not order:
                raise NotFound(f"Order {po_number} not found")

            # 2️⃣ Classify order (MILLING / PACKING)
            classification = classify_order(order)
            if classification.get("error"):
                return jsonify({"po_number": po_number, "error": classification["error"]}), 400

            order_type = classification["order_type"]
            equipment = classification["equipment"]
            
            # =============================================================================
            # SCALE LOCKING: Check if scales are locked by another order
            # =============================================================================
            # Get all scales that THIS order actually uses (equipment + byproduct)
            # ✅ Include byproduct scales for accurate conflict detection
            all_scales_for_order = get_all_scales_for_order(order, classification, include_byproduct=True)
            locked_scales_info = {}
            scales_locked_by_other = False
            locking_orders = set()
            
            # Only check scales that are actually used by this order
            # Only mark as locked if locked by a DIFFERENT order (not by current order)
            for scale in all_scales_for_order:
                scale_owner = get_scale_owner(scale)
                # Only consider it locked if it's locked by a DIFFERENT order
                if scale_owner is not None and scale_owner != po_number:
                    # If the scale is locked by another order, include it in the locked list
                    locked_scales_info[scale] = scale_owner
                    locking_orders.add(scale_owner)
                    scales_locked_by_other = True
                    print(f"🔒 [Progress-{po_number}] Scale {scale} is locked by order {scale_owner}")
                elif scale_owner == po_number:
                    # Scale is locked by current order - this is fine, not a conflict
                    print(f"✅ [Progress-{po_number}] Scale {scale} is locked by current order (not a conflict)")
                else:
                    # Scale is free (not locked)
                    print(f"🔓 [Progress-{po_number}] Scale {scale} is free (not locked)")
            
            # Create user-friendly message
            if scales_locked_by_other:
                locked_scale_list = ', '.join(locked_scales_info.keys())
                locking_order_list = ', '.join(sorted(locking_orders))
                if len(locking_orders) == 1:
                    message = f"Scales {locked_scale_list} are locked by order {locking_order_list}"
                else:
                    message = f"Scales {locked_scale_list} are locked by orders {locking_order_list}"
            else:
                message = None
            
            scale_lock_status = {
                "scales_locked": scales_locked_by_other,
                "locked_scales": locked_scales_info,
                "locking_orders": list(locking_orders),
                "message": message
            }

            # ✅ FIX: If auto-validator is stopped, calculate deltas from baseline and current SCADA
            # NOTE: scale_qty is ONLY for byproduct scales at order start, NOT for production deltas
            is_validating = is_order_validating(po_number)
            print(f"🔍 [Progress-{po_number}] CODE PATH CHECK: is_order_validating={is_validating}, equipment={equipment}")
            if not is_validating:
                # ✅ CRITICAL: Refresh order to get latest confirmed_qty and baseline from database
                db.refresh(order)
                
                # Determine unit and target
                if order_type == "MILLING":
                    target = float(get_attr_safe(order, "expected_weight") or get_attr_safe(order, "quantity") or 0.0)
                    unit = "KG"
                else:
                    # ✅ CRITICAL FIX (Jan 23, 2026): PACKING quantity is already in BAGS
                    # Only SCADA delta needs conversion (pallets → bags), NOT the target
                    target = float(get_attr_safe(order, "quantity") or 0.0)
                    unit = "BAG"

                # ✅ CRITICAL: Get stored confirmed_qty (preserved from previous run)
                # ⚠️ IMPORTANT: confirmed_qty is READ-ONLY in this endpoint - we NEVER modify it
                # confirmed_qty is only updated by the worker, not by the progress endpoint
                confirmed_qty_from_db = float(get_attr_safe(order, "confirmed_qty", 0.0) or 0.0)
                current_display = confirmed_qty_from_db
                print(f"📊 [Progress-{po_number}] Order stopped - returning preserved confirmed_qty: {current_display:.2f} {unit} (READ-ONLY, will NOT be modified)")
                # ✅ OVERFLOW: Read stored overflow for display
                overflow = float(get_attr_safe(order, "overflow_weight", 0.0) or 0.0)
                progress_pct = min(100.0, (current_display / target * 100) if target > 0 else 0.0)
                remaining = max(0.0, target - current_display)

                # ✅ CRITICAL: Calculate deltas from baseline and current SCADA readings (FOR DISPLAY ONLY)
                # ⚠️ IMPORTANT: These deltas are ONLY for display in the dialog - they do NOT affect confirmed_qty
                # confirmed_qty is preserved in database and should NOT be modified by this endpoint
                # Do NOT use scale_qty - it's only for byproduct scales at order start
                from services.scale_service import get_multiple_scada_readings
                
                # ✅ CRITICAL: Check if shift has ended (baseline was reset)
                # If shift ended, baseline was reset but confirmed_qty is preserved
                # In this case, deltas should be calculated from the NEW baseline (after reset)
                # But these deltas are just for display - they don't represent production to add to confirmed_qty
                shift_end_time = get_attr_safe(order, "shift_end_time")
                baseline_was_reset = shift_end_time is not None
                
                # Get current SCADA readings
                current_readings = get_multiple_scada_readings(equipment, force_fresh=True)
                
                # Build scale details from baseline and current SCADA (not scale_qty)
                scale_details = []
                
                # ✅ PALLETIZER AUTO-RESET at 100,000
                PALLETIZER_TAGS = ['PL601_TOT', 'PL602_TOT', 'PL603_TOT', 'SL606_TOT', 'SL607_TOT']
                PALLETIZER_AUTO_RESET_THRESHOLD = 100000.0
                
                for i, tag in enumerate(equipment, 1):
                    # ✅ FIX: For PL/SL scales, baseline is stored in scale1_qty/scale2_qty/scale3_qty
                    baseline = _get_baseline_for_tag(order, tag)
                    
                    # Get current SCADA reading
                    reading_data = current_readings.get(tag, {})
                    if isinstance(reading_data, dict):
                        current_scada = float(reading_data.get("current", 0.0) or 0.0)
                    else:
                        current_scada = float(reading_data or 0.0)
                    
                    # ✅ PALLETIZER AUTO-RESET: Handle both cases:
                    # 1. current >= 100,000 → reset baseline to current
                    # 2. rollover detected (baseline high, current low) → reset baseline to current
                    if tag.upper() in PALLETIZER_TAGS:
                        print(f"=" * 60)
                        print(f"🚨 PALLETIZER AUTO-RESET CHECK (STOPPED PATH)")
                        print(f"   Tag: {tag}")
                        print(f"   Current SCADA: {current_scada}")
                        print(f"   Baseline: {baseline}")
                        print(f"   Check: current_scada >= 100000.0 = {current_scada >= 100000.0}")
                        print(f"=" * 60)
                        
                        # Case 1: current reached 100,000 or more
                        reached_threshold = (current_scada >= 100000.0)
                        
                        # Case 2: rollover detected (baseline high, current dropped to near 0)
                        rollover_detected = (baseline > 50000 and current_scada < (baseline - 50000))
                        
                        if reached_threshold or rollover_detected:
                            reason = "reached 100,000" if reached_threshold else "rollover detected"
                            print(f"🔄 [Progress-{po_number}] AUTO-RESET {tag}: {reason}")
                            print(f"   baseline={baseline:.0f}, current={current_scada:.0f}")
                            
                            # Reset baseline to current (so delta becomes 0)
                            set_attr_safe(order, f"baseline_{tag.lower()}", current_scada)
                            baseline = current_scada
                            db.add(order)
                            db.commit()
                            print(f"   ✅ Baseline reset to {current_scada:.0f}, confirmed_qty preserved: {confirmed_qty_from_db:.2f}")
                        else:
                            print(f"   ⏭️ No reset needed (threshold not reached)")
                    
                    # ✅ FIX: DM scales - use sum_dm_readings_for_order (SUM of 30-sec readings), not dm_accumulated_*
                    if tag.startswith("DM"):
                        from services.scale_service import sum_dm_readings_for_order
                        delta = sum_dm_readings_for_order(tag, order)
                        print(f"💧 [Progress-{po_number}] {tag}: sum_dm_readings_for_order = {delta:.2f}")
                    else:
                        # WG and other scales: Calculate delta from baseline (for display only)
                        delta = max(0.0, current_scada - baseline)
                    
                    # Check if this scale is locked by another order (not by the current order)
                    scale_owner = get_scale_owner(tag)
                    # Only mark as locked if it's locked by a DIFFERENT order
                    # If scale_owner is None, scale is free (not locked)
                    # If scale_owner == po_number, scale is locked by current order (not a conflict, don't show as locked)
                    # If scale_owner != po_number, scale is locked by another order (show as locked)
                    is_locked = scale_owner is not None and scale_owner != po_number
                    locked_by = scale_owner if is_locked else None
                    
                    # Debug logging
                    print(f"🔍 [Progress-{po_number}] Scale {tag}: owner={scale_owner}, current_order={po_number}, is_locked={is_locked}")
                    
                    # ✅ FIX: DM scales show only delta (no baseline/current needed)
                    if tag.startswith("DM"):
                        scale_detail = {
                            "scale_number": i,
                            "scale_tag": tag,
                            "delta": round(float(delta), 3),  # SUM of all readings
                            "description": get_attr_safe(order, f"scale{i}") or tag,
                            "is_locked": is_locked,
                            "locked_by": locked_by,
                            "is_dm": True,  # Flag for UI to show only delta
                        }
                    else:
                        scale_detail = {
                            "scale_number": i,
                            "scale_tag": tag,
                            "baseline": round(float(baseline), 3),
                            "current_reading": round(float(current_scada), 3),
                            "delta": round(float(delta), 3),
                            "description": get_attr_safe(order, f"scale{i}") or tag,
                            "is_locked": is_locked,
                            "locked_by": locked_by,
                        }
                    scale_details.append(scale_detail)

                # Build equipment details from baseline and current SCADA (not scale_qty)
                # ✅ CRITICAL: Use RAW SQL to bypass ORM cache and get absolute latest data from database
                from sqlalchemy import text
                fresh_sql = text("""
                    SELECT scale1, scale1_qty, scale2, scale2_qty, scale3, scale3_qty 
                    FROM process_orders 
                    WHERE order_id = :order_id
                """)
                fresh_result = db.execute(fresh_sql, {"order_id": po_number}).fetchone()
                
                if fresh_result:
                    fresh_scale1_tag = str(fresh_result[0] or "")
                    fresh_scale1_qty = float(fresh_result[1] or 0.0)
                    fresh_scale2_tag = str(fresh_result[2] or "")
                    fresh_scale2_qty = float(fresh_result[3] or 0.0)
                    fresh_scale3_tag = str(fresh_result[4] or "")
                    fresh_scale3_qty = float(fresh_result[5] or 0.0)
                    print(f"🔄 [Progress-{po_number}] RAW SQL scale values: scale1={fresh_scale1_tag}({fresh_scale1_qty}), scale2={fresh_scale2_tag}({fresh_scale2_qty}), scale3={fresh_scale3_tag}({fresh_scale3_qty})")
                else:
                    fresh_scale1_qty = 0.0
                    fresh_scale2_qty = 0.0
                    fresh_scale3_qty = 0.0
                    fresh_scale1_tag = ""
                    fresh_scale2_tag = ""
                    fresh_scale3_tag = ""
                    print(f"⚠️ [Progress-{po_number}] RAW SQL returned no results for order")
                
                equipment_details = {}
                for tag in equipment:
                    # ✅ FIX: For PL/SL scales (PACKING orders), baseline is stored in scale1_qty/scale2_qty/scale3_qty
                    # not in baseline_{tag} attribute (which doesn't exist for these scales)
                    # Use fresh values queried directly from database
                    if tag.upper() == fresh_scale1_tag.upper():
                        baseline = fresh_scale1_qty
                    elif tag.upper() == fresh_scale2_tag.upper():
                        baseline = fresh_scale2_qty
                    elif tag.upper() == fresh_scale3_tag.upper():
                        baseline = fresh_scale3_qty
                    else:
                        # WG and DM scales use baseline_{tag} attributes
                        baseline = float(get_attr_safe(order, f"baseline_{tag.lower()}", 0.0) or 0.0)
                    
                    # Get current SCADA reading
                    reading_data = current_readings.get(tag, {})
                    if isinstance(reading_data, dict):
                        current_scada = float(reading_data.get("current", 0.0) or 0.0)
                    else:
                        current_scada = float(reading_data or 0.0)
                    
                    # ✅ FIX: DM scales - use sum_dm_readings_for_order (SUM of 30-sec readings), not dm_accumulated_*
                    if tag.startswith("DM"):
                        from services.scale_service import sum_dm_readings_for_order
                        delta = sum_dm_readings_for_order(tag, order)
                    else:
                        # WG and other scales: Calculate delta from baseline (for display only)
                        delta = max(0.0, current_scada - baseline)
                    
                    # ✅ NEW: Get HI/LO values separately for WG scales
                    hi_lo_data = None
                    if tag.startswith("WG") and tag in MILLING_FIELDS + INPUT_FIELDS:
                        print(f"🔍 [Progress-{po_number}] Fetching HI/LO for WG scale: {tag}")
                        from services.scale_service import get_wg_scale_hi_lo
                        hi_lo_data = get_wg_scale_hi_lo(tag, apply_reset=True)
                        print(f"🔍 [Progress-{po_number}] HI/LO data for {tag}: {hi_lo_data}")
                    else:
                        print(f"🔍 [Progress-{po_number}] Skipping HI/LO for {tag} (not WG scale in MILLING/INPUT fields)")
                    
                    # ✅ FIX: DM scales show only delta (no baseline/current needed)
                    if tag.startswith("DM"):
                        equipment_details[tag] = {
                            "delta": round(float(delta), 3),  # SUM of all readings
                            "is_dm": True,  # Flag for UI to show only delta
                        }
                    else:
                        equipment_details[tag] = {
                            "baseline": round(float(baseline), 3),
                            "current": round(float(current_scada), 3),
                            "delta": round(float(delta), 3),
                        }
                    
                    # ✅ ALWAYS Add baseline HI/LO for WG scales (split the combined baseline value)
                    # This ensures baseline HI/LO is always present, even if baseline is 0
                    if tag.startswith("WG") and tag in MILLING_FIELDS + INPUT_FIELDS:
                        baseline_hi, baseline_lo = _split_baseline_into_hi_lo(baseline)
                        equipment_details[tag]["baseline_hi"] = round(baseline_hi, 3)
                        equipment_details[tag]["baseline_lo"] = round(baseline_lo, 3)
                        # Always initialize hi/lo keys for WG scales (even if get_wg_scale_hi_lo fails)
                        equipment_details[tag].setdefault("hi", 0.0)
                        equipment_details[tag].setdefault("lo", 0.0)
                        print(f"✅ [Progress-{po_number}] Added baseline HI/LO for {tag}: baseline_hi={baseline_hi}, baseline_lo={baseline_lo}, baseline={baseline}")
                    
                    # ✅ Add HI/LO values if available
                    if hi_lo_data:
                        equipment_details[tag]["hi"] = round(hi_lo_data.get("hi", 0.0), 3)
                        equipment_details[tag]["lo"] = round(hi_lo_data.get("lo", 0.0), 3)
                        print(f"✅ [Progress-{po_number}] Added HI/LO to equipment_details[{tag}]: hi={equipment_details[tag].get('hi')}, lo={equipment_details[tag].get('lo')}")
                    else:
                        # Try to get HI/LO directly from emulator as fallback
                        if tag.startswith("WG") and tag in MILLING_FIELDS + INPUT_FIELDS:
                            try:
                                from database import USE_SCADA_EMULATOR, SCADA_EMULATOR_URL
                                if USE_SCADA_EMULATOR:
                                    import requests
                                    resp = requests.get(f"{SCADA_EMULATOR_URL}/scada/latest", timeout=5)
                                    if resp.status_code == 200:
                                        data = resp.json()
                                        raw_scales = data.get("raw_scales", {})
                                        hi_key = f"{tag}_HI"
                                        lo_key = f"{tag}_LO"
                                        if hi_key in raw_scales and lo_key in raw_scales:
                                            equipment_details[tag]["hi"] = round(float(raw_scales[hi_key]), 3)
                                            equipment_details[tag]["lo"] = round(float(raw_scales[lo_key]), 3)
                                            print(f"✅ [Progress-{po_number}] Added HI/LO via fallback for {tag}: hi={equipment_details[tag].get('hi')}, lo={equipment_details[tag].get('lo')}")
                            except Exception as e:
                                print(f"⚠️ [Progress-{po_number}] Fallback HI/LO fetch failed for {tag}: {e}")
                        if "hi" not in equipment_details[tag] or "lo" not in equipment_details[tag]:
                            print(f"⚠️ [Progress-{po_number}] No HI/LO data for {tag} (neither main nor fallback worked)")

                # Return calculated values from baseline and current SCADA (not from scale_qty)
                # ✅ CRITICAL: Refresh order to get latest byproduct scale values from database
                db.refresh(order)
                
                # ✅ Get byproduct scale quantities (for display and editing)
                scale1 = get_attr_safe(order, "scale1", "") or ""
                scale2 = get_attr_safe(order, "scale2", "") or ""
                scale3 = get_attr_safe(order, "scale3", "") or ""
                scale1_qty = float(get_attr_safe(order, "scale1_qty", 0.0) or 0.0)
                scale2_qty = float(get_attr_safe(order, "scale2_qty", 0.0) or 0.0)
                scale3_qty = float(get_attr_safe(order, "scale3_qty", 0.0) or 0.0)
                
                # ✅ NEW: Build byproduct_details with baseline/current/delta (similar to equipment_details)
                byproduct_details = {}
                for scale_key, tag in [("scale1", scale1), ("scale2", scale2), ("scale3", scale3)]:
                    if tag:
                        # Get baseline (captured at order start)
                        baseline = float(get_attr_safe(order, f"baseline_{tag.lower()}", 0.0) or 0.0)
                        # Get current SCADA reading
                        reading_data = current_readings.get(tag, {})
                        if isinstance(reading_data, dict):
                            current_val = float(reading_data.get("current", 0.0) or 0.0)
                        else:
                            current_val = float(reading_data or 0.0)
                        # Calculate delta
                        delta = max(0.0, current_val - baseline)
                        
                        # ✅ NEW: Get HI/LO values separately for WG scales
                        hi_lo_data = None
                        if tag.startswith("WG") and tag in MILLING_FIELDS + INPUT_FIELDS:
                            print(f"🔍 [Progress-{po_number}] Fetching HI/LO for byproduct WG scale: {tag}")
                            from services.scale_service import get_wg_scale_hi_lo
                            hi_lo_data = get_wg_scale_hi_lo(tag, apply_reset=True)
                            print(f"🔍 [Progress-{po_number}] HI/LO data for byproduct {tag}: {hi_lo_data}")
                        else:
                            print(f"🔍 [Progress-{po_number}] Skipping HI/LO for byproduct {tag} (not WG scale in MILLING/INPUT fields)")
                        
                        byproduct_details[tag] = {
                            "scale_key": scale_key,
                            "baseline": round(baseline, 3),
                            "current": round(current_val, 3),
                            "delta": round(delta, 3)
                        }
                        
                        # ✅ ALWAYS Add baseline HI/LO for WG scales (split the combined baseline value)
                        # This ensures baseline HI/LO is always present, even if baseline is 0
                        if tag.startswith("WG") and tag in MILLING_FIELDS + INPUT_FIELDS:
                            baseline_hi, baseline_lo = _split_baseline_into_hi_lo(baseline)
                            byproduct_details[tag]["baseline_hi"] = round(baseline_hi, 3)
                            byproduct_details[tag]["baseline_lo"] = round(baseline_lo, 3)
                            # Always initialize hi/lo keys for WG scales (even if get_wg_scale_hi_lo fails)
                            byproduct_details[tag].setdefault("hi", 0.0)
                            byproduct_details[tag].setdefault("lo", 0.0)
                            print(f"✅ [Progress-{po_number}] Added baseline HI/LO for byproduct {tag}: baseline_hi={baseline_hi}, baseline_lo={baseline_lo}, baseline={baseline}")
                        
                        # ✅ Add HI/LO values if available
                        if hi_lo_data:
                            byproduct_details[tag]["hi"] = round(hi_lo_data.get("hi", 0.0), 3)
                            byproduct_details[tag]["lo"] = round(hi_lo_data.get("lo", 0.0), 3)
                            print(f"✅ [Progress-{po_number}] Added HI/LO to byproduct_details[{tag}]: hi={byproduct_details[tag].get('hi')}, lo={byproduct_details[tag].get('lo')}")
                        else:
                            # Try to get HI/LO directly from emulator as fallback
                            if tag.startswith("WG") and tag in MILLING_FIELDS + INPUT_FIELDS:
                                try:
                                    from database import USE_SCADA_EMULATOR, SCADA_EMULATOR_URL
                                    if USE_SCADA_EMULATOR:
                                        import requests
                                        resp = requests.get(f"{SCADA_EMULATOR_URL}/scada/latest", timeout=5)
                                        if resp.status_code == 200:
                                            data = resp.json()
                                            raw_scales = data.get("raw_scales", {})
                                            hi_key = f"{tag}_HI"
                                            lo_key = f"{tag}_LO"
                                            if hi_key in raw_scales and lo_key in raw_scales:
                                                byproduct_details[tag]["hi"] = round(float(raw_scales[hi_key]), 3)
                                                byproduct_details[tag]["lo"] = round(float(raw_scales[lo_key]), 3)
                                                print(f"✅ [Progress-{po_number}] Added HI/LO via fallback for byproduct {tag}: hi={byproduct_details[tag].get('hi')}, lo={byproduct_details[tag].get('lo')}")
                                except Exception as e:
                                    print(f"⚠️ [Progress-{po_number}] Fallback HI/LO fetch failed for byproduct {tag}: {e}")
                            if "hi" not in byproduct_details[tag] or "lo" not in byproduct_details[tag]:
                                print(f"⚠️ [Progress-{po_number}] No HI/LO data for byproduct {tag} (neither main nor fallback worked)")
                
                # ✅ FIX: Show accumulated total (stored + current delta) for "Optional Overrides"
                # For stopped orders, stored value already includes previous production
                # delta = any new production since baselines were reset (usually 0 for stopped orders)
                scale1_delta = byproduct_details.get(scale1, {}).get("delta", 0.0) if scale1 else 0.0
                scale2_delta = byproduct_details.get(scale2, {}).get("delta", 0.0) if scale2 else 0.0
                scale3_delta = byproduct_details.get(scale3, {}).get("delta", 0.0) if scale3 else 0.0
                
                # Accumulated total = stored (captured on pause) + current delta (if any)
                scale1_total = scale1_qty + scale1_delta
                scale2_total = scale2_qty + scale2_delta
                scale3_total = scale3_qty + scale3_delta
                
                # ✅ DEBUG: Log byproduct values being returned
                print(f"📦 [Progress-{po_number}] (Stopped) Returning byproduct scales: scale1={scale1} (stored={scale1_qty:.5f} + delta={scale1_delta:.5f} = {scale1_total:.5f})")
                print(f"📦 [Progress-{po_number}] (Stopped) Byproduct details: {byproduct_details}")
                
                response = {
                    "po_number": po_number,
                    "order_type": order_type,
                    "status": get_attr_safe(order, "status"),
                    "material": get_attr_safe(order, "material"),
                    "version": get_attr_safe(order, "version"),
                    "batch": get_attr_safe(order, "batch"),
                    "target": round(float(target), 3),
                    "current": round(float(current_display), 3),
                    "remaining": round(float(remaining), 3),
                    "progress_pct": round(float(progress_pct), 2),
                    "unit": unit,
                    "overflow": round(float(overflow), 3),
                    "confirmed_qty": float(confirmed_qty_from_db),  # ✅ Use the value we read earlier (READ-ONLY)
                    # "last_confirmed_qty": float(get_attr_safe(order, "last_confirmed_qty", 0) or 0),
                    "equipment_list": equipment,
                    "formula": classification.get("formula", ""),
                    "scale_details": scale_details,
                    "equipment_details": equipment_details,
                    "scale_breakdown": {tag: round(float(equipment_details.get(tag, {}).get("delta", 0.0) or 0.0), 3) for tag in equipment},
                    "timestamp": datetime.now().isoformat(),
                    "auto_validation": "stopped",
                    "scale_lock_status": scale_lock_status,  # ✅ Add scale lock status
                    # ✅ Byproduct scales - use accumulated total (stored + delta)
                    "scale1": scale1,
                    "scale1_qty": round(float(scale1_total), 5),
                    "scale2": scale2,
                    "scale2_qty": round(float(scale2_total), 5),
                    "scale3": scale3,
                    "scale3_qty": round(float(scale3_total), 5),
                    # ✅ NEW: Byproduct details with baseline/current/delta (for display)
                    "byproduct_details": byproduct_details,
                    # ✅ Add shift weight fields for manual confirmation calculation
                    "weight_shift_a": float(get_attr_safe(order, "weight_shift_a", 0) or 0),
                    "weight_shift_b": float(get_attr_safe(order, "weight_shift_b", 0) or 0),
                    "weight_shift_c": float(get_attr_safe(order, "weight_shift_c", 0) or 0),
                    "confirmed_shift_a": float(get_attr_safe(order, "confirmed_shift_a", 0) or 0),
                    "confirmed_shift_b": float(get_attr_safe(order, "confirmed_shift_b", 0) or 0),
                    "confirmed_shift_c": float(get_attr_safe(order, "confirmed_shift_c", 0) or 0),
                    "current_shift": get_attr_safe(order, "current_shift", "A") or "A",
                    # ✅ CRITICAL: Add warning that deltas are display-only and do NOT affect confirmed_qty
                    "_warning": "Deltas shown are for display only and do NOT affect confirmed_qty. confirmed_qty is preserved in database and only updated by the worker."
                }
                # ✅ CRITICAL: Verify confirmed_qty was not modified (safety check)
                db.refresh(order)
                final_confirmed_qty = float(get_attr_safe(order, "confirmed_qty", 0.0) or 0.0)
                if abs(final_confirmed_qty - confirmed_qty_from_db) > 0.0001:
                    print(f"⚠️ [Progress-{po_number}] WARNING: confirmed_qty changed during progress call! {confirmed_qty_from_db:.2f} → {final_confirmed_qty:.2f}")
                else:
                    print(f"✅ [Progress-{po_number}] confirmed_qty unchanged: {confirmed_qty_from_db:.2f} (verified)")
                return jsonify(response)

            # 3️⃣ Get SCADA readings + baselines (only when auto-validator is running)
            # ✅ CRITICAL: Refresh order to ensure we have latest baseline values from database
            db.refresh(order)
            prod_info = get_current_production(order, classification, db=db)
            if prod_info.get("error"):
                return jsonify({"po_number": po_number, "error": prod_info["error"]}), 400

            deltas = prod_info["deltas"]
            baselines = prod_info["baselines"]
            per_scale = prod_info["per_scale"]
            baseline_needs_fix = prod_info.get("baseline_needs_fix", False)

            new_production = float(prod_info.get("total", 0.0) or 0.0)
            order_type = classification["order_type"]
            equipment = classification["equipment"]

            # 4️⃣ Determine unit and target
            if order_type == "MILLING":
                target = float(get_attr_safe(order, "expected_weight") or get_attr_safe(order, "quantity") or 0.0)
                unit = "KG"
            else:
                # ✅ CRITICAL FIX (Jan 23, 2026): PACKING quantity is already in BAGS
                # Only SCADA delta needs conversion (pallets → bags), NOT the target
                target = float(get_attr_safe(order, "quantity") or 0.0)
                unit = "BAG"

            # 5️⃣ Calculate progress quantities
            # ✅ CRITICAL: Refresh order to get latest shift weight from database
            db.refresh(order)
            
            # ✅ CRITICAL: For active orders, use shift weight (worker updates this in real-time)
            # confirmed_qty is only set when order completes/validates, so for active orders we use shift weight
            current_shift = get_attr_safe(order, "current_shift", "A").upper()
            shift_weight_field = f"weight_shift_{current_shift.lower()}"
            shift_weight = float(get_attr_safe(order, shift_weight_field, 0.0) or 0.0)
            
            # ✅ Display logic: Prefer confirmed_qty if available (preserved cumulative production)
            # ⚠️ IMPORTANT: confirmed_qty is READ-ONLY in this endpoint - we NEVER modify it
            # confirmed_qty is only updated by the worker, not by the progress endpoint
            # confirmed_qty is preserved even after shift ends and represents total production
            confirmed_qty_from_db = float(get_attr_safe(order, "confirmed_qty", 0.0) or 0.0)
            
            if confirmed_qty_from_db > 0.0:
                # ✅ CRITICAL: Use confirmed_qty directly - it represents cumulative production
                # The worker may update confirmed_qty continuously or at shift end
                # Either way, confirmed_qty is the source of truth for total production
                current_display = min(confirmed_qty_from_db, target)
                print(f"📊 [Progress-{po_number}] Using confirmed_qty (preserved cumulative): {confirmed_qty_from_db:.2f} {unit} (READ-ONLY)")
            elif shift_weight > 0.0:
                # No confirmed_qty yet, use shift weight (first shift, no previous production)
                current_display = min(shift_weight, target)
                print(f"📊 [Progress-{po_number}] Using shift weight for current: {shift_weight:.2f} {unit} (shift {current_shift})")
            else:
                # Worker hasn't accumulated yet, use SCADA delta as fallback
                current_display = min(new_production, target)
                print(f"📊 [Progress-{po_number}] Shift weight is 0, using SCADA delta as fallback: {new_production:.2f} {unit}")

            # ✅ OVERFLOW: Calculate and store overflow for transfer to next order
            overflow = max(0.0, current_display - target)

            # ✅ CRITICAL: update_order_scales only updates scale1_qty, scale2_qty, scale3_qty
            # It does NOT modify confirmed_qty - confirmed_qty is only updated by the worker
            update_order_scales(order, deltas)

            # ✅ OVERFLOW STORAGE: Store overflow for transfer to next order of same type
            if overflow > 0:
                set_attr_safe(order, "overflow_weight", overflow)

            # Calculate progress
            progress_pct = min(100.0, (current_display / target * 100)) if target > 0 else 0.0
            remaining = max(0.0, target - current_display)


            # 6️⃣ Build scale details for UI
            # Only show scales that are in the equipment list (for display)
            # But check lock status only for scales that are actually used by this order
            scale_details = []
            
            for i, tag in enumerate(equipment, 1):
                baseline = baselines.get(tag, 0.0)
                delta = per_scale.get(tag, 0.0)
                current_reading = deltas.get(tag, {}).get("current", 0.0)
                
                # Log baseline and current values
                print(f"🔍 [Progress-{po_number}] {tag}: baseline={baseline:.2f}, current={current_reading:.2f}, delta={delta:.2f}")

                # Check if this scale is locked by another order (not by the current order)
                # Only check lock status if this scale is actually used by the current order
                # (it should be in all_scales_for_order, which includes equipment + byproduct)
                scale_owner = get_scale_owner(tag)
                # Only mark as locked if it's locked by a DIFFERENT order
                # If scale_owner is None, scale is free (not locked)
                # If scale_owner == po_number, scale is locked by current order (not a conflict, don't show as locked)
                # If scale_owner != po_number, scale is locked by another order (show as locked)
                is_locked = scale_owner is not None and scale_owner != po_number
                locked_by = scale_owner if is_locked else None
                
                # Debug logging
                print(f"🔍 [Progress-{po_number}] Scale {tag}: owner={scale_owner}, current_order={po_number}, is_locked={is_locked}")

                scale_detail = {
                    "scale_number": i,
                    "scale_tag": tag,
                    "baseline": round(float(baseline), 3),
                    "current_reading": round(float(current_reading), 3),
                    "delta": round(float(delta), 3),
                    "description": get_attr_safe(order, f"scale{i}") or tag,
                    "is_locked": is_locked,  # ✅ Add lock status (only True if locked by another order)
                    "locked_by": locked_by,  # ✅ Add which order is locking this scale (None if not locked or locked by current order)
                }
                scale_details.append(scale_detail)

            # 7️⃣ Commit once — includes baseline fixes + progress updates
            if baseline_needs_fix:
                print(f"✅ Fixing baselines for {po_number} — committing changes.")
            db.commit()

            # 8️⃣ Prepare per-scale summary
            equipment_details = {}
            for tag in equipment:
                d = deltas.get(tag, {})
                equipment_details[tag] = {
                    "baseline": round(float(baselines.get(tag, 0.0)), 3),
                    "current": round(float(d.get("current", 0.0)), 3),
                    "delta": round(float(d.get("delta", 0.0)), 3),
                }

            # 9️⃣ Return clean JSON response
            # ✅ CRITICAL: Refresh order to get latest byproduct scale values from database
            db.refresh(order)
            
            # ✅ Get byproduct scale quantities (for display and editing)
            scale1 = get_attr_safe(order, "scale1", "") or ""
            scale2 = get_attr_safe(order, "scale2", "") or ""
            scale3 = get_attr_safe(order, "scale3", "") or ""
            scale1_qty = float(get_attr_safe(order, "scale1_qty", 0.0) or 0.0)
            scale2_qty = float(get_attr_safe(order, "scale2_qty", 0.0) or 0.0)
            scale3_qty = float(get_attr_safe(order, "scale3_qty", 0.0) or 0.0)
            print(f"🔧🔧🔧 [PROGRESS-DEBUG] {po_number}: scale1_qty={scale1_qty:.5f}, scale2_qty={scale2_qty:.5f}, scale3_qty={scale3_qty:.5f} (from DB)")
            
            # ✅ FIX: Get current SCADA readings for byproduct scales (if they're not in equipment)
            # This is needed for byproduct-only scales that might not be in the deltas dict
            byproduct_scales = [s for s in [scale1, scale2, scale3] if s and s not in equipment]
            if byproduct_scales:
                from services.scale_service import get_multiple_scada_readings
                current_readings = get_multiple_scada_readings(byproduct_scales, force_fresh=True)
            else:
                current_readings = {}
            
            # ✅ NEW: Build byproduct_details with baseline/current/delta (similar to equipment_details)
            byproduct_details = {}
            for scale_key, tag in [("scale1", scale1), ("scale2", scale2), ("scale3", scale3)]:
                if tag:
                    # Get baseline (captured at order start)
                    baseline = float(get_attr_safe(order, f"baseline_{tag.lower()}", 0.0) or 0.0)
                    # Get current SCADA reading from deltas dict (already fetched)
                    reading = deltas.get(tag, {})
                    if isinstance(reading, dict):
                        current_val = float(reading.get("current", 0.0) or 0.0)
                    else:
                        current_val = float(reading or 0.0)
                    # If not in deltas, try current_readings (for byproduct-only scales)
                    if current_val == 0.0 and tag in current_readings:
                        reading = current_readings.get(tag, {})
                        if isinstance(reading, dict):
                            current_val = float(reading.get("current", 0.0) or 0.0)
                        else:
                            current_val = float(reading or 0.0)
                    # Calculate delta
                    delta = max(0.0, current_val - baseline)
                    byproduct_details[tag] = {
                        "scale_key": scale_key,
                        "baseline": round(baseline, 3),
                        "current": round(current_val, 3),
                        "delta": round(delta, 3)
                    }
            
            # ✅ FIX: Show accumulated total (stored + current delta) for "Optional Overrides"
            # stored = value captured on previous pause(s)
            # delta = new production since last restart
            # total = what will be sent to SAP if confirmed now
            scale1_delta = byproduct_details.get(scale1, {}).get("delta", 0.0) if scale1 else 0.0
            scale2_delta = byproduct_details.get(scale2, {}).get("delta", 0.0) if scale2 else 0.0
            scale3_delta = byproduct_details.get(scale3, {}).get("delta", 0.0) if scale3 else 0.0
            
            # Accumulated total = stored (from previous pauses) + current delta (new production)
            scale1_total = scale1_qty + scale1_delta
            scale2_total = scale2_qty + scale2_delta
            scale3_total = scale3_qty + scale3_delta
            
            # ✅ DEBUG: Log byproduct values being returned
            print(f"📦 [Progress-{po_number}] Returning byproduct scales: scale1={scale1} (stored={scale1_qty:.5f} + delta={scale1_delta:.5f} = {scale1_total:.5f})")
            print(f"📦 [Progress-{po_number}] Byproduct details: {byproduct_details}")
            
            response = {
                "po_number": po_number,
                "order_type": order_type,
                "status": get_attr_safe(order, "status"),
                "material": get_attr_safe(order, "material"),
                "version": get_attr_safe(order, "version"),
                "batch": get_attr_safe(order, "batch"),
                "target": round(float(target), 3),
                "current": round(float(current_display), 3),
                "remaining": round(float(remaining), 3),
                "progress_pct": round(float(progress_pct), 2),
                "unit": unit,
                "overflow": round(float(overflow), 3),
                "confirmed_qty": float(confirmed_qty_from_db),  # ✅ Use the value we read earlier (READ-ONLY)
                # "last_confirmed_qty": float(get_attr_safe(order, "last_confirmed_qty", 0) or 0),
                "equipment_list": equipment,
                "formula": classification.get("formula", ""),
                "scale_details": scale_details,
                "equipment_details": equipment_details,
                "scale_breakdown": {tag: round(float(val), 3) for tag, val in per_scale.items()},
                "timestamp": datetime.now().isoformat(),
                "auto_validation": "running",
                "scale_lock_status": scale_lock_status,  # ✅ Add scale lock status
                # ✅ Byproduct scales - use accumulated total (stored + delta)
                "scale1": scale1,
                "scale1_qty": round(float(scale1_total), 5),
                "scale2": scale2,
                "scale2_qty": round(float(scale2_total), 5),
                "scale3": scale3,
                "scale3_qty": round(float(scale3_total), 5),
                # ✅ NEW: Byproduct details with baseline/current/delta (for display)
                "byproduct_details": byproduct_details,
                # ✅ Add shift weight fields for manual confirmation calculation
                "weight_shift_a": float(get_attr_safe(order, "weight_shift_a", 0) or 0),
                "weight_shift_b": float(get_attr_safe(order, "weight_shift_b", 0) or 0),
                "weight_shift_c": float(get_attr_safe(order, "weight_shift_c", 0) or 0),
                "confirmed_shift_a": float(get_attr_safe(order, "confirmed_shift_a", 0) or 0),
                "confirmed_shift_b": float(get_attr_safe(order, "confirmed_shift_b", 0) or 0),
                "confirmed_shift_c": float(get_attr_safe(order, "confirmed_shift_c", 0) or 0),
                "current_shift": get_attr_safe(order, "current_shift", "A") or "A",
                # ✅ CRITICAL: Add warning that deltas are display-only and do NOT affect confirmed_qty
                "_warning": "Deltas shown are for display only and do NOT affect confirmed_qty. confirmed_qty is only updated by the worker."
            }

            # ✅ CRITICAL: Verify confirmed_qty was not modified (safety check)
            db.refresh(order)
            final_confirmed_qty = float(get_attr_safe(order, "confirmed_qty", 0.0) or 0.0)
            if abs(final_confirmed_qty - confirmed_qty_from_db) > 0.0001:
                print(f"⚠️ [Progress-{po_number}] WARNING: confirmed_qty changed during progress call! {confirmed_qty_from_db:.2f} → {final_confirmed_qty:.2f}")
            else:
                print(f"✅ [Progress-{po_number}] confirmed_qty unchanged: {confirmed_qty_from_db:.2f} (verified)")

            return jsonify(response)

    except NotFound as e:
        return jsonify({"error": str(e)}), 404
    except Exception as e:
        print(f"❌ ERROR in get_progress: {e}")
        import traceback
        traceback.print_exc()
        db.rollback()
        return jsonify({"error": f"Internal error: {str(e)}"}), 500


# =============================================================================
# BATCH PROGRESS ENDPOINT - C31-T37 (Task 18)
# Fetch progress of multiple orders in a single API call
# =============================================================================

@orders_bp.route("/progress-batch", methods=["POST"])
def get_progress_batch():
    """
    Batch endpoint for fetching progress of multiple orders at once.
    Reduces N API calls to 1, improving frontend performance.
    
    Request body:
    {
        "order_ids": ["000013005841", "000013005842", ...]
    }
    
    Returns:
    {
        "success": true,
        "data": {
            "000013005841": { ...progress data... },
            "000013005842": { ...progress data... },
            ...
        },
        "errors": {
            "invalid_order_id": "Order not found"
        }
    }
    """
    if ProcessOrder is None:
        return jsonify({"success": False, "error": "ProcessOrder model not available"}), 500
    
    # Parse request body
    try:
        body = request.get_json() or {}
        order_ids = body.get("order_ids", [])
    except Exception as e:
        return jsonify({"success": False, "error": f"Invalid request body: {str(e)}"}), 400
    
    # Validate order_ids
    if not order_ids:
        return jsonify({"success": False, "error": "order_ids is required and must be a non-empty array"}), 400
    
    if not isinstance(order_ids, list):
        return jsonify({"success": False, "error": "order_ids must be an array"}), 400
    
    # Cap at 50 orders to prevent abuse
    MAX_BATCH_SIZE = 50
    if len(order_ids) > MAX_BATCH_SIZE:
        return jsonify({
            "success": False, 
            "error": f"Maximum batch size is {MAX_BATCH_SIZE} orders, received {len(order_ids)}"
        }), 400
    
    result_data = {}
    errors = {}
    
    try:
        with _db_session() as db:
            # Fetch all orders in a single query for efficiency
            orders = db.query(ProcessOrder).filter(
                ProcessOrder.order_id.in_(order_ids)
            ).all()
            
            # Create a map for quick lookup
            order_map = {order.order_id: order for order in orders}
            
            # Process each requested order
            for po_number in order_ids:
                try:
                    order = order_map.get(po_number)
                    if not order:
                        errors[po_number] = "Order not found"
                        continue
                    
                    # Get progress data for this order
                    progress_data = _get_order_progress_for_batch(db, order, po_number)
                    result_data[po_number] = progress_data
                    
                except Exception as e:
                    print(f"❌ [BatchProgress] Error processing order {po_number}: {e}")
                    errors[po_number] = f"Error: {str(e)}"
            
            return jsonify({
                "success": True,
                "data": result_data,
                "errors": errors if errors else None,
                "summary": {
                    "requested": len(order_ids),
                    "success": len(result_data),
                    "failed": len(errors)
                }
            })
            
    except Exception as e:
        print(f"❌ [BatchProgress] Error in get_progress_batch: {e}")
        import traceback
        traceback.print_exc()
        return jsonify({"success": False, "error": f"Internal error: {str(e)}"}), 500


def _get_order_progress_for_batch(db, order, po_number):
    """
    Helper function to get progress data for a single order.
    Used by the batch endpoint. Returns a dict with progress data.
    
    This is a simplified version that returns essential fields for frontend display.
    """
    # Classify order (MILLING / PACKING)
    classification = classify_order(order)
    if classification.get("error"):
        return {"po_number": po_number, "error": classification["error"]}
    
    order_type = classification["order_type"]
    equipment = classification["equipment"]
    
    # Check scale lock status
    all_scales_for_order = get_all_scales_for_order(order, classification, include_byproduct=True)
    locked_scales_info = {}
    scales_locked_by_other = False
    locking_orders = set()
    
    for scale in all_scales_for_order:
        scale_owner = get_scale_owner(scale)
        if scale_owner is not None and scale_owner != po_number:
            locked_scales_info[scale] = scale_owner
            locking_orders.add(scale_owner)
            scales_locked_by_other = True
    
    scale_lock_status = {
        "scales_locked": scales_locked_by_other,
        "locked_scales": locked_scales_info,
        "locking_orders": list(locking_orders),
    }
    
    # Determine unit and target
    if order_type == "MILLING":
        target = float(get_attr_safe(order, "expected_weight") or get_attr_safe(order, "quantity") or 0.0)
        unit = "KG"
    else:
        # ✅ CRITICAL FIX (Jan 23, 2026): PACKING quantity is already in BAGS
        # Only SCADA delta needs conversion (pallets → bags), NOT the target
        target = float(get_attr_safe(order, "quantity") or 0.0)
        unit = "BAG"
    
    # Get confirmed_qty from database
    confirmed_qty = float(get_attr_safe(order, "confirmed_qty", 0.0) or 0.0)
    
    # Get shift weights
    weight_shift_a = float(get_attr_safe(order, "weight_shift_a", 0) or 0)
    weight_shift_b = float(get_attr_safe(order, "weight_shift_b", 0) or 0)
    weight_shift_c = float(get_attr_safe(order, "weight_shift_c", 0) or 0)
    current_shift = get_attr_safe(order, "current_shift", "A") or "A"
    
    # Calculate current display value
    is_validating = is_order_validating(po_number)
    
    if confirmed_qty > 0:
        current_display = confirmed_qty
    else:
        # Use shift weight as fallback
        shift_weight_field = f"weight_shift_{current_shift.lower()}"
        shift_weight = float(get_attr_safe(order, shift_weight_field, 0.0) or 0.0)
        current_display = shift_weight
    
    # Calculate progress
    progress_pct = min(100.0, (current_display / target * 100)) if target > 0 else 0.0
    remaining = max(0.0, target - current_display)
    overflow = float(get_attr_safe(order, "overflow_weight", 0.0) or 0.0)
    
    # Get byproduct scales
    scale1 = get_attr_safe(order, "scale1", "") or ""
    scale2 = get_attr_safe(order, "scale2", "") or ""
    scale3 = get_attr_safe(order, "scale3", "") or ""
    scale1_qty = float(get_attr_safe(order, "scale1_qty", 0.0) or 0.0)
    scale2_qty = float(get_attr_safe(order, "scale2_qty", 0.0) or 0.0)
    scale3_qty = float(get_attr_safe(order, "scale3_qty", 0.0) or 0.0)
    
    # Build response
    return {
        "po_number": po_number,
        "order_type": order_type,
        "status": get_attr_safe(order, "status"),
        "material": get_attr_safe(order, "material"),
        "version": get_attr_safe(order, "version"),
        "batch": get_attr_safe(order, "batch"),
        "target": round(float(target), 3),
        "current": round(float(current_display), 3),
        "remaining": round(float(remaining), 3),
        "progress_pct": round(float(progress_pct), 2),
        "unit": unit,
        "overflow": round(float(overflow), 3),
        "confirmed_qty": round(float(confirmed_qty), 3),
        "equipment_list": equipment,
        "formula": classification.get("formula", ""),
        "scale_lock_status": scale_lock_status,
        "auto_validation": "running" if is_validating else "stopped",
        # Byproduct scales
        "scale1": scale1,
        "scale1_qty": round(float(scale1_qty), 5),
        "scale2": scale2,
        "scale2_qty": round(float(scale2_qty), 5),
        "scale3": scale3,
        "scale3_qty": round(float(scale3_qty), 5),
        # Shift weights
        "weight_shift_a": weight_shift_a,
        "weight_shift_b": weight_shift_b,
        "weight_shift_c": weight_shift_c,
        "confirmed_shift_a": float(get_attr_safe(order, "confirmed_shift_a", 0) or 0),
        "confirmed_shift_b": float(get_attr_safe(order, "confirmed_shift_b", 0) or 0),
        "confirmed_shift_c": float(get_attr_safe(order, "confirmed_shift_c", 0) or 0),
        "current_shift": current_shift,
        "timestamp": datetime.now().isoformat(),
    }


@orders_bp.route("/<string:po_number>/update-byproduct-scales", methods=["POST"])
def update_byproduct_scales(po_number: str):
    """
    Update byproduct scale quantities (scale1_qty, scale2_qty, scale3_qty).
    
    ✅ CRITICAL: This endpoint ONLY updates byproduct scale quantities.
    It does NOT affect:
    - Order validation logic
    - Weight getting logic (confirmed_qty, weight_shift_X)
    - Scale locking/unlocking
    - Priority logic
    
    This is a simple data update for display/reporting purposes only.
    """
    if ProcessOrder is None:
        raise NotFound("ProcessOrder model not available")
    
    try:
        data = request.get_json()
        if not data:
            return jsonify({"error": "No data provided"}), 400
        
        scale1_qty = data.get("scale1_qty")
        scale2_qty = data.get("scale2_qty")
        scale3_qty = data.get("scale3_qty")
        
        # Validate that at least one value is provided
        if scale1_qty is None and scale2_qty is None and scale3_qty is None:
            return jsonify({"error": "At least one scale quantity must be provided"}), 400
        
        with _db_session() as db:
            order = db.query(ProcessOrder).filter(ProcessOrder.order_id == po_number).first()
            if not order:
                return jsonify({"error": f"Order {po_number} not found"}), 404
            
            # ✅ CRITICAL: Only update the provided values
            # This does NOT affect validation, weight logic, scale locking, or priority
            updated_fields = []
            
            if scale1_qty is not None:
                try:
                    scale1_qty_val = float(scale1_qty)
                    set_attr_safe(order, "scale1_qty", scale1_qty_val)
                    updated_fields.append(f"scale1_qty={scale1_qty_val:.5f}")
                    print(f"✅ [Update-{po_number}] Updated scale1_qty: {scale1_qty_val:.5f}")
                except (ValueError, TypeError):
                    return jsonify({"error": "scale1_qty must be a valid number"}), 400
            
            if scale2_qty is not None:
                try:
                    scale2_qty_val = float(scale2_qty)
                    set_attr_safe(order, "scale2_qty", scale2_qty_val)
                    updated_fields.append(f"scale2_qty={scale2_qty_val:.5f}")
                    print(f"✅ [Update-{po_number}] Updated scale2_qty: {scale2_qty_val:.5f}")
                except (ValueError, TypeError):
                    return jsonify({"error": "scale2_qty must be a valid number"}), 400
            
            if scale3_qty is not None:
                try:
                    scale3_qty_val = float(scale3_qty)
                    set_attr_safe(order, "scale3_qty", scale3_qty_val)
                    updated_fields.append(f"scale3_qty={scale3_qty_val:.5f}")
                    print(f"✅ [Update-{po_number}] Updated scale3_qty: {scale3_qty_val:.5f}")
                except (ValueError, TypeError):
                    return jsonify({"error": "scale3_qty must be a valid number"}), 400
            
            # Commit the changes
            db.add(order)
            db.commit()
            
            print(f"✅ [Update-{po_number}] Successfully updated byproduct scales: {', '.join(updated_fields)}")
            
            return jsonify({
                "success": True,
                "po_number": po_number,
                "message": f"Successfully updated byproduct scale quantities: {', '.join(updated_fields)}",
                "updated_fields": updated_fields,
                "scale1": get_attr_safe(order, "scale1", ""),
                "scale1_qty": float(get_attr_safe(order, "scale1_qty", 0.0) or 0.0),
                "scale2": get_attr_safe(order, "scale2", ""),
                "scale2_qty": float(get_attr_safe(order, "scale2_qty", 0.0) or 0.0),
                "scale3": get_attr_safe(order, "scale3", ""),
                "scale3_qty": float(get_attr_safe(order, "scale3_qty", 0.0) or 0.0),
            })
    
    except NotFound as e:
        return jsonify({"error": str(e)}), 404
    except Exception as e:
        print(f"❌ ERROR in update_byproduct_scales: {e}")
        import traceback
        traceback.print_exc()
        db.rollback()
        return jsonify({"error": f"Internal error: {str(e)}"}), 500


# =============================================================================
# MANUAL CONFIRMATION FROM PROGRESS DIALOG
# =============================================================================
@orders_bp.route("/<string:po_number>/manual-confirm", methods=["POST"])
def manual_confirm_from_progress(po_number: str):
    """
    Manual Confirmation endpoint for the progress dialog.
    
    Features:
    - Accepts override quantity (or uses current production)
    - Handles byproduct scale overrides
    - Stores byproduct overflow for next order in queue
    - Sends confirmation to SAP
    - Resets accumulated values after successful confirmation
    """
    from services.sap_confirmation import SAPConfirmationService
    from utils.vpn_check import check_vpn_connection
    from services.error_logger import log_order_error
    
    if ProcessOrder is None:
        return jsonify({"error": "ProcessOrder model not available"}), 500
    
    data = request.get_json(silent=True) or {}
    
    # Extract fields from request
    yield_qty = data.get("yield")  # Override quantity (optional)
    scrap = float(data.get("scrap", 0) or 0)
    confirmed_text = data.get("confirmed_text", "")
    shift = data.get("shift", "A").upper()
    operator = data.get("operator", "manual")
    
    # Byproduct scale overrides (optional)
    scale1_qty_override = data.get("scale1_qty")
    scale2_qty_override = data.get("scale2_qty")
    scale3_qty_override = data.get("scale3_qty")
    
    print(f"\n{'='*60}")
    print(f"📤 [Manual Confirm] Processing {po_number}")
    print(f"   yield_override={yield_qty}, scrap={scrap}")
    print(f"   scale1_override={scale1_qty_override}, scale2_override={scale2_qty_override}, scale3_override={scale3_qty_override}")
    print(f"{'='*60}")
    
    try:
        with _db_session() as db:
            order = db.query(ProcessOrder).filter(ProcessOrder.order_id == po_number).first()
            
            if not order:
                return jsonify({"error": f"Order {po_number} not found"}), 404
            
            if order.status != 'InProgress':
                return jsonify({"error": f"Order must be InProgress to confirm. Current status: {order.status}"}), 400
            
            # Get current accumulated values
            current_confirmed_qty = float(get_attr_safe(order, "confirmed_qty", 0) or 0)
            
            # ✅ FIX: Calculate accumulated byproduct totals (stored + current delta)
            # stored = accumulated from previous pause(s), delta = new production since restart
            from services.scale_service import get_scada_reading
            
            scale1_tag = get_attr_safe(order, "scale1", None)
            scale2_tag = get_attr_safe(order, "scale2", None)
            scale3_tag = get_attr_safe(order, "scale3", None)
            
            # Get stored values (accumulated from previous pauses)
            stored_scale1_qty = float(get_attr_safe(order, "scale1_qty", 0.0) or 0.0)
            stored_scale2_qty = float(get_attr_safe(order, "scale2_qty", 0.0) or 0.0)
            stored_scale3_qty = float(get_attr_safe(order, "scale3_qty", 0.0) or 0.0)
            
            # Calculate current delta = current SCADA - baseline for each byproduct scale
            delta_scale1 = 0.0
            delta_scale2 = 0.0
            delta_scale3 = 0.0
            
            if scale1_tag:
                baseline1 = float(get_attr_safe(order, f"baseline_{scale1_tag.lower()}", 0.0) or 0.0)
                current1 = float(get_scada_reading(scale1_tag) or 0.0)
                delta_scale1 = max(0.0, current1 - baseline1)
                
            if scale2_tag:
                baseline2 = float(get_attr_safe(order, f"baseline_{scale2_tag.lower()}", 0.0) or 0.0)
                current2 = float(get_scada_reading(scale2_tag) or 0.0)
                delta_scale2 = max(0.0, current2 - baseline2)
                
            if scale3_tag:
                baseline3 = float(get_attr_safe(order, f"baseline_{scale3_tag.lower()}", 0.0) or 0.0)
                current3 = float(get_scada_reading(scale3_tag) or 0.0)
                delta_scale3 = max(0.0, current3 - baseline3)
            
            # Accumulated total = stored + current delta
            current_scale1_qty = stored_scale1_qty + delta_scale1
            current_scale2_qty = stored_scale2_qty + delta_scale2
            current_scale3_qty = stored_scale3_qty + delta_scale3
            
            print(f"📊 [{po_number}] Byproduct totals: scale1 (stored={stored_scale1_qty:.4f} + delta={delta_scale1:.4f} = {current_scale1_qty:.4f})")
            print(f"📊 [{po_number}] Byproduct totals: scale2 (stored={stored_scale2_qty:.4f} + delta={delta_scale2:.4f} = {current_scale2_qty:.4f})")
            print(f"📊 [{po_number}] Byproduct totals: scale3 (stored={stored_scale3_qty:.4f} + delta={delta_scale3:.4f} = {current_scale3_qty:.4f})")
            
            # ✅ CRITICAL FIX (Jan 23, 2026): Calculate available-to-confirm from shift weights
            # This ensures SAP confirmation sends the FULL production, not just confirmed_qty
            # Total production = sum of all shift weights
            # Total already sent to SAP = sum of all confirmed_shift values
            # Available to confirm = total production - already sent
            weight_shift_a = float(get_attr_safe(order, "weight_shift_a", 0) or 0)
            weight_shift_b = float(get_attr_safe(order, "weight_shift_b", 0) or 0)
            weight_shift_c = float(get_attr_safe(order, "weight_shift_c", 0) or 0)
            total_shift_production = weight_shift_a + weight_shift_b + weight_shift_c
            
            confirmed_shift_a = float(get_attr_safe(order, "confirmed_shift_a", 0) or 0)
            confirmed_shift_b = float(get_attr_safe(order, "confirmed_shift_b", 0) or 0)
            confirmed_shift_c = float(get_attr_safe(order, "confirmed_shift_c", 0) or 0)
            total_already_confirmed_to_sap = confirmed_shift_a + confirmed_shift_b + confirmed_shift_c
            
            available_to_confirm = total_shift_production - total_already_confirmed_to_sap
            
            print(f"📊 [{po_number}] Shift production: A={weight_shift_a:.2f}, B={weight_shift_b:.2f}, C={weight_shift_c:.2f}, Total={total_shift_production:.2f}")
            print(f"📊 [{po_number}] Already confirmed: A={confirmed_shift_a:.2f}, B={confirmed_shift_b:.2f}, C={confirmed_shift_c:.2f}, Total={total_already_confirmed_to_sap:.2f}")
            print(f"📊 [{po_number}] Available to confirm: {available_to_confirm:.2f}")
            
            # Determine confirmation quantity
            if yield_qty is not None:
                # User provided explicit override quantity
                confirm_qty = float(yield_qty)
                print(f"📤 [{po_number}] Using user-provided yield override: {confirm_qty:.2f}")
            else:
                # ✅ FIX: Use available_to_confirm (from shift weights) instead of confirmed_qty
                # This ensures we send the FULL remaining production to SAP
                confirm_qty = available_to_confirm
                print(f"📤 [{po_number}] Using available_to_confirm (shift weights - already confirmed): {confirm_qty:.2f}")
            
            if confirm_qty <= 0:
                return jsonify({"error": f"No production available to confirm. Total production: {total_shift_production:.2f}, Already confirmed to SAP: {total_already_confirmed_to_sap:.2f}"}), 400
            
            # ✅ FIX: Validate bypass values - REJECT if higher than current scale readings
            # This prevents sending inflated quantities to SAP that exceed actual production
            if scale1_qty_override is not None and float(scale1_qty_override) > current_scale1_qty:
                return jsonify({
                    "error": f"Invalid bypass value for Scale 1: entered {float(scale1_qty_override):.4f} exceeds current reading {current_scale1_qty:.4f}. Bypass value cannot be higher than the actual scale reading."
                }), 400
            
            if scale2_qty_override is not None and float(scale2_qty_override) > current_scale2_qty:
                return jsonify({
                    "error": f"Invalid bypass value for Scale 2: entered {float(scale2_qty_override):.4f} exceeds current reading {current_scale2_qty:.4f}. Bypass value cannot be higher than the actual scale reading."
                }), 400
            
            if scale3_qty_override is not None and float(scale3_qty_override) > current_scale3_qty:
                return jsonify({
                    "error": f"Invalid bypass value for Scale 3: entered {float(scale3_qty_override):.4f} exceeds current reading {current_scale3_qty:.4f}. Bypass value cannot be higher than the actual scale reading."
                }), 400
            
            # Determine byproduct quantities (use override or current)
            final_scale1_qty = float(scale1_qty_override) if scale1_qty_override is not None else current_scale1_qty
            final_scale2_qty = float(scale2_qty_override) if scale2_qty_override is not None else current_scale2_qty
            final_scale3_qty = float(scale3_qty_override) if scale3_qty_override is not None else current_scale3_qty
            
            # Calculate byproduct overflow (difference between current and confirmed)
            # Now we know final values are always <= current (validated above)
            scale1_overflow = current_scale1_qty - final_scale1_qty if current_scale1_qty > final_scale1_qty else 0
            scale2_overflow = current_scale2_qty - final_scale2_qty if current_scale2_qty > final_scale2_qty else 0
            scale3_overflow = current_scale3_qty - final_scale3_qty if current_scale3_qty > final_scale3_qty else 0
            
            # Store byproduct overflow for next order
            scale1_tag = get_attr_safe(order, "scale1", None)
            scale2_tag = get_attr_safe(order, "scale2", None)
            scale3_tag = get_attr_safe(order, "scale3", None)
            
            overflow_stored = []
            
            if scale1_overflow > 0 and scale1_tag:
                db.execute(text("""
                    INSERT INTO scale_overflows (scale_tag, overflow_qty, last_updated)
                    VALUES (:tag, :qty, NOW())
                    ON CONFLICT (scale_tag) 
                    DO UPDATE SET overflow_qty = scale_overflows.overflow_qty + :qty, last_updated = NOW()
                """), {"tag": scale1_tag, "qty": scale1_overflow})
                overflow_stored.append(f"{scale1_tag}: +{scale1_overflow:.4f}")
                print(f"🌊 [{po_number}] Storing overflow for {scale1_tag}: {scale1_overflow:.4f}")
            
            if scale2_overflow > 0 and scale2_tag:
                db.execute(text("""
                    INSERT INTO scale_overflows (scale_tag, overflow_qty, last_updated)
                    VALUES (:tag, :qty, NOW())
                    ON CONFLICT (scale_tag) 
                    DO UPDATE SET overflow_qty = scale_overflows.overflow_qty + :qty, last_updated = NOW()
                """), {"tag": scale2_tag, "qty": scale2_overflow})
                overflow_stored.append(f"{scale2_tag}: +{scale2_overflow:.4f}")
                print(f"🌊 [{po_number}] Storing overflow for {scale2_tag}: {scale2_overflow:.4f}")
            
            if scale3_overflow > 0 and scale3_tag:
                db.execute(text("""
                    INSERT INTO scale_overflows (scale_tag, overflow_qty, last_updated)
                    VALUES (:tag, :qty, NOW())
                    ON CONFLICT (scale_tag) 
                    DO UPDATE SET overflow_qty = scale_overflows.overflow_qty + :qty, last_updated = NOW()
                """), {"tag": scale3_tag, "qty": scale3_overflow})
                overflow_stored.append(f"{scale3_tag}: +{scale3_overflow:.4f}")
                print(f"🌊 [{po_number}] Storing overflow for {scale3_tag}: {scale3_overflow:.4f}")
            
            if overflow_stored:
                print(f"✅ [{po_number}] Byproduct overflow stored: {', '.join(overflow_stored)}")
            
            # Calculate cumulative total
            last_confirmed_qty = float(get_attr_safe(order, "last_confirmed_qty", 0) or 0)
            new_last_confirmed = last_confirmed_qty + confirm_qty
            
            # Build SAP payload
            order_type = get_attr_safe(order, "order_type", "MILLING")
            target = float(get_attr_safe(order, "expected_weight") or get_attr_safe(order, "quantity") or 0) if order_type == "MILLING" else float(get_attr_safe(order, "quantity") or 0)
            is_final = new_last_confirmed >= target
            
            sap_payload = {
                'po_number': order.order_id,
                'confirmed_weight': confirm_qty,
                'last_confirmed_qty': last_confirmed_qty,
                'total_qty': target,
                'material': order.material,
                'version': order.version or '',
                'material_desc': order.material_desc or '',
                'batch': order.batch or '',
                'uom': 'KG' if order_type == 'MILLING' else 'BAG',
                'plant': order.plant,
                'created_at': order.created_at,
                'shift': shift,
                'validation_method': 'Manual',
                'confirmed_text': confirmed_text or '',  # Leave empty unless user explicitly adds text
                'scrap': scrap,
                'scale1': scale1_tag or '',
                'scale1_qty': final_scale1_qty,
                'scale2': scale2_tag or '',
                'scale2_qty': final_scale2_qty,
                'scale3': scale3_tag or '',
                'scale3_qty': final_scale3_qty,
                'final_confirmation': "X" if is_final else "",
                'is_final_confirmation': is_final,
                'order_status': 'InProgress',
                'process_order_id': order.id
            }
            
            print(f"📤 [{po_number}] SAP Payload: {json.dumps(sap_payload, default=str, indent=2)}")
            
            # Send to SAP
            sap_service = SAPConfirmationService()
            
            if sap_service.mock_mode:
                vpn_status = {"connected": True, "message": "Mock mode - using demo server"}
            else:
                vpn_status = check_vpn_connection()
            
            if not vpn_status.get("connected"):
                # Store in offline confirmations
                from models.offline_confirmation import OfflineConfirmation
                from sqlalchemy import func
                
                # ✅ CRITICAL FIX: Check for existing pending offline confirmation for this order
                # If exists, UPDATE it by accumulating values instead of creating duplicates
                po_num_stripped = str(order.order_id).lstrip('0')
                existing_offline = db.query(OfflineConfirmation).filter(
                    func.ltrim(OfflineConfirmation.order_id, '0') == po_num_stripped,
                    OfflineConfirmation.status == 'pending'
                ).first()
                
                if existing_offline:
                    # ✅ UPDATE existing record - accumulate values
                    old_weight = existing_offline.confirmed_weight or 0
                    accumulated_weight = old_weight + confirm_qty
                    existing_offline.confirmed_weight = accumulated_weight
                    existing_offline.scrap = (existing_offline.scrap or 0) + scrap
                    # Update SAP payload with accumulated values
                    sap_payload['confirmed_weight'] = accumulated_weight
                    existing_offline.sap_payload = sap_payload
                    # ✅ Keep existing confirmed_text - don't overwrite user's manual notes
                    # existing_offline.confirmed_text is preserved as-is
                    print(f"✅ [{po_number}] UPDATED existing offline confirmation: {old_weight:.2f} + {confirm_qty:.2f} = {accumulated_weight:.2f}")
                else:
                    # Create new offline record
                    offline_record = OfflineConfirmation(
                        order_id=order.order_id,
                        process_order_id=order.id,
                        material=order.material,
                        version=order.version,
                        confirmed_weight=confirm_qty,
                        total_qty=target,
                        uom=sap_payload['uom'],
                        plant=order.plant,
                        batch=order.batch or '',
                        shift=shift,
                        scrap=scrap,
                        confirmed_text=sap_payload['confirmed_text'],
                        sap_payload=sap_payload,
                        validation_method='Manual',
                        status='pending'
                    )
                    db.add(offline_record)
                    print(f"✅ [{po_number}] Created NEW offline confirmation: {confirm_qty:.2f}")
                
                # ✅ CRITICAL FIX: Update byproduct scale quantities to the values sent to SAP
                # This preserves the user's modifications in the database
                # Reset accumulated values
                set_attr_safe(order, "last_confirmed_qty", new_last_confirmed)
                set_attr_safe(order, "confirmed_qty", 0)
                set_attr_safe(order, "scale1_qty", final_scale1_qty)  # ✅ Save modified value, not 0
                set_attr_safe(order, "scale2_qty", final_scale2_qty)  # ✅ Save modified value, not 0
                set_attr_safe(order, "scale3_qty", final_scale3_qty)  # ✅ Save modified value, not 0
                
                # ✅ CRITICAL FIX (Jan 23, 2026): For PACKING orders, update confirmed_shift to track SAP confirmations
                # DO NOT reset weight_shift - they represent total production
                # confirmed_shift tracks what was sent to SAP
                # available_to_confirm = weight_shift_sum - confirmed_shift_sum
                if order_type == "PACKING":
                    # ✅ Update confirmed_shift for current shift with the amount being confirmed
                    # This is done separately below in lines 13001-13007, so we don't need to do it here
                    # Just log for debugging
                    print(f"🔄 [{po_number}] PACKING: Keeping weight_shift values, updating confirmed_shift via offline queue")
                    # ✅ CRITICAL: Reset delta cache after manual confirmation
                    # This ensures we track delta from 0 after confirmation resets baseline
                    _last_delta_cache_packing[po_number] = 0.0
                    print(f"🔄 [{po_number}] Reset last_delta cache after manual confirmation")
                
                # ✅ CRITICAL FIX (Jan 23, 2026): For MILLING orders after manual confirmation
                # Set cache to CURRENT weight_shift sum, NOT 0
                # This prevents double-counting: if cache=0 but weight_shift=30, worker would add 30 again
                if order_type == "MILLING":
                    # Get current weight_shift values (these are NOT reset after confirmation)
                    current_weight_a = float(get_attr_safe(order, "weight_shift_a", 0) or 0)
                    current_weight_b = float(get_attr_safe(order, "weight_shift_b", 0) or 0)
                    current_weight_c = float(get_attr_safe(order, "weight_shift_c", 0) or 0)
                    current_total_weight = current_weight_a + current_weight_b + current_weight_c
                    
                    # Reset per-shift cache to current production (prevents double-counting)
                    for shift_code in ["a", "b", "c"]:
                        cache_key = (po_number, shift_code)
                        shift_weight = float(get_attr_safe(order, f"weight_shift_{shift_code}", 0) or 0)
                        _last_shift_production_cache[cache_key] = shift_weight
                        print(f"🔄 [{po_number}] Set shift production cache for shift {shift_code.upper()} to {shift_weight:.2f} kg after manual confirmation")
                    
                    # ✅ CRITICAL: Set total cache to current weight_shift sum
                    # This ensures worker doesn't double-count already confirmed production
                    _last_total_cache_milling[po_number] = current_total_weight
                    print(f"🔄 [{po_number}] Set last_total cache for MILLING order to {current_total_weight:.2f} kg after manual confirmation (prevents double-counting)")
                
                # ✅ FIX: Reset byproduct baselines to current SCADA readings after storing offline confirmation
                # This prevents delta from being added again on next confirmation (fixes doubling bug)
                if scale1_tag:
                    current1 = float(get_scada_reading(scale1_tag) or 0.0)
                    set_attr_safe(order, f"baseline_{scale1_tag.lower()}", current1)
                    print(f"🔄 [{po_number}] Reset baseline for {scale1_tag}: {current1:.4f}")
                
                if scale2_tag:
                    current2 = float(get_scada_reading(scale2_tag) or 0.0)
                    set_attr_safe(order, f"baseline_{scale2_tag.lower()}", current2)
                    print(f"🔄 [{po_number}] Reset baseline for {scale2_tag}: {current2:.4f}")
                
                if scale3_tag:
                    current3 = float(get_scada_reading(scale3_tag) or 0.0)
                    set_attr_safe(order, f"baseline_{scale3_tag.lower()}", current3)
                    print(f"🔄 [{po_number}] Reset baseline for {scale3_tag}: {current3:.4f}")
                
                # ✅ CRITICAL FIX: For PACKING orders, reset shift baseline for main production scale
                # This prevents automatic worker from double-counting manually confirmed production
                if order_type == "PACKING":
                    # Get the main production scale (usually scale1 for PACKING orders)
                    main_scale_tag = scale1_tag  # For PACKING, scale1 is usually the main production scale
                    if main_scale_tag:
                        # Get current shift
                        current_shift = get_attr_safe(order, "current_shift", "A").upper()
                        shift_baseline_field = f"baseline_shift_{current_shift.lower()}_start"
                        
                        # Get current shift baseline dictionary
                        shift_baseline_dict = get_attr_safe(order, shift_baseline_field, {}) or {}
                        if not isinstance(shift_baseline_dict, dict):
                            shift_baseline_dict = {}
                        
                        # Get current SCADA reading for main scale
                        current_main_scale = float(get_scada_reading(main_scale_tag) or 0.0)
                        
                        # Update shift baseline with current SCADA reading
                        shift_baseline_dict[main_scale_tag] = current_main_scale
                        set_attr_safe(order, shift_baseline_field, shift_baseline_dict)
                        print(f"🔄 [{po_number}] Reset shift baseline for {main_scale_tag} in {shift_baseline_field}: {current_main_scale:.4f}")
                        print(f"🔄 [{po_number}] Updated shift baseline dict: {shift_baseline_dict}")
                
                # ✅ CRITICAL FIX (Jan 23, 2026): Update confirmed_shift_X for offline case too
                # This tracks what was queued for SAP confirmation
                if shift == 'A':
                    order.confirmed_shift_a = float(order.confirmed_shift_a or 0) + confirm_qty
                elif shift == 'B':
                    order.confirmed_shift_b = float(order.confirmed_shift_b or 0) + confirm_qty
                elif shift == 'C':
                    order.confirmed_shift_c = float(order.confirmed_shift_c or 0) + confirm_qty
                print(f"📊 [{po_number}] Updated confirmed_shift_{shift.lower()} with {confirm_qty:.2f} (offline)")
                
                db.commit()
                
                print(f"✅ [{po_number}] Updated byproduct quantities in DB: scale1={final_scale1_qty:.4f}, scale2={final_scale2_qty:.4f}, scale3={final_scale3_qty:.4f}")
                
                print(f"✅ [{po_number}] Offline confirmation stored (VPN disconnected)")
                
                return jsonify({
                    "success": True,
                    "offline_mode": True,
                    "message": "VPN disconnected - confirmation stored for offline send",
                    "confirmed_qty": confirm_qty,
                    "last_confirmed_qty": new_last_confirmed,
                    "overflow_stored": overflow_stored
                }), 200
            
            # VPN connected - send to SAP (use offline to include SCRAP and CONFIRMED_TEXT)
            sap_result = sap_service.confirm_offline([sap_payload])
            
            if sap_result.get("ok"):
                # ✅ CRITICAL FIX: Update byproduct scale quantities to the values sent to SAP
                # This preserves the user's modifications in the database
                # SUCCESS: Reset accumulated values
                set_attr_safe(order, "last_confirmed_qty", new_last_confirmed)
                set_attr_safe(order, "confirmed_qty", 0)
                set_attr_safe(order, "scale1_qty", final_scale1_qty)  # ✅ Save modified value, not 0
                set_attr_safe(order, "scale2_qty", final_scale2_qty)  # ✅ Save modified value, not 0
                set_attr_safe(order, "scale3_qty", final_scale3_qty)  # ✅ Save modified value, not 0
                
                # ✅ CRITICAL FIX (Jan 23, 2026): For PACKING orders, DO NOT reset shift weights
                # Keep weight_shift values - they represent total production
                # confirmed_shift is updated below (lines 13001-13007) to track SAP confirmations
                # available_to_confirm = weight_shift_sum - confirmed_shift_sum (stays correct)
                if order_type == "PACKING":
                    print(f"🔄 [{po_number}] PACKING: Keeping weight_shift values for correct available_to_confirm calculation")
                
                # ✅ CRITICAL FIX (Jan 23, 2026): For MILLING orders, update cache to current weight_shift sum
                # This prevents double-counting: if cache=0 but weight_shift=30, worker would add 30 again
                if order_type == "MILLING":
                    current_weight_a = float(get_attr_safe(order, "weight_shift_a", 0) or 0)
                    current_weight_b = float(get_attr_safe(order, "weight_shift_b", 0) or 0)
                    current_weight_c = float(get_attr_safe(order, "weight_shift_c", 0) or 0)
                    current_total_weight = current_weight_a + current_weight_b + current_weight_c
                    
                    # Update per-shift cache to current production
                    for shift_code in ["a", "b", "c"]:
                        cache_key = (po_number, shift_code)
                        shift_weight = float(get_attr_safe(order, f"weight_shift_{shift_code}", 0) or 0)
                        _last_shift_production_cache[cache_key] = shift_weight
                        print(f"🔄 [{po_number}] Set shift production cache for shift {shift_code.upper()} to {shift_weight:.2f} kg after SAP confirmation")
                    
                    # Set total cache to current weight_shift sum
                    _last_total_cache_milling[po_number] = current_total_weight
                    print(f"🔄 [{po_number}] Set last_total cache for MILLING order to {current_total_weight:.2f} kg after SAP confirmation (prevents double-counting)")
                
                # ✅ FIX: Reset byproduct baselines to current SCADA readings after successful confirmation
                # This prevents delta from being added again on next confirmation (fixes doubling bug)
                if scale1_tag:
                    current1 = float(get_scada_reading(scale1_tag) or 0.0)
                    set_attr_safe(order, f"baseline_{scale1_tag.lower()}", current1)
                    print(f"🔄 [{po_number}] Reset baseline for {scale1_tag}: {current1:.4f}")
                
                if scale2_tag:
                    current2 = float(get_scada_reading(scale2_tag) or 0.0)
                    set_attr_safe(order, f"baseline_{scale2_tag.lower()}", current2)
                    print(f"🔄 [{po_number}] Reset baseline for {scale2_tag}: {current2:.4f}")
                
                if scale3_tag:
                    current3 = float(get_scada_reading(scale3_tag) or 0.0)
                    set_attr_safe(order, f"baseline_{scale3_tag.lower()}", current3)
                    print(f"🔄 [{po_number}] Reset baseline for {scale3_tag}: {current3:.4f}")
                
                # ✅ CRITICAL FIX: For PACKING orders, reset shift baseline for main production scale
                # This prevents automatic worker from double-counting manually confirmed production
                if order_type == "PACKING":
                    # Get the main production scale (usually scale1 for PACKING orders)
                    main_scale_tag = scale1_tag  # For PACKING, scale1 is usually the main production scale
                    if main_scale_tag:
                        # Get current shift
                        current_shift = get_attr_safe(order, "current_shift", "A").upper()
                        shift_baseline_field = f"baseline_shift_{current_shift.lower()}_start"
                        
                        # Get current shift baseline dictionary
                        shift_baseline_dict = get_attr_safe(order, shift_baseline_field, {}) or {}
                        if not isinstance(shift_baseline_dict, dict):
                            shift_baseline_dict = {}
                        
                        # Get current SCADA reading for main scale
                        current_main_scale = float(get_scada_reading(main_scale_tag) or 0.0)
                        
                        # Update shift baseline with current SCADA reading
                        shift_baseline_dict[main_scale_tag] = current_main_scale
                        set_attr_safe(order, shift_baseline_field, shift_baseline_dict)
                        print(f"🔄 [{po_number}] Reset shift baseline for {main_scale_tag} in {shift_baseline_field}: {current_main_scale:.4f}")
                        print(f"🔄 [{po_number}] Updated shift baseline dict: {shift_baseline_dict}")
                
                # Update confirmed_shift_X column
                if shift == 'A':
                    order.confirmed_shift_a = float(order.confirmed_shift_a or 0) + confirm_qty
                elif shift == 'B':
                    order.confirmed_shift_b = float(order.confirmed_shift_b or 0) + confirm_qty
                elif shift == 'C':
                    order.confirmed_shift_c = float(order.confirmed_shift_c or 0) + confirm_qty
                
                db.commit()
                
                print(f"✅ [{po_number}] SAP confirmation successful!")
                print(f"✅ [{po_number}] Updated byproduct quantities in DB: scale1={final_scale1_qty:.4f}, scale2={final_scale2_qty:.4f}, scale3={final_scale3_qty:.4f}")
                
                return jsonify({
                    "success": True,
                    "message": "Confirmation sent to SAP successfully",
                    "confirmed_qty": confirm_qty,
                    "last_confirmed_qty": new_last_confirmed,
                    "overflow_stored": overflow_stored,
                    "sap_response": sap_result.get("sap_response", "")
                })
            else:
                # SAP failed - log to error_log
                log_order_error(
                    po_number=str(order.order_id).lstrip("0"),
                    error_type="sap_failed",
                    error_message=sap_result.get("error", "Manual confirmation failed"),
                    payload={
                        "sent_payload": sap_payload,
                        "sap_response": sap_result,
                        "confirmation_type": "manual_progress_dialog",
                        "timestamp": datetime.now().isoformat(),
                        "vpn_connected": True
                    },
                    source="manual_confirm_progress"
                )
                
                return jsonify({
                    "success": False,
                    "error": sap_result.get("error", "SAP confirmation failed"),
                    "message": "Confirmation failed - logged to error_log for reprocess"
                }), 500
    
    except Exception as e:
        print(f"❌ [{po_number}] Error in manual confirmation: {e}")
        import traceback
        traceback.print_exc()
        return jsonify({"error": str(e)}), 500


@orders_bp.route("/auto-validator/start", methods=["POST"])
def start_auto_validator():
    """
    Start validation for next Milling + Packing orders in parallel.

    Behaviour:
    - Resume all existing InProgress orders (if not already validating).
    - If no Milling in progress, find next Pending order whose classification is MILLING.
    - If no Packing in progress, find next Pending order whose classification is PACKING.
    - Initialize them (baselines, shift, status=InProgress) and spawn workers.
    
    ✅ Enhanced with Scale Locking (Dec 13, 2025):
    - Detects conflict groups before starting orders
    - Only starts orders that can run (no scale conflicts)
    - Orders with conflicts are marked as waiting
    
    ✅ OPTIMIZED (Jan 30, 2026): Background startup for instant response
    - Returns immediately after setting master switch
    - All order processing happens in background thread
    - Frontend doesn't wait for all orders to be processed
    """
    global AUTO_VALIDATOR_MASTER
    
    print("=" * 80)
    print("🚀 START AUTO-VALIDATOR ENDPOINT CALLED")
    print("=" * 80)
    
    # Set master switch to True IMMEDIATELY (so UI shows "running")
    AUTO_VALIDATOR_MASTER["isrunning"] = True
    print("⚡ AUTO VALIDATOR MASTER = ON")
    sys.stdout.flush()
    
    # =========================================================================
    # ✅ OPTIMIZATION: Start all order processing in background thread
    # This returns instantly to the frontend while orders start in background
    # =========================================================================
    def background_startup():
        """Background thread that processes all orders."""
        print("🔄 [BACKGROUND] Starting order processing in background thread...")
        _do_auto_validator_startup()
        print("✅ [BACKGROUND] Order processing completed")
    
    startup_thread = threading.Thread(target=background_startup, daemon=True, name="AutoValidator-Startup")
    startup_thread.start()
    
    print("🚀 START AUTO-VALIDATOR ENDPOINT RETURNING IMMEDIATELY (processing in background)")
    print("=" * 80)
    sys.stdout.flush()
    
    # Return immediately - orders will start in background
    return jsonify({
        "success": True,
        "message": "Auto-validator starting... Orders will begin processing shortly.",
        "background": True
    })


def _do_auto_validator_startup():
    """
    Internal function that does the actual order startup work.
    Called from background thread for fast response, or directly for testing.
    
    ✅ All original logic preserved - just moved to separate function.
    """
    with _db_session() as db:
        started_orders: List[str] = []
        waiting_orders: List[str] = []

        # =========================================================
        # STEP 0: Clear stale scale locks and detect conflict groups
        # =========================================================
        from services.scale_lock_service import (
            get_conflict_groups_for_orders,
            lock_scales,
            add_to_queue,
            clear_all_scale_locks,
            set_order_running
        )
        
        # Clear stale locks from previous session
        clear_all_scale_locks()
        print("🧹 Cleared stale scale locks from previous session")
        
        # ✅ CRITICAL FIX (Jan 22, 2026): Clear ALL VALIDATION_STATES on restart
        # This prevents ANY orders from being skipped due to stale "isrunning" state
        # Previously only cleared for Pending orders, but race conditions could leave stale states
        with VALIDATION_LOCK:
            if VALIDATION_STATES:
                stale_count = len(VALIDATION_STATES)
                stale_order_ids = list(VALIDATION_STATES.keys())
                print(f"🧹 Clearing ALL {stale_count} validation states: {stale_order_ids}")
                for po_number in stale_order_ids:
                    order = db.query(ProcessOrder).filter(ProcessOrder.order_id == po_number).first()
                    order_status = order.status if order else "NOT_FOUND"
                    order_type = get_attr_safe(order, "order_type", "UNKNOWN") if order else "UNKNOWN"
                    print(f"   🗑️ Clearing state for {po_number} (status={order_status}, type={order_type})")
                VALIDATION_STATES.clear()  # Clear ALL states unconditionally
                print(f"✅ Cleared ALL {stale_count} validation states for fresh start")
            else:
                print("✅ No stale validation states to clear")
        
        # ✅ CRITICAL FIX (Jan 27, 2026): Reset ALL InProgress orders to Pending
        # This ensures we start from a clean state without orphaned InProgress orders from previous sessions
        stale_inprogress = db.query(ProcessOrder).filter(ProcessOrder.status == "InProgress").all()
        if stale_inprogress:
            print(f"🧹 Resetting {len(stale_inprogress)} stale InProgress orders to Pending...")
            for order in stale_inprogress:
                set_attr_safe(order, "status", "Pending")
                db.add(order)
                print(f"   🔄 {order.order_id}: InProgress → Pending")
            db.commit()
            print(f"✅ Reset {len(stale_inprogress)} stale InProgress orders to Pending")
        else:
            print("✅ No stale InProgress orders to reset")
        
        # ✅ FIX: Clear DM baseline values so they reset on restart
        # This ensures DM starts at 0 when auto-validation restarts
        from sqlalchemy.orm.attributes import flag_modified
        all_orders_to_reset = db.query(ProcessOrder).filter(
            ProcessOrder.status.in_(["InProgress", "Pending"])
        ).all()
        dm_reset_count = 0
        for order in all_orders_to_reset:
            last_scada_values = get_attr_safe(order, "last_scada_values", {}) or {}
            if isinstance(last_scada_values, dict):
                # Remove DM baseline keys to force fresh capture
                keys_to_remove = [k for k in list(last_scada_values.keys()) if k.startswith("dm_")]
                if keys_to_remove:
                    for key in keys_to_remove:
                        del last_scada_values[key]
                    order.last_scada_values = last_scada_values  # Direct assignment
                    flag_modified(order, "last_scada_values")  # Force SQLAlchemy to detect change
                    dm_reset_count += 1
                    print(f"🧹 Cleared DM keys for order {order.order_id}: {keys_to_remove}")
        db.commit()
        print(f"🧹 Cleared DM baseline values for {dm_reset_count} orders")

        # =========================================================
        # STEP 1: Gather ALL orders (InProgress + Pending) for conflict detection
        # =========================================================
        from sqlalchemy import func
        
        inprogress_orders = db.query(ProcessOrder).filter(
            ProcessOrder.status == "InProgress"
        ).order_by(
            func.coalesce(ProcessOrder.hercules_priority, 999).asc(),
            ProcessOrder.id.asc()
        ).all()
        
        pending_orders = db.query(ProcessOrder).filter(
            ProcessOrder.status == "Pending"
        ).order_by(
            func.coalesce(ProcessOrder.hercules_priority, 999).asc(),
            ProcessOrder.id.asc()
        ).all()

        print(f"🔍 Found {len(inprogress_orders)} InProgress orders and {len(pending_orders)} Pending orders")
        
        # Build orders data for conflict detection - include BOTH InProgress AND Pending
        orders_data_for_conflict = []
        order_classifications = {}
        order_objects = {}  # Map order_id to order object
        
        # Add InProgress orders
        for order in inprogress_orders:
            po_number = order.order_id
            classification = classify_order(order)
            if classification.get("error"):
                print(f"❌ Classification error for {po_number}: {classification['error']}")
                continue
            
            order_classifications[po_number] = classification
            order_objects[po_number] = order
            all_scales = get_all_scales_for_order(order, classification, include_byproduct=True)
            
            orders_data_for_conflict.append({
                "order_id": po_number,
                "version": get_attr_safe(order, "version", ""),
                "scales": all_scales,
                "order_type": classification.get("order_type"),
                "priority": get_attr_safe(order, "priority", 999) or 999,
                "status": order.status
            })
        
        # Add Pending orders
        for order in pending_orders:
            po_number = order.order_id
            classification = classify_order(order)
            if classification.get("error"):
                print(f"❌ Classification error for pending {po_number}: {classification['error']}")
                continue
            
            order_classifications[po_number] = classification
            order_objects[po_number] = order
            all_scales = get_all_scales_for_order(order, classification, include_byproduct=True)
            
            orders_data_for_conflict.append({
                "order_id": po_number,
                "version": get_attr_safe(order, "version", ""),
                "scales": all_scales,
                "order_type": classification.get("order_type"),
                "priority": get_attr_safe(order, "hercules_priority", 999) or get_attr_safe(order, "priority", 999) or 999,
                "status": order.status
            })
        
        # Detect conflict groups across ALL orders (InProgress + Pending)
        conflict_info = get_conflict_groups_for_orders(orders_data_for_conflict)
        print(f"🔍 Detected {len(conflict_info['conflict_groups'])} conflict group(s) across ALL orders")
        
        for group in conflict_info["conflict_groups"]:
            print(f"   📊 Group {group['group_id']}: orders={group['orders']}, shared_scales={group['shared_scales']}")
            for oid, prio in group.get("priority_order", {}).items():
                can_run = "CAN RUN" if prio == 1 else "WAITING"
                status = "InProgress" if oid in [o.order_id for o in inprogress_orders] else "Pending"
                print(f"      - {oid} ({status}): group_priority={prio} ({can_run})")

        # =========================================================
        # STEP 2: Process ALL orders - start those that can run
        # =========================================================
        # Combine all orders, sorted by priority
        all_orders = inprogress_orders + pending_orders
        all_orders.sort(key=lambda o: (get_attr_safe(o, "hercules_priority", 999) or get_attr_safe(o, "priority", 999) or 999, o.id))
        
        # ✅ Jan 30, 2026: STRICT PRIORITY ENFORCEMENT (using hercules_priority for queue order)
        # Find the MINIMUM priority among ALL ACTIVE orders (InProgress + Pending)
        min_pending_priority = 999
        for order in all_orders:  # all_orders = inprogress_orders + pending_orders
            p = int(get_attr_safe(order, "hercules_priority", 999) or get_attr_safe(order, "priority", 999) or 999)
            if p < min_pending_priority:
                min_pending_priority = p
        
        print(f"🔍 Processing {len(all_orders)} total orders...")
        print(f"🔒 STRICT PRIORITY: Only priority {min_pending_priority} orders can start (highest priority group)")
        
        # ✅ DEBUG: Count order types
        milling_count = sum(1 for o in all_orders if order_classifications.get(o.order_id, {}).get("order_type") == "MILLING")
        packing_count = sum(1 for o in all_orders if order_classifications.get(o.order_id, {}).get("order_type") == "PACKING")
        print(f"   📊 Order breakdown: {milling_count} MILLING, {packing_count} PACKING")
        sys.stdout.flush()
        
        for order in all_orders:
            po_number = order.order_id
            order_status = order.status
            
            # ✅ DEBUG: Log every order being processed
            order_type_for_log = order_classifications.get(po_number, {}).get("order_type", "UNKNOWN")
            print(f"🔎 Processing order {po_number} ({order_type_for_log}, status={order_status})")
            
            # ✅ ENHANCED DEBUG (Jan 22, 2026): Extra logging for PACKING orders
            if order_type_for_log == "PACKING":
                print(f"   📦 [PACKING DEBUG] Processing PACKING order {po_number}")
            
            # ✅ ENHANCED DEBUG (Jan 28, 2026): Extra logging for MILLING orders
            if order_type_for_log == "MILLING":
                print(f"   🔧 [MILLING DEBUG] Processing MILLING order {po_number}")
            
            # Skip if already validating
            if is_order_validating(po_number):
                print(f"⏭️ {po_number} already validating - SKIPPED")
                if order_type_for_log == "PACKING":
                    print(f"   📦 [PACKING DEBUG] ❌ PACKING order {po_number} SKIPPED - already validating!")
                if order_type_for_log == "MILLING":
                    print(f"   🔧 [MILLING DEBUG] ❌ MILLING order {po_number} SKIPPED - already validating!")
                continue
            
            # Skip if classification failed earlier
            if po_number not in order_classifications:
                print(f"⏭️ {po_number} classification failed earlier - SKIPPED")
                if order_type_for_log == "PACKING":
                    print(f"   📦 [PACKING DEBUG] ❌ PACKING order {po_number} SKIPPED - classification failed!")
                if order_type_for_log == "MILLING":
                    print(f"   🔧 [MILLING DEBUG] ❌ MILLING order {po_number} SKIPPED - classification failed!")
                continue
            
            classification = order_classifications[po_number]
            order_type = classification.get("order_type")
            all_scales = get_all_scales_for_order(order, classification, include_byproduct=True)
            priority = int(get_attr_safe(order, "hercules_priority", 999) or get_attr_safe(order, "priority", 999) or 999)
            version = get_attr_safe(order, "version", "").upper().strip()
            
            # ✅ Jan 30, 2026: SCALE-BASED START (not priority-based)
            # Orders with FREE scales can start regardless of priority
            # Priority only matters within same-scale conflict groups
            # (Removed strict priority enforcement - priority 5 with free scales can start)
            
            # Check conflict info for this order
            order_conflict = conflict_info["order_conflict_info"].get(po_number, {"has_conflict": False})
            
            # If order has conflict and is NOT priority 1 in its group, mark as waiting
            if order_conflict.get("has_conflict") and not order_conflict.get("can_run", True):
                print(f"⏸️ [{po_number}] Has scale conflict (group_priority={order_conflict.get('group_priority', '?')}) - waiting for: {order_conflict.get('waiting_for', [])}")
                if order_type == "PACKING":
                    print(f"   📦 [PACKING DEBUG] ⏸️ PACKING order {po_number} WAITING due to scale conflict!")
                    print(f"   📦 [PACKING DEBUG]    scales={all_scales}, waiting_for={order_conflict.get('waiting_for', [])}")
                if order_type == "MILLING":
                    print(f"   🔧 [MILLING DEBUG] ⏸️ MILLING order {po_number} WAITING due to scale conflict!")
                    print(f"   🔧 [MILLING DEBUG]    scales={all_scales}, waiting_for={order_conflict.get('waiting_for', [])}")
                waiting_orders.append(po_number)
                
                # Register in queue as WAITING
                add_to_queue(po_number, all_scales, priority, version, order_type)
                
                set_order_validation_state(po_number, {
                    "isrunning": False,
                    "waiting": True,
                    "waiting_for_scales": order_conflict.get("shared_scales", []),
                    "blocked_by": order_conflict.get("waiting_for", []),
                    "progress_pct": 0,
                })
                continue
            
            # ✅ This order can run (priority 1 in its conflict group or no conflict)
            print(f"✅ [{po_number}] Order CAN RUN (priority {priority}, type={order_type}) - attempting to lock scales: {all_scales}")
            
            # Try to lock scales
            has_conflict, locked_scales, conflict_details, preempted = lock_scales(
                po_number, all_scales, priority, version, order_type
            )
            print(f"🔐 [{po_number}] lock_scales result: has_conflict={has_conflict}, locked={locked_scales}, conflicts={conflict_details}")
            
            # ✅ Handle preempted orders - signal them to pause (critical for priority enforcement)
            if preempted:
                print(f"⚠️ [{po_number}] Higher priority - preempting orders: {preempted}")
                for preempted_po in preempted:
                    set_order_validation_state(preempted_po, {"isrunning": False})
                    print(f"🛑 [{po_number}] Signaled order {preempted_po} to stop (preempted by higher priority)")
                    preempted_order = db.query(ProcessOrder).filter(ProcessOrder.order_id == preempted_po).first()
                    if preempted_order:
                        set_attr_safe(preempted_order, "status", "Pending")
                        db.add(preempted_order)
                        print(f"📋 [{po_number}] Set preempted order {preempted_po} status to Pending in database")
                db.commit()
            
            # Add to queue
            add_to_queue(po_number, all_scales, priority, version, order_type)
            
            if has_conflict:
                # Unexpected - order should be able to run but scales are locked
                print(f"⚠️ [{po_number}] Unexpected: Could not lock all scales: {conflict_details} - setting to waiting")
                waiting_orders.append(po_number)
                set_order_validation_state(po_number, {
                    "isrunning": False,
                    "waiting": True,
                    "waiting_for_scales": list(conflict_details.keys()),
                    "blocked_by": list(set(conflict_details.values())),
                    "progress_pct": 0,
                })
                continue
            
            print(f"🔒 [{po_number}] Locked scales: {locked_scales}")
            
            # Mark as running in the scale lock queue
            set_order_running(po_number)
            
            # Handle based on current status
            if order.status == "InProgress":
                # Resume existing InProgress order
                # ✅ C31-T27: Update validation_method to Automatic when auto-validation resumes an order
                # This ensures orders resumed by auto-validation are tracked correctly
                set_attr_safe(order, "validation_method", "Automatic")
                db.add(order)
                db.commit()
                print(f"🔧 [{po_number}] Auto-validation resuming - setting validation_method=Automatic")
                
                thread = threading.Thread(
                    target=auto_validation_worker,
                    args=(po_number, classification),
                    daemon=True,
                    name=f"Validation-{po_number}",
                )

                set_order_validation_state(po_number, {
                    "isrunning": True,
                    "thread": thread,
                    "progress_pct": 0,
                })

                thread.start()
                started_orders.append(po_number)
                print(f"🔁 Resumed InProgress: {po_number} ({order_type})")
            else:
                # Start new Pending order - auto-validation start
                print(f"🚀 [{po_number}] Starting Pending {order_type} order (priority={priority})...")
                if order_type == "MILLING":
                    print(f"   🔧 [MILLING DEBUG] Attempting to start MILLING order {po_number}...")
                    print(f"   🔧 [MILLING DEBUG]    scales={all_scales}, version={version}, priority={priority}")
                try:
                    init_and_start_order_worker(db, order, classification, is_manual_start=False)
                    started_orders.append(po_number)
                    print(f"▶️ ✅ Started Pending: {po_number} ({order_type}) - SUCCESS")
                    if order_type == "MILLING":
                        print(f"   🔧 [MILLING DEBUG] ✅ MILLING order {po_number} STARTED SUCCESSFULLY!")
                except Exception as e:
                    print(f"❌ [{po_number}] Failed to start {order_type} order: {e}")
                    if order_type == "MILLING":
                        print(f"   🔧 [MILLING DEBUG] ❌ MILLING order {po_number} FAILED TO START: {e}")
                    import traceback
                    traceback.print_exc()
                    # Release scales if start failed
                    release_scales(po_number, all_scales)
        
        # =========================================================
        # Summary
        # =========================================================
        print(f"📊 Summary: Started {len(started_orders)} orders, {len(waiting_orders)} orders waiting")
        print(f"   ✅ Started: {started_orders}")
        print(f"   ⏸️ Waiting: {waiting_orders}")
        
        # ✅ DEBUG: Check if any PACKING orders were started
        packing_started = [po for po in started_orders if order_classifications.get(po, {}).get("order_type") == "PACKING"]
        milling_started = [po for po in started_orders if order_classifications.get(po, {}).get("order_type") == "MILLING"]
        print(f"   📦 MILLING started: {len(milling_started)} - {milling_started}")
        print(f"   📦 PACKING started: {len(packing_started)} - {packing_started}")
        
        if len(packing_started) == 0 and packing_count > 0:
            print(f"   ⚠️ WARNING: No PACKING orders started despite {packing_count} being available!")
            # ✅ ENHANCED DEBUG (Jan 22, 2026): Show why PACKING orders didn't start
            packing_waiting = [po for po in waiting_orders if order_classifications.get(po, {}).get("order_type") == "PACKING"]
            print(f"   📦 [PACKING DEBUG] PACKING orders waiting: {len(packing_waiting)} - {packing_waiting}")
            for po in packing_waiting:
                conflict_detail = conflict_info["order_conflict_info"].get(po, {})
                print(f"      - {po}: conflict={conflict_detail}")
        else:
            print(f"   ✅ PACKING orders successfully started: {packing_started}")
        
        # ✅ ENHANCED DEBUG (Jan 28, 2026): Show why MILLING orders didn't start
        if len(milling_started) == 0 and milling_count > 0:
            print(f"   ⚠️ WARNING: No MILLING orders started despite {milling_count} being available!")
            milling_waiting = [po for po in waiting_orders if order_classifications.get(po, {}).get("order_type") == "MILLING"]
            print(f"   🔧 [MILLING DEBUG] MILLING orders waiting: {len(milling_waiting)} - {milling_waiting}")
            for po in milling_waiting:
                conflict_detail = conflict_info["order_conflict_info"].get(po, {})
                print(f"      - {po}: conflict={conflict_detail}")
        else:
            print(f"   ✅ MILLING orders successfully started: {milling_started}")

        # =========================================================
        # NOTE: STEP 2 & 3 (old MILLING/PACKING selection) have been replaced
        # by the unified loop above which processes ALL pending orders.
        # =========================================================
        
        # =========================================================
        # RESPONSE
        # =========================================================
        print(f"🔍 Start summary: {len(started_orders)} order(s) started: {started_orders}")
        sys.stdout.flush()
        print("=" * 80)
        print("🚀 START AUTO-VALIDATOR ENDPOINT COMPLETED")
        print("=" * 80)
        sys.stdout.flush()
        
        if started_orders:
            return jsonify({
                "success": True,
                "orders": started_orders,
                "waiting_orders": waiting_orders,
                "count": len(started_orders),
            })
        else:
            return jsonify({
                "success": False,
                "message": "No orders to start (no eligible Pending orders or classification errors)",
            }), 400

# ========== DEPRECATED CODE REMOVED ========== 
# OLD STEP 2 (MILLING) and STEP 3 (PACKING) sections that only started ONE order each
# have been replaced by the unified loop above that starts ALL pending orders.
# The following is kept as reference comment only:
"""
REMOVED: Old code that did:
- next_milling = first pending MILLING order
- next_packing = first pending PACKING order  
- Only start one of each type

NOW: Unified loop processes ALL pending orders:
- Lock scales for each order
- Start if scales available
- Mark as WAITING if scales in conflict
"""
# ========== END DEPRECATED CODE ==========

# [DEPRECATED OLD STEP 2 & STEP 3 CODE REMOVED]
# The old code that only started ONE MILLING + ONE PACKING order has been
# replaced by the unified loop above that starts ALL pending orders.

_DEPRECATED_OLD_STEP_CODE = '''
            # ✅ CRITICAL: Clear production cache for this order on restart
            # This ensures we start tracking from 0 after baseline is captured
            # ✅ CRITICAL: ALWAYS clear cache unconditionally - use pop() to avoid KeyError
            # This ensures we remove any stale cache from deleted orders with the same PO number
            for shift_code in ["a", "b", "c"]:
                cache_key = (po_number, shift_code)
                # Use pop() with default to safely remove cache even if it doesn't exist
                old_prod_cache = _last_shift_production_cache.pop(cache_key, None)
                if old_prod_cache is not None:
                    print(f"🧹 [AutoStart-{po_number}] Cleared production cache for shift {shift_code.upper()} (had value: {old_prod_cache:.2f})")
                # Initialize max weight cache from preserved weight
                weight_field = f"weight_shift_{shift_code}"
                preserved_weight = float(get_attr_safe(order, weight_field, 0.0) or 0.0)
                if preserved_weight > 0.0:
                    # But first, clear any existing cache to ensure clean state
                    old_max_cache = _max_shift_weight_cache.pop(cache_key, None)
                    if old_max_cache is not None and old_max_cache != preserved_weight:
                        print(f"🧹 [AutoStart-{po_number}] Cleared old max weight cache for shift {shift_code.upper()} (had value: {old_max_cache:.2f}, will use preserved: {preserved_weight:.2f})")
                    _max_shift_weight_cache[cache_key] = preserved_weight
                    print(f"🔍 [AutoStart-{po_number}] Initialized max weight cache for shift {shift_code.upper()} to {preserved_weight:.2f}")
                else:
                    # Brand new order - ALWAYS clear max weight cache if it exists (from deleted order)
                    old_max_cache = _max_shift_weight_cache.pop(cache_key, None)
                    if old_max_cache is not None:
                        print(f"🧹 [AutoStart-{po_number}] Cleared max weight cache for shift {shift_code.upper()} (had value: {old_max_cache:.2f} from deleted order)")
            
            # ✅ CRITICAL: Read confirmed_qty IMMEDIATELY after refreshing (before any modifications)
            # Read directly from the order object to ensure we get the actual database value
            preserved_confirmed_qty_milling = float(order.confirmed_qty if hasattr(order, 'confirmed_qty') and order.confirmed_qty is not None else 0.0)
            if preserved_confirmed_qty_milling > 0.0:
                print(f"🔍 [{po_number}] Found existing confirmed_qty in DB: {preserved_confirmed_qty_milling} - will preserve on restart")
                sys.stdout.flush()
            else:
                print(f"🔍 [{po_number}] confirmed_qty is 0 or None in DB - will set to 0 for new order")
                sys.stdout.flush()
            
            # ✅ CRITICAL: Preserve shift weights (DO NOT reset them!)
            preserved_weight_a_milling = float(get_attr_safe(order, "weight_shift_a", 0.0) or 0.0)
            preserved_weight_b_milling = float(get_attr_safe(order, "weight_shift_b", 0.0) or 0.0)
            preserved_weight_c_milling = float(get_attr_safe(order, "weight_shift_c", 0.0) or 0.0)
            if preserved_weight_a_milling > 0.0 or preserved_weight_b_milling > 0.0 or preserved_weight_c_milling > 0.0:
                print(f"🔍 [{po_number}] Found existing shift weights in DB: A={preserved_weight_a_milling:.2f}, B={preserved_weight_b_milling:.2f}, C={preserved_weight_c_milling:.2f} - will preserve on restart")
                sys.stdout.flush()

            print(f"🧮 Preparing MILLING order {po_number}")

            equipment = classification.get("equipment", []) or []
            
            # ✅ CRITICAL: FIRST reset ALL baseline columns to 0 to ensure clean slate
            print(f"🔄 [{po_number}] Resetting all baseline columns to 0 before capturing fresh SCADA values...")
            # PACKING: Bag counter baselines
            set_attr_safe(order, "baseline_sl601_counter", 0.0)
            set_attr_safe(order, "baseline_sl602_counter", 0.0)
            set_attr_safe(order, "baseline_sl603_counter", 0.0)
            set_attr_safe(order, "baseline_sl606_counter", 0.0)
            set_attr_safe(order, "baseline_sl607_counter", 0.0)
            # MILLING: Flour/Bran output baselines
            set_attr_safe(order, "baseline_wg101", 0.0)
            set_attr_safe(order, "baseline_wg201", 0.0)
            set_attr_safe(order, "baseline_wg202", 0.0)
            set_attr_safe(order, "baseline_wg301", 0.0)
            set_attr_safe(order, "baseline_wg302", 0.0)
            set_attr_safe(order, "baseline_wg501", 0.0)
            set_attr_safe(order, "baseline_wg502", 0.0)
            set_attr_safe(order, "baseline_wg503", 0.0)
            # WATER DOSING METER baselines
            set_attr_safe(order, "baseline_dm101", 0.0)
            set_attr_safe(order, "baseline_dm102", 0.0)
            set_attr_safe(order, "baseline_dm201", 0.0)
            set_attr_safe(order, "baseline_dm202", 0.0)
            set_attr_safe(order, "baseline_dm203", 0.0)
            
            # ✅ CRITICAL: Commit baseline reset to database BEFORE capturing fresh SCADA values
            db.add(order)
            db.flush()  # Flush to ensure reset is in database before SCADA capture
            
            # ✅ VERIFY: Refresh order to confirm baselines were reset in database
            db.refresh(order)
            baseline_wg502_check = float(get_attr_safe(order, "baseline_wg502", 0.0) or 0.0)
            baseline_wg501_check = float(get_attr_safe(order, "baseline_wg501", 0.0) or 0.0)
            print(f"✅ [{po_number}] All baseline columns reset to 0 and flushed to database")
            print(f"🔍 [{po_number}] Verification: baseline_wg502={baseline_wg502_check}, baseline_wg501={baseline_wg501_check}")
            
            baselines = capture_baseline_readings(equipment)

            if not baselines:
                print(f"⚠️ No baselines captured for MILLING {po_number}, skipping")
            else:
                # Ensure every equipment tag has at least a default baseline entry
                for tag in equipment:
                    baselines.setdefault(tag, 0.0)

                # ---- Shift detection ----
                plant = get_attr_safe(order, "plant", "3130")
                shift_row = get_current_shift(plant, "MILLING", db)
                current_shift = shift_row.shift_code if shift_row else "A"

                set_attr_safe(order, "current_shift", current_shift)
                set_attr_safe(order, "shift_start_time", datetime.now())
                set_attr_safe(order, "order_type", "MILLING")   # normalize
                set_attr_safe(order, "status", "InProgress")
                set_attr_safe(order, "validation_method", "Automatic")
                # =============================================================================
                # ✅ MAIN PRODUCT OVERFLOW: Apply overflow from previous VALIDATED orders
                # =============================================================================
                # Transfer overflow from DIFFERENT validated orders of same type
                # MILLING overflow → next MILLING order
                overflow_applied = 0.0
                
                # Find overflow from validated orders of the SAME TYPE (but different PO number)
                # ✅ C31-T27: Only transfer overflow from AUTO-validated orders
                completed_with_overflow_list = db.query(ProcessOrder).filter(
                    ProcessOrder.status.in_(["Validated", "Completed"]),
                    ProcessOrder.validation_method == "Automatic",  # ✅ C31-T27: Only auto-validated
                    ProcessOrder.overflow_weight > 0,
                    ProcessOrder.order_type == "MILLING",
                    ProcessOrder.order_id != po_number
                ).order_by(ProcessOrder.id.desc()).all()
                
                completed_with_overflow = None
                for candidate in completed_with_overflow_list:
                    # First match by type is sufficient
                    completed_with_overflow = candidate
                    break
                
                if completed_with_overflow:
                    overflow_weight = float(get_attr_safe(completed_with_overflow, "overflow_weight", 0.0) or 0.0)
                    if overflow_weight > 0:
                        overflow_applied = overflow_weight
                        print(f"✅ [AutoStart-{po_number}] Found main product overflow {overflow_applied:.2f} from {completed_with_overflow.order_id}")
                        
                        # Clear overflow from source order
                        set_attr_safe(completed_with_overflow, "overflow_weight", 0.0)
                        db.add(completed_with_overflow)
                else:
                    print(f"ℹ️ [AutoStart-{po_number}] No main product overflow found from other MILLING orders")
            
                # ✅ CRITICAL: Use the preserved confirmed_qty value we read at the start
                # NEVER reset confirmed_qty if it has a value - only set to 0 for brand new orders
                if preserved_confirmed_qty_milling > 0.0:
                    # Explicitly preserve the existing confirmed_qty for restarted orders
                    set_attr_safe(order, "confirmed_qty", preserved_confirmed_qty_milling)
                    print(f"✅ [{po_number}] PRESERVING confirmed_qty: {preserved_confirmed_qty_milling} (DO NOT RESET)")
                    # Verify it was set correctly
                    verify_qty = float(order.confirmed_qty if hasattr(order, 'confirmed_qty') and order.confirmed_qty is not None else 0.0)
                    if verify_qty != preserved_confirmed_qty_milling:
                        print(f"⚠️ [{po_number}] WARNING: confirmed_qty mismatch! Expected {preserved_confirmed_qty_milling}, got {verify_qty}")
                    else:
                        print(f"✅ [{po_number}] Verified: confirmed_qty correctly set to {verify_qty}")
                    sys.stdout.flush()
                elif overflow_applied > 0.0:
                    # Brand new order with overflow - apply it
                    set_attr_safe(order, "confirmed_qty", overflow_applied)
                    print(f"✅ [AutoStart-{po_number}] Applied main product overflow to confirmed_qty: {overflow_applied:.2f}")
                    sys.stdout.flush()
                else:
                    # Brand new order, set to 0
                    set_attr_safe(order, "confirmed_qty", 0.0)
                    print(f"ℹ️ [{po_number}] Setting confirmed_qty to 0.0 for brand new order")
                    sys.stdout.flush()
                
                # ✅ CRITICAL: Explicitly preserve shift weights (DO NOT reset them!)
                # ✅ ALSO apply overflow to current shift's weight column
                # ✅ CRITICAL FIX: For brand new orders, SET (not ADD) shift weight to overflow
                if overflow_applied > 0.0:
                    # Apply overflow to current shift weight
                    current_shift_for_overflow = (get_attr_safe(order, "current_shift") or "A").upper()
                    shift_weight_field = f"weight_shift_{current_shift_for_overflow.lower()}"
                    
                    # Check if this is a brand new order (no existing production)
                    is_brand_new_for_overflow = (preserved_confirmed_qty_milling == 0.0)
                    
                    if current_shift_for_overflow == "A":
                        existing_weight = preserved_weight_a_milling
                        if is_brand_new_for_overflow:
                            # Brand new order - SET to overflow only
                            set_attr_safe(order, "weight_shift_a", overflow_applied)
                            set_attr_safe(order, "weight_shift_b", 0.0)
                            set_attr_safe(order, "weight_shift_c", 0.0)
                            print(f"✅ [{po_number}] Applied overflow to shift A: SET to {overflow_applied:.2f} (brand new order, ignoring stale {existing_weight:.2f})")
                        else:
                            # Restarted order - ADD overflow to existing
                            new_weight = existing_weight + overflow_applied
                            set_attr_safe(order, "weight_shift_a", new_weight)
                            set_attr_safe(order, "weight_shift_b", preserved_weight_b_milling)
                            set_attr_safe(order, "weight_shift_c", preserved_weight_c_milling)
                            print(f"✅ [{po_number}] Applied overflow to shift A: {existing_weight:.2f} + {overflow_applied:.2f} = {new_weight:.2f} (restarted order)")
                    elif current_shift_for_overflow == "B":
                        existing_weight = preserved_weight_b_milling
                        if is_brand_new_for_overflow:
                            set_attr_safe(order, "weight_shift_a", 0.0)
                            set_attr_safe(order, "weight_shift_b", overflow_applied)
                            set_attr_safe(order, "weight_shift_c", 0.0)
                            print(f"✅ [{po_number}] Applied overflow to shift B: SET to {overflow_applied:.2f} (brand new order, ignoring stale {existing_weight:.2f})")
                        else:
                            new_weight = existing_weight + overflow_applied
                            set_attr_safe(order, "weight_shift_a", preserved_weight_a_milling)
                            set_attr_safe(order, "weight_shift_b", new_weight)
                            set_attr_safe(order, "weight_shift_c", preserved_weight_c_milling)
                            print(f"✅ [{po_number}] Applied overflow to shift B: {existing_weight:.2f} + {overflow_applied:.2f} = {new_weight:.2f} (restarted order)")
                    else:
                        existing_weight = preserved_weight_c_milling
                        if is_brand_new_for_overflow:
                            set_attr_safe(order, "weight_shift_a", 0.0)
                            set_attr_safe(order, "weight_shift_b", 0.0)
                            set_attr_safe(order, "weight_shift_c", overflow_applied)
                            print(f"✅ [{po_number}] Applied overflow to shift C: SET to {overflow_applied:.2f} (brand new order, ignoring stale {existing_weight:.2f})")
                        else:
                            new_weight = existing_weight + overflow_applied
                            set_attr_safe(order, "weight_shift_a", preserved_weight_a_milling)
                            set_attr_safe(order, "weight_shift_b", preserved_weight_b_milling)
                            set_attr_safe(order, "weight_shift_c", new_weight)
                            print(f"✅ [{po_number}] Applied overflow to shift C: {existing_weight:.2f} + {overflow_applied:.2f} = {new_weight:.2f} (restarted order)")
                    sys.stdout.flush()
                else:
                    # No overflow, just preserve existing shift weights
                    set_attr_safe(order, "weight_shift_a", preserved_weight_a_milling)
                    set_attr_safe(order, "weight_shift_b", preserved_weight_b_milling)
                    set_attr_safe(order, "weight_shift_c", preserved_weight_c_milling)
                
                if preserved_weight_a_milling > 0.0 or preserved_weight_b_milling > 0.0 or preserved_weight_c_milling > 0.0:
                    print(f"✅ [{po_number}] PRESERVING shift weights: A={preserved_weight_a_milling:.2f}, B={preserved_weight_b_milling:.2f}, C={preserved_weight_c_milling:.2f} (DO NOT RESET)")
                    sys.stdout.flush()

                # ---- BYPRODUCT baselines + scale1/2/3 assignment ----
                version = (get_attr_safe(order, "version") or "").strip().upper()
                
                # ✅ CRITICAL FIX: Check if byproduct scale TAGS are already set
                # If scale tags are set, byproducts were already captured on FIRST START - preserve them
                existing_scale1 = get_attr_safe(order, "scale1", None)
                existing_scale1_qty = float(get_attr_safe(order, "scale1_qty", 0.0) or 0.0)
                existing_scale2 = get_attr_safe(order, "scale2", None)
                existing_scale2_qty = float(get_attr_safe(order, "scale2_qty", 0.0) or 0.0)
                existing_scale3 = get_attr_safe(order, "scale3", None)
                existing_scale3_qty = float(get_attr_safe(order, "scale3_qty", 0.0) or 0.0)
                
                # ✅ FIX: Only check if byproduct TAGS are set (not quantities or confirmed_qty)
                # If tags are set, byproducts were already captured on first start - ALWAYS preserve
                byproduct_tags_already_set = (
                    (existing_scale1 is not None and existing_scale1 != "") or
                    (existing_scale2 is not None and existing_scale2 != "") or
                    (existing_scale3 is not None and existing_scale3 != "")
                )
                
                if byproduct_tags_already_set:
                    # RESTART/PAUSED scenario: Byproduct scales already configured, preserve them
                    print(f"🔒 [{po_number}] Byproduct scale tags already set - preserving existing values")
                    print(f"   scale1: {existing_scale1} ({existing_scale1_qty:.4f})")
                    print(f"   scale2: {existing_scale2} ({existing_scale2_qty:.4f})")
                    print(f"   scale3: {existing_scale3} ({existing_scale3_qty:.4f})")
                    print(f"   ✅ Byproduct scales will NOT be re-captured (captured on first start)")
                    
                    # ✅ CRITICAL FIX: Reset byproduct baselines to CURRENT SCADA readings on restart
                    # This ensures delta only shows NEW production since restart, not total since order start
                    # Without this fix, baseline was 0 (reset on pause), making delta = current = incorrect!
                    from services.scale_service import get_scada_reading
                    for scale_tag in [existing_scale1, existing_scale2, existing_scale3]:
                        if scale_tag:
                            # Get CURRENT SCADA reading as new baseline (not old value from DB which is 0)
                            current_reading = float(get_scada_reading(scale_tag) or 0.0)
                            baselines[scale_tag] = current_reading
                            set_attr_safe(order, f"baseline_{scale_tag.lower()}", current_reading)
                            print(f"   📌 Reset baseline to CURRENT SCADA: {scale_tag} = {current_reading:.2f}")
                    
                    print(f"   ✅ Byproduct baselines reset to current SCADA readings for accurate delta tracking")
                else:
                    # BRAND NEW order: No byproduct tags set yet - capture fresh baselines from SCADA
                    print(f"🆕 [{po_number}] BRAND NEW order - no byproduct tags set - capturing baselines fresh")
                    print(f"🛠 [AUTO-START] Setting by-product scales for {po_number} / {version}")

                    # 1) Capture ALL baselines (main + byproduct)
                    baselines = _capture_byproduct_baselines(version, baselines, order=order)

                    # 2) Save main + byproduct baselines into baseline_* columns
                    for tag, value in baselines.items():
                        set_attr_safe(order, f"baseline_{tag.lower()}", float(value or 0.0))

                    # 3) Set scale1/2/3 tags and their baseline quantities
                    _set_byproduct_scales(order, version, baselines)
                    print(f"✅ [{po_number}] Byproduct scales captured and set for brand new order")

                # =============================================================================
                # ✅ BYPRODUCT SCALE OVERFLOW: Apply overflow from previous MILLING orders
                # =============================================================================
                # When a previous order's byproduct quantity was manually overridden (reduced),
                # the difference is stored in scale_overflows table. Apply it to this order.
                scale1_tag = get_attr_safe(order, "scale1", None)
                scale2_tag = get_attr_safe(order, "scale2", None)
                scale3_tag = get_attr_safe(order, "scale3", None)
                
                byproduct_overflow_applied = []
                
                for scale_idx, scale_tag in enumerate([scale1_tag, scale2_tag, scale3_tag], 1):
                    if not scale_tag:
                        continue
                        
                    try:
                        # Check for overflow in scale_overflows table
                        result = db.execute(text("""
                            SELECT overflow_qty FROM scale_overflows 
                            WHERE scale_tag = :tag AND overflow_qty > 0
                        """), {"tag": scale_tag}).fetchone()
                        
                        if result and result[0] > 0:
                            overflow_qty = float(result[0])
                            scale_qty_field = f"scale{scale_idx}_qty"
                            current_scale_qty = float(get_attr_safe(order, scale_qty_field, 0.0) or 0.0)
                            new_scale_qty = current_scale_qty + overflow_qty
                            
                            # Apply overflow to the byproduct scale quantity
                            set_attr_safe(order, scale_qty_field, new_scale_qty)
                            
                            # Clear the overflow from the table
                            db.execute(text("""
                                UPDATE scale_overflows SET overflow_qty = 0, last_updated = NOW()
                                WHERE scale_tag = :tag
                            """), {"tag": scale_tag})
                            
                            byproduct_overflow_applied.append(f"{scale_tag}: +{overflow_qty:.4f}")
                            print(f"🌊 [AutoStart-{po_number}] Applied MILLING byproduct overflow for {scale_tag}: {current_scale_qty:.4f} + {overflow_qty:.4f} = {new_scale_qty:.4f}")
                            
                    except Exception as e:
                        print(f"⚠️ [AutoStart-{po_number}] Error applying byproduct overflow for {scale_tag}: {e}")
                
                if byproduct_overflow_applied:
                    print(f"✅ [AutoStart-{po_number}] MILLING byproduct overflow applied: {', '.join(byproduct_overflow_applied)}")
                else:
                    print(f"ℹ️ [AutoStart-{po_number}] No MILLING byproduct overflow to apply")

                # ✅ CRITICAL: Always capture fresh shift baselines on restart
                # This allows us to track NEW production after restart
                # Shift WEIGHTS are preserved (not reset), so we accumulate: old_weight + new_production
                set_attr_safe(
                    order,
                    f"baseline_shift_{current_shift.lower()}_start",
                    baselines,
                )
                # ✅ Store baseline capture time for tracking
                set_attr_safe(order, f"baseline_shift_{current_shift.lower()}_time", datetime.now())
                print(f"✅ [{po_number}] Set fresh shift baselines for shift {current_shift} (shift weight preserved for accumulation)")

                db.add(order)
                db.commit()
                
                # ✅ CRITICAL: Verify preserved confirmed_qty and shift weights were committed correctly
                db.refresh(order)
                final_confirmed_qty = float(order.confirmed_qty if hasattr(order, 'confirmed_qty') and order.confirmed_qty is not None else 0.0)
                final_weight_a = float(get_attr_safe(order, "weight_shift_a", 0.0) or 0.0)
                final_weight_b = float(get_attr_safe(order, "weight_shift_b", 0.0) or 0.0)
                final_weight_c = float(get_attr_safe(order, "weight_shift_c", 0.0) or 0.0)
                
                if preserved_confirmed_qty_milling > 0.0:
                    if final_confirmed_qty != preserved_confirmed_qty_milling:
                        print(f"❌ [{po_number}] ERROR: confirmed_qty not preserved after commit! Expected {preserved_confirmed_qty_milling:.2f}, got {final_confirmed_qty:.2f}")
                        # Force set it again
                        set_attr_safe(order, "confirmed_qty", preserved_confirmed_qty_milling)
                        db.add(order)
                        db.commit()
                        print(f"✅ [{po_number}] Fixed: confirmed_qty set to {preserved_confirmed_qty_milling:.2f}")
                    else:
                        print(f"✅ [{po_number}] Verified: confirmed_qty={final_confirmed_qty:.2f} correctly committed to database")
                
                # Verify shift weights were preserved
                if preserved_weight_a_milling > 0.0 or preserved_weight_b_milling > 0.0 or preserved_weight_c_milling > 0.0:
                    if final_weight_a != preserved_weight_a_milling or final_weight_b != preserved_weight_b_milling or final_weight_c != preserved_weight_c_milling:
                        print(f"❌ [{po_number}] ERROR: Shift weights not preserved after commit!")
                        print(f"   Expected: A={preserved_weight_a_milling:.2f}, B={preserved_weight_b_milling:.2f}, C={preserved_weight_c_milling:.2f}")
                        print(f"   Got: A={final_weight_a:.2f}, B={final_weight_b:.2f}, C={final_weight_c:.2f}")
                        # Force set them again
                        set_attr_safe(order, "weight_shift_a", preserved_weight_a_milling)
                        set_attr_safe(order, "weight_shift_b", preserved_weight_b_milling)
                        set_attr_safe(order, "weight_shift_c", preserved_weight_c_milling)
                        db.add(order)
                        db.commit()
                        print(f"✅ [{po_number}] Fixed: Shift weights restored")
                    else:
                        print(f"✅ [{po_number}] Verified: Shift weights preserved correctly: A={final_weight_a:.2f}, B={final_weight_b:.2f}, C={final_weight_c:.2f}")

                # tiny delay so worker session can see committed data
                time.sleep(0.2)

                print(
                    f"✅ Initialized MILLING {po_number} "
                    f"(scale1={order.scale1}, scale2={order.scale2}, scale3={order.scale3}) "
                    f"— starting thread..."
                )

                thread = threading.Thread(
                    target=auto_validation_worker,
                    args=(po_number, classification),
                    daemon=True,
                    name=f"Validation-{po_number}",
                )

                set_order_validation_state(po_number, {
                    "isrunning": True,
                    "thread": thread,
                    "progress_pct": 0,
                })

                thread.start()
                started_orders.append(po_number)
                print(f"▶️ Started MILLING: {po_number}")

        # =========================================================
        # STEP 3: Start PACKING Pending Order (with pallet scale1)
        # =========================================================
        print(f"🔍 Checking PACKING start conditions: has_packing={has_packing}, next_packing={next_packing is not None}, next_packing_class={next_packing_class is not None}")
        sys.stdout.flush()
        if not has_packing and next_packing and next_packing_class:
            order = next_packing
            classification = next_packing_class
            po_number = order.order_id

            # ✅ CRITICAL: Refresh order from database to get latest values
            db.refresh(order)
            
            # ✅ CRITICAL: Clear production cache for this order on restart
            # This ensures we start tracking from 0 after baseline is captured
            # ✅ CRITICAL: ALWAYS clear cache unconditionally - use pop() to avoid KeyError
            # This ensures we remove any stale cache from deleted orders with the same PO number
            for shift_code in ["a", "b", "c"]:
                cache_key = (po_number, shift_code)
                # Use pop() with default to safely remove cache even if it doesn't exist
                old_prod_cache = _last_shift_production_cache.pop(cache_key, None)
                if old_prod_cache is not None:
                    print(f"🧹 [AutoStart-{po_number}] Cleared production cache for shift {shift_code.upper()} (had value: {old_prod_cache:.2f})")
                # Initialize max weight cache from preserved weight
                weight_field = f"weight_shift_{shift_code}"
                preserved_weight = float(get_attr_safe(order, weight_field, 0.0) or 0.0)
                if preserved_weight > 0.0:
                    # But first, clear any existing cache to ensure clean state
                    old_max_cache = _max_shift_weight_cache.pop(cache_key, None)
                    if old_max_cache is not None and old_max_cache != preserved_weight:
                        print(f"🧹 [AutoStart-{po_number}] Cleared old max weight cache for shift {shift_code.upper()} (had value: {old_max_cache:.2f}, will use preserved: {preserved_weight:.2f})")
                    _max_shift_weight_cache[cache_key] = preserved_weight
                    print(f"🔍 [AutoStart-{po_number}] Initialized max weight cache for shift {shift_code.upper()} to {preserved_weight:.2f}")
                else:
                    # Brand new order - ALWAYS clear max weight cache if it exists (from deleted order)
                    old_max_cache = _max_shift_weight_cache.pop(cache_key, None)
                    if old_max_cache is not None:
                        print(f"🧹 [AutoStart-{po_number}] Cleared max weight cache for shift {shift_code.upper()} (had value: {old_max_cache:.2f} from deleted order)")
            
            # ✅ CRITICAL: Read confirmed_qty IMMEDIATELY after refreshing (before any modifications)
            # Read directly from the order object to ensure we get the actual database value
            preserved_confirmed_qty_packing = float(order.confirmed_qty if hasattr(order, 'confirmed_qty') and order.confirmed_qty is not None else 0.0)
            if preserved_confirmed_qty_packing > 0.0:
                print(f"🔍 [{po_number}] Found existing confirmed_qty in DB: {preserved_confirmed_qty_packing} - will preserve on restart")
                sys.stdout.flush()
            else:
                print(f"🔍 [{po_number}] confirmed_qty is 0 or None in DB - will set to 0 for new order")
                sys.stdout.flush()
            
            # ✅ CRITICAL: Preserve shift weights (DO NOT reset them!)
            preserved_weight_a_packing = float(get_attr_safe(order, "weight_shift_a", 0.0) or 0.0)
            preserved_weight_b_packing = float(get_attr_safe(order, "weight_shift_b", 0.0) or 0.0)
            preserved_weight_c_packing = float(get_attr_safe(order, "weight_shift_c", 0.0) or 0.0)
            if preserved_weight_a_packing > 0.0 or preserved_weight_b_packing > 0.0 or preserved_weight_c_packing > 0.0:
                print(f"🔍 [{po_number}] Found existing shift weights in DB: A={preserved_weight_a_packing:.2f}, B={preserved_weight_b_packing:.2f}, C={preserved_weight_c_packing:.2f} - will preserve on restart")
                sys.stdout.flush()

            print(f"🧮 Preparing PACKING order {po_number}")

            equipment = classification.get("equipment", []) or []
            
            # ✅ CRITICAL: FIRST reset ALL baseline columns to 0 to ensure clean slate
            print(f"🔄 [{po_number}] Resetting all baseline columns to 0 before capturing fresh SCADA values...")
            # PACKING: Bag counter baselines
            set_attr_safe(order, "baseline_sl601_counter", 0.0)
            set_attr_safe(order, "baseline_sl602_counter", 0.0)
            set_attr_safe(order, "baseline_sl603_counter", 0.0)
            set_attr_safe(order, "baseline_sl606_counter", 0.0)
            set_attr_safe(order, "baseline_sl607_counter", 0.0)
            # MILLING: Flour/Bran output baselines
            set_attr_safe(order, "baseline_wg101", 0.0)
            set_attr_safe(order, "baseline_wg201", 0.0)
            set_attr_safe(order, "baseline_wg202", 0.0)
            set_attr_safe(order, "baseline_wg301", 0.0)
            set_attr_safe(order, "baseline_wg302", 0.0)
            set_attr_safe(order, "baseline_wg501", 0.0)
            set_attr_safe(order, "baseline_wg502", 0.0)
            set_attr_safe(order, "baseline_wg503", 0.0)
            # WATER DOSING METER baselines
            set_attr_safe(order, "baseline_dm101", 0.0)
            set_attr_safe(order, "baseline_dm102", 0.0)
            set_attr_safe(order, "baseline_dm201", 0.0)
            set_attr_safe(order, "baseline_dm202", 0.0)
            set_attr_safe(order, "baseline_dm203", 0.0)
            
            # ✅ CRITICAL: Commit baseline reset to database BEFORE capturing fresh SCADA values
            db.add(order)
            db.flush()  # Flush to ensure reset is in database before SCADA capture
            
            # ✅ VERIFY: Refresh order to confirm baselines were reset in database
            db.refresh(order)
            baseline_sl601_check = float(get_attr_safe(order, "baseline_sl601_counter", 0.0) or 0.0)
            print(f"✅ [{po_number}] All baseline columns reset to 0 and flushed to database")
            print(f"🔍 [{po_number}] Verification: baseline_sl601_counter={baseline_sl601_check}")
            
            baselines = capture_baseline_readings(equipment)

            if not baselines:
                print(f"⚠️ No baselines captured for PACKING {po_number}, skipping")
            else:
                # ---- Shift detection ----
                plant = get_attr_safe(order, "plant", "3130")
                shift_row = get_current_shift(plant, "PACKING", db)
                current_shift = shift_row.shift_code if shift_row else "A"

                set_attr_safe(order, "current_shift", current_shift)
                set_attr_safe(order, "shift_start_time", datetime.now())
                set_attr_safe(order, "order_type", "PACKING")   # normalize
                set_attr_safe(order, "status", "InProgress")
                set_attr_safe(order, "validation_method", "Automatic")
                # =============================================================================
                # ✅ MAIN PRODUCT OVERFLOW: Apply overflow from previous VALIDATED orders
                # =============================================================================
                # Transfer overflow from DIFFERENT validated orders of same type
                # PACKING overflow → next PACKING order
                overflow_applied = 0.0
                
                # Find overflow from validated orders of the SAME TYPE (but different PO number)
                # ✅ C31-T27: Only transfer overflow from AUTO-validated orders
                completed_with_overflow_list = db.query(ProcessOrder).filter(
                    ProcessOrder.status.in_(["Validated", "Completed"]),
                    ProcessOrder.validation_method == "Automatic",  # ✅ C31-T27: Only auto-validated
                    ProcessOrder.overflow_weight > 0,
                    ProcessOrder.order_type == "PACKING",
                    ProcessOrder.order_id != po_number
                ).order_by(ProcessOrder.id.desc()).all()
                
                completed_with_overflow = None
                for candidate in completed_with_overflow_list:
                    # First match by type is sufficient
                    completed_with_overflow = candidate
                    break
                
                if completed_with_overflow:
                    overflow_weight = float(get_attr_safe(completed_with_overflow, "overflow_weight", 0.0) or 0.0)
                    if overflow_weight > 0:
                        overflow_applied = overflow_weight
                        print(f"✅ [AutoStart-{po_number}] Found main product overflow {overflow_applied:.2f} from {completed_with_overflow.order_id}")
                        
                        # Clear overflow from source order
                        set_attr_safe(completed_with_overflow, "overflow_weight", 0.0)
                        db.add(completed_with_overflow)
                else:
                    print(f"ℹ️ [AutoStart-{po_number}] No main product overflow found from other PACKING orders")
            
                # ✅ CRITICAL: Use the preserved confirmed_qty value we read at the start
                # NEVER reset confirmed_qty if it has a value - only set to 0 for brand new orders
                if preserved_confirmed_qty_packing > 0.0:
                    # Explicitly preserve the existing confirmed_qty for restarted orders
                    set_attr_safe(order, "confirmed_qty", preserved_confirmed_qty_packing)
                    print(f"✅ [{po_number}] PRESERVING confirmed_qty: {preserved_confirmed_qty_packing} (DO NOT RESET)")
                    # Verify it was set correctly
                    verify_qty = float(order.confirmed_qty if hasattr(order, 'confirmed_qty') and order.confirmed_qty is not None else 0.0)
                    if verify_qty != preserved_confirmed_qty_packing:
                        print(f"⚠️ [{po_number}] WARNING: confirmed_qty mismatch! Expected {preserved_confirmed_qty_packing}, got {verify_qty}")
                    else:
                        print(f"✅ [{po_number}] Verified: confirmed_qty correctly set to {verify_qty}")
                    sys.stdout.flush()
                elif overflow_applied > 0.0:
                    # Brand new order with overflow - apply it
                    set_attr_safe(order, "confirmed_qty", overflow_applied)
                    print(f"✅ [AutoStart-{po_number}] Applied main product overflow to confirmed_qty: {overflow_applied:.2f}")
                    sys.stdout.flush()
                else:
                    # Brand new order, set to 0
                    set_attr_safe(order, "confirmed_qty", 0.0)
                    print(f"ℹ️ [{po_number}] Setting confirmed_qty to 0.0 for brand new order")
                    sys.stdout.flush()
                
                # ✅ CRITICAL: Explicitly preserve shift weights (DO NOT reset them!)
                # ✅ ALSO apply overflow to current shift's weight column
                # ✅ CRITICAL FIX: For brand new orders, SET (not ADD) shift weight to overflow
                if overflow_applied > 0.0:
                    # Apply overflow to current shift weight
                    current_shift_for_overflow = (get_attr_safe(order, "current_shift") or "A").upper()
                    shift_weight_field = f"weight_shift_{current_shift_for_overflow.lower()}"
                    
                    # Check if this is a brand new order (no existing production)
                    is_brand_new_for_overflow = (preserved_confirmed_qty_packing == 0.0)
                    
                    if current_shift_for_overflow == "A":
                        existing_weight = preserved_weight_a_packing
                        if is_brand_new_for_overflow:
                            # Brand new order - SET to overflow only
                            set_attr_safe(order, "weight_shift_a", overflow_applied)
                            set_attr_safe(order, "weight_shift_b", 0.0)
                            set_attr_safe(order, "weight_shift_c", 0.0)
                            print(f"✅ [{po_number}] Applied overflow to shift A: SET to {overflow_applied:.2f} (brand new order, ignoring stale {existing_weight:.2f})")
                        else:
                            # Restarted order - ADD overflow to existing
                            new_weight = existing_weight + overflow_applied
                            set_attr_safe(order, "weight_shift_a", new_weight)
                            set_attr_safe(order, "weight_shift_b", preserved_weight_b_packing)
                            set_attr_safe(order, "weight_shift_c", preserved_weight_c_packing)
                            print(f"✅ [{po_number}] Applied overflow to shift A: {existing_weight:.2f} + {overflow_applied:.2f} = {new_weight:.2f} (restarted order)")
                    elif current_shift_for_overflow == "B":
                        existing_weight = preserved_weight_b_packing
                        if is_brand_new_for_overflow:
                            set_attr_safe(order, "weight_shift_a", 0.0)
                            set_attr_safe(order, "weight_shift_b", overflow_applied)
                            set_attr_safe(order, "weight_shift_c", 0.0)
                            print(f"✅ [{po_number}] Applied overflow to shift B: SET to {overflow_applied:.2f} (brand new order, ignoring stale {existing_weight:.2f})")
                        else:
                            new_weight = existing_weight + overflow_applied
                            set_attr_safe(order, "weight_shift_a", preserved_weight_a_packing)
                            set_attr_safe(order, "weight_shift_b", new_weight)
                            set_attr_safe(order, "weight_shift_c", preserved_weight_c_packing)
                            print(f"✅ [{po_number}] Applied overflow to shift B: {existing_weight:.2f} + {overflow_applied:.2f} = {new_weight:.2f} (restarted order)")
                    else:
                        existing_weight = preserved_weight_c_packing
                        if is_brand_new_for_overflow:
                            set_attr_safe(order, "weight_shift_a", 0.0)
                            set_attr_safe(order, "weight_shift_b", 0.0)
                            set_attr_safe(order, "weight_shift_c", overflow_applied)
                            print(f"✅ [{po_number}] Applied overflow to shift C: SET to {overflow_applied:.2f} (brand new order, ignoring stale {existing_weight:.2f})")
                        else:
                            new_weight = existing_weight + overflow_applied
                            set_attr_safe(order, "weight_shift_a", preserved_weight_a_packing)
                            set_attr_safe(order, "weight_shift_b", preserved_weight_b_packing)
                            set_attr_safe(order, "weight_shift_c", new_weight)
                            print(f"✅ [{po_number}] Applied overflow to shift C: {existing_weight:.2f} + {overflow_applied:.2f} = {new_weight:.2f} (restarted order)")
                    sys.stdout.flush()
                else:
                    # No overflow, just preserve existing shift weights
                    set_attr_safe(order, "weight_shift_a", preserved_weight_a_packing)
                    set_attr_safe(order, "weight_shift_b", preserved_weight_b_packing)
                    set_attr_safe(order, "weight_shift_c", preserved_weight_c_packing)
                
                if preserved_weight_a_packing > 0.0 or preserved_weight_b_packing > 0.0 or preserved_weight_c_packing > 0.0:
                    print(f"✅ [{po_number}] PRESERVING shift weights: A={preserved_weight_a_packing:.2f}, B={preserved_weight_b_packing:.2f}, C={preserved_weight_c_packing:.2f} (DO NOT RESET)")
                    sys.stdout.flush()

                # 1) Save baselines into baseline_* columns
                for tag, value in baselines.items():
                    set_attr_safe(order, f"baseline_{tag.lower()}", float(value or 0.0))

                # 2) Set scale1 = palletizer tag, qty = its baseline
                pallet_equipment = equipment
                if pallet_equipment:
                    tag = pallet_equipment[0]
                    set_attr_safe(order, "scale1", tag)
                    set_attr_safe(
                        order,
                        "scale1_qty",
                        float(baselines.get(tag, 0.0) or 0.0),
                    )
                else:
                    set_attr_safe(order, "scale1", None)
                    set_attr_safe(order, "scale1_qty", 0.0)

                # Clear extra scales for packing
                set_attr_safe(order, "scale2", None)
                set_attr_safe(order, "scale2_qty", 0.0)
                set_attr_safe(order, "scale3", None)
                set_attr_safe(order, "scale3_qty", 0.0)

                # =============================================================================
                # ✅ BYPRODUCT SCALE OVERFLOW: Apply overflow from previous PACKING orders
                # =============================================================================
                # When a previous order's byproduct quantity was manually overridden (reduced),
                # the difference is stored in scale_overflows table. Apply it to this order.
                scale1_tag = get_attr_safe(order, "scale1", None)
                scale2_tag = get_attr_safe(order, "scale2", None)
                scale3_tag = get_attr_safe(order, "scale3", None)
                
                byproduct_overflow_applied = []
                
                for scale_idx, scale_tag in enumerate([scale1_tag, scale2_tag, scale3_tag], 1):
                    if not scale_tag:
                        continue
                        
                    try:
                        # Check for overflow in scale_overflows table
                        result = db.execute(text("""
                            SELECT overflow_qty FROM scale_overflows 
                            WHERE scale_tag = :tag AND overflow_qty > 0
                        """), {"tag": scale_tag}).fetchone()
                        
                        if result and result[0] > 0:
                            overflow_qty = float(result[0])
                            scale_qty_field = f"scale{scale_idx}_qty"
                            current_scale_qty = float(get_attr_safe(order, scale_qty_field, 0.0) or 0.0)
                            new_scale_qty = current_scale_qty + overflow_qty
                            
                            # Apply overflow to the byproduct scale quantity
                            set_attr_safe(order, scale_qty_field, new_scale_qty)
                            
                            # Clear the overflow from the table
                            db.execute(text("""
                                UPDATE scale_overflows SET overflow_qty = 0, last_updated = NOW()
                                WHERE scale_tag = :tag
                            """), {"tag": scale_tag})
                            
                            byproduct_overflow_applied.append(f"{scale_tag}: +{overflow_qty:.4f}")
                            print(f"🌊 [AutoStart-{po_number}] Applied PACKING byproduct overflow for {scale_tag}: {current_scale_qty:.4f} + {overflow_qty:.4f} = {new_scale_qty:.4f}")
                            
                    except Exception as e:
                        print(f"⚠️ [AutoStart-{po_number}] Error applying byproduct overflow for {scale_tag}: {e}")
                
                if byproduct_overflow_applied:
                    print(f"✅ [AutoStart-{po_number}] PACKING byproduct overflow applied: {', '.join(byproduct_overflow_applied)}")
                else:
                    print(f"ℹ️ [AutoStart-{po_number}] No PACKING byproduct overflow to apply")

                # ✅ CRITICAL: Always capture fresh shift baselines on restart
                # This allows us to track NEW production after restart
                # Shift WEIGHTS are preserved (not reset), so we accumulate: old_weight + new_production
                # ✅ FIX: Create shift baseline dict with ALL pallet equipment tags (not just first one)
                shift_baseline_dict = {}
                if pallet_equipment:
                    for tag in pallet_equipment:
                        shift_baseline_dict[tag] = float(baselines.get(tag, 0.0) or 0.0)
                
                set_attr_safe(
                    order,
                    f"baseline_shift_{current_shift.lower()}_start",
                    shift_baseline_dict,
                )
                # ✅ Store baseline capture time for tracking
                set_attr_safe(order, f"baseline_shift_{current_shift.lower()}_time", datetime.now())
                print(f"✅ [{po_number}] Set fresh PACKING shift baselines for shift {current_shift}: {shift_baseline_dict} (shift weight preserved for accumulation)")

                db.add(order)
                db.commit()
                
                # ✅ CRITICAL: Verify preserved confirmed_qty and shift weights were committed correctly
                db.refresh(order)
                final_confirmed_qty = float(order.confirmed_qty if hasattr(order, 'confirmed_qty') and order.confirmed_qty is not None else 0.0)
                final_weight_a = float(get_attr_safe(order, "weight_shift_a", 0.0) or 0.0)
                final_weight_b = float(get_attr_safe(order, "weight_shift_b", 0.0) or 0.0)
                final_weight_c = float(get_attr_safe(order, "weight_shift_c", 0.0) or 0.0)
                
                if preserved_confirmed_qty_packing > 0.0:
                    if final_confirmed_qty != preserved_confirmed_qty_packing:
                        print(f"❌ [{po_number}] ERROR: confirmed_qty not preserved after commit! Expected {preserved_confirmed_qty_packing:.2f}, got {final_confirmed_qty:.2f}")
                        # Force set it again
                        set_attr_safe(order, "confirmed_qty", preserved_confirmed_qty_packing)
                        db.add(order)
                        db.commit()
                        print(f"✅ [{po_number}] Fixed: confirmed_qty set to {preserved_confirmed_qty_packing:.2f}")
                    else:
                        print(f"✅ [{po_number}] Verified: confirmed_qty={final_confirmed_qty:.2f} correctly committed to database")
                
                # Verify shift weights were preserved
                if preserved_weight_a_packing > 0.0 or preserved_weight_b_packing > 0.0 or preserved_weight_c_packing > 0.0:
                    if final_weight_a != preserved_weight_a_packing or final_weight_b != preserved_weight_b_packing or final_weight_c != preserved_weight_c_packing:
                        print(f"❌ [{po_number}] ERROR: Shift weights not preserved after commit!")
                        print(f"   Expected: A={preserved_weight_a_packing:.2f}, B={preserved_weight_b_packing:.2f}, C={preserved_weight_c_packing:.2f}")
                        print(f"   Got: A={final_weight_a:.2f}, B={final_weight_b:.2f}, C={final_weight_c:.2f}")
                        # Force set them again
                        set_attr_safe(order, "weight_shift_a", preserved_weight_a_packing)
                        set_attr_safe(order, "weight_shift_b", preserved_weight_b_packing)
                        set_attr_safe(order, "weight_shift_c", preserved_weight_c_packing)
                        db.add(order)
                        db.commit()
                        print(f"✅ [{po_number}] Fixed: Shift weights restored")
                    else:
                        print(f"✅ [{po_number}] Verified: Shift weights preserved correctly: A={final_weight_a:.2f}, B={final_weight_b:.2f}, C={final_weight_c:.2f}")

                time.sleep(0.2)

                print(
                    f"✅ Initialized PACKING {po_number} "
                    f"(scale1={order.scale1}, scale1_qty={order.scale1_qty}) "
                    f"— starting thread..."
                )

                thread = threading.Thread(
                    target=auto_validation_worker,
                    args=(po_number, classification),
                    daemon=True,
                    name=f"Validation-{po_number}",
                )

                set_order_validation_state(po_number, {
                    "isrunning": True,
                    "thread": thread,
                    "progress_pct": 0,
                })

                thread.start()
                started_orders.append(po_number)
                print(f"▶️ Started PACKING: {po_number}")

        # =========================================================
        # RESPONSE
        # =========================================================
        print(f"🔍 Start summary: {len(started_orders)} order(s) started: {started_orders}")
        sys.stdout.flush()
        print("=" * 80)
        print("🚀 START AUTO-VALIDATOR ENDPOINT COMPLETED")
        print("=" * 80)
        sys.stdout.flush()
        
        if started_orders:
            return jsonify({
                "success": True,
                "orders": started_orders,
                "count": len(started_orders),
            })
        else:
            return jsonify({
                "success": False,
                "message": "No orders to start (no eligible Pending orders or classification errors)",
            }), 400

'''  # End of _DEPRECATED_OLD_STEP_CODE string - closing the triple-quoted string

@orders_bp.route("/auto-validator/status", methods=["GET"])
def get_auto_validator_status():
    """Get status of all validating orders and master switch status"""
    
    # Get master switch status (read-only, don't modify it)
    is_running = AUTO_VALIDATOR_MASTER.get("isrunning", False)
    
    with VALIDATION_LOCK:
        validating_orders = [
            {
                "po_number": po,
                "progress_pct": state.get("progress_pct", 0),
                "status": state.get("status", "unknown"),
                "current_production": state.get("current_production", 0),
                "target": state.get("target", 0),
                "unit": state.get("unit", "")
            }
            for po, state in VALIDATION_STATES.items()
            if state.get("isrunning")
        ]
    
    return jsonify({
        "is_running": is_running,
        "validating_orders": validating_orders,
        "count": len(validating_orders),
        "message": f"{len(validating_orders)} order(s) validating" if is_running else "Auto-validator is stopped"
    })

@orders_bp.route("/auto-validator/stop", methods=["POST"])
def stop_auto_validator():
    """
    Stop the global auto-validator master switch and signal all active order validations to stop.
    This will prevent new orders from starting and stop all currently running validations.
    
    Also updates database:
    - Sets order status to "Pending" for all InProgress orders
    - Resets baseline_fixed_flags to allow fresh baselines on next start
    - Preserves confirmed_qty (does NOT reset it)
    """
    global AUTO_VALIDATOR_MASTER

    print("=" * 80)
    print("🛑 STOP AUTO-VALIDATOR ENDPOINT CALLED")
    print("=" * 80)
    sys.stdout.flush()
    print("🛑 Stopping auto-validator master switch...")
    sys.stdout.flush()

    # Set master switch to False
    AUTO_VALIDATOR_MASTER["isrunning"] = False
    print("⚡ AUTO VALIDATOR MASTER = OFF")
    sys.stdout.flush()

    stopped_orders: list[str] = []
    db_updated_count = 0

    # ✅ CRITICAL FIX: Stop workers FIRST before database update
    # This prevents race condition where workers see stale data
    print("🔍 STEP 1: Stopping validation workers FIRST...")
    sys.stdout.flush()
    with VALIDATION_LOCK:
        active_orders = list(VALIDATION_STATES.keys())
        print(f"🔍 Found {len(active_orders)} active orders in VALIDATION_STATES")
        sys.stdout.flush()
        for po_number in active_orders:
            if po_number in VALIDATION_STATES:
                VALIDATION_STATES[po_number]["isrunning"] = False  # Signal worker to stop
                stopped_orders.append(po_number)
                print(f"🛑 Signaled stop for order: {po_number}")
            sys.stdout.flush()
    
    # ✅ Wait for workers to finish their current cycle (1.5 seconds max)
    import time
    print("⏳ Waiting 1.5 seconds for workers to finish current cycle...")
    sys.stdout.flush()
    time.sleep(1.5)
    
    # ✅ Now clear all validation states completely
    with VALIDATION_LOCK:
        for po_number in stopped_orders:
            if po_number in VALIDATION_STATES:
                del VALIDATION_STATES[po_number]
                print(f"🗑️ Cleared validation state for: {po_number}")
    print(f"✅ Workers stopped: {len(stopped_orders)} worker(s)")
    sys.stdout.flush()

    # STEP 2: Now update database (workers are stopped)
    print("🔍 STEP 2: Updating database...")
    sys.stdout.flush()
    print("🔍 Starting database update process...")
    sys.stdout.flush()
    print(f"🔍 Database engine: {postgres_engine}")
    print(f"🔍 Database URL: {postgres_engine.url if hasattr(postgres_engine, 'url') else 'N/A'}")
    print(f"🔍 Checking ProcessOrder model availability: {ProcessOrder is not None}")
    print(f"🔍 ProcessOrder model: {ProcessOrder}")
    sys.stdout.flush()

    sql_updated_count = 0

    # SQL used for baseline reset (shared by primary + fallback)
    reset_baselines_sql_str = """
        UPDATE process_orders
        SET
            -- MILLING: Flour/Bran output baselines
            baseline_wg101 = 0,
            baseline_wg201 = 0,
            baseline_wg202 = 0,
            baseline_wg301 = 0,
            baseline_wg302 = 0,
            baseline_wg501 = 0,
            baseline_wg502 = 0,
            baseline_wg503 = 0,
            
            -- WATER DOSING METER baselines
            baseline_dm101 = 0,
            baseline_dm102 = 0,
            baseline_dm201 = 0,
            baseline_dm202 = 0,
            baseline_dm203 = 0,

            -- PACKING: Bag counter baselines
            baseline_sl601_counter = 0,
            baseline_sl602_counter = 0,
            baseline_sl603_counter = 0,
            baseline_sl606_counter = 0,
            baseline_sl607_counter = 0
        WHERE status = 'Pending';
    """

    try:
        from sqlalchemy import text
        print("🔍 Using PostgresSessionLocal for SQL execution...")
        sys.stdout.flush()

        db_session = PostgresSessionLocal()
        print("✅ Database session created")
        sys.stdout.flush()
        try:
            # ✅ CRITICAL FIX: Capture byproduct deltas for all InProgress MILLING orders BEFORE resetting baselines
            print("🔧🔧🔧 [BYPRODUCT-FIX] Capturing byproduct deltas before auto-validator stop...")
            sys.stdout.flush()
            
            from services.scale_service import get_scada_reading
            inprogress_milling_orders = db_session.query(ProcessOrder).filter(
                ProcessOrder.status == "InProgress",
                ProcessOrder.order_type == "MILLING"
            ).all()
            
            for order in inprogress_milling_orders:
                po_number = order.order_id
                scale1_tag = get_attr_safe(order, "scale1", None)
                scale2_tag = get_attr_safe(order, "scale2", None)
                scale3_tag = get_attr_safe(order, "scale3", None)
                
                if scale1_tag or scale2_tag or scale3_tag:
                    print(f"📦 [AutoStop-{po_number}] Capturing byproduct deltas...")
                    
                    # Capture and accumulate byproduct deltas
                    if scale1_tag:
                        stored1 = float(get_attr_safe(order, "scale1_qty", 0.0) or 0.0)
                        baseline1 = float(get_attr_safe(order, f"baseline_{scale1_tag.lower()}", 0.0) or 0.0)
                        current1 = float(get_scada_reading(scale1_tag) or 0.0)
                        delta1 = max(0.0, current1 - baseline1) if baseline1 > 0 else 0.0
                        accumulated1 = stored1 + delta1
                        set_attr_safe(order, "scale1_qty", accumulated1)
                        print(f"   scale1 ({scale1_tag}): stored={stored1:.4f} + delta={delta1:.4f} = {accumulated1:.4f}")
                        
                    if scale2_tag:
                        stored2 = float(get_attr_safe(order, "scale2_qty", 0.0) or 0.0)
                        baseline2 = float(get_attr_safe(order, f"baseline_{scale2_tag.lower()}", 0.0) or 0.0)
                        current2 = float(get_scada_reading(scale2_tag) or 0.0)
                        delta2 = max(0.0, current2 - baseline2) if baseline2 > 0 else 0.0
                        accumulated2 = stored2 + delta2
                        set_attr_safe(order, "scale2_qty", accumulated2)
                        print(f"   scale2 ({scale2_tag}): stored={stored2:.4f} + delta={delta2:.4f} = {accumulated2:.4f}")
                        
                    if scale3_tag:
                        stored3 = float(get_attr_safe(order, "scale3_qty", 0.0) or 0.0)
                        baseline3 = float(get_attr_safe(order, f"baseline_{scale3_tag.lower()}", 0.0) or 0.0)
                        current3 = float(get_scada_reading(scale3_tag) or 0.0)
                        delta3 = max(0.0, current3 - baseline3) if baseline3 > 0 else 0.0
                        accumulated3 = stored3 + delta3
                        set_attr_safe(order, "scale3_qty", accumulated3)
                        print(f"   scale3 ({scale3_tag}): stored={stored3:.4f} + delta={delta3:.4f} = {accumulated3:.4f}")
                    
                    db_session.add(order)
            
            # Commit byproduct quantities before the bulk baseline reset
            if inprogress_milling_orders:
                db_session.commit()
                print(f"✅ [BYPRODUCT-FIX] Byproduct deltas captured and committed for {len(inprogress_milling_orders)} MILLING orders")
            sys.stdout.flush()
            
            # 1️⃣ Check how many InProgress orders exist
            print("🔍 Checking InProgress orders count...")
            sys.stdout.flush()
            check_result = db_session.execute(
                text("SELECT COUNT(*) FROM process_orders WHERE status = 'InProgress'")
            )
            inprogress_count = check_result.scalar()
            print(f"🔍 Found {inprogress_count} InProgress order(s) in PostgreSQL process_orders table")
            sys.stdout.flush()

            # 2️⃣ Update all InProgress → Pending
            if inprogress_count > 0:
                print("🔄 Executing UPDATE (InProgress → Pending)...")
                sys.stdout.flush()

                update_sql = text("""
                    UPDATE process_orders 
                    SET status = 'Pending', 
                        baseline_fixed_flags = '{}'::jsonb,
                        updated_at = NOW(),
                        -- Reset ALL baseline values to 0
                        baseline_wg101 = 0,
                        baseline_wg201 = 0,
                        baseline_wg202 = 0,
                        baseline_wg301 = 0,
                        baseline_wg302 = 0,
                        baseline_wg501 = 0,
                        baseline_wg502 = 0,
                        baseline_wg503 = 0,
                        baseline_dm101 = 0,
                        baseline_dm102 = 0,
                        baseline_dm201 = 0,
                        baseline_dm202 = 0,
                        baseline_dm203 = 0,
                        baseline_sl601_counter = 0,
                        baseline_sl602_counter = 0,
                        baseline_sl603_counter = 0,
                        baseline_sl606_counter = 0,
                        baseline_sl607_counter = 0,
                        -- Reset shift baseline JSON fields (CRITICAL - these are used for production calculation)
                        baseline_shift_a_start = NULL,
                        baseline_shift_b_start = NULL,
                        baseline_shift_c_start = NULL
                    WHERE status = 'InProgress'
                """)
                print(f"🔍 SQL: {update_sql}")
                sys.stdout.flush()

                update_result = db_session.execute(update_sql)
                try:
                    sql_updated_count = update_result.rowcount
                    print(f"🔍 Rowcount from result: {sql_updated_count}")
                except Exception as rowcount_error:
                    print(f"⚠️ Could not get rowcount: {rowcount_error}, using inprogress_count")
                    sql_updated_count = inprogress_count

                print(f"🔍 About to commit {sql_updated_count} order(s)...")
                sys.stdout.flush()
                db_session.commit()
                print("✅ Commit completed (InProgress → Pending)")
                sys.stdout.flush()
            else:
                print("ℹ️ No InProgress orders found in database to update")

            # 3️⃣ NOW reset baselines for all Pending orders (including just updated)
            print("🔄 Resetting baselines for all Pending orders...")
            reset_baselines_sql = text(reset_baselines_sql_str)
            db_session.execute(reset_baselines_sql)
            db_session.commit()
            print("✅ BASELINES RESET after STOP")
            sys.stdout.flush()

            # 4️⃣ Verify there are no InProgress orders left
            verify_result = db_session.execute(
                text("SELECT COUNT(*) FROM process_orders WHERE status = 'InProgress'")
            )
            remaining_inprogress = verify_result.scalar()
            print(f"✅ Verification: {remaining_inprogress} InProgress order(s) remaining (should be 0)")
            sys.stdout.flush()

        except Exception as session_error:
            db_session.rollback()
            print(f"❌ Session error, rolling back: {session_error}")
            raise session_error
        finally:
            db_session.close()
            print("🔍 Database session closed")

    except Exception as sql_error:
        # PRIMARY SQL FAILED → use fallback raw connection
        print(f"❌ Direct SQL UPDATE failed: {sql_error}")
        import traceback
        print("=" * 80)
        print("SQL UPDATE ERROR TRACEBACK:")
        traceback.print_exc()
        print("=" * 80)
        sql_updated_count = 0

        print("🔄 FALLBACK: Trying raw connection approach...")
        sys.stdout.flush()
        try:
            conn = postgres_engine.raw_connection()
            try:
                cursor = conn.cursor()
                # 1️⃣ InProgress → Pending + Reset baselines
                cursor.execute("""
                    UPDATE process_orders 
                    SET status = 'Pending', 
                        baseline_fixed_flags = '{}'::jsonb,
                        updated_at = NOW(),
                        -- Reset ALL baseline values to 0
                        baseline_wg101 = 0,
                        baseline_wg201 = 0,
                        baseline_wg202 = 0,
                        baseline_wg301 = 0,
                        baseline_wg302 = 0,
                        baseline_wg501 = 0,
                        baseline_wg502 = 0,
                        baseline_wg503 = 0,
                        baseline_dm101 = 0,
                        baseline_dm102 = 0,
                        baseline_dm201 = 0,
                        baseline_dm202 = 0,
                        baseline_dm203 = 0,
                        baseline_sl601_counter = 0,
                        baseline_sl602_counter = 0,
                        baseline_sl603_counter = 0,
                        baseline_sl606_counter = 0,
                        baseline_sl607_counter = 0,
                        -- Reset shift baseline JSON fields (CRITICAL - these are used for production calculation)
                        baseline_shift_a_start = NULL,
                        baseline_shift_b_start = NULL,
                        baseline_shift_c_start = NULL
                    WHERE status = 'InProgress'
                """)
                sql_updated_count = cursor.rowcount
                conn.commit()
                print(f"✅ FALLBACK UPDATE successful: {sql_updated_count} order(s) updated using raw connection")
                sys.stdout.flush()

                # 2️⃣ Reset baselines for all Pending
                print("🔄 FALLBACK: Resetting baselines for all Pending orders...")
                cursor.execute(reset_baselines_sql_str)
                conn.commit()
                print("✅ FALLBACK: BASELINES RESET after STOP")
                sys.stdout.flush()

                cursor.close()
            finally:
                conn.close()
        except Exception as fallback_error:
            print(f"❌ FALLBACK also failed: {fallback_error}")
            import traceback
            traceback.print_exc()
            sql_updated_count = 0

    # Set db_updated_count from SQL result
    db_updated_count = sql_updated_count
    print(f"🔍 Database update completed. Updated {db_updated_count} order(s).")
    sys.stdout.flush()

    # ORM fallback: keep as-is (only status + baseline_fixed_flags)
    try:
        if ProcessOrder is not None:
            print("✅ ProcessOrder model is available, proceeding with ORM database update")
            print("🔍 Opening database session...")
            with _db_session() as db:
                try:
                    test_count = db.query(ProcessOrder).count()
                    print(f"🔍 Database connection test: Found {test_count} total orders in PostgreSQL")
                except Exception as test_error:
                    print(f"❌ Database connection test failed: {test_error}")
                    raise test_error

                print("🔍 Querying InProgress orders from database...")
                inprogress_orders = db.query(ProcessOrder).filter(
                    ProcessOrder.status == "InProgress"
                ).all()

                if len(inprogress_orders) == 0:
                    print("⚠️ No orders found with exact 'InProgress' status, checking case variations...")
                    all_orders = db.query(ProcessOrder).all()
                    inprogress_variants = [
                        o for o in all_orders if o.status and "progress" in o.status.lower()
                    ]
                    print(f"🔍 Found {len(inprogress_variants)} order(s) with 'progress' in status: {[o.status for o in inprogress_variants[:5]]}")
                    if inprogress_variants:
                        inprogress_orders = inprogress_variants

                print(f"🔍 Found {len(inprogress_orders)} InProgress order(s) in database to update")

                if len(inprogress_orders) == 0 and stopped_orders:
                    print("⚠️ No InProgress orders found by status, trying to update by order_id from stopped workers...")
                    for po_number in stopped_orders:
                        order = db.query(ProcessOrder).filter(
                            ProcessOrder.order_id == po_number
                        ).first()
                        # ✅ CRITICAL: Only update InProgress orders, NOT Validated orders
                        # Validated orders are already completed and should not be changed to Pending
                        if order and order.status == "InProgress":
                            inprogress_orders.append(order)
                            print(f"🔍 Found order {po_number} with status '{order.status}' to update")
                        elif order and order.status in ("Validated", "Completed"):
                            print(f"⏭️ Skipping {order.status} order {po_number} - already completed, not changing to Pending")

                if len(inprogress_orders) == 0:
                    print("⚠️ No orders to update - all orders may already be Pending or no InProgress orders exist")
                else:
                    for order in inprogress_orders:
                        old_status = order.status
                        order_id = order.order_id
                        
                        # ✅ CRITICAL: Skip Validated orders - they are already completed
                        # Only update InProgress orders to Pending
                        if old_status in ("Validated", "Completed"):
                            print(f"⏭️ Skipping {old_status} order {order_id} - already completed, not changing to Pending")
                            continue

                        order.status = "Pending"

                        # Reset baseline_fixed_flags
                        if order.baseline_fixed_flags:
                            baseline_fixed_flags = order.baseline_fixed_flags.copy() if isinstance(order.baseline_fixed_flags, dict) else {}
                            for key in list(baseline_fixed_flags.keys()):
                                baseline_fixed_flags[key] = False
                            order.baseline_fixed_flags = baseline_fixed_flags
                        else:
                            order.baseline_fixed_flags = {}

                        # ✅ CRITICAL: Reset ALL baseline values to 0
                        # PACKING: Bag counter baselines
                        order.baseline_sl601_counter = 0.0
                        order.baseline_sl602_counter = 0.0
                        order.baseline_sl603_counter = 0.0
                        order.baseline_sl606_counter = 0.0
                        order.baseline_sl607_counter = 0.0
                        
                        # MILLING: Flour/Bran output baselines
                        order.baseline_wg101 = 0.0
                        order.baseline_wg201 = 0.0
                        order.baseline_wg202 = 0.0
                        order.baseline_wg301 = 0.0
                        order.baseline_wg302 = 0.0
                        order.baseline_wg501 = 0.0
                        order.baseline_wg502 = 0.0
                        order.baseline_wg503 = 0.0
                        
                        # WATER DOSING METER baselines
                        order.baseline_dm101 = 0.0
                        order.baseline_dm102 = 0.0
                        order.baseline_dm201 = 0.0
                        order.baseline_dm202 = 0.0
                        order.baseline_dm203 = 0.0
                        
                        # ✅ CRITICAL: Reset shift baseline JSON fields (these are used for production calculation)
                        order.baseline_shift_a_start = None
                        order.baseline_shift_b_start = None
                        order.baseline_shift_c_start = None

                        order.updated_at = datetime.now()
                        db.add(order)
                        db_updated_count += 1
                        print(f"🛑 DB updating: Order {order_id} (ID: {order.id}) status '{old_status}' → 'Pending', baseline flags, baseline values, and shift baselines reset")

                if db_updated_count > 0:
                    try:
                        db.flush()
                        print(f"✅ Database flush successful: {db_updated_count} order(s) flushed")
                    except Exception as flush_error:
                        print(f"❌ Database flush failed: {flush_error}")
                        import traceback
                        traceback.print_exc()
                        db.rollback()
                        raise flush_error

                    try:
                        db.commit()
                        print(f"✅ Database commit successful: {db_updated_count} order(s) committed to Pending status")
                        order_ids_list = [o.order_id for o in inprogress_orders]
                        if order_ids_list:
                            verify_orders = db.query(ProcessOrder).filter(
                                ProcessOrder.status == "Pending",
                                ProcessOrder.order_id.in_(order_ids_list)
                            ).count()
                            print(f"✅ Verification: {verify_orders} of {db_updated_count} order(s) confirmed as Pending in database")
                        else:
                            print("⚠️ No order IDs to verify")
                    except Exception as commit_error:
                        print(f"❌ Database commit failed: {commit_error}")
                        import traceback
                        traceback.print_exc()
                        db.rollback()
                        raise commit_error
                else:
                    print(f"⚠️ ORM update found 0 orders to update (SQL already updated {db_updated_count} orders)")
        else:
            print("❌ ProcessOrder model not available - ORM update skipped")
            print(f"ℹ️ SQL update already attempted: {db_updated_count} order(s) updated")
    except Exception as e:
        print(f"❌ CRITICAL ERROR updating database during stop: {e}")
        import traceback
        print("=" * 80)
        print("FULL TRACEBACK:")
        traceback.print_exc()
        print("=" * 80)
        return jsonify({
            "success": True,
            "message": f"Auto-validator stopped (workers stopped, but DB update had errors: {str(e)})",
            "stopped_orders": stopped_orders,
            "stopped_count": len(stopped_orders),
            "db_updated_count": db_updated_count,
            "warning": f"Database update failed: {str(e)}"
        })

    print(f"🔍 Database update process completed. Updated {db_updated_count} order(s)")
    print(f"✅ Auto-validator stopped completely. Stopped {len(stopped_orders)} worker(s), updated {db_updated_count} order(s) in DB")
    print("=" * 80)
    print("🛑 STOP AUTO-VALIDATOR ENDPOINT COMPLETED")
    print("=" * 80)

    response_data = {
        "success": True,
        "message": f"Auto-validator stopped successfully. Updated {db_updated_count} order(s) to Pending.",
        "stopped_orders": stopped_orders,
        "stopped_count": len(stopped_orders),
        "db_updated_count": db_updated_count
    }

    print(f"🔍 Returning response: {response_data}")
    return jsonify(response_data)


@orders_bp.route("/priority", methods=["GET", "POST"])
@optional_auth
def priority_endpoint():
    if ProcessOrder is None:
        return jsonify({"error": "ProcessOrder model not available"}), 500
    if request.method == "GET":
        try:
            with _db_session() as db:
                orders = db.query(ProcessOrder).all()
                priorities = {order.id: get_attr_safe(order, "hercules_priority", 0) or get_attr_safe(order, "priority", 0) for order in orders}
            return jsonify(priorities)
        except Exception as e:
            print(f"❌ Error fetching priorities: {e}")
            return jsonify({"error": str(e)}), 500
    else:
        try:
            data = request.get_json()
            print(f"📥 [PRIORITY] Received priority update request: {data}")
            
            if not data or not isinstance(data, dict):
                return jsonify({"error": "Invalid request body. Expected JSON mapping of order IDs to priorities."}), 400
            
            # ✅ CRITICAL: Also update the scale lock queue with new priorities
            from services.scale_lock_service import (
                ORDER_QUEUE, _scale_lock, get_scale_owner, release_scales
            )
            
            priority_changes = []  # (po_number, old_priority, new_priority) for activity log
            with _db_session() as db:
                updated_count = 0
                queue_updated_count = 0
                errors = []
                for order_id_str, priority in data.items():
                    try:
                        order_id = int(order_id_str)
                        priority = int(priority)
                        order = db.query(ProcessOrder).filter(ProcessOrder.id == order_id).first()
                        if order:
                            old_priority = get_attr_safe(order, "hercules_priority", 0) or get_attr_safe(order, "priority", 0)
                            set_attr_safe(order, "hercules_priority", priority)
                            updated_count += 1
                            po_number = order.order_id or str(order_id)
                            priority_changes.append((po_number, old_priority, priority))
                            print(f"   📝 Order {order.order_id} (id={order_id}): priority {old_priority} → {priority}")
                            
                            # ✅ Also update priority in scale lock queue if order is queued
                            with _scale_lock:
                                if po_number in ORDER_QUEUE:
                                    ORDER_QUEUE[po_number]["priority"] = priority
                                    queue_updated_count += 1
                        else:
                            errors.append(f"Order ID {order_id} not found")
                            print(f"   ⚠️ Order ID {order_id} not found in database")
                    except Exception as e:
                        errors.append(f"Invalid input for {order_id_str}: {e}")
                        print(f"   ❌ Error processing {order_id_str}: {e}")
                db.commit()
                
            print(f"✅ [PRIORITY] Update complete: {updated_count} in DB, {queue_updated_count} in queue")
            # Admin activity log (drag-to-top): same message as toast – Order PO X moved to top
            if updated_count > 0:
                try:
                    operator = (getattr(request, 'current_user', None) or {}).get('username', 'Unknown')
                    moved_po = next((po for po, old, new in priority_changes if new == 1), None)
                    details_str = f"Order PO {moved_po} moved to top" if moved_po else "; ".join(f"PO {po}: {old} → {new}" for po, old, new in priority_changes)
                    system_logger.log_event(
                        source='Operator',
                        action='Order dragged to top',
                        status='Success',
                        operator=operator,
                        details=details_str,
                        metadata={'updated_count': updated_count, 'priority_map': data, 'changes': [{"po": po, "old": old, "new": new} for po, old, new in priority_changes]}
                    )
                except Exception as log_err:
                    print(f"⚠️ Failed to log priority change to activity: {log_err}")
            # ✅ Unlock scales for new top order: release scales from lower-priority holders so hercules_priority=1 can lock
            moved_po = next((po for po, old, new in priority_changes if new == 1), None) if priority_changes else None
            if moved_po and updated_count > 0:
                try:
                    with _db_session() as db2:
                        order = db2.query(ProcessOrder).filter(ProcessOrder.order_id == moved_po).first()
                        if order:
                            classification = classify_order(order)
                            if not classification.get("error"):
                                all_scales = get_all_scales_for_order(order, classification, include_byproduct=True)
                                for scale in (all_scales or []):
                                    scale_upper = (scale or "").upper().strip()
                                    if not scale_upper:
                                        continue
                                    owner = get_scale_owner(scale_upper)
                                    if owner and owner != moved_po:
                                        with _scale_lock:
                                            owner_priority = (ORDER_QUEUE.get(owner) or {}).get("priority")
                                        if owner_priority is not None and owner_priority > 1:
                                            released = release_scales(owner, [scale_upper])
                                            if released:
                                                print(f"🔓 [PRIORITY] Released {released} from {owner} (priority {owner_priority}) so {moved_po} (priority 1) can lock")
                except Exception as unlock_err:
                    print(f"⚠️ [PRIORITY] Scale rebalance after drag failed: {unlock_err}")
            return jsonify({"success": True, "updated_count": updated_count, "queue_updated": queue_updated_count, "errors": errors if errors else None, "message": f"Updated priorities for {updated_count} order(s)"})
        except Exception as e:
            print(f"❌ Error updating priorities: {e}")
            import traceback
            traceback.print_exc()
            return jsonify({"error": f"Failed to update priorities: {str(e)}"}), 500

@orders_bp.route("/error-log", methods=["POST", "OPTIONS"])
def log_order_validation_error():
    """
    Simple error logging endpoint for order validation page.
    No validation logic - just logs errors for monitoring.
    
    Expected JSON payload:
    {
        "po_number": "000012002907",
        "error_message": "Error description",
        "error_type": "validation_error|api_error|scada_error|sap_error",
        "error_details": {...},  # Optional additional details
        "user": "username",  # Optional
        "page": "order_validation"  # Optional
    }
    """
    if request.method == "OPTIONS":
        return jsonify({"ok": True}), 200
    
    try:
        from services.system_logger import SystemLogger
        from models.user_roles import SystemLog
        from datetime import datetime, timezone
        import json as json_lib
        
        data = request.get_json() or {}
        
        # Extract error information
        po_number = data.get("po_number", "UNKNOWN")
        error_message = data.get("error_message", "Unknown error")
        error_type = data.get("error_type", "unknown_error")
        error_details = data.get("error_details", {})
        user = data.get("user", "unknown")
        page = data.get("page", "order_validation")
        
        # Prepare metadata
        metadata = {
            "po_number": po_number,
            "error_type": error_type,
            "page": page,
            "user": user,
            "error_details": error_details,
            "timestamp": datetime.now(timezone.utc).isoformat()
        }
        
        # Log using SystemLog model directly (more control)
        with _db_session() as db:
            error_log = SystemLog(
                timestamp=datetime.now(timezone.utc),
                source="order_validation_page",
                action=f"error_{error_type}",
                status="error",
                details=json_lib.dumps({
                    "error_message": error_message,
                    "po_number": po_number,
                    "error_type": error_type,
                    "error_details": error_details
                }),
                operator=user,
                error_code=error_type.upper(),
                log_metadata=json_lib.dumps(metadata),
                shift=None,  # Will be auto-set by SystemLogger if needed
                level="ERROR",
                message=error_message,
                category="order_validation"
            )
            db.add(error_log)
            db.commit()
            log_id = error_log.id
        
        return jsonify({
            "success": True,
            "message": "Error logged successfully",
            "log_id": log_id,
            "timestamp": datetime.now(timezone.utc).isoformat()
        }), 200
        
    except Exception as e:
        # Even if logging fails, return success to not break the frontend
        print(f"⚠️ Failed to log error: {e}")
        import traceback
        traceback.print_exc()
        return jsonify({
            "success": False,
            "message": f"Failed to log error: {str(e)}"
        }), 500

# =============================================================================
# SCALE LOCK STATUS ENDPOINTS (Feature 2: Scale Locking)
# =============================================================================

@orders_bp.route("/scale-lock-status", methods=["GET"])
def get_scale_lock_status_api():
    """
    Get comprehensive scale lock status for all orders.
    
    Returns:
    - Active scale locks (which scales are locked by which orders)
    - Queue status (running and waiting orders)
    - Version conflicts (multiple orders with same version)
    - Scale conflicts (multiple orders needing same scales)
    
    This endpoint supports the UI for:
    - Showing lock status indicators
    - Displaying waiting queue
    - Highlighting scale conflicts
    """
    try:
        status = get_scale_usage_status()
        
        return jsonify({
            "success": True,
            "timestamp": datetime.now().isoformat(),
            "data": status
        })
    except Exception as e:
        print(f"❌ Error getting scale lock status: {e}")
        import traceback
        traceback.print_exc()
        return jsonify({
            "success": False,
            "error": str(e)
        }), 500


@orders_bp.route("/<string:po_number>/scale-lock-status", methods=["GET"])
def get_order_scale_lock_status(po_number: str):
    """
    Get scale lock status for a specific order.
    
    Returns:
    - Which scales this order has locked
    - Which scales this order is waiting for
    - Which orders are blocking this order
    - Queue position and priority
    """
    try:
        status = get_lock_status_for_order(po_number)
        
        return jsonify({
            "success": True,
            "timestamp": datetime.now().isoformat(),
            "data": status
        })
    except Exception as e:
        print(f"❌ Error getting scale lock status for {po_number}: {e}")
        import traceback
        traceback.print_exc()
        return jsonify({
            "success": False,
            "error": str(e)
        }), 500


@orders_bp.route("/<string:po_number>/check-conflicts", methods=["GET"])
def check_order_conflicts(po_number: str):
    """
    Check for potential conflicts before starting an order.
    
    Returns:
    - can_start: Whether this order can start immediately
    - scale_conflicts: Scales blocked by other orders
    - version_conflicts: Orders with same version that are blocking
    - waiting_orders: Orders that will wait if this order starts
    """
    if ProcessOrder is None:
        return jsonify({"success": False, "error": "ProcessOrder model not available"}), 500
    
    try:
        with _db_session() as db:
            order = db.query(ProcessOrder).filter(ProcessOrder.order_id == po_number).first()
            if not order:
                return jsonify({"success": False, "error": f"Order {po_number} not found"}), 404
            
            # Classify order to get equipment list
            classification = classify_order(order)
            if classification.get("error"):
                return jsonify({
                    "success": False,
                    "error": classification["error"]
                }), 400
            
            equipment = classification.get("equipment", [])
            version = get_attr_safe(order, "version", "")
            order_type = classification.get("order_type")
            priority = get_attr_safe(order, "hercules_priority", 100) or get_attr_safe(order, "priority", 100) or 100
            
            # Check conflicts
            conflicts = check_scale_conflicts_for_order(
                po_number, equipment, priority, version, order_type
            )
            
            return jsonify({
                "success": True,
                "timestamp": datetime.now().isoformat(),
                "po_number": po_number,
                "order_type": order_type,
                "version": version,
                "priority": priority,
                "equipment": equipment,
                "conflicts": conflicts
            })
    except Exception as e:
        print(f"❌ Error checking conflicts for {po_number}: {e}")
        import traceback
        traceback.print_exc()
        return jsonify({
            "success": False,
            "error": str(e)
        }), 500


@orders_bp.route("/with-conflicts", methods=["GET"])
def get_orders_with_conflicts():
    """
    Get all orders with conflict group information.
    
    This endpoint returns orders with:
    - has_priority_conflict: True if order is in a conflict group
    - conflict_group_priority: Priority within conflict group (1, 2, 3...)
    - conflict_can_run: Whether this order can run (only True for priority 1)
    - conflict_waiting_for: List of order IDs this order is waiting for
    - conflict_shared_scales: List of scales causing the conflict
    
    Query params:
    - status: Filter by status (default: InProgress,Pending)
    
    Returns:
    {
        "success": True,
        "orders": [...],
        "conflict_groups": [...]
    }
    """
    if ProcessOrder is None:
        return jsonify({"success": False, "error": "ProcessOrder model not available"}), 500
    
    try:
        from services.scale_lock_service import get_conflict_groups_for_orders
        
        # Get filter parameter
        status_filter = request.args.get("status", "InProgress,Pending")
        status_list = [s.strip() for s in status_filter.split(",") if s.strip()]
        
        with _db_session() as db:
            # Query orders with status filter
            query = db.query(ProcessOrder)
            if status_list and "All" not in status_list:
                query = query.filter(ProcessOrder.status.in_(status_list))
            
            orders = query.order_by(ProcessOrder.hercules_priority.asc(), ProcessOrder.id.asc()).all()
            
            # Build orders data for conflict detection
            # ✅ CRITICAL FIX: Exclude COMPLETED orders from conflict detection
            # A completed order is one where confirmation matches target - these shouldn't hold scale locks
            orders_data = []
            excluded_completed = []
            
            for order in orders:
                # ✅ Exclude terminal/validated orders from conflict detection - they no longer hold scale locks.
                # Including them would incorrectly show Pending orders as "Wait" (padlock) after the order has
                # validated and released scales (e.g. when using separate Start button instead of Auto Validation).
                if (getattr(order, "status", None) or "").strip() in ("Validated", "Rejected", "Validation_Failed", "Completed"):
                    continue

                # Check if order is completed (confirmation matches target)
                order_type = None
                last_confirmed = float(get_attr_safe(order, "last_confirmed_qty", 0) or 0)
                
                # Determine target based on order type
                material = str(get_attr_safe(order, "material", "") or "").strip().lstrip("0")
                if material.startswith("13"):
                    order_type = "MILLING"
                    target_qty = float(get_attr_safe(order, "expected_weight", 0) or get_attr_safe(order, "quantity", 0) or 0)
                elif material.startswith("14"):
                    order_type = "PACKING"
                    target_qty = float(get_attr_safe(order, "quantity", 0) or 0)
                else:
                    target_qty = float(get_attr_safe(order, "quantity", 0) or 0)
                
                # Skip completed orders from conflict detection
                # Use a small tolerance for floating point comparison
                tolerance = 0.01
                is_completed = target_qty > 0 and abs(last_confirmed - target_qty) < tolerance
                
                if is_completed:
                    excluded_completed.append(f"{order.order_id} (confirmed={last_confirmed}, target={target_qty})")
                    continue  # Don't include in conflict detection
                
                classification = classify_order(order)
                if classification.get("error"):
                    continue
                
                all_scales = get_all_scales_for_order(order, classification, include_byproduct=True)
                
                orders_data.append({
                    "order_id": order.order_id,
                    "version": get_attr_safe(order, "version", ""),
                    "scales": all_scales,
                    "order_type": classification.get("order_type"),
                    "priority": get_attr_safe(order, "hercules_priority", 100) or get_attr_safe(order, "priority", 100) or 100,
                    "status": order.status
                })
            
            if excluded_completed:
                print(f"✅ [with-conflicts] Excluded {len(excluded_completed)} completed orders from conflict detection:")
                for exc in excluded_completed:
                    print(f"   🏁 {exc}")
            
            # Detect conflict groups
            conflict_info = get_conflict_groups_for_orders(orders_data)
            
            # Build response with conflict info attached to each order
            # Also add a map of order_id -> scales for debugging
            order_scales_map = {od["order_id"]: od["scales"] for od in orders_data}
            
            result = []
            for order in orders:
                order_dict = serialize_order(order)
                order_conflict = conflict_info["order_conflict_info"].get(order.order_id, {"has_conflict": False})
                
                order_dict["has_priority_conflict"] = order_conflict.get("has_conflict", False)
                order_dict["conflict_group_priority"] = order_conflict.get("group_priority") if order_conflict.get("has_conflict") else None
                order_dict["conflict_can_run"] = order_conflict.get("can_run", True)
                order_dict["conflict_waiting_for"] = order_conflict.get("waiting_for", [])
                order_dict["conflict_shared_scales"] = order_conflict.get("shared_scales", [])
                order_dict["conflict_shared_with"] = order_conflict.get("shared_with", [])
                order_dict["conflict_group_id"] = order_conflict.get("group_id") if order_conflict.get("has_conflict") else None
                # Add detected scales for debugging
                order_dict["detected_scales"] = order_scales_map.get(order.order_id, [])
                
                result.append(order_dict)
            
            # Log for debugging - VERBOSE mode to trace conflict detection issues
            print(f"\n{'='*80}")
            print(f"📊 [with-conflicts] CONFLICT ANALYSIS REPORT")
            print(f"{'='*80}")
            print(f"Total orders analyzed: {len(result)}")
            print(f"\n📦 SCALES DETECTED FOR EACH ORDER:")
            for od in orders_data:
                print(f"   {od['order_id']} ({od['version']}): {od['scales']} [type={od['order_type']}]")
            
            print(f"\n🔒 CONFLICT GROUPS DETECTED: {len(conflict_info['conflict_groups'])}")
            for group in conflict_info["conflict_groups"]:
                print(f"\n   GROUP {group['group_id']}:")
                print(f"      Shared scales: {group['shared_scales']}")
                print(f"      Orders (priority order):")
                for oid, prio in group['priority_order'].items():
                    can_run = "✅ CAN RUN" if prio == 1 else "⏳ WAITING"
                    order_info = conflict_info['order_conflict_info'].get(oid, {})
                    waiting_for = order_info.get('waiting_for', [])
                    print(f"         {prio}. {oid} - {can_run}{f' (for: {waiting_for})' if waiting_for else ''}")
            
            # Highlight orders with NO conflict
            no_conflict_orders = [od['order_id'] for od in orders_data if not conflict_info['order_conflict_info'].get(od['order_id'], {}).get('has_conflict')]
            if no_conflict_orders:
                print(f"\n✅ ORDERS WITH NO CONFLICT (can start independently): {no_conflict_orders}")
            
            print(f"{'='*80}\n")
            
            return jsonify({
                "success": True,
                "timestamp": datetime.now().isoformat(),
                "orders": result,
                "conflict_groups": conflict_info["conflict_groups"],
                "total_orders": len(result),
                "total_conflict_groups": len(conflict_info["conflict_groups"])
            })
            
    except Exception as e:
        print(f"❌ Error getting orders with conflicts: {e}")
        import traceback
        traceback.print_exc()
        return jsonify({
            "success": False,
            "error": str(e)
        }), 500


@orders_bp.route("/debug/scale-mappings", methods=["GET"])
def debug_scale_mappings():
    """
    Debug endpoint to show all version mappings and their scales.
    Helps diagnose conflict detection issues.
    """
    try:
        from models.milling_version_mapping import MillingVersionMapping
        
        with _mapping_db_session() as db:
            mappings = db.query(MillingVersionMapping).order_by(MillingVersionMapping.version).all()
            
            result = []
            for m in mappings:
                # Parse scales properly
                scales = m.scales
                if isinstance(scales, str):
                    import json
                    try:
                        scales = json.loads(scales)
                    except:
                        scales = [s.strip() for s in scales.split(",") if s.strip()]
                
                all_scales = set()
                if scales:
                    for s in scales:
                        all_scales.add(s.upper().strip())
                if m.scale1:
                    all_scales.add(m.scale1.upper().strip())
                if m.scale2:
                    all_scales.add(m.scale2.upper().strip())
                if m.scale3:
                    all_scales.add(m.scale3.upper().strip())
                
                result.append({
                    "version": m.version,
                    "main_equipment": scales,
                    "byproduct_scale1": m.scale1,
                    "byproduct_scale2": m.scale2,
                    "byproduct_scale3": m.scale3,
                    "ALL_SCALES_FOR_CONFLICT": list(all_scales)
                })
            
            # Find which versions share scales
            scale_to_versions = {}
            for mapping in result:
                for scale in mapping["ALL_SCALES_FOR_CONFLICT"]:
                    if scale not in scale_to_versions:
                        scale_to_versions[scale] = []
                    scale_to_versions[scale].append(mapping["version"])
            
            # Identify conflicts
            conflicting_scales = {s: v for s, v in scale_to_versions.items() if len(v) > 1}
            
            return jsonify({
                "success": True,
                "mappings": result,
                "scale_to_versions": scale_to_versions,
                "CONFLICTING_SCALES": conflicting_scales,
                "message": "Versions that share any of the conflicting scales will be in the same conflict group"
            })
            
    except Exception as e:
        import traceback
        traceback.print_exc()
        return jsonify({"success": False, "error": str(e)}), 500


@orders_bp.route("/debug/packing-mappings", methods=["GET"])
def debug_packing_mappings():
    """
    Debug endpoint to show all packing (palletizer) version mappings.
    Shows which palletizer counter each packing version uses.
    """
    try:
        from models.palletizer_mapping import PalletizerMapping
        
        with _db_session() as db:
            mappings = db.query(PalletizerMapping).order_by(PalletizerMapping.version).all()
            
            result = []
            for m in mappings:
                # Convert palletizer code to SCADA counter tag
                palletizer = m.palletizer or ""
                scada_counter = _translate_pl_to_scada([palletizer]) if palletizer else []
                
                result.append({
                    "version": m.version,
                    "palletizer": m.palletizer,
                    "scada_counter": scada_counter[0] if scada_counter else None,
                    "bag_size_kg": m.bag_size_kg,
                    "bags_per_pallet": m.bags_per_pallet,
                    "kg_per_pallet": m.kg_per_pallet
                })
            
            # Find which versions share palletizers (and thus SCADA counters)
            counter_to_versions = {}
            for mapping in result:
                counter = mapping["scada_counter"]
                if counter:
                    if counter not in counter_to_versions:
                        counter_to_versions[counter] = []
                    counter_to_versions[counter].append(mapping["version"])
            
            # Identify conflicts (same counter = same conflict group)
            conflicting_counters = {c: v for c, v in counter_to_versions.items() if len(v) > 1}
            
            return jsonify({
                "success": True,
                "mappings": result,
                "counter_to_versions": counter_to_versions,
                "CONFLICTING_COUNTERS": conflicting_counters,
                "message": "Packing versions that share the same palletizer (SCADA counter) will be in the same conflict group"
            })
            
    except Exception as e:
        import traceback
        traceback.print_exc()
        return jsonify({"success": False, "error": str(e)}), 500


@orders_bp.route("/version/<string:version>/orders", methods=["GET"])
def get_orders_by_version_api(version: str):
    """
    Get all orders with a specific product version.
    
    Query params:
    - order_type: "MILLING" or "PACKING" (required)
    
    Returns:
    - List of orders with this version, sorted by priority
    - Helps identify duplicate version conflicts
    """
    order_type = request.args.get("order_type", "").upper()
    
    if not order_type or order_type not in ["MILLING", "PACKING"]:
        return jsonify({
            "success": False,
            "error": "order_type query parameter required (MILLING or PACKING)"
        }), 400
    
    try:
        orders = get_orders_with_same_version("", version, order_type)
        
        return jsonify({
            "success": True,
            "timestamp": datetime.now().isoformat(),
            "version": version,
            "order_type": order_type,
            "orders": orders
        })
    except Exception as e:
        print(f"❌ Error getting orders for version {version}: {e}")
        import traceback
        traceback.print_exc()
        return jsonify({
            "success": False,
            "error": str(e)
        }), 500


@orders_bp.route("/scale/<string:scale_tag>/orders", methods=["GET"])
def get_orders_by_scale_api(scale_tag: str):
    """
    Get all orders that use a specific scale.
    
    Returns:
    - List of orders using this scale, sorted by priority
    - Helps identify scale conflicts
    """
    try:
        orders = get_orders_using_scale(scale_tag)
        
        return jsonify({
            "success": True,
            "timestamp": datetime.now().isoformat(),
            "scale_tag": scale_tag.upper(),
            "orders": orders
        })
    except Exception as e:
        print(f"❌ Error getting orders for scale {scale_tag}: {e}")
        import traceback
        traceback.print_exc()
        return jsonify({
            "success": False,
            "error": str(e)
        }), 500


@orders_bp.route("/palletizer-mapping", methods=["GET", "POST", "OPTIONS"])
def palletizer_mapping():
    from models.palletizer_mapping import PalletizerMapping

    # Handle CORS preflight
    if request.method == "OPTIONS":
        response = jsonify({})
        origin = request.headers.get("Origin", "http://localhost:5173")
        response.headers.add("Access-Control-Allow-Origin", origin)
        response.headers.add("Access-Control-Allow-Headers", "Content-Type, ngrok-skip-browser-warning")
        response.headers.add("Access-Control-Allow-Methods", "GET, POST, OPTIONS")
        response.headers.add("Access-Control-Allow-Credentials", "true")
        return response

    if request.method == "GET":
        # GET: Fetch all palletizer mappings
        with _db_session() as db:
            mappings = db.query(PalletizerMapping).order_by(PalletizerMapping.version.asc()).all()
            result = []
            for mapping in mappings:
                result.append({
                    "id": mapping.id,
                    "version": mapping.version,
                    "palletizer": mapping.palletizer,
                    "bag_size_kg": float(mapping.bag_size_kg) if mapping.bag_size_kg else 0.0,
                    "bags_per_pallet": int(mapping.bags_per_pallet) if mapping.bags_per_pallet else 0,
                    "kg_per_pallet": float(mapping.kg_per_pallet) if mapping.kg_per_pallet else 0.0,
                    "description": mapping.description,
                })
            return jsonify(result)
    
    # POST: Create or update palletizer mapping
    data = request.json or {}
    version = data.get("version", "").strip().upper()
    palletizer = data.get("palletizer")
    bag_size = data.get("bag_size_kg")
    bags_per_pallet = data.get("bags_per_pallet")
    kg_per_pallet = data.get("kg_per_pallet")
    description = data.get("description")

    if not version or not palletizer:
        return jsonify({"success": False, "message": "Version and palletizer required"}), 400
    
    with _db_session() as db:
        existing = db.query(PalletizerMapping).filter(
            PalletizerMapping.version == version
        ).first()

        if existing:
            # UPDATE mapping
            existing.palletizer = palletizer
            existing.bag_size_kg = bag_size
            existing.bags_per_pallet = bags_per_pallet
            existing.kg_per_pallet = kg_per_pallet
            existing.description = description if description else None
            db.commit()
            return jsonify({"success": True, "message": "Mapping updated", "mode": "update"})

        # INSERT new row
        new_row = PalletizerMapping(
            version=version,
            palletizer=palletizer,
            bag_size_kg=bag_size,
            bags_per_pallet=bags_per_pallet,
            kg_per_pallet=kg_per_pallet,
            description=description if description else None
        )
        db.add(new_row)
        db.commit()

        return jsonify({"success": True, "message": "Mapping created", "mode": "create"})


@orders_bp.route("/palletizer-mapping/<int:mapping_id>", methods=["DELETE", "OPTIONS"])
def delete_palletizer_mapping(mapping_id: int):
    """DELETE endpoint for removing palletizer mappings by ID"""
    from models.palletizer_mapping import PalletizerMapping

    # Handle CORS preflight
    if request.method == "OPTIONS":
        response = jsonify({})
        origin = request.headers.get("Origin", "http://localhost:5173")
        response.headers.add("Access-Control-Allow-Origin", origin)
        response.headers.add("Access-Control-Allow-Headers", "Content-Type, ngrok-skip-browser-warning")
        response.headers.add("Access-Control-Allow-Methods", "DELETE, OPTIONS")
        response.headers.add("Access-Control-Allow-Credentials", "true")
        return response

    try:
        with _db_session() as db:
            mapping = db.query(PalletizerMapping).filter(PalletizerMapping.id == mapping_id).first()
            if not mapping:
                return jsonify({"success": False, "message": f"Palletizer mapping with ID {mapping_id} not found"}), 404
            
            version = mapping.version
            palletizer = mapping.palletizer
            db.delete(mapping)
            db.commit()
            
            print(f"✅ Deleted palletizer mapping: {version} - {palletizer} (ID: {mapping_id})")
            return jsonify({
                "success": True,
                "message": f"Palletizer mapping for {version} - {palletizer} deleted successfully"
            })
    except Exception as e:
        print(f"❌ Error deleting palletizer mapping: {e}")
        return jsonify({"success": False, "message": str(e)}), 500
