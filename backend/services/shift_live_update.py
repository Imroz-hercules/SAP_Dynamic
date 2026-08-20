# services/shift_live_update.py

import logging
import threading

from database import PostgresSessionLocal
from services.scale_service import calculate_deltas, get_attr_safe
from services import baseline_guard  # A7: unmapped-tag guard for baselines
from services.classification_service import classify_order  # A4: one classifier
from models.process_order_pg import ProcessOrderPG

log = logging.getLogger("shift_live_update")

# =============================================================================
# A4 — this module no longer has its own opinion about equipment
# =============================================================================
# MILLING_PV_SPECS and PL_TO_SCADA used to live here: a second, hardcoded copy
# of the version -> scales mapping, consulted every 60 seconds to write
# weight_shift_a/b/c — the values confirmed to SAP at shift end — while order
# validation read the database. Any version added through Material Map never
# reached this function.
#
# Both now go through services.classification_service.classify_order, which is
# cached (A3), so converging them costs nothing per cycle.
#
# Reconciled before deleting the dict. Of the 15 versions the two
# implementations shared, 13 matched exactly. The other two:
#
#   BRF2  the dict said WG502, the database said WG501. The DATABASE was wrong -
#         two independent checks against Book1.xlsx and the stream annotations
#         in auto_validator.py single it out as the only inconsistent row.
#         Corrected by migrate_fix_brf2_mapping.py, which carries the evidence.
#         That correction is a prerequisite for this change: applied the other
#         way round, A4 would have propagated the wrong value to the one
#         implementation that had it right.
#
#   BRF1  existed only in the dict, never in the database. classify_order reads
#         the database, so BRF1 orders have already been failing validation with
#         "No milling mapping found". It is retired; if it ever returns it needs
#         a row in milling_version_mappings, like any other version.

# Reported-once tracking, so a misconfigured version does not write an error_log
# row every 60 seconds until someone notices.
_reported_lock = threading.Lock()
_reported = set()


def _report_unresolvable(order, shift, reason):
    """
    A4: an order whose version cannot be resolved used to be a one-line warning
    and a `continue` — weight_shift_* was simply never written and nothing
    surfaced. Now it reaches error_log, which the UI polls.

    Deduped per (order, version, reason) for the life of the process.
    """
    key = (order.order_id, order.version, reason)
    with _reported_lock:
        if key in _reported:
            return False
        _reported.add(key)

    message = (
        f"Order {order.order_id} (version {order.version or 'unset'}): {reason}. "
        f"Shift {shift} production is NOT being recorded for this order. "
        f"Add or correct the version mapping in Material Map."
    )
    log.error(message)
    try:
        from services.error_logger import log_order_error

        log_order_error(
            po_number=str(order.order_id or ""),
            error_type="configuration_error",
            error_message=message,
            payload={
                "version": order.version,
                "material": order.material,
                "shift": shift,
                "reason": reason,
                "effect": f"weight_shift_{shift.lower()} not updated",
            },
            source="shift_live_update",
        )
    except Exception as exc:
        log.exception("Failed to write the unresolvable-version error: %s", exc)
    return True


def clear_reported():
    """Forget dedupe state, so a recurrence reports again. Used by the tests."""
    with _reported_lock:
        _reported.clear()


def evaluate_formula_using_deltas(formula: str, per_tag_delta: dict) -> float:
    """
    Evaluate a milling formula against per-tag deltas.

    ✅ A4: delegates to the AST-validated implementation in
    routes/order_validation.py rather than keeping a second one here. The local
    copy differed in two ways that mattered:

      - on a formula it could not evaluate it returned `sum(deltas)` instead of
        0.0, so a malformed formula silently produced the SUM of the streams
        where the validator produced nothing. For "WG101-WG302" with deltas of
        100 and 30 that is 130 instead of 70 — a plausible wrong number written
        straight into weight_shift_*.
      - it called bare `eval()` on a string that comes from the database and is
        editable through POST /api/milling-mapping. The uppercasing it did first
        happens to break most identifiers, but there was no actual validation.

    Imported lazily: routes/order_validation.py imports this module's siblings,
    and a module-level import would risk a cycle.
    """
    from routes.order_validation import evaluate_formula_using_deltas as _safe_eval

    return _safe_eval(formula, per_tag_delta)


def update_live_shift_production():
    """
    LIVE shift weight calculation using EXACT same delta logic as confirmed_qty.

    Uses:
    - classify_order() from classification_service (same as order validation)
    - calculate_deltas() from scale_service (same as auto-validator)
    - baseline_shift_X_start (same as shift end confirmation)

    Updates weight_shift_a/b/c every 60 seconds.
    """
    db = None
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

                # ✅ A4: one classifier, shared with order validation. Cached by
                # A3, so this is not a query per order per cycle.
                classification = classify_order(order)

                if classification.get("error"):
                    _report_unresolvable(order, shift, classification["error"])
                    continue

                order_type = classification.get("order_type")
                equipment = classification.get("equipment") or []
                formula = classification.get("formula") or ""
                packing_info = classification.get("packing_info") or {}

                if not equipment:
                    _report_unresolvable(
                        order, shift,
                        "classification resolved no equipment for this version",
                    )
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

                # Build per-tag delta dict.
                # ✅ A4: keyed by the tag as written, matching what
                # get_current_production builds and what the shared formula
                # evaluator expects. The old local evaluator used lowercase keys
                # and uppercased the formula to compensate.
                per_tag_delta = {}
                for tag in equipment:
                    delta_info = deltas.get(tag, {})
                    per_tag_delta[tag] = float(delta_info.get("delta", 0.0) or 0.0)

                # ✅ FIX: Use sum_dm_readings_for_order for DM water meters
                # DM tags are 30-sec averages on PLC side, so we must SUM all readings in the time window,
                # rather than using the delta/accumulation logic which misses readings between polls.
                try:
                    from services.scale_service import sum_dm_readings_for_order

                    for tag in equipment:
                        if tag.startswith("DM"):
                            dm_sum = sum_dm_readings_for_order(tag, order)
                            per_tag_delta[tag] = dm_sum
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
                # ✅ A4: the multiplier comes from the classification, which A2
                # resolved from palletizer_mapping. This used to be a third copy
                # of the lookup — a raw `SELECT bag_size_kg` per order per cycle,
                # against the column A2 deprecated.
                if order_type == "PACKING":
                    bags_per_pallet = float(packing_info.get("bags_per_pallet_actual") or 1)
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

                tags_str = ", ".join([f"{t}={per_tag_delta.get(t, 0):.2f}" for t in equipment])
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
        if db is not None:
            db.close()
