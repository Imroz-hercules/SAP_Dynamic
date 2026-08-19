"""
Scale Lock Service - Multi-Order Validation System

This service manages scale locking to prevent conflicts when multiple orders
are running simultaneously. It supports:
- FIFO queue logic based on priority (lower priority number = higher priority)
- Scale conflict detection for duplicate scales
- Product version conflict detection (same version = same scales)
- Partial validation (when orders share some scales but not all)
- No duplicate weight consumption across orders
- Real-time lock status and queue management

CRITICAL FEATURES (Dec 12, 2025):
1. Scale Locking for Duplicated Product Versions:
   - When multiple orders have the same product version, scales are locked
   - Highest priority order (lowest priority number) gets access first
   - Lower priority orders wait in queue

2. Scale Locking for Duplicated Scales:
   - When different orders use the same scales, priority logic applies
   - Same priority logic as duplicated product versions

3. Unified Priority Logic:
   - Priority = order.priority column (lower = higher priority)
   - If priority is same, order_id (numeric part) determines order
   - Priority 1 > Priority 2 > Priority 3 > ...
"""

from typing import Dict, List, Set, Optional, Tuple, Any
from threading import Lock
from datetime import datetime
import logging
import re

logger = logging.getLogger(__name__)

# Global registry: {scale_tag: order_id}
ACTIVE_SCALE_USAGE: Dict[str, str] = {}

# Thread-safe lock for scale registry operations
_scale_lock = Lock()

# Order queue: {order_id: {"status": "WAITING"|"RUNNING", "required_scales": [...], "priority": int, "version": str, "order_type": str}}
ORDER_QUEUE: Dict[str, Dict] = {}

# Version-to-order mapping: {version: [order_id1, order_id2, ...]}
# This helps detect duplicate product versions quickly
VERSION_REGISTRY: Dict[str, List[str]] = {}


def _extract_numeric_order_id(order_id: str) -> int:
    """
    Extract numeric portion from order_id for secondary sorting.
    Example: "1000023456" -> 1000023456
    """
    # Extract all digits from order_id
    digits = re.sub(r'\D', '', str(order_id))
    return int(digits) if digits else 0


def _compare_priority(order_a_info: Dict, order_b_info: Dict) -> int:
    """
    Compare two orders by priority.
    Returns:
        -1 if order_a has higher priority (should go first)
        +1 if order_b has higher priority
        0 if equal priority
    
    Priority Logic:
    1. Lower priority number = higher priority (1 > 2 > 3 > ...)
    2. If priority is same, lower order_id (numeric) = higher priority
    """
    priority_a = order_a_info.get("priority") if order_a_info.get("priority") is not None else 100
    priority_b = order_b_info.get("priority") if order_b_info.get("priority") is not None else 100
    
    # Lower priority number = higher priority
    if priority_a < priority_b:
        return -1  # order_a has higher priority
    elif priority_a > priority_b:
        return 1   # order_b has higher priority
    
    # Same priority - use order_id as tiebreaker
    order_id_a = _extract_numeric_order_id(order_a_info.get("order_id", ""))
    order_id_b = _extract_numeric_order_id(order_b_info.get("order_id", ""))
    
    if order_id_a < order_id_b:
        return -1
    elif order_id_a > order_id_b:
        return 1
    
    return 0


def register_order_version(order_id: str, version: str, order_type: str) -> None:
    """
    Register an order's version for duplicate detection.
    
    Args:
        order_id: Order ID
        version: Product version (e.g., "BKF1", "CKL1")
        order_type: "MILLING" or "PACKING"
    """
    global VERSION_REGISTRY
    
    if not version:
        return
    
    version_upper = version.upper().strip()
    version_key = f"{order_type}:{version_upper}"
    
    with _scale_lock:
        if version_key not in VERSION_REGISTRY:
            VERSION_REGISTRY[version_key] = []
        
        if order_id not in VERSION_REGISTRY[version_key]:
            VERSION_REGISTRY[version_key].append(order_id)
            logger.info(f"📋 Registered order {order_id} with version {version_key}")


def unregister_order_version(order_id: str, version: str = None, order_type: str = None) -> None:
    """
    Unregister an order's version when it completes.
    
    Args:
        order_id: Order ID
        version: Product version (optional - if None, removes from all versions)
        order_type: "MILLING" or "PACKING" (optional)
    """
    global VERSION_REGISTRY
    
    with _scale_lock:
        if version and order_type:
            version_key = f"{order_type}:{version.upper().strip()}"
            if version_key in VERSION_REGISTRY and order_id in VERSION_REGISTRY[version_key]:
                VERSION_REGISTRY[version_key].remove(order_id)
                if not VERSION_REGISTRY[version_key]:
                    del VERSION_REGISTRY[version_key]
                logger.debug(f"🗑️ Unregistered order {order_id} from version {version_key}")
        else:
            # Remove from all versions
            for version_key in list(VERSION_REGISTRY.keys()):
                if order_id in VERSION_REGISTRY[version_key]:
                    VERSION_REGISTRY[version_key].remove(order_id)
                    if not VERSION_REGISTRY[version_key]:
                        del VERSION_REGISTRY[version_key]


def get_orders_with_same_version(order_id: str, version: str, order_type: str) -> List[str]:
    """
    Get all orders with the same product version (excluding the given order).
    
    Args:
        order_id: Order ID to exclude
        version: Product version
        order_type: "MILLING" or "PACKING"
        
    Returns:
        List of order IDs with the same version
    """
    if not version:
        return []
    
    version_key = f"{order_type}:{version.upper().strip()}"
    
    with _scale_lock:
        orders = VERSION_REGISTRY.get(version_key, [])
        return [oid for oid in orders if oid != order_id]


def check_version_conflict(order_id: str, version: str, order_type: str, priority: int) -> Tuple[bool, Optional[str], List[str]]:
    """
    Check if there's a version conflict (another order with same version is running).
    
    Args:
        order_id: Order ID requesting to start
        version: Product version
        order_type: "MILLING" or "PACKING"
        priority: Order priority
        
    Returns:
        Tuple: (has_conflict, blocking_order_id, waiting_orders)
            - has_conflict: True if there's a higher priority order with same version
            - blocking_order_id: Order ID that's blocking (if any)
            - waiting_orders: List of orders waiting for same version
    """
    if not version:
        return False, None, []
    
    same_version_orders = get_orders_with_same_version(order_id, version, order_type)
    
    if not same_version_orders:
        return False, None, []
    
    # Check if any of these orders have higher priority
    with _scale_lock:
        current_order_info = {
            "order_id": order_id,
            "priority": priority
        }
        
        blocking_order = None
        waiting_orders = []
        
        for other_order_id in same_version_orders:
            other_info = ORDER_QUEUE.get(other_order_id, {})
            if not other_info:
                continue
            
            other_priority = other_info.get("priority") if other_info.get("priority") is not None else 100
            other_status = other_info.get("status", "WAITING")
            
            if other_status == "RUNNING":
                # Another order with same version is already running
                comparison = _compare_priority(
                    {"order_id": other_order_id, "priority": other_priority},
                    current_order_info
                )
                
                if comparison < 0:
                    # Other order has higher priority - current order should wait
                    blocking_order = other_order_id
                    break
                elif comparison > 0:
                    # Current order has higher priority - it can take over
                    # (The other order should be paused/waiting)
                    waiting_orders.append(other_order_id)
            else:
                waiting_orders.append(other_order_id)
        
        return blocking_order is not None, blocking_order, waiting_orders


def lock_scales(order_id: str, scale_list: List[str], priority: int = None, version: str = None, order_type: str = None) -> Tuple[bool, List[str], Dict[str, str], List[str]]:
    """
    Attempt to lock scales for an order with priority checking.
    
    Args:
        order_id: The order ID requesting the scales
        scale_list: List of scale tags required by the order
        priority: Order priority (lower = higher priority). If None, uses 100 as default.
        version: Product version for duplicate detection
        order_type: "MILLING" or "PACKING"
        
    Returns:
        tuple: (has_conflict, locked_scales, conflict_details, preempted_orders)
            - has_conflict: True if any required scale is locked by a higher-priority order
            - locked_scales: List of scales successfully locked
            - conflict_details: Dict of {scale: blocking_order_id} for conflicting scales
            - preempted_orders: List of order IDs that were preempted (lost their scales to higher priority)
    """
    global ACTIVE_SCALE_USAGE
    
    if priority is None:
        priority = 100
    
    # ✅ CRITICAL FIX: Ensure scale_list is a proper list, not a JSON string
    # This prevents iterating over characters if a string is accidentally passed
    if isinstance(scale_list, str):
        import json
        try:
            scale_list = json.loads(scale_list)
            logger.info(f"🔧 [lock_scales] Parsed scale_list string as JSON: {scale_list}")
        except json.JSONDecodeError:
            # If it's a comma-separated string, split it
            scale_list = [s.strip() for s in scale_list.split(",") if s.strip()]
            logger.info(f"🔧 [lock_scales] Parsed scale_list as comma-separated: {scale_list}")
    
    # Ensure scale_list is a list
    if not isinstance(scale_list, list):
        scale_list = [scale_list] if scale_list else []
    
    # Register version for duplicate detection
    if version and order_type:
        register_order_version(order_id, version, order_type)
    
    with _scale_lock:
        locked_scales = []
        has_conflict = False
        conflict_details = {}
        preempted_orders = set()  # Track orders that lost their scales
        
        current_order_info = {
            "order_id": order_id,
            "priority": priority
        }
        
        for scale in scale_list:
            if not scale:
                continue
                
            scale_upper = scale.upper().strip()
            
            # Check if scale is already in use by another order
            if scale_upper in ACTIVE_SCALE_USAGE:
                existing_order = ACTIVE_SCALE_USAGE[scale_upper]
                if existing_order != order_id:
                    # Get priority of existing order
                    existing_info = ORDER_QUEUE.get(existing_order, {})
                    existing_priority = existing_info.get("priority") if existing_info.get("priority") is not None else 100
                    
                    existing_order_info = {
                        "order_id": existing_order,
                        "priority": existing_priority
                    }
                    
                    # Compare priorities
                    comparison = _compare_priority(existing_order_info, current_order_info)
                    
                    if comparison < 0:
                        # Existing order has higher priority - conflict, current order should wait
                        has_conflict = True
                        conflict_details[scale_upper] = existing_order
                        logger.info(f"🔒 Scale {scale_upper} is locked by higher-priority order {existing_order} (priority {existing_priority}), order {order_id} (priority {priority}) must wait")
                        continue
                    elif comparison > 0:
                        # Current order has higher priority - take over the scale
                        logger.info(f"⬆️ Order {order_id} (priority {priority}) taking over scale {scale_upper} from lower-priority order {existing_order} (priority {existing_priority})")
                        # Track preempted order for notification/pause
                        preempted_orders.add(existing_order)
                    else:
                        # Same priority - existing order keeps the lock (FIFO)
                        has_conflict = True
                        conflict_details[scale_upper] = existing_order
                        logger.info(f"🔒 Scale {scale_upper} is locked by same-priority order {existing_order}, order {order_id} must wait (FIFO)")
                        continue
            
            # Scale is free or current order has higher priority - lock it
            ACTIVE_SCALE_USAGE[scale_upper] = order_id
            locked_scales.append(scale_upper)
            logger.debug(f"✅ Locked scale {scale_upper} for order {order_id}")
        
        if preempted_orders:
            logger.info(f"⚠️ Order {order_id}: Preempted {len(preempted_orders)} lower-priority order(s): {list(preempted_orders)}")
        
        if has_conflict:
            logger.info(f"⚠️ Order {order_id}: Partial lock - {len(locked_scales)}/{len(scale_list)} scales locked, conflicts: {conflict_details}")
        else:
            logger.info(f"✅ Order {order_id}: All {len(locked_scales)} scales locked successfully")
        
        return has_conflict, locked_scales, conflict_details, list(preempted_orders)


def release_scales(order_id: str, scale_list: Optional[List[str]] = None) -> List[str]:
    """
    Release scales locked by an order.
    
    Args:
        order_id: The order ID releasing the scales
        scale_list: Optional list of specific scales to release. If None, releases all scales for this order.
        
    Returns:
        List of released scale tags
    """
    global ACTIVE_SCALE_USAGE
    
    # ✅ CRITICAL FIX: Ensure scale_list is a proper list if provided
    if scale_list is not None and isinstance(scale_list, str):
        import json
        try:
            scale_list = json.loads(scale_list)
        except json.JSONDecodeError:
            scale_list = [s.strip() for s in scale_list.split(",") if s.strip()]
    
    with _scale_lock:
        released = []
        
        if scale_list:
            # Release specific scales
            for scale in scale_list:
                scale_upper = scale.upper().strip()
                if scale_upper in ACTIVE_SCALE_USAGE and ACTIVE_SCALE_USAGE[scale_upper] == order_id:
                    del ACTIVE_SCALE_USAGE[scale_upper]
                    released.append(scale_upper)
                    logger.debug(f"🔓 Released scale {scale_upper} from order {order_id}")
        else:
            # Release all scales for this order
            scales_to_release = [
                scale for scale, oid in ACTIVE_SCALE_USAGE.items()
                if oid == order_id
            ]
            for scale in scales_to_release:
                del ACTIVE_SCALE_USAGE[scale]
                released.append(scale)
            
            if released:
                logger.info(f"🔓 Released {len(released)} scales from order {order_id}: {released}")
        
        return released


def is_scale_available(scale: str, order_id: str) -> bool:
    """
    Check if a scale is available for use by an order.
    
    Args:
        scale: Scale tag to check
        order_id: Order ID requesting the scale
        
    Returns:
        True if scale is available (free or already locked by this order), False otherwise
    """
    with _scale_lock:
        scale_upper = scale.upper().strip()
        if scale_upper not in ACTIVE_SCALE_USAGE:
            return True
        return ACTIVE_SCALE_USAGE[scale_upper] == order_id


def get_scale_owner(scale: str) -> Optional[str]:
    """
    Get the order ID that currently owns a scale.
    
    Args:
        scale: Scale tag to check
        
    Returns:
        Order ID if scale is locked, None if free
    """
    with _scale_lock:
        scale_upper = scale.upper().strip()
        return ACTIVE_SCALE_USAGE.get(scale_upper)


def add_to_queue(order_id: str, required_scales: List[str], priority: int = 0, 
                  version: str = None, order_type: str = None) -> None:
    """
    Add an order to the queue with version tracking.
    
    Args:
        order_id: Order ID
        required_scales: List of required scale tags
        priority: Order priority (lower = higher priority, 1 = highest)
        version: Product version for duplicate detection
        order_type: "MILLING" or "PACKING"
    """
    global ORDER_QUEUE
    
    # ✅ CRITICAL FIX: Ensure required_scales is a proper list, not a JSON string
    if isinstance(required_scales, str):
        import json
        try:
            required_scales = json.loads(required_scales)
            logger.info(f"🔧 [add_to_queue] Parsed required_scales string as JSON: {required_scales}")
        except json.JSONDecodeError:
            # If it's a comma-separated string, split it
            required_scales = [s.strip() for s in required_scales.split(",") if s.strip()]
            logger.info(f"🔧 [add_to_queue] Parsed required_scales as comma-separated: {required_scales}")
    
    # Ensure required_scales is a list
    if not isinstance(required_scales, list):
        required_scales = [required_scales] if required_scales else []
    
    # Register version
    if version and order_type:
        register_order_version(order_id, version, order_type)
    
    with _scale_lock:
        ORDER_QUEUE[order_id] = {
            "status": "WAITING",
            "required_scales": [s.upper().strip() for s in required_scales if s and isinstance(s, str)],
            "priority": priority or 100,  # Default to 100 if not specified
            "version": version.upper().strip() if version else None,
            "order_type": order_type,
            "queued_at": datetime.now().isoformat()
        }
        logger.info(f"📋 Added order {order_id} to queue with priority {priority}, {len(required_scales)} scales, version={version}")


def remove_from_queue(order_id: str) -> None:
    """
    Remove an order from the queue and unregister its version.
    
    Args:
        order_id: Order ID to remove
    """
    global ORDER_QUEUE
    
    with _scale_lock:
        if order_id in ORDER_QUEUE:
            # Unregister version before removing
            order_info = ORDER_QUEUE[order_id]
            version = order_info.get("version")
            order_type = order_info.get("order_type")
            
            del ORDER_QUEUE[order_id]
            logger.debug(f"🗑️ Removed order {order_id} from queue")
    
    # Unregister version (outside the lock to avoid nested locking)
    if order_id:
        unregister_order_version(order_id)


def update_queue_status(order_id: str, status: str) -> None:
    """
    Update the status of an order in the queue.
    
    Args:
        order_id: Order ID
        status: New status ("WAITING" or "RUNNING")
    """
    global ORDER_QUEUE
    
    with _scale_lock:
        if order_id in ORDER_QUEUE:
            ORDER_QUEUE[order_id]["status"] = status
            logger.debug(f"📝 Updated order {order_id} status to {status}")


def get_waiting_orders() -> List[Dict]:
    """
    Get all orders in WAITING status, sorted by priority (ascending - lower = higher priority).
    
    Returns:
        List of order queue entries sorted by priority (highest priority first)
    """
    with _scale_lock:
        waiting = [
            {"order_id": oid, **info}
            for oid, info in ORDER_QUEUE.items()
            if info["status"] == "WAITING"
        ]
        
        # Sort by priority (ascending - lower number = higher priority)
        # Then by order_id as tiebreaker
        def sort_key(x):
            priority = x.get("priority") if x.get("priority") is not None else 100
            order_num = _extract_numeric_order_id(x.get("order_id", ""))
            return (priority, order_num)
        
        waiting.sort(key=sort_key)
        return waiting


def get_running_orders() -> List[Dict]:
    """
    Get all orders in RUNNING status.
    
    Returns:
        List of order queue entries that are currently running
    """
    with _scale_lock:
        running = [
            {"order_id": oid, **info}
            for oid, info in ORDER_QUEUE.items()
            if info["status"] == "RUNNING"
        ]
        return running


def get_orders_by_version(version: str, order_type: str) -> List[Dict]:
    """
    Get all orders with a specific version, sorted by priority.
    
    Args:
        version: Product version
        order_type: "MILLING" or "PACKING"
        
    Returns:
        List of order info dicts sorted by priority (highest first)
    """
    if not version:
        return []
    
    version_key = f"{order_type}:{version.upper().strip()}"
    
    with _scale_lock:
        order_ids = VERSION_REGISTRY.get(version_key, [])
        orders = []
        
        for oid in order_ids:
            if oid in ORDER_QUEUE:
                orders.append({"order_id": oid, **ORDER_QUEUE[oid]})
        
        # Sort by priority (ascending - lower = higher priority)
        def sort_key(x):
            priority = x.get("priority") if x.get("priority") is not None else 100
            order_num = _extract_numeric_order_id(x.get("order_id", ""))
            return (priority, order_num)
        
        orders.sort(key=sort_key)
        return orders


def get_orders_using_scale(scale: str) -> List[Dict]:
    """
    Get all orders that require a specific scale, sorted by priority.
    
    Args:
        scale: Scale tag to check
        
    Returns:
        List of order info dicts for orders using this scale
    """
    scale_upper = scale.upper().strip()
    
    with _scale_lock:
        orders = []
        
        for oid, info in ORDER_QUEUE.items():
            required_scales = info.get("required_scales", [])
            if scale_upper in required_scales:
                orders.append({"order_id": oid, **info})
        
        # Sort by priority (ascending - lower = higher priority)
        def sort_key(x):
            priority = x.get("priority") if x.get("priority") is not None else 100
            order_num = _extract_numeric_order_id(x.get("order_id", ""))
            return (priority, order_num)
        
        orders.sort(key=sort_key)
        return orders


def check_and_promote_waiting_orders() -> List[str]:
    """
    Check waiting orders and promote them to RUNNING if their scales are now available.
    Orders are processed in priority order (lowest priority number first).
    
    Returns:
        List of order IDs that were promoted
    """
    promoted = []
    waiting_orders = get_waiting_orders()  # Already sorted by priority
    
    for order_info in waiting_orders:
        order_id = order_info["order_id"]
        required_scales = order_info["required_scales"]
        priority = order_info.get("priority", 100)
        version = order_info.get("version")
        order_type = order_info.get("order_type")
        
        # Check if all required scales are now available
        all_available = True
        for scale in required_scales:
            if not is_scale_available(scale, order_id):
                all_available = False
                break
        
        # Also check for version conflicts
        version_conflict = False
        if version and order_type:
            has_version_conflict, blocking_order, _ = check_version_conflict(
                order_id, version, order_type, priority
            )
            if has_version_conflict:
                version_conflict = True
                logger.info(f"⚠️ Order {order_id} cannot be promoted - version conflict with {blocking_order}")
        
        if all_available and not version_conflict:
            # Try to lock all scales
            has_conflict, locked, _, preempted = lock_scales(
                order_id, required_scales, priority, version, order_type
            )
            
            if not has_conflict and len(locked) == len(required_scales):
                # All scales locked successfully - promote to RUNNING
                update_queue_status(order_id, "RUNNING")
                promoted.append(order_id)
                logger.info(f"🚀 Promoted order {order_id} (priority {priority}) from WAITING to RUNNING")
    
    return promoted


def check_scale_conflicts_for_order(order_id: str, scale_list: List[str], priority: int, 
                                     version: str = None, order_type: str = None) -> Dict[str, Any]:
    """
    Check all potential conflicts for an order before starting.
    
    Args:
        order_id: Order ID
        scale_list: Required scales
        priority: Order priority
        version: Product version
        order_type: "MILLING" or "PACKING"
        
    Returns:
        Dict with conflict information:
        {
            "can_start": bool,
            "scale_conflicts": {scale: blocking_order},
            "version_conflicts": [blocking_orders],
            "waiting_orders": [orders_that_will_wait],
            "message": str
        }
    """
    result = {
        "can_start": True,
        "scale_conflicts": {},
        "version_conflicts": [],
        "waiting_orders": [],
        "message": None
    }
    
    # Check scale conflicts
    with _scale_lock:
        current_order_info = {"order_id": order_id, "priority": priority}
        
        for scale in scale_list:
            if not scale:
                continue
            scale_upper = scale.upper().strip()
            
            if scale_upper in ACTIVE_SCALE_USAGE:
                existing_order = ACTIVE_SCALE_USAGE[scale_upper]
                if existing_order != order_id:
                    existing_info = ORDER_QUEUE.get(existing_order, {})
                    existing_priority = existing_info.get("priority") if existing_info.get("priority") is not None else 100
                    
                    comparison = _compare_priority(
                        {"order_id": existing_order, "priority": existing_priority},
                        current_order_info
                    )
                    
                    if comparison <= 0:
                        # Existing order has higher or equal priority
                        result["scale_conflicts"][scale_upper] = existing_order
                        result["can_start"] = False
    
    # Check version conflicts
    if version and order_type:
        has_version_conflict, blocking_order, waiting = check_version_conflict(
            order_id, version, order_type, priority
        )
        if has_version_conflict:
            result["version_conflicts"].append(blocking_order)
            result["can_start"] = False
        result["waiting_orders"] = waiting
    
    # Build message
    if not result["can_start"]:
        messages = []
        if result["scale_conflicts"]:
            conflicts = ", ".join(f"{s} (by {o})" for s, o in result["scale_conflicts"].items())
            messages.append(f"Scale conflicts: {conflicts}")
        if result["version_conflicts"]:
            messages.append(f"Version conflict with: {', '.join(result['version_conflicts'])}")
        result["message"] = "; ".join(messages)
    else:
        if result["waiting_orders"]:
            result["message"] = f"Can start, {len(result['waiting_orders'])} order(s) will wait"
    
    return result


def get_scale_usage_status() -> Dict:
    """
    Get comprehensive scale usage status for monitoring and UI display.
    
    Returns:
        Dictionary with scale usage, queue information, and version conflicts
    """
    with _scale_lock:
        # Build detailed queue info with priority sorting
        queue_details = []
        for order_id, info in ORDER_QUEUE.items():
            queue_details.append({
                "order_id": order_id,
                "status": info.get("status"),
                "priority": info.get("priority", 100),
                "version": info.get("version"),
                "order_type": info.get("order_type"),
                "required_scales": info.get("required_scales", []),
                "queued_at": info.get("queued_at")
            })
        
        # Sort by priority (ascending) then order_id
        def sort_key(x):
            priority = x.get("priority") if x.get("priority") is not None else 100
            order_num = _extract_numeric_order_id(x.get("order_id", ""))
            return (priority, order_num)
        
        queue_details.sort(key=sort_key)
        
        # Build version conflict summary
        version_conflicts = {}
        for version_key, order_ids in VERSION_REGISTRY.items():
            if len(order_ids) > 1:
                version_conflicts[version_key] = order_ids
        
        # Build scale-to-orders mapping
        scale_to_orders = {}
        for order_id, info in ORDER_QUEUE.items():
            for scale in info.get("required_scales", []):
                if scale not in scale_to_orders:
                    scale_to_orders[scale] = []
                scale_to_orders[scale].append({
                    "order_id": order_id,
                    "priority": info.get("priority", 100),
                    "status": info.get("status")
                })
        
        # Detect scale conflicts (multiple orders need same scale)
        scale_conflicts = {s: orders for s, orders in scale_to_orders.items() if len(orders) > 1}
        
        return {
            "active_scales": dict(ACTIVE_SCALE_USAGE),
            "queue": queue_details,
            "total_locked_scales": len(ACTIVE_SCALE_USAGE),
            "total_queued_orders": len(ORDER_QUEUE),
            "running_orders": len([o for o in ORDER_QUEUE.values() if o.get("status") == "RUNNING"]),
            "waiting_orders": len([o for o in ORDER_QUEUE.values() if o.get("status") == "WAITING"]),
            "version_conflicts": version_conflicts,
            "scale_conflicts": scale_conflicts,
            "version_registry": dict(VERSION_REGISTRY)
        }


def get_lock_status_for_order(order_id: str) -> Dict[str, Any]:
    """
    Get lock status details for a specific order.
    
    Args:
        order_id: Order ID
        
    Returns:
        Dict with lock status information
    """
    with _scale_lock:
        if order_id not in ORDER_QUEUE:
            return {
                "order_id": order_id,
                "in_queue": False,
                "status": None,
                "locked_scales": [],
                "waiting_for_scales": [],
                "blocking_orders": []
            }
        
        order_info = ORDER_QUEUE[order_id]
        required_scales = order_info.get("required_scales", [])
        
        locked_scales = []
        waiting_for_scales = []
        blocking_orders = set()
        
        for scale in required_scales:
            if scale in ACTIVE_SCALE_USAGE:
                owner = ACTIVE_SCALE_USAGE[scale]
                if owner == order_id:
                    locked_scales.append(scale)
                else:
                    waiting_for_scales.append(scale)
                    blocking_orders.add(owner)
            else:
                waiting_for_scales.append(scale)
        
        return {
            "order_id": order_id,
            "in_queue": True,
            "status": order_info.get("status"),
            "priority": order_info.get("priority", 100),
            "version": order_info.get("version"),
            "order_type": order_info.get("order_type"),
            "locked_scales": locked_scales,
            "waiting_for_scales": waiting_for_scales,
            "blocking_orders": list(blocking_orders),
            "queued_at": order_info.get("queued_at")
        }


def set_order_running(order_id: str) -> bool:
    """
    Mark an order as RUNNING in the queue.
    
    Args:
        order_id: Order ID
        
    Returns:
        True if successfully updated, False if order not in queue
    """
    global ORDER_QUEUE
    
    with _scale_lock:
        if order_id in ORDER_QUEUE:
            ORDER_QUEUE[order_id]["status"] = "RUNNING"
            logger.info(f"▶️ Order {order_id} marked as RUNNING")
            return True
        return False


# =============================================================================
# CONFLICT GROUP DETECTION (Dec 13, 2025)
# =============================================================================

def get_conflict_groups_for_orders(orders_data: List[Dict]) -> Dict:
    """
    Detect conflict groups for a list of orders.
    
    Conflict occurs when:
    1. Orders have the SAME VERSION (same version = same scales)
    2. Orders have DIFFERENT versions but SHARE any scale
    
    Each conflict group has its own independent priority numbering (1, 2, 3...).
    Orders without conflicts show no priority number.
    
    Args:
        orders_data: List of dicts with keys: order_id, version, scales (list), order_type, priority, status
        
    Returns:
        {
            "conflict_groups": [
                {
                    "group_id": 1,
                    "orders": ["16041", "16047", "16030"],  # Sorted by priority
                    "shared_scales": ["WG501", "WG503"],
                    "priority_order": {"16041": 1, "16047": 2, "16030": 3}
                }
            ],
            "order_conflict_info": {
                "16041": {"has_conflict": True, "group_id": 1, "group_priority": 1, "can_run": True, ...},
                "16047": {"has_conflict": True, "group_id": 1, "group_priority": 2, "can_run": False, ...},
                "16037": {"has_conflict": False}
            }
        }
    """
    logger.info(f"🔍 [get_conflict_groups_for_orders] Analyzing {len(orders_data)} orders for conflicts")
    
    # Log each order's scales for debugging
    for order_data in orders_data:
        logger.info(f"   📦 Order {order_data.get('order_id')}: version={order_data.get('version')}, scales={order_data.get('scales')}, type={order_data.get('order_type')}")
    
    # Separate orders by type (MILLING and PACKING use different scales)
    milling_orders = [o for o in orders_data if o.get("order_type") == "MILLING"]
    packing_orders = [o for o in orders_data if o.get("order_type") == "PACKING"]
    
    logger.info(f"   📊 MILLING orders: {len(milling_orders)}, PACKING orders: {len(packing_orders)}")
    
    # Process conflicts separately for each type
    milling_result = _detect_conflicts_for_order_type(milling_orders)
    packing_result = _detect_conflicts_for_order_type(packing_orders)
    
    # Merge results - renumber group_ids for packing to be unique
    all_conflict_groups = milling_result["conflict_groups"].copy()
    max_group_id = len(all_conflict_groups)
    
    for group in packing_result["conflict_groups"]:
        group["group_id"] = max_group_id + group["group_id"]
        all_conflict_groups.append(group)
    
    # Merge order conflict info
    all_order_info = {**milling_result["order_conflict_info"]}
    for order_id, info in packing_result["order_conflict_info"].items():
        if info.get("has_conflict") and "group_id" in info:
            info["group_id"] = max_group_id + info["group_id"]
        all_order_info[order_id] = info
    
    # Add orders that weren't in either list (shouldn't happen, but safety)
    for order_data in orders_data:
        order_id = order_data.get("order_id")
        if order_id and order_id not in all_order_info:
            all_order_info[order_id] = {"has_conflict": False}
    
    return {
        "conflict_groups": all_conflict_groups,
        "order_conflict_info": all_order_info
    }


def _detect_conflicts_for_order_type(orders_data: List[Dict]) -> Dict:
    """
    Detect conflicts within a single order type (MILLING or PACKING).
    Uses union-find algorithm to group orders that share scales.
    
    Args:
        orders_data: List of order data dicts for one order type
        
    Returns:
        Dict with conflict_groups and order_conflict_info
    """
    if not orders_data:
        logger.info(f"   ⚠️ [_detect_conflicts_for_order_type] No orders to analyze")
        return {"conflict_groups": [], "order_conflict_info": {}}
    
    logger.info(f"   🔎 [_detect_conflicts_for_order_type] Analyzing {len(orders_data)} orders")
    
    # Build mappings
    scale_to_orders: Dict[str, List[str]] = {}
    order_to_scales: Dict[str, List[str]] = {}
    order_to_priority: Dict[str, int] = {}
    order_to_status: Dict[str, str] = {}
    
    for order_data in orders_data:
        order_id = str(order_data.get("order_id", ""))
        scales = order_data.get("scales", []) or []
        priority = order_data.get("priority") if order_data.get("priority") is not None else 100
        status = order_data.get("status", "Pending")
        
        # Normalize scales
        normalized_scales = [s.upper().strip() for s in scales if s and isinstance(s, str)]
        
        order_to_scales[order_id] = normalized_scales
        order_to_priority[order_id] = priority
        order_to_status[order_id] = status
        
        for scale in normalized_scales:
            if scale not in scale_to_orders:
                scale_to_orders[scale] = []
            if order_id not in scale_to_orders[scale]:
                scale_to_orders[scale].append(order_id)
    
    # Log scale-to-orders mapping for debugging
    logger.info(f"   📊 Scale-to-orders mapping:")
    for scale, order_ids in scale_to_orders.items():
        if len(order_ids) > 1:
            logger.info(f"      ⚠️ CONFLICT: Scale {scale} used by: {order_ids}")
        else:
            logger.info(f"      ✅ Scale {scale} used by: {order_ids}")
    
    # Union-Find to merge orders into conflict groups
    parent: Dict[str, str] = {oid: oid for oid in order_to_scales.keys()}
    
    def find(x: str) -> str:
        if parent[x] != x:
            parent[x] = find(parent[x])  # Path compression
        return parent[x]
    
    def union(x: str, y: str) -> None:
        px, py = find(x), find(y)
        if px != py:
            parent[px] = py
    
    # Union orders that share any scale
    for scale, order_ids in scale_to_orders.items():
        if len(order_ids) > 1:
            first = order_ids[0]
            for other in order_ids[1:]:
                union(first, other)
    
    # Group orders by their root
    groups: Dict[str, List[str]] = {}
    for order_id in order_to_scales.keys():
        root = find(order_id)
        if root not in groups:
            groups[root] = []
        groups[root].append(order_id)
    
    # Build conflict groups (only groups with more than 1 order)
    conflict_groups = []
    order_conflict_info = {}
    group_id = 0
    
    for root, order_ids in groups.items():
        if len(order_ids) > 1:
            group_id += 1
            
            # Find shared scales for this group
            shared_scales = set()
            for scale, scale_order_ids in scale_to_orders.items():
                # Count how many orders in this group use this scale
                orders_using_scale = [o for o in scale_order_ids if o in order_ids]
                if len(orders_using_scale) > 1:
                    shared_scales.add(scale)
            
            # Sort orders by priority (lower = higher priority), then by order_id numeric
            sorted_orders = sorted(order_ids, key=lambda o: (
                order_to_priority.get(o, 100),
                _extract_numeric_order_id(o)
            ))
            
            # Assign group-relative priority (1, 2, 3...)
            priority_order = {oid: idx + 1 for idx, oid in enumerate(sorted_orders)}
            
            conflict_groups.append({
                "group_id": group_id,
                "orders": sorted_orders,
                "shared_scales": list(shared_scales),
                "priority_order": priority_order
            })
            
            # Build per-order conflict info
            for idx, order_id in enumerate(sorted_orders):
                can_run = (idx == 0)  # Only first order (highest priority) can run
                waiting_for = sorted_orders[:idx] if idx > 0 else []
                
                order_conflict_info[order_id] = {
                    "has_conflict": True,
                    "group_id": group_id,
                    "group_priority": priority_order[order_id],
                    "can_run": can_run,
                    "waiting_for": waiting_for,
                    "shared_scales": list(shared_scales),
                    "shared_with": [o for o in sorted_orders if o != order_id],
                    "status": order_to_status.get(order_id, "Pending")
                }
        else:
            # Single order - no conflict
            order_id = order_ids[0]
            order_conflict_info[order_id] = {
                "has_conflict": False,
                "status": order_to_status.get(order_id, "Pending")
            }
    
    # Log results
    logger.info(f"   📊 Conflict detection complete: {len(conflict_groups)} conflict group(s) found")
    for group in conflict_groups:
        logger.info(f"      🔒 Group {group['group_id']}: orders={group['orders']}, shared_scales={group['shared_scales']}")
        for oid, prio in group['priority_order'].items():
            can_run = "CAN RUN" if prio == 1 else "WAITING"
            logger.info(f"         - {oid}: priority={prio} ({can_run})")
    
    return {
        "conflict_groups": conflict_groups,
        "order_conflict_info": order_conflict_info
    }


def clear_all_scale_locks() -> int:
    """
    Clear all scale locks and queue entries. Used for cleanup/reset.
    
    Returns:
        Number of locks cleared
    """
    global ACTIVE_SCALE_USAGE, ORDER_QUEUE, VERSION_REGISTRY
    
    with _scale_lock:
        count = len(ACTIVE_SCALE_USAGE)
        ACTIVE_SCALE_USAGE.clear()
        ORDER_QUEUE.clear()
        VERSION_REGISTRY.clear()
        logger.info(f"🧹 Cleared all scale locks ({count} scales, {len(ORDER_QUEUE)} queue entries)")
        return count


# =============================================================================
# PRIORITY RECALCULATION (Jan 26, 2026)
# =============================================================================

def recalculate_conflict_group_priorities(db_session=None) -> Dict:
    """
    Recalculate priorities for all active orders based on conflict groups.
    
    This function:
    1. Detects all conflict groups for InProgress/Pending/Paused orders
    2. Assigns sequential priorities within each group (1, 2, 3...)
    3. Orders with no conflicts get priority = 1
    
    Call this on: SAP sync, order completion, drag-and-drop
    
    Args:
        db_session: Optional SQLAlchemy session. If None, creates a new session.
        
    Returns:
        Dict with updated_count and details
    """
    from database import _db_session
    from models import ProcessOrder
    from routes.order_validation import classify_order, get_all_scales_for_order, get_attr_safe, set_attr_safe
    
    logger.info("🔄 [RECALC] Recalculating conflict group priorities...")
    
    result = {
        "updated_count": 0,
        "orders_updated": [],
        "conflict_groups": [],
        "errors": []
    }
    
    try:
        # Use provided session or create new one
        if db_session:
            db = db_session
            should_close = False
        else:
            db = _db_session().__enter__()
            should_close = True
        
        try:
            # Get all active orders (not Validated, not Rejected, not Cancelled)
            active_statuses = ["InProgress", "Pending", "Paused"]
            orders = db.query(ProcessOrder).filter(
                ProcessOrder.status.in_(active_statuses)
            ).all()
            
            if not orders:
                logger.info("🔄 [RECALC] No active orders to recalculate")
                return result
            
            logger.info(f"🔄 [RECALC] Found {len(orders)} active orders")
            
            # Build order data for conflict detection
            orders_data = []
            order_objects = {}
            
            for order in orders:
                po_number = order.order_id
                classification = classify_order(order)
                
                if classification.get("error"):
                    result["errors"].append(f"{po_number}: {classification['error']}")
                    continue
                
                all_scales = get_all_scales_for_order(order, classification, include_byproduct=True)
                
                # Use current hercules_priority for initial sorting within groups
                current_priority = get_attr_safe(order, "hercules_priority") or get_attr_safe(order, "priority")
                current_priority = int(current_priority) if current_priority is not None else 999
                
                orders_data.append({
                    "order_id": po_number,
                    "version": get_attr_safe(order, "version", ""),
                    "scales": all_scales,
                    "order_type": classification.get("order_type"),
                    "priority": current_priority,
                    "status": order.status
                })
                order_objects[po_number] = order
            
            # Detect conflict groups
            conflict_info = get_conflict_groups_for_orders(orders_data)
            result["conflict_groups"] = conflict_info["conflict_groups"]
            
            logger.info(f"🔄 [RECALC] Detected {len(conflict_info['conflict_groups'])} conflict groups")
            
            # Update priorities based on conflict groups
            for po_number, order_data in order_objects.items():
                order = order_data
                conflict = conflict_info["order_conflict_info"].get(po_number, {"has_conflict": False})
                
                if conflict.get("has_conflict"):
                    # Order is in a conflict group - use group_priority
                    new_priority = conflict.get("group_priority", 1)
                else:
                    # Order has no conflicts - priority = 1 (runs immediately)
                    new_priority = 1
                
                # Get current hercules_priority
                current_priority = get_attr_safe(order, "hercules_priority") or get_attr_safe(order, "priority")
                current_priority = int(current_priority) if current_priority is not None else 999
                
                # Update if different (write to hercules_priority)
                if current_priority != new_priority:
                    set_attr_safe(order, "hercules_priority", new_priority)
                    db.add(order)
                    result["updated_count"] += 1
                    result["orders_updated"].append({
                        "order_id": po_number,
                        "old_priority": current_priority,
                        "new_priority": new_priority,
                        "has_conflict": conflict.get("has_conflict", False)
                    })
                    logger.info(f"🔄 [RECALC] {po_number}: priority {current_priority} -> {new_priority}")
            
            db.commit()
            logger.info(f"🔄 [RECALC] Updated {result['updated_count']} orders")
            
        finally:
            if should_close:
                db.close()
                
    except Exception as e:
        logger.error(f"❌ [RECALC] Error recalculating priorities: {e}")
        import traceback
        traceback.print_exc()
        result["errors"].append(str(e))
    
    return result