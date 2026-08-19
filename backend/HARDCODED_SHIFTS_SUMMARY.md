# 🔍 Hardcoded Shift Locations in Backend

This document lists all places where shift times and logic are hardcoded in the backend.

---

## 📍 **File 1: `routes/process_orders.py`**

### **Function: `_get_shift_name()` (Lines 60-93)**
**Location:** Hardcoded shift number to letter conversion
- **Milling (plant 3130):** 1→A, 2→B, 3→C
- **Packing (others):** 1→A, 2→B

### **Function: `_derive_shift_from_timestamp()` (Lines 95-115)**
**Location:** Hardcoded shift time ranges
```python
# MILLING (plant 3130):
if 7 * 60 <= total_minutes < 15 * 60:    # 07:00-15:00 → Shift A
if 15 * 60 <= total_minutes < 23 * 60:   # 15:00-23:00 → Shift B
return "C"                                 # 23:00-07:00 → Shift C

# PACKING (others):
if 7 * 60 + 30 <= total_minutes < 15 * 60 + 30:  # 07:30-15:30 → Shift A
return "B"                                        # 15:30-23:30 → Shift B
```

**Hardcoded Values:**
- Milling Shift A: `07:00` - `15:00`
- Milling Shift B: `15:00` - `23:00`
- Milling Shift C: `23:00` - `07:00`
- Packing Shift A: `07:30` - `15:30`
- Packing Shift B: `15:30` - `23:30`

---

## 📍 **File 2: `routes/order_validation.py`**

### **Constant: `SHIFT_DURATION_HOURS` (Line 120)**
```python
SHIFT_DURATION_HOURS = 8  # Hardcoded 8-hour shift duration
```

### **Function: `get_current_shift_for_plant()` (Lines 692-706)**
**Location:** Hardcoded shift time ranges (same as process_orders.py)
```python
# MILLING (plant 3130):
if 7 * 60 <= total_minutes < 15 * 60:    # 07:00-15:00 → "A"
elif 15 * 60 <= total_minutes < 23 * 60: # 15:00-23:00 → "B"
else:                                     # 23:00-07:00 → "C"

# PACKING (others):
if 7 * 60 + 30 <= total_minutes < 15 * 60 + 30:  # 07:30-15:30 → "1"
else:                                             # 15:30-23:30 → "2"
```

**Hardcoded Values:**
- Same time ranges as `process_orders.py`
- Note: Packing returns "1"/"2" instead of "A"/"B"

### **Function: `get_next_shift()` (Lines 709-718)**
**Location:** Hardcoded shift rotation logic
```python
return {"A": "B", "B": "C", "C": "A"}.get(cur, ...)  # Hardcoded rotation
```

---

## 📍 **File 3: `services/sap_confirmation.py`**

### **Function: `_get_shift_name()` (Lines 188-221)**
**Location:** Hardcoded shift number to letter conversion (duplicate of process_orders.py)
- **Milling (plant 3130):** 1→A, 2→B, 3→C
- **Packing (others):** 1→A, 2→B

---

## 📊 **Summary of Hardcoded Values:**

| Plant Type | Shift | Start Time | End Time | Location |
|------------|-------|------------|----------|----------|
| **MILLING (3130)** | A | `07:00` | `15:00` | `process_orders.py:106`, `order_validation.py:696` |
| **MILLING (3130)** | B | `15:00` | `23:00` | `process_orders.py:108`, `order_validation.py:698` |
| **MILLING (3130)** | C | `23:00` | `07:00` | `process_orders.py:110`, `order_validation.py:700` |
| **PACKING (others)** | A | `07:30` | `15:30` | `process_orders.py:113`, `order_validation.py:703` |
| **PACKING (others)** | B | `15:30` | `23:30` | `process_orders.py:115`, `order_validation.py:705` |
| **SHIFT DURATION** | - | - | `8 hours` | `order_validation.py:120` |

---

## 🔧 **Recommendation:**

**Replace all hardcoded shift logic with database queries to `shift_master` table:**

1. Create a helper function to fetch shifts from database:
   ```python
   def get_shift_from_db(plant: str, department: str, timestamp: datetime) -> str:
       # Query shift_master table based on plant, department, and time
   ```

2. Replace hardcoded time checks with database lookups
3. Replace hardcoded shift rotation with database-driven logic
4. Make shift duration configurable per shift in database

---

## 📝 **Files to Update:**

1. ✅ `routes/process_orders.py` - Lines 60-115
2. ✅ `routes/order_validation.py` - Lines 120, 692-718
3. ✅ `services/sap_confirmation.py` - Lines 188-221

---

**Last Updated:** Generated automatically
