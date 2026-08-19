# ORDER VALIDATION CRITICAL FIXES - December 12, 2025
# Priority: CRITICAL | Precision: HIGH

## Overview
This document specifies critical fixes required for the order validation system. These fixes must be implemented with HIGH PRECISION to ensure production stability.

---

## ISSUE 1: Current Order Values Must Only Increase

### Problem
Current implementation allows `confirmed_qty` and `weight_shift_X` to change automatically based on SCADA calculations, which can cause values to decrease or fluctuate unexpectedly.

### Current Problematic Code
**File: `backend/routes/order_validation.py`**

Lines 8966-8979 (auto_validation_worker):
# PROBLEM: Worker forces confirmed_qty to display_total unconditionally
if shift_weights_sum > 0.0:
    final_confirmed = display_total  # This can DECREASE confirmed_qty!
    print(f"✅ [Worker-{po_number}] FORCING confirmed_qty to {final_confirmed:.2f}...")Lines 9088-9092:
# PROBLEM: Forces confirmed_qty even if it would decrease
if abs(final_verified - display_total) > 0.01:
    current_order.confirmed_qty = display_total  # Can decrease value!### Required Fix
**RULE: `confirmed_qty` and `weight_shift_X` must ONLY INCREASE, never decrease.**

# FIX for auto_validation_worker (around line 8966):

# OLD CODE - REMOVE:
# if shift_weights_sum > 0.0:
#     final_confirmed = display_total

# NEW CODE - ADD:
# ✅ CRITICAL FIX: confirmed_qty can ONLY increase, never decrease
old_confirmed = float(get_attr_safe(current_order, "confirmed_qty", 0.0) or 0.0)
new_production_value = display_total

# Only update if new value is GREATER than existing
if new_production_value > old_confirmed:
    final_confirmed = new_production_value
    print(f"✅ [Worker-{po_number}] Increasing confirmed_qty: {old_confirmed:.2f} → {final_confirmed:.2f}")
else:
    final_confirmed = old_confirmed  # PRESERVE existing value
    print(f"🔒 [Worker-{po_number}] Preserving confirmed_qty: {old_confirmed:.2f} (new calc {new_production_value:.2f} is not higher)")**Same fix for shift weights:**
# FIX for shift weight update (around line 8705):

# Before setting shift weight, ensure it only increases:
new_shift_weight = final_shift_weight
existing_shift_weight = float(get_attr_safe(current_order, shift_field, 0.0) or 0.0)

# Only update if new value is GREATER
if new_shift_weight > existing_shift_weight:
    setattr(current_order, shift_field, new_shift_weight)
    print(f"✅ [Worker-{po_number}] Shift {code.upper()} increased: {existing_shift_weight:.2f} → {new_shift_weight:.2f}")
else:
    # Keep existing - never decrease
    print(f"🔒 [Worker-{po_number}] Shift {code.upper()} preserved: {existing_shift_weight:.2f}")---

## ISSUE 2: Remove Auto-Adding of Confirmed Text

### Problem
The system automatically sets `confirmed_text` in auto-validation mode. This should ONLY be entered by the user in manual and offline mode.

### Current Problematic Code
**File: `backend/routes/order_validation.py`**

Line 9742 (start_order):
# PROBLEM: Auto-setting confirmed_text
set_attr_safe(order, "confirmed_text", f"Auto: Target met instantly from overflow ({overflow_applied:.2f}/{target_qty:.2f} {unit})")### Required Fix
**RULE: Never auto-set `confirmed_text`. Only user can set it in manual/offline mode.**

# FIX - REMOVE this line completely:
# set_attr_safe(order, "confirmed_text", f"Auto: Target met instantly from overflow...")

# If confirmation text is needed for logging/debugging, use a different field:
# set_attr_safe(order, "validation_notes", f"Auto: Target met from overflow...")  # Internal notes only**Search and remove ALL instances of automatic `confirmed_text` setting:**
- Search pattern: `set_attr_safe.*confirmed_text`
- Only allow `confirmed_text` to be set from manual confirmation endpoints

---

## ISSUE 3: SAP Confirmations Only at Shift End or Manual Push

### Problem
The system may push confirmations to SAP automatically outside of:
1. End of shift (triggered by `shift_auto_confirm.py`)
2. Manual user push

### Current Behavior Analysis
**File: `backend/routes/order_validation.py`**

Line 7367 (end_shift_and_confirm):
# This function sends to SAP - called from shift_auto_confirm
sap_result = sap_service.push_confirmation([order_data], 'online')**File: `backend/services/shift_auto_confirm.py`**
- Function `auto_push_shift_confirmation()` runs on scheduler
- This is CORRECT - it only triggers at shift end

### Required Fix
**RULE: Ensure NO automatic SAP push happens from auto_validation_worker or anywhere else.**

1. **Verify in `auto_validation_worker`** - NO SAP calls should exist:
# VERIFY: Search for sap_service.push or confirm_online/confirm_offline in auto_validation_worker
# These should NOT exist within the worker loop

# The worker should ONLY:
# 1. Update shift weights from SCADA
# 2. Update confirmed_qty (internal tracking only)
# 3. Mark order as "Validated" when target is reached
# 4. NOT send to SAP - this is done ONLY by:
#    - shift_auto_confirm.py at shift end
#    - Manual push-confirmation endpoint2. **Add explicit guard in auto_validation_worker completion block (around line 9129):**
# When order is complete, do NOT send to SAP
if completion.get("is_complete", False):
    print(f"🏁 [Worker-{po_number}] ORDER COMPLETE!")
    
    # ✅ CRITICAL: Do NOT call SAP here
    # SAP confirmation ONLY happens at:
    # 1. Shift end (via shift_auto_confirm.py)
    # 2. Manual push (via /push-confirmation endpoint)
    
    set_attr_safe(current_order, "status", "Validated")
    # Do NOT call: sap_service.push_confirmation or end_shift_and_confirm---

## ISSUE 4: Mark Order as Completed at Target - No Overflow

### Problem
When an order reaches its target quantity, the system should:
1. Immediately mark the order as "Validated/Completed"
2. Stop tracking production for this order
3. Capture scales baseline for the NEXT order
4. Never allow overflow to be recorded on the current order

### Current Problematic Code
**File: `backend/routes/order_validation.py`**

Lines 7388-7392 (overflow handling):
# PROBLEM: Allows overflow
overflow = max(0, new_total_confirmed_to_sap - target)
if overflow > 0:
    set_attr_safe(order, "overflow_weight", overflow)Lines 6612-6614 (check_order_completion):
is_complete = (total_actual >= target_qty) or (existing_confirmed >= target_qty)
overflow = max(0.0, total_actual - target_qty)  # PROBLEM: Calculates overflow### Required Fix
**RULE: When target is reached, CAP at target. No overflow on current order.**

1. **Fix in auto_validation_worker (shift weight calculation):**
# Calculate remaining to target
target_qty = float(get_attr_safe(current_order, "expected_weight") or get_attr_safe(current_order, "quantity") or 0.0)
current_confirmed = float(get_attr_safe(current_order, "confirmed_qty", 0.0) or 0.0)
remaining_to_target = max(0.0, target_qty - current_confirmed)

# Cap new production at remaining to target
if production_increment > remaining_to_target:
    production_increment = remaining_to_target
    print(f"🛑 [Worker-{po_number}] Capped production at target. Remaining: {remaining_to_target:.2f}")

# If we've hit target, mark complete IMMEDIATELY
new_total = current_confirmed + production_increment
if new_total >= target_qty:
    new_total = target_qty  # Cap at exactly target
    set_attr_safe(current_order, "status", "Validated")
    print(f"🏁 [Worker-{po_number}] Target reached! Order marked as Validated. Final: {new_total:.2f}/{target_qty:.2f}")
    
    # ✅ CRITICAL: Stop processing this order - prepare for next order
    # Release scales for next order to capture baseline
    release_scales_and_start_waiting_orders(po_number, current_order, classification, db)2. **Fix in check_order_completion:**
def check_order_completion(order, classification: Dict) -> Dict[str, Any]:
    # ... existing code ...
    
    # ✅ FIX: Cap actual at target - no overflow
    if total_actual >= target_qty:
        total_actual = target_qty  # Cap at target
    
    overflow = 0.0  # ✅ NO OVERFLOW - always 0
    
    return {
        "is_complete": total_actual >= target_qty or existing_confirmed >= target_qty,
        "actual_qty": round(min(total_actual, target_qty), 3),  # Capped at target
        "target_qty": round(target_qty, 3),
        "overflow": 0.0,  # Always 0 - no overflow allowed
        "unit": unit
    }3. **Remove overflow_weight field usage:**
# Search and remove/comment all: set_attr_safe(order, "overflow_weight", ...)
# Overflow should be 0 or tracked separately for audit purposes only (not applied to orders)---

## Implementation Checklist

### Files to Modify:
1. `backend/routes/order_validation.py`
   - [ ] Fix confirmed_qty to only increase (Issue 1)
   - [ ] Fix weight_shift_X to only increase (Issue 1)
   - [ ] Remove auto-confirmed_text (Issue 2)
   - [ ] Verify no SAP calls in auto_validation_worker (Issue 3)
   - [ ] Cap production at target (Issue 4)
   - [ ] Remove overflow handling (Issue 4)

2. `backend/services/shift_auto_confirm.py`
   - [ ] Verify this is the ONLY place that triggers SAP at shift end

### Testing Checklist:
- [ ] Start an order, verify confirmed_qty only increases
- [ ] Verify weight_shift_X only increases, never decreases
- [ ] Verify confirmed_text is empty unless manually entered
- [ ] Verify SAP confirmation only happens at shift end or manual push
- [ ] Verify when order reaches target, it's immediately marked Validated
- [ ] Verify no overflow is recorded on the order
- [ ] Verify next order can start with fresh baseline when previous completes

---

## Summary of Rules
1. **confirmed_qty**: Only increases. Never decreases. Never resets mid-order.
2. **weight_shift_X**: Only increases. Never decreases.
3. **confirmed_text**: User-entered only (manual/offline mode). Never auto-set.
4. **SAP Confirmation**: Only at shift end OR manual push. Never automatic otherwise.
5. **Target Reached**: Cap at target. Mark Validated immediately. No overflow.
6. **Next Order**: Capture fresh baseline when previous order completes.