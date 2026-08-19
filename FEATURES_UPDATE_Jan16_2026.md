# Hercules SFMS - Features Update & System Verification
## January 16, 2026

---

# Executive Summary

| Category | Status | Details |
|----------|--------|---------|
| **Overall System** | ⚠️ Needs Fixes | 2 critical issues, 2 medium, 2 low |
| **SCADA → Hercules** | ⚠️ Partial | WG tracking ✅, DM handling ❌, `/scada/readings` ❌ |
| **SAP → Hercules** | ✅ Working | Order pull, classification, storage all correct |
| **Order Tracking** | ⚠️ Partial | WG/PL/SL ✅, DM in formulas ❌ |
| **SAP Confirmations** | ✅ Working | Auto, manual, and offline modes all correct |
| **SCADA Reset** | ⚠️ Partial | WG/DM ✅, Palletizers ❌ not included |

---

# 1. System Architecture

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                           HERCULES SFMS SYSTEM                              │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                             │
│  ┌─────────────┐     ┌──────────────┐     ┌─────────────┐                  │
│  │   SCADA     │────▶│  SQL Server  │────▶│  Hercules   │                  │
│  │  (PLC/OPC)  │     │  (MSSQL)     │     │  Backend    │                  │
│  └─────────────┘     └──────────────┘     └──────┬──────┘                  │
│       │                                          │                          │
│       │ Every 30s                   ┌────────────┼────────────┐             │
│       ▼                             ▼            ▼            ▼             │
│  ┌─────────────┐              ┌──────────┐ ┌──────────┐ ┌──────────┐        │
│  │ ASMArchive  │              │PostgreSQL│ │  React   │ │   SAP    │        │
│  │    DB5      │              │ (Orders) │ │ Frontend │ │  (ERP)   │        │
│  └─────────────┘              └──────────┘ └──────────┘ └──────────┘        │
│                                                                             │
└─────────────────────────────────────────────────────────────────────────────┘
```

---

# 2. Data Types & Handling

| Data Type | Source | Nature | Current Handling | Status |
|-----------|--------|--------|------------------|--------|
| **WG (Weights)** | `WG101_HI + WG101_LO` etc. | Totalizer | `delta = current - baseline` | ✅ Correct |
| **PL/SL (Palletizers)** | `PL601_TOT`, `SL606_TOT` etc. | Totalizer (Pallets) | `delta × bags_per_pallet` | ✅ Correct |
| **DM (Water Meters)** | `DM101`, `DM201` etc. | 30-sec Average | `delta = current - baseline` | ❌ **Wrong** |

### WG Scales (Weight Totalizers)
- **In MSSQL**: Split into `_HI` and `_LO` columns
- **Concatenation**: `"226847" + "708057"` → `226847708057.0`
- **Tracking**: ✅ Correct in `scale_service.py` and `order_validation.py`
- **Frontend API**: ❌ `/scada/readings` uses only HI values

### PL/SL Palletizers (Confirmed as PALLETS)
- **Input**: Pallet counts (not bag counts)
- **Conversion**: `bags = pallets × bags_per_pallet` from `palletizer_mapping` table
- **Status**: ✅ Correctly implemented

### DM Water Meters (30-Second Averages)
- **Nature**: Each reading = water used in last 30 seconds (NOT cumulative)
- **Required**: Sum all readings during order/shift
- **Current**: Incorrectly treated as totalizer (`current - baseline`)
- **Impact**: Wrong water consumption in KPIs and MILLING formulas

---

# 3. Complete System Flow

## 3.1 SAP → Hercules (Order Reception) ✅

```
SAP API ──GET──▶ /zmi_get_orders/GETORD ──▶ process_order_pull.py ──▶ PostgreSQL
```

| Step | Status | Details |
|------|--------|---------|
| API Connection | ✅ | HTTPS port 44300, Basic Auth |
| Order Fetch | ✅ | `SAPRealClient.get_process_orders()` |
| Data Transform | ✅ | SAP format → Internal format |
| Upsert | ✅ | New inserted, InProgress/Validated preserved |
| Auto-Classification | ✅ | Prefix 13→MILLING, 14→PACKING |

## 3.2 Order Tracking (Worker Thread) ✅ (except DM)

```
Order Start ──▶ Baseline Capture ──▶ Worker Loop ──▶ Completion Check
```

| Component | Status |
|-----------|--------|
| Baseline capture (reset-adjusted) | ✅ |
| Shift-specific baselines (A/B/C) | ✅ |
| WG delta calculation | ✅ |
| PL/SL delta → bags conversion | ✅ |
| DM delta calculation | ❌ Should SUM, not delta |
| Formula evaluation | ✅ |
| Scale locking (priority-based) | ✅ |
| Shift change handling | ✅ |
| Restart preservation | ✅ |

## 3.3 Hercules → SAP (Confirmations) ✅

### Automatic Mode (Shift-End)
```
Scheduler (1 min) ──▶ Detect Shift End ──▶ VPN Check ──▶ SAP or Offline Storage
```

| Component | Status |
|-----------|--------|
| Shift-end detection (2-min buffer) | ✅ |
| Incremental confirmation (weight - already_confirmed) | ✅ |
| Final flag for validated orders | ✅ |
| VPN check before send | ✅ |
| PACKING: Skip Shift C (only A/B) | ✅ |

### Manual Mode
```
User Click ──▶ Enter Scrap/Text ──▶ VPN Check ──▶ SAP or Offline Storage
```

| Component | Status |
|-----------|--------|
| Scrap/confirmed_text input | ✅ |
| VPN check | ✅ |
| Offline fallback | ✅ |

### Offline Mode (VPN Disconnected)
```
VPN Down ──▶ Store in offline_confirmations ──▶ User Re-Push when VPN Up
```

| Component | Status |
|-----------|--------|
| VPN detection (5s timeout) | ✅ |
| Offline storage with payload | ✅ |
| Duplicate handling (validated skip, partial accumulate) | ✅ |
| Row-level locking | ✅ |
| Re-push endpoint | ✅ |
| Edit scrap/text before push | ✅ |

---

# 4. SCADA Reset Functionality

## Current Capabilities

| Feature | Supported | Notes |
|---------|-----------|-------|
| Reset specific scales | ✅ | Via `scale_resets` parameter |
| Reset all scales | ✅ | Empty request body |
| Reset to 0 | ✅ | Default behavior |
| Reset to custom value | ✅ | Via `custom_current_value` |
| Reset WG scales | ✅ | All WG101-WG503 |
| Reset DM meters | ✅ | All DM columns |
| Reset Palletizers | ❌ | **PL/SL NOT included** |

## API Usage

```json
// Reset specific scales to custom values
POST /api/scada/reset
{
  "scale_resets": [
    { "tag": "WG501", "custom_current_value": 1500.0 },
    { "tag": "WG502", "custom_current_value": 0 }
  ]
}

// Reset specific scales to 0 (legacy)
POST /api/scada/reset
{ "scale_tags": ["WG501", "WG502", "DM101"] }

// Reset ALL WG + DM to 0
POST /api/scada/reset
{}
```

## Gap: Palletizers Not Resettable

**File**: `backend/routes/scada_routes.py:292`
```python
SCALE_TAG_PREFIXES = ("WG", "DM")  # ❌ Missing "PL", "SL"
```

---

# 5. Issues Found (Consolidated)

## ❌ Critical (Must Fix)

| # | Issue | Location | Impact | Fix |
|---|-------|----------|--------|-----|
| 1 | **DM treated as totalizer** | `scale_service.py`, `order_validation.py`, `kpi_routes.py` | Wrong water in KPIs & formulas | Sum readings instead of delta |
| 2 | **`/scada/readings` uses only WG HI** | `scada_routes.py:560-575` | Frontend shows wrong values | Concatenate HI+LO |

## ⚠️ Medium (Should Fix)

| # | Issue | Location | Impact | Fix |
|---|-------|----------|--------|-----|
| 3 | **2kg noise threshold** | `order_validation.py:8873` | May lose small production | Review/remove threshold |
| 4 | **Palletizers not in reset** | `scada_routes.py:292` | Can't reset PL/SL totals | Add "PL", "SL" to prefixes |

## ℹ️ Low (Consider)

| # | Issue | Location | Impact | Fix |
|---|-------|----------|--------|-----|
| 5 | **1-second worker interval** | `order_validation.py:8554` | High DB load | Increase to 5-10 seconds |
| 6 | **Code comments say "BAG counters"** | `scale_service.py:733-738` | Misleading | Update to "PALLET counters" |

---

# 6. Files Requiring Changes

| File | Issues |
|------|--------|
| `backend/routes/scada_routes.py` | #2 (HI-only), #4 (reset prefixes) |
| `backend/services/scale_service.py` | #1 (DM delta), #6 (comments) |
| `backend/routes/kpi_routes.py` | #1 (DM delta) |
| `backend/routes/order_validation.py` | #1 (DM in formulas), #3 (threshold), #5 (interval) |
| `backend/services/kpi_shift_auto_sync.py` | #1 (DM delta) |

---

# 7. Action Items

## Immediate (Before Production)

- [ ] **Fix DM handling**: Change from delta to accumulation/sum
- [ ] **Fix `/scada/readings`**: Concatenate WG HI+LO values
- [ ] **Add palletizers to reset**: Include "PL", "SL" in `SCALE_TAG_PREFIXES`

## Short-Term

- [ ] Review 2kg noise threshold with plant team
- [ ] Update code comments for PL/SL (pallets not bags)
- [ ] Test all fixes with real SCADA data

## Optional

- [ ] Consider increasing worker interval (1s → 5-10s)
- [ ] Add logging for DM accumulation for debugging

---

# 8. Communication Verification ✅

## SCADA ↔ Hercules Communication

| Direction | Status | Details |
|-----------|--------|---------|
| **SCADA → MSSQL** | ✅ Working | Data written every ~30 seconds to `ASMArchive_DB5` |
| **MSSQL → Hercules** | ✅ Working | `scale_service.py` reads via `pyodbc` correctly |
| **WG HI+LO Concat** | ✅ Working | Properly concatenated in tracking/KPIs |
| **Reset Offset Apply** | ✅ Working | `SCADA_RESET_BASE` applied correctly |

**Status**: ✅ Communication is flawless. Issues #1 and #2 are about data interpretation, not communication.

## SAP ↔ Hercules Communication

| Direction | Endpoint | Status | Details |
|-----------|----------|--------|---------|
| **SAP → Hercules** | `GET /zmi_get_orders/GETORD` | ✅ Working | Orders fetched and stored correctly |
| **Hercules → SAP (Online)** | `POST /zmi_conf_online/CONF` | ✅ Working | CSRF token fetched, data sent |
| **Hercules → SAP (Offline)** | `POST /zmi_conf_offlin/CONFOFF` | ✅ Working | Used for manual confirmations |
| **VPN Detection** | Real SAP endpoint | ✅ Working | 5-second timeout, fallback to offline |
| **Retry/Re-push** | Offline queue | ✅ Working | Stored in `offline_confirmations`, re-pushed when VPN up |

**Status**: ✅ Communication is flawless. Authentication, CSRF, and offline fallback all working correctly.

---

# 9. What's Working Correctly ✅

- SAP order pull and storage
- Order classification (MILLING/PACKING)
- Version mapping lookups (database-driven)
- WG HI+LO concatenation in tracking
- Pallet → bag conversion
- Shift-end auto confirmation
- Manual confirmation with scrap/text
- Offline mode storage and re-push
- VPN detection
- SCADA reset for WG/DM scales
- Demo/mock mode for testing
- SCADA ↔ Hercules communication
- SAP ↔ Hercules communication

---

# 10. Complete A-to-Z System Review

## 10.1 Frontend Layer (React + TypeScript)

### Architecture
| Component | Technology | Status |
|-----------|------------|--------|
| Framework | React 18 + TypeScript | ✅ Modern |
| Routing | Wouter | ✅ Lightweight |
| State Management | React Query (@tanstack/react-query) | ✅ Good caching |
| UI Components | shadcn/ui + Tailwind CSS | ✅ Modern |
| API Calls | Native fetch | ✅ Standard |

### Pages (13 Active)
- `SAPDashboard.tsx` - Main dashboard (44KB)
- `ProcessOrderValidation.tsx` - Order validation (397KB - **very large**)
- `KpiCalculations.tsx` - KPI display
- `LiveMonitor.tsx` - Real-time monitoring
- `OfflineOrderValidation.tsx` - Offline orders management
- `Logs.tsx` - System logs viewer
- `Reports.tsx` - Reporting
- `Admin.tsx` - Admin settings
- `UserManagement.tsx` - User management
- `MaterialMap.tsx`, `PalletizerMapping.tsx` - Mappings

### Frontend Issues Found

| # | Issue | Location | Severity | Recommendation |
|---|-------|----------|----------|----------------|
| F1 | **Massive file size** | `ProcessOrderValidation.tsx` (397KB) | ⚠️ Medium | Split into smaller components |
| F2 | **Hardcoded SAP URL** | `sapHerculesService.ts:72` | ⚠️ Medium | Move to environment config |
| F3 | **No error boundary** | `App.tsx` | ℹ️ Low | Add React Error Boundary |

---

## 10.2 Backend Layer (Flask + Python)

### Architecture
| Component | Technology | Status |
|-----------|------------|--------|
| Framework | Flask | ✅ Standard |
| ORM | SQLAlchemy | ✅ Good |
| Background Jobs | APScheduler + Threading | ✅ Working |
| Authentication | JWT + bcrypt | ✅ Secure |
| CORS | flask-cors | ✅ Configured |

### Blueprints (15 Registered)
```
kpi_bp, material_bp, orders_bp, dev_bp, process_orders_bp,
scada_bp, reports_bp, sap_sync_bp, system_logs_bp, auth_bp,
sync_interval_bp, shifts_bp, milling_bp, error_log_bp, offline_bp, sap_log_bp
```

### Background Workers
| Worker | Interval | Purpose | Status |
|--------|----------|---------|--------|
| `auto_validation_worker` | 1 second | Order tracking | ⚠️ High frequency |
| `auto_push_shift_confirmation` | 1 minute | Shift-end SAP push | ✅ OK |
| `sync_scheduler` | Configurable | SAP order pull | ✅ OK |

### Backend Issues Found

| # | Issue | Location | Severity | Recommendation |
|---|-------|----------|----------|----------------|
| B1 | **1-second worker interval** | `order_validation.py:8554` | ⚠️ Medium | Increase to 5-10 seconds |
| B2 | **No connection pooling config** | `database.py` | ⚠️ Medium | Add `pool_size`, `pool_recycle` |
| B3 | **Thread-per-order model** | `order_validation.py` | ⚠️ Medium | Consider async or queue |
| B4 | **Large cache in memory** | `order_validation.py` (493 cache refs) | ℹ️ Low | Monitor memory usage |

---

## 10.3 PostgreSQL Database

### Tables (Key)
| Table | Indexed Columns | Purpose |
|-------|-----------------|---------|
| `process_orders` | order_id, status, date, priority, order_type | Active orders |
| `offline_confirmations` | order_id, status | Pending offline |
| `shift_reports` | shift_date, shift_code, department | Historical |
| `milling_version_mappings` | version | Static config |
| `palletizer_mapping` | version | Static config |
| `sap_logs` | created_at | Growing |
| `error_log` | po_number, created_at | Growing |

### Database Issues Found

| # | Issue | Location | Severity | Recommendation |
|---|-------|----------|----------|----------------|
| D1 | **No connection pool tuning** | `database.py:23` | ⚠️ Medium | Add `pool_size=10, pool_recycle=3600` |
| D2 | **No log table cleanup** | `sap_logs`, `error_log` | ⚠️ Medium | Add retention policy (30 days) |
| D3 | **JSON columns for baselines** | `process_order_pg.py` | ℹ️ Low | OK for flexibility, monitor size |

---

## 10.4 SQL Server (SCADA)

### Data Source
| Table | Purpose | Update Frequency |
|-------|---------|------------------|
| `[HerculesV2].[dbo].[ASMArchive_DB5]` | SCADA readings | Every ~30 seconds |

### SCADA Issues (Previously Identified)

| # | Issue | Severity |
|---|-------|----------|
| S1 | **DM values treated as totalizers** | ❌ Critical |
| S2 | **`/scada/readings` uses only WG HI** | ❌ Critical |
| S3 | **Palletizers not in reset prefixes** | ⚠️ Medium |

---

## 10.5 SAP Integration

### Endpoints Used
| Direction | Endpoint | Port | Status |
|-----------|----------|------|--------|
| Pull Orders | `GET /zmi_get_orders/GETORD` | 44300 | ✅ Working |
| Online Confirm | `POST /zmi_conf_online/CONF` | 44300 | ✅ Working |
| Offline Confirm | `POST /zmi_conf_offlin/CONFOFF` | 44300 | ✅ Working |

**SAP Status**: ✅ Integration is solid, no issues found.

---

# 11. Performance Enhancement Recommendations

## 11.1 Immediate (High Impact)

| # | Enhancement | Current | Recommended | Impact |
|---|-------------|---------|-------------|--------|
| P1 | **Worker interval** | 1 second | 5-10 seconds | Reduce DB load by 80-90% |
| P2 | **Connection pooling** | Default | `pool_size=10, pool_recycle=3600` | Better connection reuse |
| P3 | **Log table cleanup** | None | 30-day retention cron | Prevent table bloat |

## 11.2 Short-Term (Medium Impact)

| # | Enhancement | Current | Recommended | Impact |
|---|-------------|---------|-------------|--------|
| P4 | **Split large components** | 397KB file | Multiple smaller files | Faster builds, easier maintenance |
| P5 | **Add Redis caching** | In-memory dicts | Redis | Persistent cache, lower memory |
| P6 | **Batch DB commits** | Per-order commits | Batch every 5 seconds | Fewer transactions |

## 11.3 Long-Term (Architecture)

| # | Enhancement | Current | Recommended | Impact |
|---|-------------|---------|-------------|--------|
| P7 | **Async workers** | Threading | Celery + Redis | Better scalability |
| P8 | **API rate limiting** | None | Flask-Limiter | Prevent abuse |
| P9 | **Health monitoring** | Basic `/api/health` | Prometheus + Grafana | Full observability |

---

# 12. Final Assessment

## Question 1: Is the system working properly as intended?

| Category | Verdict | Notes |
|----------|---------|-------|
| **Core Functionality** | ✅ YES | Order tracking, SAP sync, offline mode all work |
| **Data Accuracy** | ⚠️ PARTIAL | DM water values are calculated wrong |
| **Communication** | ✅ YES | SCADA and SAP connections flawless |
| **User Interface** | ✅ YES | All pages functional |

**Summary**: System is **operational and serving its purpose** with **2 critical data handling bugs** (DM values, `/scada/readings` HI-only).

## Question 2: Performance - Is there anything needed for enhancing?

| Category | Current State | Recommendation |
|----------|---------------|----------------|
| **DB Load** | High (1s worker) | Increase interval to 5-10s |
| **Connection Pooling** | Not configured | Add pool settings |
| **Memory** | In-memory caches | Monitor, consider Redis |
| **Log Tables** | Growing unbounded | Add 30-day retention |
| **Code Organization** | Some large files | Split into smaller modules |

**Summary**: System is **functional but could benefit from performance tuning** before scaling.

---

# 13. Priority Action List

## Must Fix (Before Production)
1. ❌ **Fix DM water handling** - Sum readings instead of delta
2. ❌ **Fix `/scada/readings`** - Concatenate WG HI+LO
3. ⚠️ **Add palletizers to reset** - Include "PL", "SL" prefixes

## Should Fix (Performance)
4. ⚠️ **Increase worker interval** - 1s → 5-10s
5. ⚠️ **Configure connection pooling** - Add pool_size, pool_recycle
6. ⚠️ **Add log table cleanup** - 30-day retention

## Nice to Have
7. ℹ️ Split `ProcessOrderValidation.tsx` into smaller components
8. ℹ️ Move hardcoded URLs to environment config
9. ℹ️ Add React Error Boundary
