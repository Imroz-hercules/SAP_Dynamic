Drafting a markdown document describing these requirements:


[3 tools called]


Creating a markdown document describing these requirements:


[2 tools called]


Markdown document:

```markdown
# Order Validation Page - Byproduct Scales and Manual Confirmation Features

## Overview
This document describes two features to be implemented in the Order Validation page, specifically for MILLING orders.

---

## Feature 1: Byproduct Scales Columns Display (MILLING Orders Only)

### Requirement
Add two columns in the Order Validation table to display byproduct scales readings, **only for MILLING orders**.

### Implementation Details

#### 1.1 Table Header
- Add two new columns in the table header (after the "UNIT" column and before "Confirm"):
  - Column 1: "Byproduct Scale 1" (or use the actual scale name if available, e.g., "WG501")
  - Column 2: "Byproduct Scale 2" (or use the actual scale name if available, e.g., "WG503")
- These columns should **only be visible for MILLING orders** (hide for PACKING orders)

#### 1.2 Data Display
- For each MILLING order row:
  - **Column 1 (Byproduct Scale 1)**:
    - Display the scale name (e.g., "WG501") as a label/tag
    - Display the current quantity value (`scale1_qty`) from the order data
    - Format: Show value with appropriate decimal places (e.g., 5 decimal places: `1440.20031`)
    - If no byproduct scale 1 is defined for the order, show "-" or empty
  - **Column 2 (Byproduct Scale 2)**:
    - Display the scale name (e.g., "WG503") as a label/tag
    - Display the current quantity value (`scale2_qty`) from the order data
    - Format: Show value with appropriate decimal places (e.g., 5 decimal places: `4.07038`)
    - If no byproduct scale 2 is defined for the order, show "-" or empty

#### 1.3 Data Source
- Read from order object:
  - `order.scale1` - Scale 1 name/tag
  - `order.scale1_qty` - Scale 1 quantity value
  - `order.scale2` - Scale 2 name/tag
  - `order.scale2_qty` - Scale 2 quantity value
- These values should come from the backend API response when fetching orders

#### 1.4 Conditional Display
- Only show these columns when:
  - Order type is "MILLING"
  - At least one of the byproduct scales (scale1 or scale2) has a value or is defined
- For PACKING orders, these columns should be hidden or show "-"

---

## Feature 2: Manual Confirmation for Accumulated Scale Values

### Requirement
At any point during order progress, when there are accumulated scale values (current production > 0), provide a manual confirmation option that:
1. Sends current accumulated values to SAP confirmation
2. Resets the "Current" value to 0 after confirmation
3. Updates the "Confirm" column with the last manually confirmed value

### Implementation Details

#### 2.1 Manual Confirmation Button/Option
- **Location**: In the "Actions" column of the Order Validation table
- **Visibility**: Show the "Manual Confirm" button only when:
  - Order status is "InProgress"
  - Current accumulated value > 0 (i.e., `confirmed_qty > 0` or `current > 0`)
- **Button Label**: "Manual Confirm" or "Confirm Now"
- **Button Style**: Distinctive (e.g., green or blue) to differentiate from other action buttons

#### 2.2 Manual Confirmation Process

**Step 1: User Clicks "Manual Confirm"**
- Display a confirmation dialog/modal asking user to confirm:
  - "Send current accumulated production to SAP?"
  - Show current values that will be sent:
    - Main production value (current accumulated)
    - Byproduct scale 1 value (if applicable)
    - Byproduct scale 2 value (if applicable)
    - Byproduct scale 3 value (if applicable)

**Step 2: Send to SAP**
- When user confirms:
  - Call the SAP confirmation endpoint with current values:
    - `confirmed_qty` = current accumulated value
    - `scale1_qty` = current scale1_qty value
    - `scale2_qty` = current scale2_qty value
    - `scale3_qty` = current scale3_qty value
  - Include all other required SAP payload fields (PO number, material, version, batch, shift, etc.)
  - Mark this as a "Manual Confirmation" (not automatic)

**Step 3: After Successful SAP Confirmation**
- Update the database:
  - Set `last_confirmed_qty` = current `confirmed_qty` value (the value that was just sent)
  - Reset `confirmed_qty` = 0 (start fresh for next accumulation)
  - Reset `scale1_qty` = 0 (if applicable)
  - Reset `scale2_qty` = 0 (if applicable)
  - Reset `scale3_qty` = 0 (if applicable)
  - Update `last_manual_confirm_time` = current timestamp (new field to track when manual confirmation happened)

**Step 4: Update UI Display**
- **"Confirm" Column**: Display the `last_confirmed_qty` value (the value that was just confirmed)
- **"Current" Column**: Display 0.00 (since `confirmed_qty` was reset to 0)
- **"Remaining" Column**: Recalculate as `target - last_confirmed_qty`
- **Byproduct Scale Columns**: Show 0.00 for scales that were reset

#### 2.3 Database Schema Changes
- Ensure the following fields exist in the `process_orders` table:
  - `last_confirmed_qty` (DECIMAL) - Stores the last manually confirmed quantity
  - `last_manual_confirm_time` (DATETIME) - Timestamp of last manual confirmation (optional, for tracking)
  - `confirmed_qty` (DECIMAL) - Current accumulated quantity (resets to 0 after manual confirmation)

#### 2.4 API Endpoint
- Create or use existing endpoint: `POST /api/orders/<po_number>/manual-confirm`
- Request body:
  ```json
  {
    "confirmed_qty": 40.00,
    "scale1_qty": 1440.20031,
    "scale2_qty": 4.07038,
    "scale3_qty": 0.0,
    "shift": "B",
    "manual_confirm": true
  }
  ```
- Response:
  ```json
  {
    "success": true,
    "message": "Manual confirmation sent to SAP successfully",
    "last_confirmed_qty": 40.00,
    "confirmed_at": "2025-12-14T12:19:00Z"
  }
  ```

#### 2.5 Backend Logic
- When manual confirmation is received:
  1. Send confirmation to SAP using existing SAP confirmation service
  2. Update `last_confirmed_qty` = current `confirmed_qty`
  3. Reset `confirmed_qty` = 0
  4. Reset byproduct scale quantities to 0
  5. Log the manual confirmation event
  6. Return success response

#### 2.6 Frontend Display Logic
- **"Confirm" Column**:
  - Display: `order.last_confirmed_qty || 0`
  - This shows the cumulative total of all manually confirmed values
  - Format: Show with 2 decimal places (e.g., "40.00 TO")
  
- **"Current" Column**:
  - Display: `order.confirmed_qty || 0`
  - This shows the current accumulated production since last manual confirmation
  - Format: Show with 2 decimal places (e.g., "15.50 TO")
  - After manual confirmation, this will be 0.00

- **"Remaining" Column**:
  - Calculate: `target - (last_confirmed_qty + confirmed_qty)`
  - Or: `target - last_confirmed_qty` (since confirmed_qty resets to 0 after manual confirm)

#### 2.7 Multiple Manual Confirmations
- Users can perform multiple manual confirmations during an order's lifecycle
- Each manual confirmation:
  - Sends the current accumulated value to SAP
  - Adds to `last_confirmed_qty` (cumulative total)
  - Resets `confirmed_qty` to 0
- Example:
  - Initial: confirmed_qty = 40, last_confirmed_qty = 0
  - Manual Confirm 1: Send 40 to SAP → last_confirmed_qty = 40, confirmed_qty = 0
  - Production continues: confirmed_qty = 25, last_confirmed_qty = 40
  - Manual Confirm 2: Send 25 to SAP → last_confirmed_qty = 65, confirmed_qty = 0

---

## Technical Notes

### Files to Modify

#### Frontend
- `Frontend/client/src/pages/hercules-sfms/ProcessOrderValidation.tsx`
  - Add byproduct scale columns to table header (MILLING only)
  - Add byproduct scale data display in table rows (MILLING only)
  - Add "Manual Confirm" button in Actions column
  - Implement manual confirmation dialog/modal
  - Update "Confirm" column to show `last_confirmed_qty`
  - Update "Current" column display logic

#### Backend
- `backend/routes/order_validation.py` or `backend/routes/process_orders.py`
  - Create/update manual confirmation endpoint
  - Implement logic to send to SAP and reset values
- `backend/services/sap_confirmation.py`
  - Ensure manual confirmations are properly sent to SAP
- Database schema
  - Ensure `last_confirmed_qty` field exists
  - Add `last_manual_confirm_time` field if needed

### Important Considerations

1. **MILLING Orders Only**: Byproduct scale columns should only appear for MILLING orders
2. **Data Persistence**: `last_confirmed_qty` should persist across order restarts and shift changes
3. **SAP Integration**: Manual confirmations should use the same SAP payload structure as automatic confirmations
4. **Validation**: Ensure manual confirmation can only be performed when order is "InProgress" and has accumulated production
5. **Error Handling**: Handle SAP confirmation failures gracefully (don't reset values if SAP send fails)
6. **User Feedback**: Show success/error messages after manual confirmation attempt

---

## Testing Checklist

- [ ] Byproduct scale columns appear only for MILLING orders
- [ ] Byproduct scale columns show correct scale names and values
- [ ] Byproduct scale columns are hidden for PACKING orders
- [ ] Manual Confirm button appears only when order is InProgress and has accumulated production
- [ ] Manual Confirm button opens confirmation dialog with current values
- [ ] Manual confirmation sends correct values to SAP
- [ ] After manual confirmation, "Confirm" column shows `last_confirmed_qty`
- [ ] After manual confirmation, "Current" column shows 0.00
- [ ] After manual confirmation, byproduct scale columns show 0.00
- [ ] Multiple manual confirmations accumulate correctly in `last_confirmed_qty`
- [ ] Production continues to accumulate in `confirmed_qty` after manual confirmation
- [ ] Error handling works correctly if SAP confirmation fails
```

This document describes both features
# SAP Confirmation Fallback Strategy - Implementation Guide

## Overview
This document describes a robust fallback strategy to prevent system crashes, SAP issues, and order loss during confirmation pushes. The strategy handles two critical failure scenarios with proper error isolation and recovery mechanisms.

---

## Problem Statement

When pushing order confirmations to SAP, we need to handle two failure cases:

1. **VPN Disconnected**: Network/VPN connection is down before attempting to send to SAP
2. **SAP Error Response**: Request reaches SAP successfully, but SAP returns an error response indicating the confirmation was not received/processed

Both cases must be handled gracefully without losing orders or crashing the system.

---

## Current State Analysis

### Existing Implementation
- VPN check exists in `push_confirmation()` endpoint
- Failed SAP responses are logged to `error_log` table
- Some failed orders are stored in `offline_confirmations` table
- Error log has reprocess functionality (`/api/error-log/<id>/reprocess`)

### Gaps and Issues
1. VPN check may not be consistently applied across all confirmation paths
2. SAP error responses may not always be properly isolated in error_log
3. Failed orders may not always be stored in offline_confirmations for retry
4. Error log reprocess may not handle all edge cases
5. No clear distinction between VPN errors and SAP rejection errors

---

## Required Implementation

### Case 1: VPN Disconnected Before Push

#### 1.1 VPN Check Location
**All confirmation entry points must check VPN before attempting SAP push:**

- `POST /api/process_orders/push-confirmation` (Manual push)
- `POST /api/orders/<po_number>/validate` (Validation endpoint)
- `services/shift_auto_confirm.py::auto_push_shift_confirmation()` (Auto shift-end)
- `services/sap_confirmation.py::confirm_online()` (Direct service calls)
- Any other endpoint that calls SAP confirmation

#### 1.2 VPN Check Logic
# Pseudo-code for VPN check
from utils.vpn_check import check_vpn_connection

# Skip VPN check in mock mode
if sap_service.mock_mode:
    vpn_status = {"connected": True, "message": "Mock mode - skipping VPN check"}
else:
    vpn_status = check_vpn_connection()

if not vpn_status["connected"]:
    # VPN DISCONNECTED - Store in offline_confirmations
    # DO NOT attempt to send to SAP
    # DO NOT log to error_log (this is not an error, just offline mode)
    store_in_offline_confirmations(orders_data)
    return {
        "success": False,
        "offline_mode": True,
        "message": "VPN disconnected - orders stored for offline confirmation",
        "stored_count": len(orders_data)
    }#### 1.3 Offline Storage Requirements
When VPN is disconnected:
1. **Store ALL orders** in `offline_confirmations` table:
   - Set `status = 'pending'`
   - Store full `sap_payload` as JSON
   - Set `validation_method` appropriately (Manual/Automatic/ShiftAuto)
   - Set `retry_count = 0`
   - Preserve all order data (confirmed_weight, shift, material, version, etc.)

2. **DO NOT**:
   - Attempt to send to SAP
   - Log to error_log (this is expected offline behavior, not an error)
   - Update order status to "Confirmed" (wait until successfully sent to SAP)

3. **Return response**:
   - HTTP 200 (not an error, just offline mode)
   - Include `offline_mode: true` flag
   - Include count of stored orders
   - Include list of stored PO numbers

#### 1.4 Implementation Points

**File: `backend/routes/process_orders.py`**
- Function: `push_confirmation()`
- Location: Before any SAP API call
- Action: Check VPN, if disconnected → store in offline_confirmations, return offline response

**File: `backend/services/shift_auto_confirm.py`**
- Function: `auto_push_shift_confirmation()`
- Location: Before calling `confirm_orders_batch()`
- Action: Check VPN, if disconnected → store validated orders in offline_confirmations

**File: `backend/routes/order_validation.py`**
- Function: `end_shift_and_confirm()`
- Location: Before calling `sap_service.push_confirmation()`
- Action: Check VPN, if disconnected → store in offline_confirmations

**File: `backend/services/sap_confirmation.py`**
- Function: `confirm_online()`
- Location: At the very beginning, before any network calls
- Action: Check VPN, if disconnected → raise exception or return offline response (to be caught by caller)

---

### Case 2: SAP Error Response After Successful Push

#### 2.1 Problem Definition
When:
- VPN is connected (request reaches SAP)
- HTTP request succeeds (status 200/201)
- SAP processes the request
- **BUT** SAP response indicates error/rejection for one or more orders

These orders must be:
1. Isolated in `error_log` table (not in offline_confirmations)
2. Available for reprocessing with updated scrap/confirmed_text
3. Not lost or forgotten

#### 2.2 SAP Response Parsing
SAP returns a JSON array with per-order status:
[
  {
    "PROCESS_ORDER": "000012002900",
    "MESSAGE": "Error: Order already being processed",
    "STATUS": "Error"
  },
  {
    "PROCESS_ORDER": "000012002901",
    "MESSAGE": "Confirmations have been entered successfully",
    "STATUS": "Success"
  }
]#### 2.3 Error Detection Logichon
# After receiving SAP response (status 200/201)
sap_orders = json.loads(sap_response_text)

successful_orders = []
failed_orders = []

for sap_order in sap_orders:
    message = sap_order.get('MESSAGE', '').lower()
    po_number = sap_order.get('PROCESS_ORDER', '').lstrip('0')
    
    # Success indicators
    success_indicators = ['saved', 'confirmations have been entered', 'confirmed', 'successfully', 'success']
    has_success = any(indicator in message for indicator in success_indicators)
    
    # Error indicators
    error_indicators = [
        'already being processed', 'error', 'failed', 'locked', 
        'not found', 'invalid', 'reject', 'rejected', 'denied', 
        'refused', 'cannot', 'unable', 'warning', 'exception'
    ]
    has_error = any(indicator in message for indicator in error_indicators)
    
    if has_success and not has_error:
        successful_orders.append(po_number)
    else:
        failed_orders.append({
            "po_number": po_number,
            "error": sap_order.get('MESSAGE', 'SAP confirmation rejected'),
            "sap_response": sap_order
        })#### 2.4 Error Isolation Requirements

**For each failed order:**

1. **Log to `error_log` table**:
   
   log_order_error(
       po_number=po_clean,
       error_type="sap_failed",  # Distinguish from VPN errors
       error_message=error_msg,
       payload={
           "sent_payload": original_order_data,  # Full order data that was sent
           "sap_reply": sap_error_response,      # SAP's error response
           "sap_response": full_sap_response,   # Full SAP response array
           "confirmation_type": "online",
           "timestamp": datetime.now().isoformat(),
           "vpn_connected": True,  # Important: VPN was connected
           "http_status": 200      # HTTP request succeeded
       },
       source="sap_online"
   )
   2. **DO NOT** store in `offline_confirmations` (this is a SAP rejection, not a network issue)

3. **DO NOT** update order status to "Confirmed" (SAP rejected it)

4. **Preserve order state**:
   - Keep order in current status (InProgress/Validated)
   - Do not reset confirmed_qty
   - Allow user to reprocess with corrected data

#### 2.5 Reprocess Functionality

**Error Log Entry Structure:**
- `error_type = "sap_failed"` (distinguishes from VPN errors)
- `status = "Open"` (can be changed to "Resolved" after successful reprocess)
- `payload.sent_payload` = Original order data that was sent to SAP
- `payload.sap_reply` = SAP's error response for this order
- `payload.vpn_connected = True` = Indicates this was a SAP rejection, not VPN issue

**Reprocess Endpoint: `POST /api/error-log/<log_id>/reprocess`**

**Request Body:**
{
  "scrap": 0.0,              // Optional: Updated scrap value
  "confirmed_text": "",     // Optional: Updated confirmed text
  "retry_vpn_check": false  // Optional: Force VPN check before retry
}
**Reprocess Logic:**
1. Retrieve error log entry
2. Extract `sent_payload` from `payload`
3. Update payload with new scrap/confirmed_text if provided
4. **Check VPN** (if `retry_vpn_check = true` or if original error was network-related)
5. If VPN disconnected → store in offline_confirmations (Case 1)
6. If VPN connected → send to SAP again
7. If SAP succeeds → mark error_log as "Resolved"
8. If SAP fails again → update error_log with new error, keep status "Open"

**Frontend UI:**
- Show error log entries with `error_type = "sap_failed"` in Error Log modal
- Provide "Reprocess" button for each entry
- Reprocess modal should allow editing:
  - Scrap value
  - Confirmed text
  - Option to force VPN check
- Show original error message and SAP response

---

## Implementation Checklist

### Backend Changes

#### 1. Ensure VPN Check in All Confirmation Paths
- [ ] `backend/routes/process_orders.py::push_confirmation()`
  - [ ] Add VPN check before SAP call
  - [ ] Store in offline_confirmations if VPN down
  - [ ] Return offline response (not error)
  
- [ ] `backend/services/shift_auto_confirm.py::auto_push_shift_confirmation()`
  - [ ] Verify VPN check exists
  - [ ] Ensure offline storage works correctly
  
- [ ] `backend/routes/order_validation.py::end_shift_and_confirm()`
  - [ ] Verify VPN check exists
  - [ ] Ensure offline storage works correctly
  
- [ ] `backend/services/sap_confirmation.py::confirm_online()`
  - [ ] Add VPN check at function start (before any network calls)
  - [ ] If VPN down, raise `VPNDisconnectedException` or return offline response
  - [ ] Ensure callers handle VPN exception properly

#### 2. Improve SAP Error Response Handling
- [ ] `backend/services/sap_confirmation.py::confirm_online()`
  - [ ] Ensure ALL failed orders are logged to error_log
  - [ ] Ensure failed orders are NOT stored in offline_confirmations (SAP rejection ≠ VPN issue)
  - [ ] Ensure failed orders are NOT marked as "Confirmed"
  - [ ] Add `vpn_connected: True` flag to error_log payload
  - [ ] Add `http_status` to error_log payload
  
- [ ] `backend/services/sap_confirmation.py::confirm_offline()`
  - [ ] Apply same error handling logic
  - [ ] Distinguish between network errors and SAP rejections

#### 3. Enhance Error Log Reprocess
- [ ] `backend/routes/error_log_routes.py::reprocess_error_order()`
  - [ ] Add VPN check before reprocessing
  - [ ] If VPN down → store in offline_confirmations (Case 1)
  - [ ] If VPN up → send to SAP (Case 2 retry)
  - [ ] Update error_log status appropriately
  - [ ] Handle both success and failure scenarios

#### 4. Database Schema
- [ ] Verify `error_log` table has required fields:
  - `id` (primary key)
  - `po_number` (indexed)
  - `error_type` (sap_failed / vpn_disconnected / etc.)
  - `error_message`
  - `payload` (JSONB - stores full context)
  - `source` (sap_online / sap_offline / etc.)
  - `status` (Open / Resolved)
  - `created_at`
  - `resolved_at`

- [ ] Verify `offline_confirmations` table has required fields:
  - `id` (primary key)
  - `order_id` (indexed)
  - `status` (pending / sent / failed)
  - `sap_payload` (JSONB)
  - `retry_count`
  - All order fields (material, version, confirmed_weight, etc.)

### Frontend Changes

#### 1. Error Log Display
- [ ] Show error log entries in Error Log modal
- [ ] Distinguish between error types:
  - VPN errors → Show "VPN Disconnected" badge
  - SAP errors → Show "SAP Rejected" badge
- [ ] Display error message and SAP response
- [ ] Show payload details (expandable)

#### 2. Reprocess Functionality
- [ ] Add "Reprocess" button for `sap_failed` errors
- [ ] Create Reprocess Modal:
  - PO Number (read-only)
  - Material (read-only)
  - Original Error Message (read-only)
  - Scrap (editable, default from payload)
  - Confirmed Text (editable, default from payload)
  - "Force VPN Check" checkbox (optional)
  - "Cancel" and "Reprocess" buttons
- [ ] Call `/api/error-log/<id>/reprocess` endpoint
- [ ] Handle success/error responses
- [ ] Refresh error log after successful reprocess

#### 3. Offline Confirmations Display
- [ ] Show offline confirmations in separate modal/section
- [ ] Distinguish from error log (these are not errors, just queued)
- [ ] Provide "Send Now" button for each offline confirmation
- [ ] Show retry count and last attempt time

---

## Error Flow Diagrams

### Case 1: VPN Disconnected
1.3 Offline Storage Requirements
When VPN is disconnected:
Store ALL orders in offline_confirmations table:
Set status = 'pending'
Store full sap_payload as JSON
Set validation_method appropriately (Manual/Automatic/ShiftAuto)
Set retry_count = 0
Preserve all order data (confirmed_weight, shift, material, version, etc.)
DO NOT:
Attempt to send to SAP
Log to error_log (this is expected offline behavior, not an error)
Update order status to "Confirmed" (wait until successfully sent to SAP)
Return response:
HTTP 200 (not an error, just offline mode)
Include offline_mode: true flag
Include count of stored orders
Include list of stored PO numbers
1.4 Implementation Points
File: backend/routes/process_orders.py
Function: push_confirmation()
Location: Before any SAP API call
Action: Check VPN, if disconnected → store in offline_confirmations, return offline response
File: backend/services/shift_auto_confirm.py
Function: auto_push_shift_confirmation()
Location: Before calling confirm_orders_batch()
Action: Check VPN, if disconnected → store validated orders in offline_confirmations
File: backend/routes/order_validation.py
Function: end_shift_and_confirm()
Location: Before calling sap_service.push_confirmation()
Action: Check VPN, if disconnected → store in offline_confirmations
File: backend/services/sap_confirmation.py
Function: confirm_online()
Location: At the very beginning, before any network calls
Action: Check VPN, if disconnected → raise exception or return offline response (to be caught by caller)
Case 2: SAP Error Response After Successful Push
2.1 Problem Definition
When:
VPN is connected (request reaches SAP)
HTTP request succeeds (status 200/201)
SAP processes the request
BUT SAP response indicates error/rejection for one or more orders
These orders must be:
Isolated in error_log table (not in offline_confirmations)
Available for reprocessing with updated scrap/confirmed_text
Not lost or forgotten
2.2 SAP Response Parsing
SAP returns a JSON array with per-order status:
[  {    "PROCESS_ORDER": "000012002900",    "MESSAGE": "Error: Order already being processed",    "STATUS": "Error"  },  {    "PROCESS_ORDER": "000012002901",    "MESSAGE": "Confirmations have been entered successfully",    "STATUS": "Success"  }]
2.3 Error Detection Logic
# After receiving SAP response (status 200/201)sap_orders = json.loads(sap_response_text)successful_orders = []failed_orders = []for sap_order in sap_orders:    message = sap_order.get('MESSAGE', '').lower()    po_number = sap_order.get('PROCESS_ORDER', '').lstrip('0')        # Success indicators    success_indicators = ['saved', 'confirmations have been entered', 'confirmed', 'successfully', 'success']    has_success = any(indicator in message for indicator in success_indicators)        # Error indicators    error_indicators = [        'already being processed', 'error', 'failed', 'locked',         'not found', 'invalid', 'reject', 'rejected', 'denied',         'refused', 'cannot', 'unable', 'warning', 'exception'    ]    has_error = any(indicator in message for indicator in error_indicators)        if has_success and not has_error:        successful_orders.append(po_number)    else:        failed_orders.append({            "po_number": po_number,            "error": sap_order.get('MESSAGE', 'SAP confirmation rejected'),            "sap_response": sap_order        })
2.4 Error Isolation Requirements
For each failed order:
Log to error_log table:
   log_order_error(       po_number=po_clean,       error_type="sap_failed",  # Distinguish from VPN errors       error_message=error_msg,       payload={           "sent_payload": original_order_data,  # Full order data that was sent           "sap_reply": sap_error_response,      # SAP's error response           "sap_response": full_sap_response,   # Full SAP response array           "confirmation_type": "online",           "timestamp": datetime.now().isoformat(),           "vpn_connected": True,  # Important: VPN was connected           "http_status": 200      # HTTP request succeeded       },       source="sap_online"   )ed)- **SAP Rejection**: Order status remains unchanged (InProgress/Validated)- **SAP Success**: Order status updated to "Confirmed"- Only update status after **successful** SAP confirmation### Rule 4: Reprocess Capability- All `error_log` entries with `error_type='sap_failed'` must be reprocessable- Reprocess must allow editing scrap and confirmed_text- Reprocess must check VPN before retry- Reprocess must handle both VPN and SAP errors---## Testing Scenarios### Test Case 1: VPN Disconnected - Manual Push1. Disconnect VPN2. Click "Send" button for validated order3. **Expected**: Order stored in `offline_confirmations`, status='pending'4. **Expected**: Response shows `offline_mode: true`5. **Expected**: Order status remains "Validated" (not "Confirmed")### Test Case 2: VPN Disconnected - Auto Shift-End1. Disconnect VPN2. Wait for 5 minutes before shift end3. **Expected**: Validated orders stored in `offline_confirmations`4. **Expected**: No error_log entries created5. **Expected**: Orders remain "Validated"### Test Case 3: SAP Rejection - Single Order1. Connect VPN2. Send order to SAP3. Mock SAP to return error for this order4. **Expected**: Order logged to `error_log` with `error_type='sap_failed'`5. **Expected**: Order NOT stored in `offline_confirmations`6. **Expected**: Order status remains "Validated"7. **Expected**: Error log shows "Reprocess" button### Test Case 4: SAP Rejection - Multiple Orders1. Connect VPN2. Send 3 orders to SAP3. Mock SAP to return: 1 success, 2 errors4. **Expected**: 1 order marked as "Confirmed"5. **Expected**: 2 orders logged to `error_log`6. **Expected**: 2 orders remain "Validated"### Test Case 5: Reprocess - VPN Down1. Select `sap_failed` error from error_log2. Click "Reprocess"3. Disconnect VPN before submitting4. **Expected**: Order stored in `offline_confirmations`5. **Expected**: Error log marked as "Resolved"### Test Case 6: Reprocess - SAP Success1. Select `sap_failed` error from error_log2. Click "Reprocess"3. Edit scrap/confirmed_text4. Submit (VPN connected, SAP accepts)5. **Expected**: Order sent to SAP successfully6. **Expected**: Error log marked as "Resolved"7. **Expected**: Order status updated to "Confirmed"### Test Case 7: Reprocess - SAP Rejection Again1. Select `sap_failed` error from error_log2. Click "Reprocess"3. Submit (VPN connected, SAP rejects again)4. **Expected**: Error log updated with new error5. **Expected**: Error log status remains "Open"6. **Expected**: Order status remains "Validated"---## Error Log Payload Structure### VPN Disconnected (should not be in error_log, but if logged):{  "error_type": "vpn_disconnected",  "vpn_connected": false,  "sent_payload": {...},  "timestamp": "2025-12-14T12:19:00Z"}### SAP Rejection:{  "error_type": "sap_failed",  "vpn_connected": true,  "http_status": 200,  "sent_payload": {    "po_number": "000012002900",    "material": "...",    "confirmed_weight": 40.0,    "shift": "B",    "scrap": 0.0,    "confirmed_text": "",    ...  },  "sap_reply": {    "PROCESS_ORDER": "12002900",    "MESSAGE": "Error: Order already being processed",    "STATUS": "Error"  },  "sap_response": "[{...}]",  "confirmation_type": "online",  "timestamp": "2025-12-14T12:19:00Z"}---## API Endpoints Summary### Existing Endpoints (Verify/Enhance)- `POST /api/process_orders/push-confirmation` - Add VPN check, offline storage- `POST /api/error-log/<id>/reprocess` - Add VPN check, handle offline mode- `GET /api/error-log/` - List error log entries- `GET /api/error-log/count` - Get error count### New Endpoints (If Needed)- `GET /api/error-log/<id>` - Get single error log entry details- `POST /api/error-log/<id>/resolve` - Manually mark as resolved- `GET /api/offline-confirmations/` - List offline confirmations- `POST /api/offline-confirmations/<id>/send` - Manually send offline confirmation---## Implementation Priority### Phase 1: Critical (Prevent Order Loss)1. ✅ Ensure VPN check in all confirmation paths2. ✅ Ensure offline storage for VPN disconnections3. ✅ Ensure error_log for SAP rejections4. ✅ Ensure no orders are silently lost### Phase 2: Important (Error Recovery)1. ✅ Enhance reprocess functionality2. ✅ Add VPN check to reprocess3. ✅ Improve error log UI4. ✅ Add reprocess modal with scrap/confirmed_text editing### Phase 3: Nice to Have (Monitoring)1. Add error log dashboard2. Add offline confirmations monitoring3. Add retry statistics4. Add alerting for high error rates---## Notes- **Mock Mode**: VPN checks should be skipped in mock mode (`MOCK_SAP_MODE=true`)- **Order Status**: Only update to "Confirmed" after **successful** SAP confirmation- **Duplicate Prevention**: Check for duplicates in both `offline_confirmations` and `error_log` before storing- **Retry Logic**: Offline confirmations can be retried automatically or manually- **Error Log**: SAP rejections should remain in error_log until manually resolved or successfully reprocessed
DO NOT store in offline_confirmations (this is a SAP rejection, not a network issue)
DO NOT update order status to "Confirmed" (SAP rejected it)
Preserve order state:
Keep order in current status (InProgress/Validated)
Do not reset confirmed_qty
Allow user to reprocess with corrected data
2.5 Reprocess Functionality
Error Log Entry Structure:
error_type = "sap_failed" (distinguishes from VPN errors)
status = "Open" (can be changed to "Resolved" after successful reprocess)
payload.sent_payload = Original order data that was sent to SAP
payload.sap_reply = SAP's error response for this order
payload.vpn_connected = True = Indicates this was a SAP rejection, not VPN issue
Reprocess Endpoint: POST /api/error-log/<log_id>/reprocess
Request Body:
{  "scrap": 0.0,              // Optional: Updated scrap value  "confirmed_text": "",     // Optional: Updated confirmed text  "retry_vpn_check": false  // Optional: Force VPN check before retry}
Reprocess Logic:
Retrieve error log entry
Extract sent_payload from payload
Update payload with new scrap/confirmed_text if provided
Check VPN (if retry_vpn_check = true or if original error was network-related)
If VPN disconnected → store in offline_confirmations (Case 1)
If VPN connected → send to SAP again
If SAP succeeds → mark error_log as "Resolved"
If SAP fails again → update error_log with new error, keep status "Open"
Frontend UI:
Show error log entries with error_type = "sap_failed" in Error Log modal
Provide "Reprocess" button for each entry
Reprocess modal should allow editing:
Scrap value
Confirmed text
Option to force VPN check
Show original error message and SAP response
Implementation Checklist
Backend Changes
1. Ensure VPN Check in All Confirmation Paths
[ ] backend/routes/process_orders.py::push_confirmation()
[ ] Add VPN check before SAP call
[ ] Store in offline_confirmations if VPN down
[ ] Return offline response (not error)
[ ] backend/services/shift_auto_confirm.py::auto_push_shift_confirmation()
[ ] Verify VPN check exists
[ ] Ensure offline storage works correctly
[ ] backend/routes/order_validation.py::end_shift_and_confirm()
[ ] Verify VPN check exists
[ ] Ensure offline storage works correctly
[ ] backend/services/sap_confirmation.py::confirm_online()
[ ] Add VPN check at function start (before any network calls)
[ ] If VPN down, raise VPNDisconnectedException or return offline response
[ ] Ensure callers handle VPN exception properly
2. Improve SAP Error Response Handling
[ ] backend/services/sap_confirmation.py::confirm_online()
[ ] Ensure ALL failed orders are logged to error_log
[ ] Ensure failed orders are NOT stored in offline_confirmations (SAP rejection ≠ VPN issue)
[ ] Ensure failed orders are NOT marked as "Confirmed"
[ ] Add vpn_connected: True flag to error_log payload
[ ] Add http_status to error_log payload
[ ] backend/services/sap_confirmation.py::confirm_offline()
[ ] Apply same error handling logic
[ ] Distinguish between network errors and SAP rejections
3. Enhance Error Log Reprocess
[ ] backend/routes/error_log_routes.py::reprocess_error_order()
[ ] Add VPN check before reprocessing
[ ] If VPN down → store in offline_confirmations (Case 1)
[ ] If VPN up → send to SAP (Case 2 retry)
[ ] Update error_log status appropriately
[ ] Handle both success and failure scenarios
4. Database Schema
[ ] Verify error_log table has required fields:
id (primary key)
po_number (indexed)
error_type (sap_failed / vpn_disconnected / etc.)
error_message
payload (JSONB - stores full context)
source (sap_online / sap_offline / etc.)
status (Open / Resolved)
created_at
resolved_at
[ ] Verify offline_confirmations table has required fields:
id (primary key)
order_id (indexed)
status (pending / sent / failed)
sap_payload (JSONB)
retry_count
All order fields (material, version, confirmed_weight, etc.)
Frontend Changes
1. Error Log Display
[ ] Show error log entries in Error Log modal
[ ] Distinguish between error types:
VPN errors → Show "VPN Disconnected" badge
SAP errors → Show "SAP Rejected" badge
[ ] Display error message and SAP response
[ ] Show payload details (expandable)
2. Reprocess Functionality
[ ] Add "Reprocess" button for sap_failed errors
[ ] Create Reprocess Modal:
PO Number (read-only)
Material (read-only)
Original Error Message (read-only)
Scrap (editable, default from payload)
Confirmed Text (editable, default from payload)
"Force VPN Check" checkbox (optional)
"Cancel" and "Reprocess" buttons
[ ] Call /api/error-log/<id>/reprocess endpoint
[ ] Handle success/error responses
[ ] Refresh error log after successful reprocess
3. Offline Confirmations Display
[ ] Show offline confirmations in separate modal/section
[ ] Distinguish from error log (these are not errors, just queued)
[ ] Provide "Send Now" button for each offline confirmation
[ ] Show retry count and last attempt time
Error Flow Diagrams
Case 1: VPN Disconnected
User/System → Push Confirmation    ↓Check VPN    ↓VPN Disconnected?    ├─ YES → Store in offline_confirmations    │         (status='pending')    │         Return: {offline_mode: true, stored_count: N}    │    └─ NO → Continue to SAP push
Case 2: SAP Error Response
User/System → Push Confirmation    ↓Check VPN → Connected ✓    ↓Send to SAP → HTTP 200/201 ✓    ↓Parse SAP Response    ↓For each order:    ├─ Success? → Mark as confirmed    │    └─ Error? → Log to error_log                (error_type='sap_failed')                (status='Open')                (DO NOT store in offline_confirmations)                (DO NOT mark order as confirmed)
Reprocess Flow
User clicks "Reprocess" on error_log entry    ↓Open Reprocess Modal    ↓User edits scrap/confirmed_text (optional)    ↓Submit → POST /api/error-log/<id>/reprocess    ↓Check VPN    ├─ Disconnected? → Store in offline_confirmations    │                   Mark error_log as "Resolved"    │    └─ Connected? → Send to SAP with updated data                      ├─ Success? → Mark error_log as "Resolved"                      └─ Failed? → Update error_log with new error                                    Keep status "Open"
Critical Rules
Rule 1: Never Lose Orders
All orders must be stored in either:
offline_confirmations (if VPN down)
error_log (if SAP rejected)
Never silently fail or discard orders
Always return meaningful response to caller
Rule 2: Distinguish Error Types
VPN Disconnected → offline_confirmations (not an error, just offline)
SAP Rejection → error_log with error_type='sap_failed' (actual error)
Network Exception → error_log with error_type='network_error' (actual error)
Rule 3: Status Management
VPN Disconnected: Order status remains unchanged (InProgress/Validated)
SAP Rejection: Order status remains unchanged (InProgress/Validated)
SAP Success: Order status updated to "Confirmed"
Only update status after successful SAP confirmation
Rule 4: Reprocess Capability
All error_log entries with error_type='sap_failed' must be reprocessable
Reprocess must allow editing scrap and confirmed_text
Reprocess must check VPN before retry
Reprocess must handle both VPN and SAP errors
Testing Scenarios
Test Case 1: VPN Disconnected - Manual Push
Disconnect VPN
Click "Send" button for validated order
Expected: Order stored in offline_confirmations, status='pending'
Expected: Response shows offline_mode: true
Expected: Order status remains "Validated" (not "Confirmed")
Test Case 2: VPN Disconnected - Auto Shift-End
Disconnect VPN
Wait for 5 minutes before shift end
Expected: Validated orders stored in offline_confirmations
Expected: No error_log entries created
Expected: Orders remain "Validated"
Test Case 3: SAP Rejection - Single Order
Connect VPN
Send order to SAP
Mock SAP to return error for this order
Expected: Order logged to error_log with error_type='sap_failed'
Expected: Order NOT stored in offline_confirmations
Expected: Order status remains "Validated"
Expected: Error log shows "Reprocess" button
Test Case 4: SAP Rejection - Multiple Orders
Connect VPN
Send 3 orders to SAP
Mock SAP to return: 1 success, 2 errors
Expected: 1 order marked as "Confirmed"
Expected: 2 orders logged to error_log
Expected: 2 orders remain "Validated"
Test Case 5: Reprocess - VPN Down
Select sap_failed error from error_log
Click "Reprocess"
Disconnect VPN before submitting
Expected: Order stored in offline_confirmations
Expected: Error log marked as "Resolved"
Test Case 6: Reprocess - SAP Success
Select sap_failed error from error_log
Click "Reprocess"
Edit scrap/confirmed_text
Submit (VPN connected, SAP accepts)
Expected: Order sent to SAP successfully
Expected: Error log marked as "Resolved"
Expected: Order status updated to "Confirmed"
Test Case 7: Reprocess - SAP Rejection Again
Select sap_failed error from error_log
Click "Reprocess"
Submit (VPN connected, SAP rejects again)
Expected: Error log updated with new error
Expected: Error log status remains "Open"
Expected: Order status remains "Validated"
Error Log Payload Structure
VPN Disconnected (should not be in error_log, but if logged):
{  "error_type": "vpn_disconnected",  "vpn_connected": false,  "sent_payload": {...},  "timestamp": "2025-12-14T12:19:00Z"}
SAP Rejection:
{  "error_type": "sap_failed",  "vpn_connected": true,  "http_status": 200,  "sent_payload": {    "po_number": "000012002900",    "material": "...",    "confirmed_weight": 40.0,    "shift": "B",    "scrap": 0.0,    "confirmed_text": "",    ...  },  "sap_reply": {    "PROCESS_ORDER": "12002900",    "MESSAGE": "Error: Order already being processed",    "STATUS": "Error"  },  "sap_response": "[{...}]",  "confirmation_type": "online",  "timestamp": "2025-12-14T12:19:00Z"}
API Endpoints Summary
Existing Endpoints (Verify/Enhance)
POST /api/process_orders/push-confirmation - Add VPN check, offline storage
POST /api/error-log/<id>/reprocess - Add VPN check, handle offline mode
GET /api/error-log/ - List error log entries
GET /api/error-log/count - Get error count
New Endpoints (If Needed)
GET /api/error-log/<id> - Get single error log entry details
POST /api/error-log/<id>/resolve - Manually mark as resolved
GET /api/offline-confirmations/ - List offline confirmations
POST /api/offline-confirmations/<id>/send - Manually send offline confirmation
Implementation Priority
Phase 1: Critical (Prevent Order Loss)
✅ Ensure VPN check in all confirmation paths
✅ Ensure offline storage for VPN disconnections
✅ Ensure error_log for SAP rejections
✅ Ensure no orders are silently lost
Phase 2: Important (Error Recovery)
✅ Enhance reprocess functionality
✅ Add VPN check to reprocess
✅ Improve error log UI
✅ Add reprocess modal with scrap/confirmed_text editing
Phase 3: Nice to Have (Monitoring)
Add error log dashboard
Add offline confirmations monitoring
Add retry statistics
Add alerting for high error rates
Notes
Mock Mode: VPN checks should be skipped in mock mode (MOCK_SAP_MODE=true)
Order Status: Only update to "Confirmed" after successful SAP confirmation
Duplicate Prevention: Check for duplicates in both offline_confirmations and error_log before storing
Retry Logic: Offline confirmations can be retried automatically or manually
Error Log: SAP rejections should remain in error_log until manually resolved or successfully reprocessed