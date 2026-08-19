# Byproduct Quantities Update Fix - December 14, 2025

## Problem Statement
When users modified byproduct quantities (WG501, WG503) in the progress dialog and sent confirmation to SAP, the modified values were not being saved to the database. This caused:

1. Modified values not persisting after confirmation
2. Next time the progress dialog was opened, old SCADA values showed instead of the updated values
3. Database fields (scale1_qty, scale2_qty, scale3_qty) were being reset to 0, losing the user's modifications

## Root Cause

### Old Behavior (Before Fix):
```
User modifies byproduct in UI: WG501 = 460.20031 → 500.00
   ↓
Sends confirmation to SAP with modified value (500.00)
   ↓
Backend stores overflow in scale_overflows table
   ↓
Backend RESETS scale1_qty, scale2_qty, scale3_qty to 0 in database ❌
   ↓
User reopens dialog → Shows old SCADA value (460.20031), not modified value (500.00) ❌
```

### Why This Happened:

**Two Endpoints Were Resetting Byproduct Quantities:**

1. **`/api/orders/<po_number>/manual-confirm`** (order_validation.py, line 11255):
   - Calculated overflow correctly
   - Stored overflow in scale_overflows table ✅
   - Reset scale1_qty, scale2_qty, scale3_qty to 0 ❌

2. **`/api/process_orders/manual-confirm`** (process_orders.py, line 4301):
   - Calculated overflow correctly
   - Stored overflow in scale_overflows table ✅
   - Did NOT update scale1_qty, scale2_qty, scale3_qty (left unchanged) ❌

## Solution

### New Behavior (After Fix):
```
User modifies byproduct in UI: WG501 = 460.20031 → 500.00
   ↓
Sends confirmation to SAP with modified value (500.00)
   ↓
Backend stores overflow in scale_overflows table
   ↓
Backend UPDATES scale1_qty = 500.00 in database ✅
   ↓
User reopens dialog → Shows updated value (500.00) ✅
```

## Changes Made

### 1. Updated `/api/orders/<po_number>/manual-confirm` (order_validation.py)

**Lines ~11457-11463 (Offline Mode):**
```python
# OLD CODE:
set_attr_safe(order, "scale1_qty", 0)  # ❌ Reset to 0
set_attr_safe(order, "scale2_qty", 0)
set_attr_safe(order, "scale3_qty", 0)

# NEW CODE:
set_attr_safe(order, "scale1_qty", final_scale1_qty)  # ✅ Save modified value
set_attr_safe(order, "scale2_qty", final_scale2_qty)  # ✅ Save modified value
set_attr_safe(order, "scale3_qty", final_scale3_qty)  # ✅ Save modified value
```

**Lines ~11483-11489 (SAP Success):**
```python
# OLD CODE:
set_attr_safe(order, "scale1_qty", 0)  # ❌ Reset to 0
set_attr_safe(order, "scale2_qty", 0)
set_attr_safe(order, "scale3_qty", 0)

# NEW CODE:
set_attr_safe(order, "scale1_qty", final_scale1_qty)  # ✅ Save modified value
set_attr_safe(order, "scale2_qty", final_scale2_qty)  # ✅ Save modified value
set_attr_safe(order, "scale3_qty", final_scale3_qty)  # ✅ Save modified value
```

### 2. Updated `/api/process_orders/manual-confirm` (process_orders.py)

**Lines ~4499-4506 (Offline Mode):**
```python
# NEW CODE ADDED:
order.scale1_qty = scale1_qty  # ✅ Update to value sent to SAP
order.scale2_qty = scale2_qty  # ✅ Update to value sent to SAP
order.scale3_qty = scale3_qty  # ✅ Update to value sent to SAP
print(f"✅ Updated byproduct quantities in DB: scale1={scale1_qty:.4f}, scale2={scale2_qty:.4f}, scale3={scale3_qty:.4f}")
```

**Lines ~4600-4607 (SAP Success):**
```python
# NEW CODE ADDED:
order.scale1_qty = scale1_qty  # ✅ Update to value sent to SAP
order.scale2_qty = scale2_qty  # ✅ Update to value sent to SAP
order.scale3_qty = scale3_qty  # ✅ Update to value sent to SAP
print(f"✅ Updated byproduct quantities in DB: scale1={scale1_qty:.4f}, scale2={scale2_qty:.4f}, scale3={scale3_qty:.4f}")
```

### 3. UI Changes (ProcessOrderValidation.tsx)

**Confirmation Quantity Field:**
- Removed increment/decrement spinner controls
- Simple text input for numbers
- Lines ~5955: Added CSS to hide spinners

**Scrap Field:**
- Changed from mandatory to optional
- Removed red asterisk (*) and validation
- Changed placeholder to "Optional (default: 0)"
- Removed spinner controls
- Lines ~6045-6061, ~5332-5348

## How It Works Now

### Data Flow:

1. **User Opens Progress Dialog:**
   - Frontend fetches `/api/orders/{po_number}/progress`
   - Backend returns current scale1_qty, scale2_qty, scale3_qty from database
   - UI displays these values in byproduct override fields

2. **User Modifies Byproduct Values:**
   - Changes WG501 from 460.20031 to 500.00
   - Frontend stores modification in `manualConfirmData.custom_byproducts.scale1_qty`

3. **User Sends Confirmation:**
   - Frontend sends request to `/api/process_orders/manual-confirm` with:
     ```json
     {
       "po_number": "000012002907",
       "confirmed_qty": 20.00,
       "scale1_qty": 500.00,  // ✅ Modified value
       "scale2_qty": 4.07038,
       "scale3_qty": 0,
       "scrap": 0,
       "confirmed_text": "",
       "shift": "A",
       "operator": "manual"
     }
     ```

4. **Backend Processing:**
   - Calculates overflow: `current_scale1_qty - scale1_qty` (e.g., 460.20031 - 500.00)
   - If overflow > 0, stores in scale_overflows table
   - **Updates database:** `order.scale1_qty = 500.00` ✅
   - Sends confirmation to SAP with scale1_qty = 500.00
   - Commits changes to database

5. **User Reopens Dialog:**
   - Backend reads scale1_qty = 500.00 from database
   - UI shows updated value 500.00 ✅

### Overflow Handling:

**Case 1: User Reduces Byproduct (Creates Overflow)**
- Current: 460.20031, User sends: 400.00
- Overflow: 60.20031 stored in scale_overflows table
- Database: scale1_qty = 400.00
- Next order will get overflow added

**Case 2: User Increases Byproduct (No Overflow)**
- Current: 460.20031, User sends: 500.00
- Overflow: 0 (negative overflow not allowed)
- Database: scale1_qty = 500.00
- Value accepted and saved

**Case 3: User Keeps Same Value**
- Current: 460.20031, User sends: 460.20031
- Overflow: 0
- Database: scale1_qty = 460.20031
- No change

## Testing Steps

### Test 1: Modify and Confirm
1. Open progress dialog for an InProgress order
2. Modify WG501 from 460.20031 to 500.00
3. Click "Send Confirmation to SAP"
4. Close and reopen progress dialog
5. **Expected:** WG501 shows 500.00 (not 460.20031)

### Test 2: Multiple Confirmations
1. Open progress dialog
2. Modify WG501 to 500.00, send confirmation
3. Continue production (worker accumulates more)
4. Open dialog again
5. **Expected:** WG501 still shows 500.00 (preserved)
6. Modify to 520.00, send confirmation
7. Reopen dialog
8. **Expected:** WG501 shows 520.00

### Test 3: Overflow Transfer
1. Order 1: Modify WG501 from 460 to 400 (reduce by 60)
2. Send confirmation
3. Complete Order 1
4. Start Order 2 (same material/version)
5. **Expected:** Order 2's WG501 starts at 60 (overflow applied)

## Database Impact

### Fields Updated After Confirmation:
- `last_confirmed_qty`: Total sent to SAP (cumulative)
- `confirmed_shift_a/b/c`: Amount sent in each shift
- **`scale1_qty`**: Updated to value sent to SAP ✅ NEW
- **`scale2_qty`**: Updated to value sent to SAP ✅ NEW
- **`scale3_qty`**: Updated to value sent to SAP ✅ NEW

### Fields NOT Touched:
- `confirmed_qty`: Calculated by worker from SCADA
- `weight_shift_a/b/c`: SCADA production totals
- `baseline_*`: Original shift baselines

## Files Modified

1. **backend/routes/order_validation.py**
   - Updated `/api/orders/<po_number>/manual-confirm` endpoint
   - Lines ~11457-11463 (offline mode)
   - Lines ~11483-11489 (SAP success)

2. **backend/routes/process_orders.py**
   - Updated `/api/process_orders/manual-confirm` endpoint
   - Lines ~4499-4506 (offline mode)
   - Lines ~4600-4607 (SAP success)

3. **Frontend/client/src/pages/hercules-sfms/ProcessOrderValidation.tsx**
   - Made scrap field optional
   - Removed spinner controls from input fields
   - Updated validation logic

## Key Benefits

✅ Byproduct modifications persist in database
✅ Values shown in UI match what was sent to SAP
✅ Overflow calculation still works correctly
✅ Worker continues accumulating from SCADA normally
✅ No interference between user modifications and SCADA updates
✅ Scrap field now optional (defaults to 0)
✅ Clean input fields (no spinner controls)

