"""
Emulator API Routes
===================
REST API endpoints for controlling the embedded SCADA emulator.
"""

from flask import Blueprint, request, jsonify
import logging

log = logging.getLogger("emulator_routes")

emulator_bp = Blueprint("emulator", __name__, url_prefix="/api/emulator")

# Lazy import helper to avoid circular imports
_emulator = None
def get_emulator_instance():
    global _emulator
    if _emulator is None:
        from services.embedded_emulator import get_emulator
        _emulator = get_emulator()
    return _emulator


# Simple test endpoint
@emulator_bp.route("/test", methods=["GET"])
def test_endpoint():
    """Simple test endpoint that returns immediately."""
    return jsonify({"status": "ok", "message": "Test endpoint works!"})


# =============================================================================
# Emulator Status & Control
# =============================================================================

@emulator_bp.route("/status", methods=["GET"])
def get_status():
    """Get emulator status and configuration."""
    log.info("=== /status endpoint called ===")
    try:
        emulator = get_emulator_instance()
        log.info("Got emulator instance, calling get_status...")
        result = emulator.get_status()
        log.info(f"Got status: running={result.get('running')}")
        return jsonify(result)
    except Exception as e:
        log.error(f"Error getting emulator status: {e}")
        return jsonify({"error": str(e)}), 500


@emulator_bp.route("/start", methods=["POST"])
def start_emulator():
    """Start the emulator worker thread."""
    log.info("=== /start endpoint called ===")
    try:
        emulator = get_emulator_instance()
        result = emulator.start()
        return jsonify(result)
    except Exception as e:
        log.error(f"Error starting emulator: {e}")
        return jsonify({"error": str(e)}), 500


@emulator_bp.route("/stop", methods=["POST"])
def stop_emulator():
    """Stop the emulator worker thread."""
    try:
        from services.embedded_emulator import get_emulator
        emulator = get_emulator()
        result = emulator.stop()
        log.info(f"Emulator stop result: {result}")
        return jsonify(result)
    except Exception as e:
        log.error(f"Error stopping emulator: {e}")
        return jsonify({"error": str(e)}), 500


@emulator_bp.route("/tick", methods=["POST"])
def manual_tick():
    """Manually trigger one data generation tick."""
    try:
        from services.embedded_emulator import get_emulator
        emulator = get_emulator()
        result = emulator.generate_tick()
        return jsonify(result)
    except Exception as e:
        log.error(f"Error generating tick: {e}")
        return jsonify({"error": str(e)}), 500


# =============================================================================
# Configuration
# =============================================================================

@emulator_bp.route("/config", methods=["GET"])
def get_config():
    """Get emulator configuration."""
    log.info("=== /config GET endpoint called ===")
    try:
        emulator = get_emulator_instance()
        log.info("Got emulator instance, calling get_config...")
        result = emulator.get_config()
        log.info(f"Got config: {result}")
        return jsonify(result)
    except Exception as e:
        log.error(f"Error getting config: {e}")
        return jsonify({"error": str(e)}), 500


@emulator_bp.route("/config", methods=["PUT"])
def update_config():
    """Update emulator configuration."""
    try:
        from services.embedded_emulator import get_emulator
        from models.system_settings import set_setting
        
        emulator = get_emulator()
        data = request.get_json() or {}
        log.info(f"Config update request: {data}")
        
        # Save to DB for persistence
        if "interval" in data:
            set_setting("emulator_interval", data["interval"], "float")
        if "step_min" in data:
            set_setting("emulator_step_min", data["step_min"], "float")
        if "step_max" in data:
            set_setting("emulator_step_max", data["step_max"], "float")
            
        result = emulator.set_config(
            interval=data.get("interval"),
            step_min=data.get("step_min"),
            step_max=data.get("step_max"),
            jitter=data.get("jitter"),
        )
        log.info(f"Config update result: {result}")
        return jsonify(result)
    except Exception as e:
        log.error(f"Error updating config: {e}")
        return jsonify({"error": str(e)}), 500


# =============================================================================
# Scale Control
# =============================================================================

@emulator_bp.route("/scales", methods=["GET"])
def get_scales():
    """Get all scales with their values and active status."""
    log.info("=== /scales GET endpoint called ===")
    try:
        emulator = get_emulator_instance()
        log.info("Got emulator instance, calling get_scales_status...")
        result = emulator.get_scales_status()
        log.info(f"Got scales: {result.get('active_count', 0)} active")
        return jsonify(result)
    except Exception as e:
        log.error(f"Error getting scales: {e}")
        return jsonify({"error": str(e)}), 500


@emulator_bp.route("/scales/<scale>", methods=["PUT"])
def toggle_scale(scale: str):
    """Toggle a single scale on/off."""
    try:
        from services.embedded_emulator import get_emulator
        emulator = get_emulator()
        data = request.get_json() or {}
        active = data.get("active", True)
        
        success = emulator.set_scale_active(scale, active)
        if success:
            return jsonify({"status": "ok", "scale": scale, "active": active})
        else:
            return jsonify({"error": f"Scale {scale} not found"}), 404
    except Exception as e:
        log.error(f"Error toggling scale: {e}")
        return jsonify({"error": str(e)}), 500


@emulator_bp.route("/scales/bulk", methods=["PUT"])
def bulk_update_scales():
    """Bulk update scale activation."""
    try:
        from services.embedded_emulator import get_emulator
        emulator = get_emulator()
        data = request.get_json() or {}
        log.info(f"Bulk update request: {data}")
        
        result = emulator.set_scales_bulk(
            on=data.get("on"),
            off=data.get("off"),
            set_all=data.get("set_all"),
        )
        log.info(f"Bulk update result: {result}")
        return jsonify(result)
    except Exception as e:
        log.error(f"Error bulk updating scales: {e}")
        return jsonify({"error": str(e)}), 500


@emulator_bp.route("/category/<category>", methods=["PUT"])
def toggle_category(category: str):
    """Enable/disable all scales in a category."""
    try:
        from services.embedded_emulator import get_emulator
        emulator = get_emulator()
        data = request.get_json() or {}
        active = data.get("active", True)
        
        success = emulator.set_category_active(category, active)
        if success:
            return jsonify({"status": "ok", "category": category, "active": active})
        else:
            return jsonify({"error": f"Category {category} not found"}), 404
    except Exception as e:
        log.error(f"Error toggling category: {e}")
        return jsonify({"error": str(e)}), 500


# =============================================================================
# Reset Functions
# =============================================================================

@emulator_bp.route("/reset/zero", methods=["POST"])
def reset_to_zero():
    """Reset all emulator values to zero and refresh baselines for in-progress orders."""
    try:
        from services.embedded_emulator import get_emulator
        emulator = get_emulator()
        result = emulator.reset_to_zero()
        
        # ✅ CRITICAL FIX: Refresh baselines for all in-progress orders
        # This prevents orders from getting stuck when current < baseline after emulator reset
        refresh_result = _refresh_inprogress_order_baselines()
        result["baselines_refreshed"] = refresh_result
        
        return jsonify(result)
    except Exception as e:
        log.error(f"Error resetting to zero: {e}")
        return jsonify({"error": str(e)}), 500


def _refresh_inprogress_order_baselines():
    """
    Refresh baselines for all in-progress orders to current SCADA values.
    This should be called after emulator reset to prevent orders from getting stuck.
    
    Returns:
        Dict with refresh results
    """
    import time
    from sqlalchemy.orm import sessionmaker
    from database import postgres_engine
    from services.scale_service import get_multiple_scada_readings, get_attr_safe, set_attr_safe
    
    try:
        from models.process_order_pg import ProcessOrderPG as ProcessOrder
    except Exception as e:
        log.error(f"Failed to import ProcessOrder: {e}")
        return {"error": str(e), "orders_refreshed": 0}
    
    PostgresSessionLocal = sessionmaker(
        bind=postgres_engine, autoflush=False, autocommit=False, future=True
    )
    
    refreshed_orders = []
    errors = []
    
    try:
        db = PostgresSessionLocal()
        
        # Find all in-progress orders
        inprogress_orders = db.query(ProcessOrder).filter(
            ProcessOrder.status == "InProgress"
        ).all()
        
        log.info(f"🔄 [Emulator Reset] Found {len(inprogress_orders)} in-progress orders to refresh baselines")
        
        # Wait a moment for emulator values to settle after reset
        time.sleep(0.5)
        
        for order in inprogress_orders:
            try:
                po_number = order.order_id
                order_type = get_attr_safe(order, "order_type", "UNKNOWN")
                current_shift = get_attr_safe(order, "current_shift", "A")
                
                # Get equipment list based on order type
                # This is stored in the classification or we need to derive it
                equipment = _get_order_equipment(order)
                
                if not equipment:
                    log.warning(f"⚠️ [{po_number}] No equipment found, skipping baseline refresh")
                    errors.append({"order_id": po_number, "error": "No equipment found"})
                    continue
                
                # Capture fresh baselines from current SCADA (should be 0 or near 0 after reset)
                log.info(f"🔄 [{po_number}] Capturing fresh baselines for equipment: {equipment}")
                fresh_baselines = get_multiple_scada_readings(equipment)
                log.info(f"🔄 [{po_number}] SCADA readings received: {fresh_baselines}")
                
                if not fresh_baselines or len(fresh_baselines) == 0:
                    log.warning(f"⚠️ [{po_number}] Failed to capture fresh baselines - empty response")
                    errors.append({"order_id": po_number, "error": "Failed to capture baselines - empty response", "equipment": equipment})
                    continue
                
                # Update individual baseline columns
                for tag in equipment:
                    reading = fresh_baselines.get(tag)
                    if reading is not None:
                        if isinstance(reading, dict):
                            baseline_val = float(reading.get('current', 0.0) or 0.0)
                        else:
                            baseline_val = float(reading or 0.0)
                        
                        baseline_attr = f"baseline_{tag.lower()}"
                        old_val = float(get_attr_safe(order, baseline_attr, 0.0) or 0.0)
                        set_attr_safe(order, baseline_attr, baseline_val)
                        log.info(f"✅ [{po_number}] {tag}: Refreshed baseline from {old_val:.2f} to {baseline_val:.2f}")
                
                # Update shift baseline dictionary
                shift_baseline_field = f"baseline_shift_{current_shift.lower()}_start"
                fresh_baseline_dict = {}
                for tag in equipment:
                    reading = fresh_baselines.get(tag)
                    if reading is not None:
                        if isinstance(reading, dict):
                            fresh_baseline_dict[tag] = float(reading.get('current', 0.0) or 0.0)
                        else:
                            fresh_baseline_dict[tag] = float(reading or 0.0)
                
                set_attr_safe(order, shift_baseline_field, fresh_baseline_dict)
                
                # Commit changes for this order
                db.add(order)
                db.commit()
                db.refresh(order)
                
                refreshed_orders.append({
                    "order_id": po_number,
                    "order_type": order_type,
                    "equipment": equipment,
                    "new_baselines": fresh_baseline_dict
                })
                
                log.info(f"✅ [{po_number}] Baselines refreshed successfully: {fresh_baseline_dict}")
                
            except Exception as e:
                log.error(f"❌ Error refreshing baselines for order {order.order_id}: {e}")
                errors.append({"order_id": order.order_id, "error": str(e)})
                db.rollback()
        
        db.close()
        
        log.info(f"✅ [Emulator Reset] Refreshed baselines for {len(refreshed_orders)} orders")
        
        return {
            "orders_refreshed": len(refreshed_orders),
            "refreshed_orders": refreshed_orders,
            "errors": errors if errors else None
        }
        
    except Exception as e:
        log.error(f"❌ Error in _refresh_inprogress_order_baselines: {e}")
        import traceback
        traceback.print_exc()
        return {"error": str(e), "orders_refreshed": 0}


def _get_order_equipment(order):
    """
    Get the full equipment list for an order including byproduct scales.
    Uses the same logic as classify_order to get all scales.
    """
    from services.scale_service import get_attr_safe
    
    order_type = get_attr_safe(order, "order_type", "").upper()
    version = get_attr_safe(order, "version", "").upper().strip()
    
    if not version:
        return []
    
    all_scales = []
    
    # Try to get equipment from milling_version_mappings table
    if order_type == "MILLING":
        try:
            from sqlalchemy.orm import sessionmaker
            from database import postgres_engine
            from models.milling_version_mapping import MillingVersionMapping
            
            PostgresSessionLocal = sessionmaker(
                bind=postgres_engine, autoflush=False, autocommit=False, future=True
            )
            
            with PostgresSessionLocal() as db:
                mapping = db.query(MillingVersionMapping).filter(
                    MillingVersionMapping.version == version
                ).first()
                
                if mapping:
                    # Get main scales from mapping
                    if mapping.scales:
                        # scales can be stored as JSON string or comma-separated
                        scales_str = str(mapping.scales)
                        if scales_str.startswith("["):
                            # JSON format
                            import json
                            try:
                                scales = json.loads(scales_str)
                            except:
                                scales = [s.strip() for s in scales_str.split(",") if s.strip()]
                        else:
                            scales = [s.strip() for s in scales_str.split(",") if s.strip()]
                        all_scales.extend(scales)
                    
                    # Get byproduct scales from mapping (scale1, scale2, scale3)
                    if mapping.scale1:
                        all_scales.append(str(mapping.scale1).strip())
                    if mapping.scale2:
                        all_scales.append(str(mapping.scale2).strip())
                    if mapping.scale3:
                        all_scales.append(str(mapping.scale3).strip())
        except Exception as e:
            log.warning(f"Failed to get equipment from milling_version_mappings: {e}")
        
        # Also get byproduct scales directly from order (they may have been set during order start)
        for scale_attr in ["scale1", "scale2", "scale3"]:
            scale_val = get_attr_safe(order, scale_attr, None)
            if scale_val and str(scale_val).strip():
                scale_tag = str(scale_val).strip()
                if scale_tag not in all_scales:
                    all_scales.append(scale_tag)
    
    elif order_type == "PACKING":
        try:
            from sqlalchemy.orm import sessionmaker
            from database import postgres_engine
            from models.palletizer_mapping import PalletizerMapping
            
            PostgresSessionLocal = sessionmaker(
                bind=postgres_engine, autoflush=False, autocommit=False, future=True
            )
            
            with PostgresSessionLocal() as db:
                mapping = db.query(PalletizerMapping).filter(
                    PalletizerMapping.version == version
                ).first()
                
                if mapping and mapping.equipment:
                    all_scales.append(mapping.equipment)
        except Exception as e:
            log.warning(f"Failed to get equipment from palletizer_mapping: {e}")
    
    # Remove duplicates while preserving order
    seen = set()
    unique_scales = []
    for scale in all_scales:
        if scale and scale not in seen:
            seen.add(scale)
            unique_scales.append(scale)
    
    log.info(f"📦 [_get_order_equipment] {order.order_id}: version={version}, type={order_type}, scales={unique_scales}")
    return unique_scales


@emulator_bp.route("/reset/realistic", methods=["POST"])
def reset_to_realistic():
    """Reset emulator values to realistic starting values and refresh baselines for in-progress orders."""
    try:
        from services.embedded_emulator import get_emulator
        emulator = get_emulator()
        result = emulator.reset_to_realistic()
        
        # ✅ CRITICAL FIX: Refresh baselines for all in-progress orders
        # This prevents orders from getting stuck when current < baseline after emulator reset
        refresh_result = _refresh_inprogress_order_baselines()
        result["baselines_refreshed"] = refresh_result
        
        return jsonify(result)
    except Exception as e:
        log.error(f"Error resetting to realistic: {e}")
        return jsonify({"error": str(e)}), 500


@emulator_bp.route("/refresh-baselines", methods=["POST"])
def refresh_baselines():
    """
    Manually refresh baselines for all in-progress orders to current SCADA values.
    Use this when orders are stuck because current < baseline.
    """
    try:
        result = _refresh_inprogress_order_baselines()
        return jsonify({
            "status": "ok",
            "message": "Baselines refreshed for in-progress orders",
            **result
        })
    except Exception as e:
        log.error(f"Error refreshing baselines: {e}")
        return jsonify({"error": str(e)}), 500


@emulator_bp.route("/reset-order-tracking", methods=["POST"])
def reset_order_tracking():
    """
    Reset all order tracking values to 0 for demo/testing purposes.
    This resets: confirmed_qty, weight_shift_a/b/c, scale1/2/3_qty, baselines, etc.
    Only works when demo mode is active.
    """
    try:
        # Check if demo mode is active
        from models.system_settings import get_setting
        demo_mode = get_setting("demo_mode", True)
        
        if not demo_mode:
            return jsonify({
                "status": "error",
                "message": "This operation is only allowed in demo mode"
            }), 403
        
        result = _reset_all_order_tracking()
        return jsonify({
            "status": "ok",
            "message": "Order tracking reset to 0 for all orders",
            **result
        })
    except Exception as e:
        log.error(f"Error resetting order tracking: {e}")
        import traceback
        traceback.print_exc()
        return jsonify({"error": str(e)}), 500


@emulator_bp.route("/delete-all-orders", methods=["POST"])
def delete_all_orders():
    """
    Delete all rows from the process_orders table (PostgreSQL).
    Only works when demo mode is active. Use for clearing in-process order table in demo.
    """
    try:
        from models.system_settings import get_setting
        from models.process_order_pg import ProcessOrderPG
        from database import postgres_engine
        from sqlalchemy.orm import sessionmaker

        demo_mode = get_setting("demo_mode", True)
        if not demo_mode:
            return jsonify({
                "status": "error",
                "message": "This operation is only allowed in demo mode"
            }), 403

        PostgresSessionLocal = sessionmaker(
            bind=postgres_engine, autoflush=False, autocommit=False, future=True
        )
        db = PostgresSessionLocal()
        try:
            count = db.query(ProcessOrderPG).delete()
            db.commit()
            log.info(f"🗑️ [Delete All Orders] Deleted {count} orders from process_orders")
            return jsonify({
                "status": "ok",
                "message": "All orders deleted from process orders table",
                "deleted_count": count
            })
        finally:
            db.close()
    except Exception as e:
        log.error(f"Error deleting all orders: {e}")
        import traceback
        traceback.print_exc()
        return jsonify({"error": str(e)}), 500


def _reset_all_order_tracking():
    """
    Reset all tracking values for all orders (Pending, InProgress, Validated).
    This is useful for demo/testing scenarios.
    
    Returns:
        Dict with reset results
    """
    from sqlalchemy.orm import sessionmaker
    from database import postgres_engine
    from services.scale_service import get_attr_safe, set_attr_safe
    
    try:
        from models.process_order_pg import ProcessOrderPG as ProcessOrder
    except Exception as e:
        log.error(f"Failed to import ProcessOrder: {e}")
        return {"error": str(e), "orders_reset": 0}
    
    PostgresSessionLocal = sessionmaker(
        bind=postgres_engine, autoflush=False, autocommit=False, future=True
    )
    
    reset_orders = []
    errors = []
    
    try:
        db = PostgresSessionLocal()
        
        # Find all orders that have tracking values (Pending, InProgress, Validated)
        all_orders = db.query(ProcessOrder).filter(
            ProcessOrder.status.in_(["Pending", "InProgress", "Validated"])
        ).all()
        
        log.info(f"🔄 [Reset Tracking] Found {len(all_orders)} orders to reset")
        
        for order in all_orders:
            try:
                po_number = order.order_id
                old_confirmed = float(get_attr_safe(order, "confirmed_qty", 0.0) or 0.0)
                
                # Reset confirmed quantity
                set_attr_safe(order, "confirmed_qty", 0.0)
                set_attr_safe(order, "last_confirmed_qty", 0.0)
                
                # Reset shift weights
                set_attr_safe(order, "weight_shift_a", 0.0)
                set_attr_safe(order, "weight_shift_b", 0.0)
                set_attr_safe(order, "weight_shift_c", 0.0)
                
                # Reset shift confirmations
                set_attr_safe(order, "confirmed_shift_a", 0.0)
                set_attr_safe(order, "confirmed_shift_b", 0.0)
                set_attr_safe(order, "confirmed_shift_c", 0.0)
                
                # Reset byproduct scale quantities
                set_attr_safe(order, "scale1_qty", 0.0)
                set_attr_safe(order, "scale2_qty", 0.0)
                set_attr_safe(order, "scale3_qty", 0.0)
                
                # Reset overflow
                set_attr_safe(order, "overflow_weight", 0.0)
                
                # Reset baselines to 0 (will be recaptured on order start)
                set_attr_safe(order, "baseline_wg101", 0.0)
                set_attr_safe(order, "baseline_wg201", 0.0)
                set_attr_safe(order, "baseline_wg202", 0.0)
                set_attr_safe(order, "baseline_wg301", 0.0)
                set_attr_safe(order, "baseline_wg302", 0.0)
                set_attr_safe(order, "baseline_wg501", 0.0)
                set_attr_safe(order, "baseline_wg502", 0.0)
                set_attr_safe(order, "baseline_wg503", 0.0)
                set_attr_safe(order, "baseline_dm101", 0.0)
                set_attr_safe(order, "baseline_dm102", 0.0)
                set_attr_safe(order, "baseline_dm201", 0.0)
                set_attr_safe(order, "baseline_dm202", 0.0)
                set_attr_safe(order, "baseline_dm203", 0.0)
                set_attr_safe(order, "baseline_sl601_counter", 0.0)
                set_attr_safe(order, "baseline_sl602_counter", 0.0)
                set_attr_safe(order, "baseline_sl603_counter", 0.0)
                set_attr_safe(order, "baseline_sl606_counter", 0.0)
                set_attr_safe(order, "baseline_sl607_counter", 0.0)
                
                # Reset shift baselines
                for s in ["a", "b", "c"]:
                    set_attr_safe(order, f"baseline_shift_{s}_start", {})
                    set_attr_safe(order, f"baseline_shift_{s}_time", None)
                
                # Reset validation flags but keep status
                set_attr_safe(order, "is_target_reached", False)
                set_attr_safe(order, "is_final_sent", False)
                
                # If order was Validated, set back to Pending for re-validation
                old_status = get_attr_safe(order, "status", "Pending")
                if old_status == "Validated":
                    set_attr_safe(order, "status", "Pending")
                    log.info(f"📋 [{po_number}] Status changed from Validated to Pending")
                
                db.add(order)
                
                reset_orders.append({
                    "order_id": po_number,
                    "old_confirmed_qty": old_confirmed,
                    "old_status": old_status,
                    "new_status": get_attr_safe(order, "status", "Pending")
                })
                
                log.info(f"✅ [{po_number}] Tracking values reset (was {old_confirmed:.2f} KG)")
                
            except Exception as e:
                log.error(f"❌ Error resetting order {order.order_id}: {e}")
                errors.append({"order_id": order.order_id, "error": str(e)})
        
        # Commit all changes
        db.commit()
        db.close()
        
        log.info(f"✅ [Reset Tracking] Reset {len(reset_orders)} orders")
        
        return {
            "orders_reset": len(reset_orders),
            "reset_orders": reset_orders,
            "errors": errors if errors else None
        }
        
    except Exception as e:
        log.error(f"❌ Error in _reset_all_order_tracking: {e}")
        import traceback
        traceback.print_exc()
        return {"error": str(e), "orders_reset": 0}


@emulator_bp.route("/reset/category/<category>", methods=["POST"])
def reset_category(category: str):
    """Reset a specific category to zero."""
    try:
        from services.embedded_emulator import get_emulator
        emulator = get_emulator()
        success = emulator.reset_category(category)
        if success:
            return jsonify({"status": "ok", "category": category, "message": "Reset to zero"})
        else:
            return jsonify({"error": f"Category {category} not found"}), 404
    except Exception as e:
        log.error(f"Error resetting category: {e}")
        return jsonify({"error": str(e)}), 500


# =============================================================================
# Data Access (matches external emulator format for compatibility)
# =============================================================================

@emulator_bp.route("/latest", methods=["GET"])
def get_latest():
    """Get latest emulator data (same format as external emulator)."""
    try:
        from services.embedded_emulator import get_emulator
        emulator = get_emulator()
        return jsonify(emulator.get_latest())
    except Exception as e:
        log.error(f"Error getting latest data: {e}")
        return jsonify({"error": str(e)}), 500


# Alternative endpoint for SCADA compatibility
@emulator_bp.route("/scada/latest", methods=["GET"])
def get_scada_latest():
    """SCADA-compatible endpoint for latest data."""
    try:
        from services.embedded_emulator import get_emulator
        emulator = get_emulator()
        data = emulator.get_latest()
        
        # Return in SCADA-compatible format
        return jsonify({
            "status": "ok",
            "data": data.get("scales", {}),
            "raw": data.get("raw_scales", {}),
            "timestamp": data.get("timestamp"),
            "source": "embedded_emulator",
        })
    except Exception as e:
        log.error(f"Error getting SCADA data: {e}")
        return jsonify({"error": str(e)}), 500
