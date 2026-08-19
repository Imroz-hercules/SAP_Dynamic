# services/auto_validator.py
"""
Priority-Based Auto-Validator with Manual Start/Stop Control

Features:
- Manual start/stop from frontend
- Processes orders by priority (priority 1 first)
- Automatically starts priority 1 orders
- Validates completed orders
"""

import logging
import time
import threading
from datetime import datetime
from typing import Dict, List, Optional, Any
from sqlalchemy.orm import Session

from database import postgres_engine
from sqlalchemy.orm import sessionmaker

from services.scale_service import (
    get_multiple_scada_readings,
    calculate_deltas,
    capture_baseline_readings
)

# Import scale lock service for proper conflict detection and scale management
from services.scale_lock_service import (
    lock_scales,
    release_scales,
    add_to_queue,
    remove_from_queue,
    set_order_running,
    register_order_version,
    get_conflict_groups_for_orders
)

try:
    from models.process_order_pg import ProcessOrderPG as ProcessOrder
    print("✅ Auto-validator: ProcessOrder model loaded")
except Exception as e:
    print(f"❌ Auto-validator: Failed to load ProcessOrder model: {e}")
    ProcessOrder = None

log = logging.getLogger(__name__)

PostgresSessionLocal = sessionmaker(
    bind=postgres_engine, autoflush=False, autocommit=False, future=True
)

# ✅ C31-T26 FIX: Cache for tracking delta increases in restart scenarios
_auto_validator_delta_cache = {}


# ============================================================================
# CLASSIFICATION MAPPINGS
# ============================================================================

MILLING_PV_MAPPING = {
    # SCALE-based versions (WG101 + WG302 SCREENINGS)
    "LWSM": ["WG101", "WG302"],
    "IWSM": ["WG101", "WG302"],
    "SWSM": ["WG101", "WG302"],
    
    # SCALE-based versions (WG201 + WG301 SCREENINGS)
    "CWIM": ["WG201", "WG301"],
    "CWLM": ["WG201", "WG301"],
    "CWMM": ["WG201", "WG301"],
    "CWSM": ["WG201", "WG301"],
    
    # ✅ REMOVED WG202: Only use OUTPUT scales (WG501, WG502, WG503) for MILLING orders
    # BKF1 and BRF1 versions don't use WG502 (F2 stream)
    "BKF1": ["WG501", "WG503"],  # BAKERY FLOUR + BRAN (NO WG502)
    "BRF1": ["WG501", "WG503"],  # BRAWNY + BRAN (NO WG502)
    # All other versions use all 3 output scales
    "CKF1": ["WG501", "WG502", "WG503"],  # BAKERY + CAKE + BRAN
    "IWF1": ["WG501", "WG502", "WG503"],  # BAKERY + IWW + BRAN
    "IWF2": ["WG501", "WG502", "WG503"],  # CAKE + IWW + BRAN
    "BRF2": ["WG501", "WG502", "WG503"],  # BAKERY + BRAWNY + BRAN
    "BRF3": ["WG501", "WG502", "WG503"],  # BRAWNY + CAKE + BRAN
    "MMCF": ["WG501", "WG502", "WG503"]   # BAKERY + CAKE + BRAN
}

PACKING_PV_MAPPING = {
    "CKL1": ["PL601", "PL602"],
    "CKL2": ["PL601", "PL602"],
    "BKL1": ["PL601", "PL602"],
    "BKL2": ["PL601", "PL602"],
    "BWL1": ["PL601", "PL602"],
    "BWL2": ["PL601", "PL602"],
    "IWL1": ["PL601", "PL602"],
    "IWL2": ["PL601", "PL602"],
    "KL1": ["PL601", "PL602"],  # Add missing KL1 version
    "KL2": ["PL601", "PL602"],  # Add missing KL2 version
    "BK10": ["PL607"],
    "BW10": ["PL607"],
    "IW10": ["PL607"],
    "CK10": ["PL607"],
    "BK05": ["PL607"],
    "EB25": ["PL603"],
    "BR40": ["PL603"],
    "CM01": ["PL606"],
    "BM01": ["PL606"],
    "QRC1": ["PL606"],
    "QRW1": ["PL606"],
    "MM01": ["PL606"]
}


# ============================================================================
# CLASSIFICATION HELPER
# ============================================================================

def _convert_to_tons(quantity: float, unit: str, material_desc: str = "", material: str = "", version: str = "") -> float:
    """
    Convert quantity to tons based on unit and material type.
    """
    if not quantity or quantity <= 0:
        return 0.0
    
    unit = unit.upper() if unit else ""
    
    # Direct ton conversions
    if unit in ["TO", "TON", "TONS", "MT", "METRIC TON"]:
        return float(quantity)
    
    # Kilogram to ton conversion
    elif unit in ["KG", "KILOGRAM", "KILOGRAMS"]:
        return float(quantity) / 1000.0
    
    # Gram to ton conversion
    elif unit in ["G", "GRAM", "GRAMS"]:
        return float(quantity) / 1000000.0
    
    # Bag conversions (assuming standard bag weights)
    elif unit in ["BAG", "BAGS"]:
        # Try to determine bag size from material description or version
        bag_size = 50.0  # Default 50kg bag
        
        if material_desc:
            # Look for bag size in material description
            import re
            size_match = re.search(r'(\d+)\s*KG', material_desc.upper())
            if size_match:
                bag_size = float(size_match.group(1))
        
        if version:
            # Look for bag size in version
            import re
            size_match = re.search(r'(\d+)', version)
            if size_match:
                bag_size = float(size_match.group(1))
        
        # Convert bags to tons
        return (float(quantity) * bag_size) / 1000.0
    
    # Pound to ton conversion
    elif unit in ["LB", "LBS", "POUND", "POUNDS"]:
        return float(quantity) * 0.000453592  # 1 lb = 0.000453592 metric tons
    
    # Default: assume it's already in tons
    else:
        return float(quantity)


def classify_order(order) -> Dict[str, Any]:
    """Classify order using 2-level system."""
    material_code = str(order.material or "").strip()
    version = (order.version or "").upper().strip()
    
    result = {
        "order_type": None,
        "equipment": [],
        "version": version,
        "error": None
    }
    
    # Level 1: Material code
    material_stripped = material_code.lstrip('0')
    if len(material_stripped) < 2:
        result["error"] = f"Invalid material code: {material_code}"
        return result
    
    material_prefix = material_stripped[:2]
    
    # Log classification for debugging
    log.info(f"Classifying order {order.order_id}: material={material_code} -> stripped={material_stripped} -> prefix={material_prefix}")
    
    if material_prefix == "13":
        result["order_type"] = "MILLING"
        result["equipment"] = MILLING_PV_MAPPING.get(version, ["WG501", "WG502", "WG503"])
        result["confidence"] = "HIGH"
    elif material_prefix == "14":
        result["order_type"] = "PACKING"
        result["equipment"] = PACKING_PV_MAPPING.get(version, ["PL601", "PL602"])  # Default fallback equipment
        result["confidence"] = "HIGH"
        
        # Check if equipment mapping exists for this version
        if version not in PACKING_PV_MAPPING:
            result["error"] = f"No specific equipment mapping found for PACKING version '{version}'. Using default equipment: {result['equipment']}. Available versions: {list(PACKING_PV_MAPPING.keys())}"
            result["confidence"] = "MEDIUM"  # Not LOW since we have fallback equipment
    else:
        result["error"] = f"Unknown material prefix: {material_prefix}. Expected '13' (MILLING) or '14' (PACKING)"
        result["confidence"] = "LOW"
    
    return result


# ============================================================================
# VALIDATION HELPERS
# ============================================================================

def get_byproduct_scales_for_version(version: str, order_type: str) -> List[str]:
    """
    Get byproduct scales for a milling version from the milling_version_mappings table.
    
    Args:
        version: Product version (e.g., "BKF1", "CWLM")
        order_type: "MILLING" or "PACKING"
        
    Returns:
        List of byproduct scale tags (scale1, scale2)
    """
    if order_type != "MILLING":
        return []
    
    try:
        from models.milling_version_mapping import MillingVersionMapping
        
        version_upper = (version or "").upper().strip()
        if not version_upper:
            return []
        
        # Use PostgresSessionLocal defined at module level
        mapping_db = PostgresSessionLocal()
        try:
            mapping = mapping_db.query(MillingVersionMapping).filter(
                MillingVersionMapping.version == version_upper
            ).first()
            
            if mapping:
                byproduct_scales = []
                if mapping.scale1:
                    byproduct_scales.append(mapping.scale1.upper())
                if mapping.scale2:
                    byproduct_scales.append(mapping.scale2.upper())
                log.info(f"📦 [get_byproduct_scales] Version {version_upper}: byproduct scales = {byproduct_scales}")
                return byproduct_scales
            else:
                log.warning(f"⚠️ [get_byproduct_scales] No mapping found for version {version_upper}")
                return []
        finally:
            mapping_db.close()
    except Exception as e:
        log.error(f"❌ [get_byproduct_scales] Error getting byproduct scales: {e}")
        import traceback
        traceback.print_exc()
        return []


def get_all_scales_for_order(order, classification: Dict, include_byproduct: bool = True) -> List[str]:
    """
    Get all scales for an order (main equipment + byproduct scales).
    
    Args:
        order: ProcessOrder object
        classification: Order classification dict
        include_byproduct: Whether to include byproduct scales
        
    Returns:
        List of all scale tags
    """
    equipment = classification.get("equipment", []) or []
    all_scales = list(equipment)  # Start with main equipment
    
    if include_byproduct and classification.get("order_type") == "MILLING":
        version = (getattr(order, "version", "") or "").upper().strip()
        byproduct_scales = get_byproduct_scales_for_version(version, "MILLING")
        
        # Add byproduct scales if not already in list
        for scale in byproduct_scales:
            if scale and scale not in all_scales:
                all_scales.append(scale)
        
        # Also check existing scale1/scale2 attributes (for restarted orders)
        for attr in ["scale1", "scale2"]:
            existing_scale = (getattr(order, attr, "") or "").upper().strip()
            if existing_scale and existing_scale not in all_scales:
                all_scales.append(existing_scale)
    
    return all_scales


def start_single_order(db: Session, order) -> Dict[str, Any]:
    """
    Start a single order by capturing baselines with proper scale locking.
    
    ✅ ENHANCED (Jan 27, 2026): Now integrates with scale lock service for:
    - Scale locking to prevent conflicts
    - Queue management for visibility
    - Byproduct scale handling for milling orders
    
    Returns:
        Success/error dict
    """
    try:
        po_number = order.order_id
        version = (getattr(order, "version", "") or "").upper().strip()
        priority = int(getattr(order, "hercules_priority", None) or getattr(order, "priority", 100) or 100)
        
        log.info(f"🚀 [auto_validator] Starting order {po_number}: version={version}, priority={priority}")
        
        # Classify order
        classification = classify_order(order)
        
        if classification.get("error") and classification.get("confidence") == "LOW":
            return {
                "success": False,
                "po_number": po_number,
                "error": classification["error"]
            }
        
        order_type = classification["order_type"]
        equipment = classification.get("equipment", [])
        
        if not equipment:
            return {
                "success": False,
                "po_number": po_number,
                "error": "No equipment mapped for this order"
            }
        
        # =============================================================================
        # SCALE LOCKING: Get all scales and lock them
        # =============================================================================
        all_scales = get_all_scales_for_order(order, classification, include_byproduct=True)
        log.info(f"🔒 [{po_number}] Attempting to lock scales: {all_scales}")
        
        # Register order in version registry and add to queue
        if version and order_type:
            register_order_version(po_number, version, order_type)
        
        # Add to queue with full details
        add_to_queue(po_number, all_scales, priority, version, order_type)
        
        # Try to lock all scales
        has_conflict, locked_scales, conflict_details, preempted_orders = lock_scales(
            po_number, all_scales, priority, version, order_type
        )
        
        # Check if ALL scales were locked successfully
        all_scales_locked = not has_conflict and len(locked_scales) == len(all_scales)
        
        if not all_scales_locked:
            # Scales are locked by another order - cannot start
            log.warning(f"🛑 [{po_number}] BLOCKED: Scales are locked by another order. Conflicts: {conflict_details}")
            
            # Release any partially locked scales
            if locked_scales:
                release_scales(po_number, locked_scales)
                log.info(f"🔓 [{po_number}] Released partially locked scales: {locked_scales}")
            
            # Remove from queue since we can't start
            remove_from_queue(po_number)
            
            return {
                "success": False,
                "po_number": po_number,
                "error": f"Scales locked by another order: {conflict_details}",
                "scales_locked": True,
                "conflict_details": conflict_details
            }
        
        log.info(f"✅ [{po_number}] All scales locked successfully: {locked_scales}")
        
        # Mark order as running in queue
        set_order_running(po_number)
        
        # =============================================================================
        # CAPTURE BASELINES
        # =============================================================================
        # Clear SCADA cache before capturing baselines
        try:
            from services.scale_service import clear_scada_cache
            clear_scada_cache()
        except Exception as e:
            log.warning(f"⚠️ [{po_number}] Could not clear SCADA cache: {e}")
        
        # Wait for SCADA values to settle
        time.sleep(0.5)
        
        # Capture baselines with multiple readings for accuracy
        baselines_1 = capture_baseline_readings(all_scales)
        time.sleep(0.3)
        baselines_2 = capture_baseline_readings(all_scales)
        
        # Use the more recent reading
        baselines = baselines_2 if baselines_2 else baselines_1
        
        if not baselines:
            # Release scales since we failed to capture baselines
            release_scales(po_number, all_scales)
            remove_from_queue(po_number)
            
            return {
                "success": False,
                "po_number": po_number,
                "error": "Failed to capture baseline readings from SCADA"
            }
        
        log.info(f"📊 [{po_number}] Captured baselines: {baselines}")
        
        # =============================================================================
        # UPDATE ORDER
        # =============================================================================
        order.order_type = order_type
        order.status = "InProgress"
        
        # Store baselines for ALL scales (equipment + byproduct)
        for tag, value in baselines.items():
            baseline_attr = f"baseline_{tag.lower()}"
            try:
                setattr(order, baseline_attr, float(value or 0.0))
            except Exception as e:
                log.warning(f"⚠️ [{po_number}] Could not set {baseline_attr}: {e}")
        
        # =============================================================================
        # SET BYPRODUCT SCALES FOR MILLING ORDERS
        # =============================================================================
        if order_type == "MILLING" and version:
            byproduct_scales = get_byproduct_scales_for_version(version, order_type)
            
            if len(byproduct_scales) >= 1:
                setattr(order, "scale1", byproduct_scales[0])
                baseline_val = baselines.get(byproduct_scales[0], 0.0)
                setattr(order, "scale1_qty", float(baseline_val or 0.0))
                log.info(f"📦 [{po_number}] Set scale1={byproduct_scales[0]}, scale1_qty={baseline_val}")
            
            if len(byproduct_scales) >= 2:
                setattr(order, "scale2", byproduct_scales[1])
                baseline_val = baselines.get(byproduct_scales[1], 0.0)
                setattr(order, "scale2_qty", float(baseline_val or 0.0))
                log.info(f"📦 [{po_number}] Set scale2={byproduct_scales[1]}, scale2_qty={baseline_val}")
        
        db.add(order)
        
        log.info(f"✅ [{po_number}] Started order ({order_type}) with scales locked: {all_scales}")
        
        return {
            "success": True,
            "po_number": po_number,
            "order_type": order_type,
            "equipment": equipment,
            "all_scales": all_scales,
            "baselines": baselines,
            "locked_scales": locked_scales
        }
        
    except Exception as e:
        log.error(f"❌ Error starting order {order.order_id}: {e}", exc_info=True)
        
        # Clean up on error
        try:
            release_scales(order.order_id, None)
            remove_from_queue(order.order_id)
        except:
            pass
        
        return {
            "success": False,
            "po_number": order.order_id,
            "error": str(e)
        }


def check_order_completion(order, classification: Dict, db=None) -> Dict[str, Any]:
    """Check if order has reached target production."""
    order_type = classification["order_type"]
    equipment = classification["equipment"]
    
    if not equipment:
        return {
            "is_complete": False,
            "error": "No equipment mapped for this order"
        }
    
    # Get baselines
    # ✅ FIX: For PL/SL scales (PACKING), baseline is stored in scale1_qty/scale2_qty/scale3_qty
    # For WG/DM scales (MILLING), baseline is stored in baseline_{tag} attributes
    baselines = {}
    scale1_tag = str(getattr(order, 'scale1', '') or '').upper()
    scale2_tag = str(getattr(order, 'scale2', '') or '').upper()
    scale3_tag = str(getattr(order, 'scale3', '') or '').upper()
    
    for tag in equipment:
        tag_upper = tag.upper()
        # ✅ ONLY use scale1_qty for PL/SL palletizer scales
        if (tag_upper.startswith("PL") or tag_upper.startswith("SL")):
            if tag_upper == scale1_tag:
                baseline_value = float(getattr(order, 'scale1_qty', 0.0) or 0.0)
            elif tag_upper == scale2_tag:
                baseline_value = float(getattr(order, 'scale2_qty', 0.0) or 0.0)
            elif tag_upper == scale3_tag:
                baseline_value = float(getattr(order, 'scale3_qty', 0.0) or 0.0)
            else:
                baseline_attr = f"baseline_{tag.lower()}"
                baseline_value = float(getattr(order, baseline_attr, 0.0) or 0.0)
        else:
            # WG/DM scales ALWAYS use baseline_{tag} attributes
            baseline_attr = f"baseline_{tag.lower()}"
            baseline_value = float(getattr(order, baseline_attr, 0.0) or 0.0)
        baselines[tag] = baseline_value
    
    # Calculate current production (pass order and db for auto-reset)
    deltas = calculate_deltas(equipment, baselines, order=order, db=db)
    
    # ✅ FIX: Use sum_dm_readings_for_order for DM water meters
    # DM tags are 30-sec averages on PLC side, so we must SUM all readings in the time window,
    # rather than using the delta/accumulation logic which misses readings between polls.
    try:
        from services.scale_service import sum_dm_readings_for_order
        
        for tag in equipment:
            if tag.startswith("DM"):
                # Calculate correct sum from database
                dm_sum = sum_dm_readings_for_order(tag, order)
                
                # Update delta in deltas dict
                if tag in deltas:
                    deltas[tag]["delta"] = dm_sum
                    log.debug(f"💧 [auto_validator] Replaced DM delta for {tag} with SUM: {dm_sum}")
    except Exception as e:
        log.warning(f"⚠️ [auto_validator] Error calculating DM sums: {e}")
    
    delta_total = sum(delta_info["delta"] for delta_info in deltas.values())
    
    # Get target quantity
    if order_type == "MILLING":
        target_qty = float(order.expected_weight or order.quantity or 0.0)
        unit = "TON"
        actual_qty = delta_total
    else:  # PACKING
        target_qty = float(order.quantity or 0.0)
        unit = "BAG"
        
        # ✅ C31-T26 FIX: For PACKING orders, use WORKER's weight_shift values
        # The worker (shift_live_update) tracks production correctly including 100K rollovers
        # Recalculating delta from scratch can give WRONG values after rollover
        # (e.g., baseline=340, current=340 after rollover → delta=0, but actual production=12800)
        
        # Get the worker's calculated shift weights (these are already in BAGS)
        weight_a = float(getattr(order, 'weight_shift_a', 0.0) or 0.0)
        weight_b = float(getattr(order, 'weight_shift_b', 0.0) or 0.0)
        weight_c = float(getattr(order, 'weight_shift_c', 0.0) or 0.0)
        
        # Total production = sum of all shift weights
        total_shift_weight = weight_a + weight_b + weight_c
        
        # Also check confirmed_qty in case it's higher (from previous accumulation)
        prev_confirmed = float(getattr(order, 'confirmed_qty', 0.0) or 0.0)
        
        # Use the higher of: total shift weight OR previous confirmed
        # This ensures we don't lose production after restarts
        actual_qty = int(max(total_shift_weight, prev_confirmed))
        
        log.info(f"✅ [auto_validator] PACKING: weight_a={weight_a:.0f}, weight_b={weight_b:.0f}, weight_c={weight_c:.0f}, total={total_shift_weight:.0f}, prev_confirmed={prev_confirmed:.0f} → actual_qty={actual_qty}")
    
    if target_qty <= 0:
        return {
            "is_complete": False,
            "error": "Invalid target quantity"
        }
    
    # Calculate variance
    variance = actual_qty - target_qty
    variance_pct = (variance / target_qty * 100.0)
    
    # Check tolerance (±5%)
    tolerance = 5.0
    lower_limit = target_qty * (1 - tolerance / 100)
    upper_limit = target_qty * (1 + tolerance / 100)
    
    within_tolerance = lower_limit <= actual_qty <= upper_limit
    is_complete = actual_qty >= lower_limit
    
    return {
        "is_complete": is_complete,
        "actual_qty": round(actual_qty, 3),
        "target_qty": round(target_qty, 3),
        "variance": round(variance, 3),
        "variance_pct": round(variance_pct, 2),
        "within_tolerance": within_tolerance,
        "unit": unit,
        "lower_limit": round(lower_limit, 3),
        "upper_limit": round(upper_limit, 3),
        "equipment_details": deltas
    }


# ============================================================================
# AUTO-VALIDATOR SERVICE WITH PRIORITY-BASED PROCESSING
# ============================================================================

class AutoValidator:
    """
    Priority-Based Auto-Validator with Manual Start/Stop Control
    
    Features:
    - Manual start/stop via API
    - Processes orders by priority (priority 1 first, then 2, 3, etc.)
    - Automatically starts pending orders with priority 1
    - Validates InProgress orders
    """
    
    def __init__(self, check_interval: int = 60):
        self.check_interval = check_interval
        self.is_running = False
        self.thread = None
        self._lock = threading.Lock()
        log.info(f"AutoValidator initialized with {check_interval}s interval")
    
    def start(self):
        """Start the auto-validator (called by frontend button)."""
        with self._lock:
            if self.is_running:
                log.warning("AutoValidator already running")
                return {"success": False, "message": "Auto-validator already running"}
            
            self.is_running = True
            self.thread = threading.Thread(target=self._run, daemon=True)
            self.thread.start()
            log.info("✅ AutoValidator started by user")
            
            return {"success": True, "message": "Auto-validator started successfully"}
    
    def stop(self):
        """Stop the auto-validator (called by frontend button)."""
        with self._lock:
            if not self.is_running:
                log.warning("AutoValidator not running")
                return {"success": False, "message": "Auto-validator is not running"}
            
            log.info("🛑 Stopping AutoValidator...")
            
            # Set flag to False first to signal the thread to stop
            self.is_running = False
            
            # Wait for thread to finish with timeout
            if self.thread and self.thread.is_alive():
                log.info("⏳ Waiting for AutoValidator thread to finish...")
                self.thread.join(timeout=3)  # Increased to 3 seconds
                
                if self.thread.is_alive():
                    log.warning("⚠️ AutoValidator thread did not stop within timeout")
                    # Force cleanup - set thread to None to indicate it's dead
                    self.thread = None
                    log.info("🔧 Forced thread cleanup - AutoValidator marked as stopped")
                else:
                    log.info("✅ AutoValidator thread stopped successfully")
                    self.thread = None
            else:
                log.info("✅ No active thread to stop")
                self.thread = None
            
            # Double-check that we're actually stopped
            if self.is_running:
                log.error("❌ CRITICAL: is_running is still True after stop attempt!")
                self.is_running = False
            
            log.info("🛑 AutoValidator stopped by user - is_running=False, thread=None")
            
            return {"success": True, "message": "Auto-validator stopped successfully"}
    
    def _run(self):
        """Main loop that runs in background thread."""
        log.info("AutoValidator main loop started")
        
        while self.is_running:
            try:
                self._process_cycle()
            except Exception as e:
                log.error(f"Error in auto-validation cycle: {e}", exc_info=True)
            
            # Sleep in smaller chunks to be more responsive to stop requests
            sleep_time = 0
            while sleep_time < self.check_interval and self.is_running:
                time.sleep(1)  # Sleep in 1-second chunks
                sleep_time += 1
        
        log.info("AutoValidator main loop ended")
    
    def _process_cycle(self):
        """
        Process one validation cycle:
        1. Start priority 1 pending orders
        2. Validate all InProgress orders
        """
        if ProcessOrder is None:
            return
        
        try:
            with PostgresSessionLocal() as db:
                # Step 1: Start priority 1 pending orders
                self._start_priority_orders(db)
                
                # Step 2: Validate InProgress orders
                self._validate_inprogress_orders(db)
                
                db.commit()
                
        except Exception as e:
            log.error(f"Database error in auto-validation cycle: {e}")
    
    def _start_priority_orders(self, db: Session):
        """
        Automatically start pending orders with priority 1.
        """
        try:
            # Get all pending orders with hercules_priority 1, ordered by hercules_priority
            pending_orders = db.query(ProcessOrder).filter(
                ProcessOrder.status == "Pending",
                ProcessOrder.hercules_priority == 1
            ).order_by(ProcessOrder.hercules_priority.asc()).all()
            
            if not pending_orders:
                log.debug("No priority 1 pending orders to start")
                return
            
            log.info(f"Found {len(pending_orders)} priority 1 pending orders")
            
            for order in pending_orders:
                result = start_single_order(db, order)
                
                if result["success"]:
                    log.info(f"✅ Auto-started priority 1 order: {result['po_number']}")
                else:
                    log.warning(f"❌ Failed to start {result['po_number']}: {result.get('error')}")
            
        except Exception as e:
            log.error(f"Error starting priority orders: {e}")
    
    def _validate_inprogress_orders(self, db: Session):
        """
        Validate all InProgress orders.
        """
        try:
            # Get all InProgress orders
            inprogress_orders = db.query(ProcessOrder).filter(
                ProcessOrder.status == "InProgress"
            ).all()
            
            if not inprogress_orders:
                log.debug("No InProgress orders to validate")
                return
            
            log.info(f"Checking {len(inprogress_orders)} InProgress orders")
            
            for order in inprogress_orders:
                try:
                    self._validate_single_order(db, order)
                except Exception as e:
                    log.error(f"Error validating order {order.order_id}: {e}")
                    continue
                
        except Exception as e:
            log.error(f"Error validating InProgress orders: {e}")
    
    def _validate_single_order(self, db: Session, order):
        """Validate a single order."""
        po_number = order.order_id
        
        # Classify order
        classification = classify_order(order)
        
        if classification.get("error") and classification.get("confidence") == "LOW":
            log.warning(f"Cannot classify order {po_number}: {classification['error']}")
            return
        
        order_type = classification["order_type"]
        
        # Check completion status (pass db for auto-reset)
        completion = check_order_completion(order, classification, db=db)
        
        if completion.get("error"):
            log.warning(f"Cannot check completion for {po_number}: {completion['error']}")
            return
        
        actual_qty = completion["actual_qty"]
        target_qty = completion["target_qty"]
        variance_pct = completion["variance_pct"]
        is_complete = completion["is_complete"]
        within_tolerance = completion["within_tolerance"]
        
        log.info(
            f"[{po_number}] {order_type} - "
            f"Actual: {actual_qty} / Target: {target_qty} "
            f"({variance_pct:+.2f}%) - "
            f"Complete: {is_complete}, Tolerance: {within_tolerance}"
        )
        
        # Auto-validate if order is complete
        if is_complete:
            if within_tolerance:
                # PASS: Order validated successfully
                order.status = "Validated"
                order.validation_method = "Automatic"
                order.confirmed_qty = actual_qty
                order.confirmed_text = ""  # Leave empty unless user explicitly adds text
                
                log.info(f"✅ [{po_number}] VALIDATED - {actual_qty} {completion['unit']}")
                
                # TODO: Send confirmation to SAP
                # self._send_sap_confirmation(order, completion)
                
            else:
                # FAIL: Out of tolerance
                order.status = "Validation_Failed"
                order.confirmed_qty = actual_qty
                order.confirmed_text = ""  # Leave empty unless user explicitly adds text
                
                log.warning(f"❌ [{po_number}] FAILED - Out of tolerance ({variance_pct:+.2f}%)")
            
            db.add(order)
            
            # =============================================================================
            # RELEASE SCALES: Order completed, release scales for next order
            # =============================================================================
            try:
                all_scales = get_all_scales_for_order(order, classification, include_byproduct=True)
                released = release_scales(po_number, None)  # Release all scales for this order
                remove_from_queue(po_number)
                log.info(f"🔓 [{po_number}] Released scales after completion: {released}")
            except Exception as e:
                log.warning(f"⚠️ [{po_number}] Error releasing scales: {e}")
    
    def get_status(self) -> Dict[str, Any]:
        """Get current status of auto-validator."""
        thread_status = "unknown"
        if self.thread:
            thread_status = "alive" if self.thread.is_alive() else "dead"
        
        return {
            "is_running": self.is_running,
            "check_interval": self.check_interval,
            "thread_status": thread_status,
            "thread_alive": self.thread.is_alive() if self.thread else False
        }


# ============================================================================
# GLOBAL INSTANCE
# ============================================================================

_auto_validator_instance: Optional[AutoValidator] = None


def get_or_create_auto_validator(check_interval: int = 60) -> AutoValidator:
    """Get or create the global auto-validator instance."""
    global _auto_validator_instance
    
    if _auto_validator_instance is None:
        _auto_validator_instance = AutoValidator(check_interval=check_interval)
    
    return _auto_validator_instance


def get_auto_validator() -> Optional[AutoValidator]:
    """Get the global auto-validator instance."""
    return _auto_validator_instance


# Create a global instance for backward compatibility
# This will be initialized when the module is imported
auto_validator = None

def _initialize_auto_validator():
    """Initialize the global auto_validator instance."""
    global auto_validator
    if auto_validator is None:
        auto_validator = get_or_create_auto_validator()
    return auto_validator

# Initialize on import
_initialize_auto_validator()
