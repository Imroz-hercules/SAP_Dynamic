# OrderAccumulator Analysis

## **Purpose:**
The `OrderAccumulator.tick` is a **legacy automatic order confirmation system** that runs every 5 seconds to:
1. Find orders with status "Open", "Pending", or "Planned"
2. Set baseline for WG202 scale if not set
3. Check if production (delta) has reached target quantity
4. Automatically set order status to "Confirmed" when target is reached

## **Current Implementation:**
- **Location:** `services/accumulator_service.py`
- **Scheduled:** Every 5 seconds via APScheduler (`app_scheduler.py`)
- **Status Filter:** `["Open", "Pending", "Planned"]`
- **Scale Used:** Only WG202 (single scale)
- **Confirmation:** Sets status to "Confirmed" (not "Validated")

## **Issues & Conflicts:**

### **1. Status Values Mismatch:**
- **OrderAccumulator uses:** "Open", "Pending", "Planned"
- **New system uses:** "Pending", "InProgress", "Validated", "Rejected"
- **Problem:** "Open" and "Planned" may not be used in the new system

### **2. Single Scale Limitation:**
- **OrderAccumulator:** Only checks WG202 scale
- **New system:** Uses multiple scales based on order type:
  - MILLING: WG202 (input) + WG501, WG502, WG503 (output)
  - PACKING: SL601_COUNTER, SL602_COUNTER, etc.
- **Problem:** OrderAccumulator doesn't account for multiple equipment streams

### **3. No Classification:**
- **OrderAccumulator:** Doesn't distinguish between MILLING and PACKING
- **New system:** Uses classification to determine equipment mapping
- **Problem:** OrderAccumulator may process orders incorrectly

### **4. No 10 TON Chunking:**
- **OrderAccumulator:** Confirms entire order at once
- **New system:** Sends 10 TON chunks to SAP incrementally
- **Problem:** OrderAccumulator bypasses the chunk confirmation system

### **5. Status Conflict:**
- **OrderAccumulator:** Sets status to "Confirmed"
- **New system:** Uses "Validated" for successful validation
- **Problem:** Two different status values for the same outcome

### **6. Potential Race Condition:**
- **OrderAccumulator:** Runs every 5 seconds
- **Auto-validator:** Runs every 60 seconds
- **Problem:** Both may try to process the same order simultaneously

## **Recommendation:**

### **Option 1: Disable OrderAccumulator (RECOMMENDED)**
Since the new `auto_validation_worker()` in `order_validation.py` handles all validation properly:
- Uses proper classification (MILLING vs PACKING)
- Tracks multiple equipment streams
- Sends 10 TON chunk confirmations
- Uses correct status values (Validated, Rejected)
- Has proper baseline capture per equipment

**Action:** Comment out or remove the OrderAccumulator scheduler job in `app_scheduler.py`

### **Option 2: Update OrderAccumulator**
If OrderAccumulator is still needed for some legacy orders:
- Update status filter to match new system
- Add classification support
- Use multiple equipment streams
- Integrate with 10 TON chunking
- Use "Validated" status instead of "Confirmed"

## **Current Status:**
- ✅ OrderAccumulator is running (every 5 seconds)
- ⚠️ May conflict with new auto-validation worker
- ⚠️ Uses outdated logic (single scale, no classification)
- ⚠️ Sets status to "Confirmed" instead of "Validated"

