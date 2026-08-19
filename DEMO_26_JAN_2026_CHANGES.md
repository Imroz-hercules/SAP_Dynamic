# Demo 26 Jan 2026 - Changes Summary

**Document Date:** January 26, 2026  
**Comparison:** Current Working Version vs Main Branch  
**Status:** NOT PUSHED - Local changes only

---

## Table of Contents
1. [Recent Commits Already in Main](#0-recent-commits-already-in-main)
2. [New Features (Uncommitted)](#1-new-features)
3. [Backend Changes](#2-backend-changes)
4. [Frontend Changes](#3-frontend-changes)
5. [Database Changes](#4-database-changes)
6. [Bug Fixes](#5-bug-fixes)
7. [Removed/Deleted](#6-removeddeleted)
8. [Files Changed Summary](#7-files-changed-summary)

---

## 0. Recent Commits Already in Main (Last Merge History)

These changes are already pushed and merged into `main` branch:

### Latest Commit (Jan 25, 2026)
**Commit:** `15bb451` - Fix shift-based chart times
- Use actual shift end times from settings for Milling and Packing charts
- Added new endpoint `/api/kpi/shift-history`
- **Files:** `KpiCalculations.tsx`, `SAPDashboard.tsx`, `kpi_routes.py`
- **Impact:** +704 lines, -268 lines

### UI Changes (Jan 23, 2026)
**Commit:** `796cff1` - Syed UI changes
- UI refinements for KPI Calculations page
- Live Monitor updates
- Material Map minor changes
- Palletizer Mapping updates
- SAP Dashboard restructuring
- **Files:** `KpiCalculations.tsx`, `LiveMonitor.tsx`, `MaterialMap.tsx`, `PalletizerMapping.tsx`, `SAPDashboard.tsx`
- **Impact:** Major UI cleanup (-1027 lines removed, +504 lines added)

### Validation Fixes (Jan 24, 2026)
**Commit:** `5c5b9e6` - validation fixed
- Fixed order validation logic in backend
- SAP confirmation service updates
- Shift auto-confirm improvements
- Frontend validation UI updates
- **Files:** `ProcessOrderValidation.tsx`, `order_validation.py`, `sap_confirmation.py`, `shift_auto_confirm.py`
- **Impact:** +320 lines, -159 lines

### KPI Reports Update (Jan 24, 2026)
**Commit:** `2aecd4b` - Update KPI reports, services, and frontend API
- Enhanced reports page with KPI tracking
- New migration script for KPI payload
- KPI incremental service improvements
- Added KPI payload tracking to model
- **Files:** `api.ts`, `Reportss.tsx`, `database.py`, `migrate_add_kpi_payload.py`, `kpi_send_tracking.py`, `kpi_routes.py`, `reports_routes.py`, `kpi_incremental.py`, `kpi_shift_auto_sync.py`
- **Impact:** +724 lines, -49 lines

### KPI & Dashboard Updates (Jan 22, 2026)
**Commit:** `1b996e2` - Update KPI calculations, dashboard reporting, order validation
- Major KPI calculations enhancements
- Dashboard reporting improvements
- Order validation logic updates
- **Files:** `api.ts`, `KpiCalculations.tsx`, `Reportss.tsx`, `SAPDashboard.tsx`, `kpi_routes.py`, `order_validation.py`
- **Impact:** +1248 lines, -298 lines

### Validation Overflow Fix (Jan 22, 2026)
**Commit:** `85d2273` - Validation overflow
- Fixed validation UI overflow issues
- SAP Dashboard enhancements
- **Files:** `ProcessOrderValidation.tsx`, `SAPDashboard.tsx`
- **Impact:** +210 lines, -80 lines

### Validation Logic Fix (Jan 22, 2026)
**Commit:** `e5303a4` - Fix validation logic: frontend UI updates and backend order validation
- Frontend App.tsx updates
- API layer enhancements
- Backend order validation improvements
- **Files:** `App.tsx`, `api.ts`, `order_validation.py`
- **Impact:** +171 lines, -22 lines

### Historical KPI Data (Before Jan 22)
**Commit:** `cf2c93f` - added Historical KPI raw data to report page

### Live Monitor Fix (Before Jan 22)
**Commit:** `58bfe2f` - Live monitor URL issue fixed

---

## 1. New Features (UNCOMMITTED - Current Session Jan 26, 2026)

> **Note:** All features below are LOCAL CHANGES that have NOT been pushed to main yet.

### 1.1 Embedded SCADA Emulator
- **Purpose:** Run SCADA emulator directly within the Flask backend instead of requiring a separate emulator service
- **Functionality:**
  - Simulates all scale readings (WG301, WG302, WG501, WG502, WG503, WG504, DM301, DM302, DM303, DM501, DM502, DM503)
  - Generates realistic incremental values over time
  - Supports HI/LO value concatenation (same as production SCADA)
  - Auto-starts on backend startup if enabled in settings
- **Control Options:**
  - Start/Stop emulator
  - Reset to Zero (all scales start at 0)
  - Reset to Realistic Values (scales start at typical production values)
  - Adjustable tick interval (default: 1 second)

### 1.2 Demo Mode Toggle
- **Purpose:** Easily switch between production SQL Server and embedded emulator
- **Functionality:**
  - When ON: All SCADA reads come from embedded emulator
  - When OFF: All SCADA reads come from production SQL Server (MSSQL)
  - Affects: Order Validation, KPIs, Live Monitor, Scales Status
- **UI Indicator:**
  - Top banner shows "DEMO" (amber) or "PRODUCTION" (green)
  - Demo mode indicator is clickable - navigates directly to Demo Mode settings tab

### 1.3 System Mode Settings Page
- **Location:** Admin > Demo Mode tab
- **Features:**
  - Toggle Demo Mode ON/OFF
  - Toggle Mock SAP Mode ON/OFF
  - Configure emulator auto-start on backend startup
  - Set emulator tick interval
  - View current scale values in real-time
  - Reset buttons: "Reset to 0", "Reset Realistic", "Refresh Baselines"
  - "Reset Order Tracking" button (only visible in Demo Mode)

### 1.4 Reset Order Tracking (Demo Mode Only)
- **Purpose:** Reset all order progress for testing purposes
- **What it resets:**
  - `confirmed_qty` → 0
  - All shift weight baselines → 0
  - Byproduct quantities (`scale1_qty`, `scale2_qty`, `scale3_qty`) → 0
  - All SCADA baselines for orders → current emulator values
  - Validated orders → set back to Pending status
- **Availability:** Only active when Demo Mode is enabled

### 1.5 Refresh Baselines Feature
- **Purpose:** Fix stuck orders after emulator reset
- **Problem Solved:** When emulator is reset to 0, existing orders have high baselines making delta = 0
- **Solution:** Updates all in-progress order baselines to current SCADA values
- **Triggered:**
  - Automatically when "Reset to 0" or "Reset Realistic" is clicked
  - Manually via "Refresh Baselines" button

### 1.6 Priority System Overhaul
- **New Priority Logic:**
  - Priority is now based on **conflict groups** (orders sharing the same scales)
  - Priority 1 = Can run immediately (no conflicts or first in queue)
  - Priority 2, 3, etc. = Waiting for higher priority orders in same conflict group
  - Non-conflicting orders always show Priority 1
- **Auto-Assignment:**
  - Priorities auto-calculated on SAP sync
  - Priorities recalculate on order completion/cancellation
  - Priorities recalculate after drag-and-drop
- **Drag-and-Drop Rules:**
  - RUNNING orders: Cannot be moved (must pause first)
  - PENDING orders: Can move up/down but NOT above running orders in same conflict group
  - PAUSED orders: Can move anywhere (progress is preserved)

---

## 2. Backend Changes

### 2.1 New API Endpoints

| Endpoint | Method | Purpose |
|----------|--------|---------|
| `/api/emulator/status` | GET | Get emulator running status and current values |
| `/api/emulator/start` | POST | Start the embedded emulator |
| `/api/emulator/stop` | POST | Stop the embedded emulator |
| `/api/emulator/reset/zero` | POST | Reset all scale values to 0 |
| `/api/emulator/reset/realistic` | POST | Reset to realistic starting values |
| `/api/emulator/refresh-baselines` | POST | Refresh baselines for in-progress orders |
| `/api/emulator/reset-order-tracking` | POST | Reset all order tracking values (demo mode only) |
| `/api/system-mode` | GET | Get current system mode settings |
| `/api/system-mode` | POST | Update system mode settings |

### 2.2 Modified API Behavior

| Endpoint | Change |
|----------|--------|
| `/api/orders/priority` | Now validates drag-and-drop rules and calls `recalculate_conflict_group_priorities()` |
| `/api/scada/readings` | Now checks `get_demo_mode()` to determine data source |
| `/api/scada/scales-status` | Now checks `get_demo_mode()` to determine data source |
| `/api/scada/reset` | Now fetches current values from emulator when in demo mode |
| `/api/kpis` | Now fetches data from emulator when in demo mode |
| `/api/kpis/realtime` | Now fetches data from emulator when in demo mode |
| `/api/orders/progress/{id}` | Now includes byproduct scale readings from emulator in demo mode |
| `/api/sap/sync` | Now calls `recalculate_conflict_group_priorities()` after sync |

### 2.3 New Backend Services

| Service | Purpose |
|---------|---------|
| `embedded_emulator.py` | Core emulator logic - scale simulation, HI/LO handling |
| `system_settings.py` (model) | SQLAlchemy model for SystemSettings table |

### 2.4 Modified Backend Services

| Service | Changes |
|---------|---------|
| `scale_service.py` | Now uses `get_demo_mode()` to switch between emulator and MSSQL |
| `scale_lock_service.py` | Added `recalculate_conflict_group_priorities()` function |
| `app_scheduler.py` | SCADA polling now respects demo mode setting |

### 2.5 Dynamic Configuration Functions
New functions in `database.py`:
- `get_demo_mode()` - Returns True if demo mode is active
- `get_mock_sap_mode()` - Returns True if mock SAP mode is active
- `get_emulator_url()` - Returns the emulator URL
- `get_scada_source()` - Returns "emulator" or "mssql"

---

## 3. Frontend Changes

### 3.1 Admin Page Changes
- **New Tab:** "Demo Mode" tab added to Admin settings
- **Tab Navigation:** URL parameter support (`/admin?tab=demo` navigates directly to Demo tab)
- **New Buttons:**
  - "Reset to 0" - Reset emulator to zeros
  - "Reset Realistic" - Reset emulator to realistic values
  - "Refresh Baselines" - Update order baselines to current values
  - "Reset Order Tracking" - Reset all order progress (demo mode only)

### 3.2 Top Banner Changes
- **Demo Mode Indicator:** Shows "DEMO" or "PRODUCTION" status
- **Clickable:** When in Demo Mode, clicking the indicator navigates to `/admin?tab=demo`
- **Visual Feedback:** Hover effects, cursor pointer, tooltip

### 3.3 Process Order Validation Page Changes
- **Priority Display:**
  - Now shows `conflict_group_priority` instead of raw `priority`
  - Priority 1 = Green badge (can run)
  - Priority 2+ = Amber badge (waiting)
  - Tooltip shows conflict status and waiting orders
- **Sorting:**
  - Orders now sorted by `conflict_group_priority` (ascending)
  - Priority 1 orders appear at top
- **Drag-and-Drop:**
  - Client-side validation for drag rules
  - Toast messages for rejected moves
  - Auto-refresh after successful drag

### 3.4 Order Details Popup Changes
- **Scale Values:** Now correctly shows byproduct scale names and quantities from backend
- **is_final_confirmation:** Now shows `true` for Validated orders

---

## 4. Database Changes

### 4.1 New Table: `system_settings`
| Column | Type | Purpose |
|--------|------|---------|
| `id` | Integer (PK) | Primary key |
| `setting_key` | String(100) | Setting identifier |
| `setting_value` | Text | Setting value (stored as string) |
| `description` | Text | Human-readable description |
| `created_at` | DateTime | Creation timestamp |
| `updated_at` | DateTime | Last update timestamp |

**Default Settings:**
- `demo_mode`: "false"
- `mock_sap_mode`: "false"
- `emulator_auto_start`: "true"
- `emulator_tick_interval`: "1000"

### 4.2 Modified Fields Usage
- `process_orders.priority` - Now stores conflict-group-based priority (1, 2, 3, etc.)
- Baselines are now refreshed automatically on emulator reset

---

## 5. Bug Fixes

### 5.1 Priority 0 Bug
- **Problem:** Priority value of 0 was treated as lowest priority (defaulted to 999)
- **Cause:** Python's `X or Y` expression converts 0 (falsy) to Y
- **Fix:** Changed patterns like `priority or 100` to proper None checks
- **Files Affected:** `order_validation.py`, `scale_lock_service.py`

### 5.2 HI/LO Zero-Padding Bug
- **Problem:** LO values like 12345 were concatenated as "412345" instead of "4012345"
- **Cause:** Missing zero-padding for LO values less than 6 digits
- **Fix:** Added `.zfill(6)` padding for LO values
- **Files Affected:** `scale_service.py`, `scada_routes.py`, `kpi_routes.py`

### 5.3 DM Scale Demo Mode Bug
- **Problem:** DM scales showed instantaneous emulator values instead of deltas
- **Cause:** Demo mode logic didn't calculate delta for DM scales
- **Fix:** Modified `sum_dm_readings_for_order()` to calculate `current_dm - baseline_dm`
- **Files Affected:** `scale_service.py`

### 5.4 Frontend Byproduct Display Bug
- **Problem:** Order details showed wrong scale names and huge values (228 billion)
- **Cause:** Frontend fallback logic used formula equipment scales instead of byproduct scales
- **Fix:** Prioritize `progressData.scale1/scale2/scale3` from backend
- **Files Affected:** `ProcessOrderValidation.tsx`

### 5.5 is_final_confirmation Display Bug
- **Problem:** Showed `false` for Validated orders that should be final
- **Cause:** Only checked `is_final_sent` flag, not order status
- **Fix:** Set to `true` if order status is 'Validated' OR `is_final_sent` is true
- **Files Affected:** `ProcessOrderValidation.tsx`

### 5.6 Priority Sorting Bug
- **Problem:** Priority 1 orders appeared at bottom instead of top
- **Cause:** Frontend sorted by raw `priority` field instead of `conflict_group_priority`
- **Fix:** Changed three sorting locations to use `conflict_group_priority`
- **Files Affected:** `ProcessOrderValidation.tsx`

### 5.7 Emulator Reset Stuck Orders Bug
- **Problem:** Orders got stuck (0 progress) after emulator reset
- **Cause:** Order baselines remained high while emulator values reset to low
- **Fix:** Auto-refresh baselines on emulator reset + manual refresh button
- **Files Affected:** `emulator_routes.py`, `Admin.tsx`

---

## 6. Removed/Deleted

| Item | Reason |
|------|--------|
| `kpi_routes.py` (root level) | Duplicate file removed - actual file is in `backend/routes/` |
| External SCADA emulator dependency | Replaced by embedded emulator |
| `USE_SCADA_EMULATOR` constant | Replaced by dynamic `get_demo_mode()` function |

---

## 7. Files Changed Summary

### New Files (4)
1. `backend/models/system_settings.py` - SystemSettings model
2. `backend/routes/emulator_routes.py` - Emulator API endpoints
3. `backend/routes/system_mode_routes.py` - System mode API endpoints
4. `backend/services/embedded_emulator.py` - Embedded emulator service

### Modified Files (15+)
**Backend:**
- `backend/app.py` - Blueprint registration, auto-start emulator
- `backend/app_scheduler.py` - Demo mode aware SCADA polling
- `backend/database.py` - Dynamic config functions
- `backend/routes/auth_routes.py` - Debug logging
- `backend/routes/kpi_routes.py` - Demo mode aware KPI fetching
- `backend/routes/scada_routes.py` - Demo mode aware SCADA routes
- `backend/routes/order_validation.py` - Priority logic fixes, conflict group priorities
- `backend/routes/sap_sync.py` - Auto-assign priorities on sync
- `backend/services/sap_confirmation.py` - Minor updates
- `backend/services/scale_service.py` - Demo mode integration, HI/LO fixes
- `backend/services/scale_lock_service.py` - Priority fixes, recalculate function

**Frontend:**
- `Frontend/client/src/components/hercules-sfms/WaterSystemLayout.tsx` - Clickable demo indicator
- `Frontend/client/src/components/ui/tabs.tsx` - Tab styling
- `Frontend/client/src/index.css` - CSS updates
- `Frontend/client/src/lib/api.ts` - API updates
- `Frontend/client/src/lib/apiConfig.ts` - Config updates
- `Frontend/client/src/lib/queryClient.ts` - Query client updates
- `Frontend/client/src/pages/hercules-sfms/Admin.tsx` - Demo mode tab, reset buttons
- `Frontend/client/src/pages/hercules-sfms/SAPDashboard.tsx` - Updates
- `Frontend/client/src/pages/hercules-sfms/ProcessOrderValidation.tsx` - Priority display, sorting, drag-and-drop

### Deleted Files (1)
- `kpi_routes.py` (root level duplicate)

---

## Summary of Key Functional Changes

| Feature | Before | After |
|---------|--------|-------|
| SCADA Data Source | External emulator or hardcoded | Dynamic based on Demo Mode setting |
| Priority Assignment | Manual, confusing numbering | Auto-calculated based on conflict groups |
| Priority Display | Raw priority number | Conflict-group priority (1 = can run) |
| Emulator Control | Separate service required | Embedded in backend, controllable from UI |
| Order Reset (Testing) | Manual database updates | One-click "Reset Order Tracking" button |
| Baseline Management | Manual | Auto-refresh on emulator reset |
| Demo Mode Navigation | N/A | Click banner → Demo settings tab |

---

## Quick Reference: What's Where

| Change Type | Status | Section |
|-------------|--------|---------|
| Shift-based charts, KPI history | ✅ PUSHED (main) | Section 0 |
| UI refinements (Syed) | ✅ PUSHED (main) | Section 0 |
| Validation fixes | ✅ PUSHED (main) | Section 0 |
| KPI reports enhancements | ✅ PUSHED (main) | Section 0 |
| Embedded SCADA Emulator | ⚠️ NOT PUSHED | Section 1.1 |
| Demo Mode Toggle | ⚠️ NOT PUSHED | Section 1.2 |
| System Mode Settings | ⚠️ NOT PUSHED | Section 1.3 |
| Reset Order Tracking | ⚠️ NOT PUSHED | Section 1.4 |
| Refresh Baselines | ⚠️ NOT PUSHED | Section 1.5 |
| Priority System Overhaul | ⚠️ NOT PUSHED | Section 1.6 |
| Bug Fixes (7 total) | ⚠️ NOT PUSHED | Section 5 |

---

**END OF DOCUMENT**

*This document summarizes:*
1. *Recent commits already in main branch (Jan 22-25, 2026)*
2. *Uncommitted local changes from current session (Jan 26, 2026)*

**⚠️ REMINDER: Local changes have NOT been pushed to remote repository.**
