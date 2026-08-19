# Overflow Transfer Fix - December 14, 2025

## Problem Statement
Overflow was not being added to the next order when auto-validation was running continuously (one order completes and the next order starts automatically). However, overflow was correctly applied when validation was paused and manually restarted.

## Root Cause
The system had two different code paths for starting orders:

1. **Manual Start** (via `/start` endpoint):
   - Used when user manually starts/restarts an order
   - Contains overflow application logic (lines 9851-9900)
   - ✅ Overflow was being applied correctly

2. **Auto-Validation Start** (via `init_and_start_order_worker()` function):
   - Used when scheduler automatically starts next order after previous one completes
   - Did NOT contain overflow application logic
   - ❌ Overflow was NOT being applied

### Code Flow Analysis

#### When Manual Pause/Restart:
```
User clicks Start
   ↓
POST /orders/<po_number>/start endpoint (line 9438)
   ↓
Overflow application logic (lines 9851-9900) ✅
   ↓
Order starts with overflow
```

#### When Auto-Validation Continuous:
```
Order completes
   ↓
Worker finally block (line 9393)
   ↓
_schedule_next_orders_after_completion() (line 9404)
   ↓
init_and_start_order_worker() (line 8035)
   ↓
NO overflow application logic ❌
   ↓
Order starts WITHOUT overflow
```

## Solution
Added overflow application logic to `init_and_start_order_worker()` function to match the logic in the `/start` endpoint.

### Changes Made

#### 1. Main Product Overflow Transfer
**Location:** `backend/routes/order_validation.py` after line 7539

```python
# Find validated orders with overflow of the same type
completed_with_overflow_list = db.query(ProcessOrder).filter(
    ProcessOrder.status == "Validated",
    ProcessOrder.overflow_weight > 0,
    ProcessOrder.order_type == order_type,  # Match by order type
    ProcessOrder.order_id != po_number  # Don't apply from same order
).order_by(ProcessOrder.id.desc()).all()

if completed_with_overflow:
    overflow_weight = float(get_attr_safe(completed_with_overflow, "overflow_weight", 0.0) or 0.0)
    if overflow_weight > 0:
        # Apply to confirmed_qty
        set_attr_safe(order, "confirmed_qty", overflow_applied)
        
        # Store for later application to shift weight
        temp_overflow_for_shift = overflow_applied
        
        # Clear overflow from source order
        set_attr_safe(completed_with_overflow, "overflow_weight", 0.0)
        db.commit()
```

#### 2. Apply Overflow to Shift Weight
**Location:** `backend/routes/order_validation.py` after shift detection (line ~7720)

```python
# Apply overflow to current shift's weight column
if temp_overflow_for_shift > 0:
    shift_weight_field = f"weight_shift_{current_shift.lower()}"
    existing_shift_weight = float(get_attr_safe(order, shift_weight_field, 0.0) or 0.0)
    new_shift_weight = existing_shift_weight + temp_overflow_for_shift
    set_attr_safe(order, shift_weight_field, new_shift_weight)
    db.commit()
```

#### 3. Byproduct Scale Overflow Transfer
**Location:** `backend/routes/order_validation.py` after baseline commit (line ~7850)

```python
# Apply byproduct overflow from scale_overflows table
for scale_idx, scale_tag in enumerate([scale1_tag, scale2_tag, scale3_tag], 1):
    if not scale_tag:
        continue
    
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
        
        # Apply overflow
        set_attr_safe(order, scale_qty_field, new_scale_qty)
        
        # Clear overflow from table
        db.execute(text("""
            UPDATE scale_overflows SET overflow_qty = 0, last_updated = NOW()
            WHERE scale_tag = :tag
        """), {"tag": scale_tag})
```

## Testing Steps

1. **Setup:**
   - Have at least 2 orders of the same type (both MILLING or both PACKING) with Priority 1 and Priority 2
   - Start auto-validation

2. **Test Scenario 1 - Continuous Auto-Validation:**
   - Let Priority 1 order complete with overflow (produce more than target)
   - Verify that Priority 2 order automatically starts
   - **Expected:** Priority 2 order should show overflow added to confirmed_qty and current shift weight
   - **Check:** Backend logs should show `"🌊 Applied overflow to confirmed_qty"` and `"🌊 Applied overflow to weight_shift_x"`

3. **Test Scenario 2 - Manual Restart (existing functionality):**
   - Pause auto-validation after order completes
   - Manually start the next order
   - **Expected:** Order should show overflow added (this already worked)

4. **Verification Points:**
   - Check backend console logs for overflow application messages
   - Check database: `confirmed_qty` and `weight_shift_a/b/c` should include overflow
   - Check frontend: Progress should show overflow included in current production
   - Verify source order's `overflow_weight` is cleared (set to 0)

## Log Messages to Look For

When overflow is correctly applied during auto-validation, you should see:

```
🌊 [PO_NUMBER] Found overflow from order PREVIOUS_PO: XX.XX
🌊 [PO_NUMBER] Applied overflow to confirmed_qty: XX.XX
✅ [PO_NUMBER] Applied main product overflow XX.XX from PREVIOUS_PO (same type: MILLING/PACKING)
🌊 [PO_NUMBER] Applied overflow to weight_shift_x: 0.00 + XX.XX = XX.XX
✅ [PO_NUMBER] Verified weight_shift_x in DB: XX.XX
```

For byproduct overflow:
```
🌊 [PO_NUMBER] Applied byproduct overflow to scale1 (SCALE_TAG): 0.0000 + XX.XXXX = XX.XXXX
✅ [PO_NUMBER] Applied byproduct overflows: SCALE_TAG: +XX.XXXX
```

## Expected Behavior After Fix

### Full Cycle (Continuous Auto-Validation):
1. **Order 1 completes:**
   - Produces 105 tons (target: 100 tons)
   - Overflow: 5 tons stored in `overflow_weight`
   - Order status: Validated

2. **Order 2 automatically starts:**
   - Scheduler calls `init_and_start_order_worker()`
   - ✅ Overflow logic executes
   - `confirmed_qty` set to 5 tons
   - `weight_shift_a` (or current shift) set to 5 tons
   - Order 1's `overflow_weight` cleared to 0
   - Order 2 continues from 5 tons instead of 0

3. **Order 2 production:**
   - Shows 5 tons already completed from start
   - Progress bar reflects overflow
   - Remaining target correctly calculated

## Files Modified
- `backend/routes/order_validation.py` - Added overflow application logic to `init_and_start_order_worker()` function

## Impact
- ✅ Overflow now works in both manual and automatic order transitions
- ✅ No changes required to frontend
- ✅ No database schema changes
- ✅ Maintains backward compatibility

