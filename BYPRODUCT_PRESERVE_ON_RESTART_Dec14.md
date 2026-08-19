# Byproduct Scales Preservation on Restart - December 14, 2025

## Problem Statement

When an order was paused/resumed or stopped/restarted, the system was **re-capturing byproduct baselines** (WG501, WG503), which overwrote any user modifications. This caused:

1. User modifies byproduct in UI: WG501 = 460.20031 → 500.00
2. Sends confirmation (value saved to database ✅)
3. Order is paused or stopped
4. Order is resumed or restarted
5. System re-captures byproduct baseline from SCADA: WG501 = 460.20031 ❌
6. User's modification (500.00) is lost ❌

## Root Cause

### Two Code Paths Were Re-Capturing Byproducts on Every Start:

**1. Auto-Validation Path (init_and_start_order_worker):**
```python
# Line 7851 - OLD CODE (ALWAYS captured byproducts)
if order_type == "MILLING":
    version = get_attr_safe(order, "version", "").strip().upper()
    byproduct_baselines = _capture_byproduct_baselines(version, baselines, order=order)
    _set_byproduct_scales(order, version, byproduct_baselines)
```

**2. Manual Start Path (/start endpoint):**
```python
# Line 9908 - OLD CODE (ALWAYS captured byproducts)
if order_type_new == "MILLING":
    version = (get_attr_safe(order, "version") or "").strip().upper()
    baselines = _capture_byproduct_baselines(version, baselines, order=order)
    _set_byproduct_scales(order, version, baselines)
```

### The Issue:
- `_capture_byproduct_baselines()` was called on **every restart**, not just first-time start
- This fetched fresh SCADA values and overwrote database values
- User modifications were lost

## Solution

### New Behavior:

**Check if byproduct scales already exist before capturing:**

```python
# ✅ NEW CODE - Check if restart vs brand new order
existing_scale1 = get_attr_safe(order, "scale1", None)
existing_scale1_qty = float(get_attr_safe(order, "scale1_qty", 0.0) or 0.0)
existing_scale2 = get_attr_safe(order, "scale2", None)
existing_scale2_qty = float(get_attr_safe(order, "scale2_qty", 0.0) or 0.0)
existing_scale3 = get_attr_safe(order, "scale3", None)
existing_scale3_qty = float(get_attr_safe(order, "scale3_qty", 0.0) or 0.0)

has_existing_byproducts = (
    (existing_scale1 is not None and existing_scale1 != "") or
    (existing_scale2 is not None and existing_scale2 != "") or
    (existing_scale3 is not None and existing_scale3 != "") or
    existing_scale1_qty > 0 or existing_scale2_qty > 0 or existing_scale3_qty > 0
)

if has_existing_byproducts and confirmed_qty_so_far > 0:
    # RESTART scenario: Byproduct scales already exist, PRESERVE them
    print(f"🔒 RESTART detected - preserving existing byproduct scales")
    print(f"   scale1: {existing_scale1} ({existing_scale1_qty:.4f})")
    print(f"   ✅ Byproduct scales will NOT be re-captured")
else:
    # BRAND NEW order: Capture byproduct baselines fresh
    print(f"🆕 BRAND NEW order - capturing byproduct baselines fresh")
    byproduct_baselines = _capture_byproduct_baselines(version, baselines, order=order)
    _set_byproduct_scales(order, version, baselines)
```

### Detection Logic:

**Brand New Order:**
- `scale1` is None or empty string
- `scale1_qty` = 0
- `confirmed_qty_so_far` = 0
- **Action:** Capture byproduct baselines fresh from SCADA ✅

**Restarted Order:**
- `scale1` is set (e.g., "WG501")
- `scale1_qty` > 0 (e.g., 500.00 from user modification)
- `confirmed_qty_so_far` > 0
- **Action:** SKIP byproduct capture, preserve existing values ✅

## Changes Made

### 1. init_and_start_order_worker() Function (order_validation.py)

**Location:** Lines 7848-7883

**Before:**
```python
if order_type == "MILLING":
    version = get_attr_safe(order, "version", "").strip().upper()
    byproduct_baselines = _capture_byproduct_baselines(version, baselines, order=order)
    _set_byproduct_scales(order, version, byproduct_baselines)
```

**After:**
```python
if order_type == "MILLING":
    version = get_attr_safe(order, "version", "").strip().upper()
    
    # Check if byproduct scales already exist
    existing_scale1 = get_attr_safe(order, "scale1", None)
    existing_scale1_qty = float(get_attr_safe(order, "scale1_qty", 0.0) or 0.0)
    # ... check scale2, scale3
    
    has_existing_byproducts = (
        (existing_scale1 is not None and existing_scale1 != "") or
        # ... other checks
    )
    
    if has_existing_byproducts and confirmed_qty_so_far > 0:
        # RESTART: Preserve existing scales, don't re-capture
        print(f"🔒 RESTART - preserving byproduct scales")
    else:
        # BRAND NEW: Capture fresh
        byproduct_baselines = _capture_byproduct_baselines(version, baselines, order=order)
        _set_byproduct_scales(order, version, byproduct_baselines)
```

### 2. /start Endpoint (order_validation.py)

**Location:** Lines 9902-9945

**Same logic applied to manual start endpoint**

## Data Flow After Fix

### Scenario 1: Brand New Order (First Time Start)

```
1. User starts new order 000012002907
2. System checks:
   - scale1 = None ✓
   - scale1_qty = 0 ✓
   - confirmed_qty_so_far = 0 ✓
3. Decision: BRAND NEW ORDER
4. Capture byproduct baselines from SCADA:
   - WG501 = 460.20031 (fresh from SCADA)
   - WG503 = 4.07038 (fresh from SCADA)
5. Save to database:
   - scale1 = "WG501", scale1_qty = 460.20031
   - scale2 = "WG503", scale2_qty = 4.07038
```

### Scenario 2: Order Restart After User Modification

```
1. User previously modified: WG501 = 500.00 (saved to DB)
2. User stops order
3. User starts order again
4. System checks:
   - scale1 = "WG501" ✓ (exists)
   - scale1_qty = 500.00 ✓ (>0, modified value)
   - confirmed_qty_so_far = 20.00 ✓ (>0)
5. Decision: RESTART - PRESERVE EXISTING
6. SKIP byproduct capture
7. Database values unchanged:
   - scale1 = "WG501", scale1_qty = 500.00 ✅ (user modification preserved)
   - scale2 = "WG503", scale2_qty = 4.07038 ✅
```

### Scenario 3: Order Pause/Resume

```
1. User modifies WG501 = 500.00, sends confirmation
2. Auto-validation pauses order (still InProgress)
3. Auto-validation resumes order
4. System checks:
   - scale1 = "WG501" ✓
   - scale1_qty = 500.00 ✓
   - confirmed_qty_so_far = 20.00 ✓
5. Decision: RESTART - PRESERVE
6. Byproduct scales NOT re-captured
7. User modification preserved ✅
```

## Equipment Scales (Main Production) - Unchanged

**Equipment scales (WG502, SL601, etc.) continue working as before:**

✅ Equipment baselines are ALWAYS re-captured on restart
✅ This is correct and needed for accurate production tracking
✅ Equipment scales reset to fresh SCADA values on every start
✅ Only BYPRODUCT scales are preserved

**Why?**
- Equipment scales track **cumulative production** - need fresh baselines to track new production after restart
- Byproduct scales track **cumulative byproducts** - should only be captured once and then modified by user

## Testing Steps

### Test 1: Brand New Order
1. Create and start a new MILLING order
2. Check progress dialog
3. **Expected:** WG501, WG503 show fresh SCADA values (e.g., 460.20031, 4.07038)
4. **Log:** "🆕 BRAND NEW order - capturing byproduct baselines fresh"

### Test 2: Restart After Modification
1. Start order, modify WG501 from 460.20031 to 500.00
2. Send confirmation (saves to DB)
3. Stop order
4. Start order again
5. Check progress dialog
6. **Expected:** WG501 shows 500.00 (not 460.20031) ✅
7. **Log:** "🔒 RESTART detected - preserving existing byproduct scales"

### Test 3: Pause/Resume with Modification
1. Start order with auto-validation
2. Modify WG501 to 500.00, send confirmation
3. Auto-validation completes this order, moves to next
4. Manually restart the order
5. **Expected:** WG501 shows 500.00 ✅

### Test 4: Multiple Confirmations
1. Start order
2. Modify WG501 to 500.00, send first confirmation
3. Production continues (WG502 increases)
4. Send second confirmation
5. **Expected:** WG501 still shows 500.00 (not reset) ✅

## Log Messages to Look For

**Brand New Order:**
```
🆕 [PO_NUMBER] BRAND NEW order - capturing byproduct baselines fresh
🛠 Setting by-product scales for PO_NUMBER / vCKF1
✅ [PO_NUMBER] Byproduct scales captured and set for brand new order
```

**Restarted Order:**
```
🔒 [PO_NUMBER] RESTART detected - preserving existing byproduct scales
   scale1: WG501 (500.0000)
   scale2: WG503 (4.0704)
   scale3: None (0.0000)
   ✅ Byproduct scales will NOT be re-captured - user modifications preserved
```

## Files Modified

1. **backend/routes/order_validation.py**
   - `init_and_start_order_worker()` function - Lines 7848-7883
   - `/start` endpoint - Lines 9902-9945

2. **backend/routes/process_orders.py**
   - `/manual-confirm` endpoint - Lines 4499-4607
   - Added byproduct quantity updates after confirmation

## Key Benefits

✅ Byproduct scales captured only ONCE (first time start)
✅ User modifications persisted across pause/resume/stop/restart
✅ Overflow calculation still works correctly
✅ Equipment scales (main production) continue updating normally
✅ No changes to equipment scale tracking logic
✅ Backward compatible - brand new orders work as before

## Important Notes

### What IS Preserved on Restart:
- `scale1`, `scale2`, `scale3` (byproduct scale tags)
- `scale1_qty`, `scale2_qty`, `scale3_qty` (byproduct quantities)
- `confirmed_qty` (total production)
- `weight_shift_a/b/c` (shift production totals)
- `confirmed_shift_a/b/c` (amounts sent to SAP)
- `last_confirmed_qty` (cumulative total sent to SAP)

### What IS Re-Captured on Restart:
- Equipment baseline values (WG502, SL601, etc.) - **This is correct!**
- Shift baselines (for tracking new production since restart)
- Current SCADA readings for equipment scales

### Why Byproducts Are Different:
- **Equipment scales (WG502):** Track main production, need fresh baselines to calculate deltas
- **Byproduct scales (WG501, WG503):** Track total byproducts, captured once at start, then only user can modify

