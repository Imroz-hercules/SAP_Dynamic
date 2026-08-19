# Shift Code Summary - Backend

## 📍 **Where Shift Code is Located:**

### **1. `routes/process_orders.py`**
   - **Function:** `_get_shift_name(shift_number: int, plant: str) -> str`
   - **Location:** Lines 59-92
   - **Purpose:** Converts numeric shift (1, 2, 3) to shift letter (A, B, C) based on plant type
   
   - **Function:** `_derive_shift_from_timestamp(dt: datetime | None, plant: str) -> str`
   - **Location:** Lines 94-114
   - **Purpose:** Determines shift letter from timestamp and plant (used for validation time)

### **2. `services/sap_confirmation.py`**
   - **Function:** `_get_shift_name(self, shift_number: int, plant: str) -> str`
   - **Location:** Lines 188-221
   - **Purpose:** Same as above, used when building SAP confirmation payloads

---

## 🔄 **Shift Definitions:**

### **MILLING (Plant 3130):**
   - **Number of Shifts:** **3 shifts** (A, B, C)
   
   **Shift A:**
   - Time Range: **07:00 - 15:00** (7:00 AM - 3:00 PM)
   - Shift Number: 1
   
   **Shift B:**
   - Time Range: **15:00 - 23:00** (3:00 PM - 11:00 PM)
   - Shift Number: 2
   
   **Shift C:**
   - Time Range: **23:00 - 07:00** (11:00 PM - 7:00 AM)
   - Shift Number: 3

### **PACKING (Other Plants, e.g., 3131):**
   - **Number of Shifts:** **2 shifts** (A, B)
   
   **Shift A:**
   - Time Range: **07:30 - 15:30** (7:30 AM - 3:30 PM)
   - Shift Number: 1
   
   **Shift B:**
   - Time Range: **15:30 - 23:30** (3:30 PM - 11:30 PM)
   - Shift Number: 2
   - **Note:** Overnight hours (23:30 - 07:30) are treated as Shift B

---

## 📋 **Code Logic:**

### **Milling Shift Conversion:**
```python
if plant and "3130" in str(plant):  # Milling
    if shift_number == 1:
        return "A"
    elif shift_number == 2:
        return "B"
    elif shift_number == 3:
        return "C"
    else:
        # Cycle through A, B, C
        return chr(64 + ((shift_number - 1) % 3) + 1)
```

### **Packing Shift Conversion:**
```python
else:  # Packing
    if shift_number == 1:
        return "A"
    elif shift_number == 2:
        return "B"
    else:
        # Cycle through A, B
        return chr(64 + ((shift_number - 1) % 2) + 1)
```

### **Time-Based Shift Derivation (Milling):**
```python
if plant and "3130" in str(plant):  # Milling
    total_minutes = dt.hour * 60 + dt.minute
    if 7 * 60 <= total_minutes < 15 * 60:  # 07:00-15:00
        return "A"
    if 15 * 60 <= total_minutes < 23 * 60:  # 15:00-23:00
        return "B"
    return "C"  # 23:00-07:00
```

### **Time-Based Shift Derivation (Packing):**
```python
else:  # Packing
    total_minutes = dt.hour * 60 + dt.minute
    if 7 * 60 + 30 <= total_minutes < 15 * 60 + 30:  # 07:30-15:30
        return "A"
    return "B"  # 15:30-23:30 (and overnight)
```

---

## 📊 **Summary Table:**

| Operation Type | Plant Code | Number of Shifts | Shift Names | Time Ranges |
|---------------|------------|------------------|-------------|-------------|
| **MILLING** | 3130 | **3 shifts** | A, B, C | A: 07:00-15:00<br>B: 15:00-23:00<br>C: 23:00-07:00 |
| **PACKING** | Others (e.g., 3131) | **2 shifts** | A, B | A: 07:30-15:30<br>B: 15:30-23:30 |

---

## 🔍 **Usage in Code:**

1. **`routes/process_orders.py`** - Used in `push_confirmation()` endpoint to derive shift from validation timestamp
2. **`services/sap_confirmation.py`** - Used when building SAP confirmation JSON payloads
3. **`routes/order_validation.py`** - Used in auto-validation worker (line 390)

---

## ✅ **Key Points:**

- **Milling has 3 shifts** (A, B, C) - operates 24/7
- **Packing has 2 shifts** (A, B) - operates 16 hours/day
- Shift is determined by:
  1. **Plant type** (3130 = Milling, others = Packing)
  2. **Time of validation** (for automatic shift detection)
  3. **Priority field** (for manual shift assignment)

