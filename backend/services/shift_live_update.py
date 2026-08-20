# services/shift_live_update.py

import logging
from sqlalchemy import text
from database import postgres_engine, PostgresSessionLocal
from services.scale_service import calculate_deltas, get_attr_safe
from services import baseline_guard  # A7: unmapped-tag guard for baselines
from models.process_order_pg import ProcessOrderPG

log = logging.getLogger("shift_live_update")

# INLINE MAPPINGS (copied from routes/orders.py)
MILLING_PV_SPECS = {
    "LWSM": {"scales": ["WG101", "WG302", "DM101", "DM102"], "formula": "WG101-WG302+DM101+DM102"},
    "IWSM": {"scales": ["WG101", "WG302"], "formula": "WG101-WG302"},
    "SWSM": {"scales": ["WG101", "WG302"], "formula": "WG101-WG302"},
    "CWIM": {"scales": ["WG201", "WG301", "DM201", "DM202", "DM203"], "formula": "WG201-WG301+DM201+DM202+DM203"},
    "CWLM": {"scales": ["WG201", "WG301", "DM201", "DM202", "DM203"], "formula": "WG201-WG301+DM201+DM202+DM203"},
    "CWMM": {"scales": ["WG201", "WG301", "DM201", "DM202", "DM203"], "formula": "WG201-WG301+DM201+DM202+DM203"},
    "CWSM": {"scales": ["WG201", "WG301", "DM201", "DM202", "DM203"], "formula": "WG201-WG301+DM201+DM202+DM203"},
    "BKF1": {"scales": ["WG501"], "formula": "WG501"},
    "CKF1": {"scales": ["WG502"], "formula": "WG502"},
    "IWF1": {"scales": ["WG502"], "formula": "WG502"},
    "IWF2": {"scales": ["WG502"], "formula": "WG502"},
    "BRF1": {"scales": ["WG501"], "formula": "WG501"},
    "BRF2": {"scales": ["WG502"], "formula": "WG502"},
    "BRF3": {"scales": ["WG501"], "formula": "WG501"},
    "MMCF": {"scales": ["WG502"], "formula": "WG502"},
}

PL_TO_SCADA = {
    "PL601": "PL601_TOT",
    "PL602": "PL602_TOT",
    "PL603": "PL603_TOT",
    "PL606": "SL606_TOT",
    "PL607": "SL607_TOT",
}


def get_equipment_for_order(material: str, version: str, order_type: str) -> tuple:
    """
    Get equipment list and formula for an order.
    Returns: (equipment_list, formula)
    """
    # Determine order type from material if not set
    if not order_type:
        material_stripped = material.lstrip('0')
        if len(material_stripped) >= 2:
            material_prefix = material_stripped[:2]
            if material_prefix == "13":
                order_type = "MILLING"
            elif material_prefix == "14":
                order_type = "PACKING"
    
    # MILLING: Use MILLING_PV_SPECS
    if order_type == "MILLING":
        spec = MILLING_PV_SPECS.get(version.upper())
        if spec:
            return spec.get("scales", []), spec.get("formula", ""), order_type
    
    # PACKING: Query palletizer_mapping
    elif order_type == "PACKING":
        try:
            with postgres_engine.connect() as conn:
                result = conn.execute(text("""
                    SELECT palletizer, scada_tag FROM palletizer_mapping
                    WHERE version = :ver LIMIT 1
                """), {"ver": version}).mappings().first()

                if result:
                    # ✅ A2: read the tag from the row. The local PL_TO_SCADA copy
                    # below is still used by nothing else and goes in A4 with
                    # MILLING_PV_SPECS — but leaving this branch on it would mean
                    # a line added through the screen classified fine and then
                    # silently produced no shift weight.
                    tag = result.scada_tag or PL_TO_SCADA.get(result.palletizer)
                    if tag:
                        return [tag], tag, order_type
                    log.warning(
                        "⚠️ Version %s is on line %s, which has no scada_tag - "
                        "no shift weight will be written", version, result.palletizer
                    )
        except Exception as e:
            log.error(f"Failed to query palletizer mapping: {e}")
    
    return [], "", order_type


def evaluate_formula_using_deltas(formula: str, per_tag_delta: dict) -> float:
    """
    Evaluate milling formula using delta values.
    E.g., "WG101-WG302+DM101+DM102" with deltas = {"wg101": 10, "wg302": 2, ...}
    Returns calculated weight.
    """
    try:
        import re
        
        # Replace tag names with their delta values
        expr = formula.upper()
        for tag, delta_val in per_tag_delta.items():
            expr = re.sub(rf'\b{tag.upper()}\b', str(delta_val), expr)
        
        # Evaluate the expression
        result = eval(expr)
        return float(result)
    except Exception as e:
        log.error(f"Failed to evaluate formula '{formula}': {e}")
        return sum(per_tag_delta.values())  # Fallback: sum all deltas


def update_live_shift_production():
    """
    LIVE shift weight calculation using EXACT same delta logic as confirmed_qty.
    
    Uses:
    - calculate_deltas() from scale_service (same as auto-validator)
    - baseline_shift_X_start (same as shift end confirmation)
    - Equipment from MILLING_PV_SPECS or palletizer_mapping
    
    Updates weight_shift_a/b/c every 60 seconds.
    """
    
    try:
        db = PostgresSessionLocal()
        
        # Load all InProgress orders
        orders = db.query(ProcessOrderPG).filter(
            ProcessOrderPG.status == "InProgress",
            ProcessOrderPG.current_shift.isnot(None)
        ).all()
        
        if not orders:
            log.debug("No InProgress orders found")
            return
        
        log.info(f"🔄 Processing {len(orders)} InProgress order(s) for live shift updates")
        updated_count = 0
        
        for order in orders:
            try:
                shift = (order.current_shift or "").upper()
                
                if shift not in ("A", "B", "C"):
                    continue

                # Get equipment first (needed for baseline normalization)
                equipment, formula, order_type = get_equipment_for_order(
                    order.material,
                    order.version or "",
                    order.order_type or ""
                )

                if not equipment:
                    log.warning(f"⚠️ Order {order.order_id}: No equipment found for version {order.version}")
                    continue

                # Get baseline for current shift
                baseline_field = f"baseline_shift_{shift.lower()}_start"
                raw_baseline = getattr(order, baseline_field, None)

                if not raw_baseline or not isinstance(raw_baseline, dict):
                    log.warning(f"⚠️ Order {order.order_id}: No baseline for Shift {shift}")
                    continue

                # ✅ CRITICAL: Normalize like get_current_production - flat {tag: float}, fallback to baseline_{tag}
                # ✅ A7: the fallback used to be get_attr_safe(..., 0.0), which returns
                # 0.0 for a tag that has no baseline column at all. This function writes
                # weight_shift_a/b/c, the numbers MILLING confirmations are built from,
                # so a zero baseline here reports the scale's lifetime counter as this
                # shift's production. Skip the order instead and tell the operator.
                baselines_flat = {}
                try:
                    for tag in equipment:
                        if tag in raw_baseline:
                            val = raw_baseline[tag]
                            if isinstance(val, dict):
                                baselines_flat[tag] = float(val.get("current", 0.0) or 0.0)
                            else:
                                baselines_flat[tag] = float(val or 0.0)
                        else:
                            baselines_flat[tag] = baseline_guard.read_baseline_column(
                                order, tag, po_number=order.order_id,
                                reason=(
                                    f"scale tag '{tag}' is not in this shift's captured "
                                    f"baselines ({baseline_field}) and has no baseline "
                                    f"column — the snapshot was taken before this tag "
                                    f"joined the mapping"
                                ),
                            )
                except baseline_guard.UnmappedTagError as exc:
                    baseline_guard.report_unmapped_tag(
                        exc,
                        source="shift_live_update",
                        extra={
                            "equipment": list(equipment),
                            "version": order.version,
                            "material": order.material,
                            "order_type": order_type,
                            "shift": shift,
                            "note": "weight_shift_%s not updated" % shift.lower(),
                        },
                    )
                    continue

                # ✅ USE SAME calculate_deltas() as auto-validator with NORMALIZED baselines
                deltas = calculate_deltas(equipment, baselines_flat, order=order, db=db)
                
                # Build per-tag delta dict
                per_tag_delta = {}
                for tag in equipment:
                    delta_info = deltas.get(tag, {})
                    delta_val = float(delta_info.get("delta", 0.0) or 0.0)
                    per_tag_delta[tag.lower()] = delta_val
                
                # ✅ FIX: Use sum_dm_readings_for_order for DM water meters
                # DM tags are 30-sec averages on PLC side, so we must SUM all readings in the time window,
                # rather than using the delta/accumulation logic which misses readings between polls.
                try:
                    from services.scale_service import sum_dm_readings_for_order
                    
                    for tag in equipment:
                        if tag.startswith("DM"):
                            # Calculate correct sum from database
                            dm_sum = sum_dm_readings_for_order(tag, order)
                            
                            # Update values used for formula evaluation (use lowercase for consistency)
                            per_tag_delta[tag.lower()] = dm_sum
                            log.debug(f"💧 [shift_live_update] Replaced DM delta for {tag} with SUM: {dm_sum}")
                except Exception as e:
                    log.warning(f"⚠️ [shift_live_update] Error calculating DM sums: {e}")
                
                # Calculate total weight using formula (MILLING) or sum (PACKING)
                if order_type == "MILLING" and formula:
                    total_delta = evaluate_formula_using_deltas(formula, per_tag_delta)
                    unit = "KG"
                else:
                    total_delta = sum(per_tag_delta.values())
                    unit = "KG" if order_type == "MILLING" else "PALLET"
                
                # Convert PACKING pallets → bags
                if order_type == "PACKING":
                    try:
                        with postgres_engine.connect() as conn:
                            pm = conn.execute(text("""
                                SELECT bag_size_kg FROM palletizer_mapping
                                WHERE version = :ver LIMIT 1
                            """), {"ver": order.version}).mappings().first()
                            
                            bags_per_pallet = float(pm.bag_size_kg) if pm else 1
                    except:
                        bags_per_pallet = 1
                    
                    live_weight = total_delta * bags_per_pallet
                    unit = "BAG"
                else:
                    live_weight = total_delta

                # ✅ Sanity: if formula is absurdly large (e.g. baseline 0 for WG), do NOT overwrite weight_shift
                try:
                    expected = float(get_attr_safe(order, "expected_weight") or get_attr_safe(order, "quantity") or 0.0)
                except Exception:
                    expected = 0.0
                if expected > 0 and live_weight > max(10.0 * expected, 1e6):
                    log.error(
                        "⚠️ Order %s Shift %s: REJECTED live_weight=%.2f (expected ~%.2f) - "
                        "likely baseline 0 or wrong. NOT updating weight_shift.",
                        order.order_id, shift, live_weight, expected
                    )
                    continue

                # Update weight_shift_a/b/c
                shift_field = f"weight_shift_{shift.lower()}"
                old_weight = float(get_attr_safe(order, shift_field, 0.0) or 0.0)
                
                # ✅ C31-T26 FIX: SIMPLE approach - just SET the weight, don't accumulate
                # delta from calculate_deltas is the TOTAL production from baseline
                # The C31-T26 formula handles rollover naturally:
                # - At 99999: delta = 99999 - 99998 = 1 pallet
                # - At 100001: delta = 1 + (100000 - 99998) = 3 pallets (rollover formula)
                # - At 100002: delta = 2 + (100000 - 99998) = 4 pallets
                # 
                # Baseline is NOT updated after rollover, so C31-T26 continues working.
                # weight_shift = delta × bags_per_pallet (the total from original baseline)
                
                final_weight = live_weight
                
                if final_weight != old_weight:
                    log.info(f"✅ Order {order.order_id} Shift {shift}: {old_weight:.2f} → {final_weight:.2f} {unit}")
                
                setattr(order, shift_field, final_weight)
                
                tags_str = ", ".join([f"{t}={per_tag_delta.get(t.lower(), 0):.2f}" for t in equipment])
                log.info(f"✅ Order {order.order_id} Shift {shift}: {live_weight:.2f} {unit} ({tags_str})")
                updated_count += 1
            
            except Exception as e:
                log.error(f"Failed to update shift weight for order {order.order_id}: {e}")
        
        # Commit all updates
        db.commit()
        skipped = len(orders) - updated_count
        log.info(
            "✅ LIVE shift weights updated: %d of %d order(s)%s",
            updated_count, len(orders),
            f" ({skipped} skipped)" if skipped else "",
        )
    
    except Exception as e:
        log.exception("❌ Live shift update failed: %s", e)
    finally:
        db.close()


if __name__ == "__main__":
    # For testing
    logging.basicConfig(level=logging.INFO)
    update_live_shift_production()
