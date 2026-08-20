# Endpoint → Database Mapping (Frontend → Flask → DB)

This document explains how the **frontend** calls into the **Flask backend** and which **database(s)** + **table(s)** each API endpoint reads from / writes to.

Databases:
- **PostgreSQL** (primary app data, via SQLAlchemy)
- **MSSQL** (SCADA / legacy data, via SQLAlchemy + ODBC)

---

## Frontend routing baseline (how requests reach Flask)
- Frontend calls URLs like `/api/...` using `getApiUrl()` / `apiFetch()` / `apiRequest()` in `Frontend/client/src/lib/apiConfig.ts`.
- In development, Vite proxies `/api` → Flask at `http://localhost:5000` (see `Frontend/vite.config.ts`).

So for DB connectivity, this mapping focuses on **how Flask handlers under `/api/*` query MSSQL vs Postgres**.

---

## Auth

### `POST /api/auth/login` → Postgres
Tables used (via SQLAlchemy models in `backend/models/user_roles.py`):
- `users`
- `roles`
- `user_roles`

JWT is created in `backend/services/auth_service.py` after bcrypt password verification.

### `GET /api/auth/me` → usually no DB read
- The JWT decorator decodes the JWT and returns `request.current_user`.
- The handler mostly uses decoded JWT payload/permissions (not a DB query in the common path).

### `GET /api/auth/users`, `PUT /api/auth/users/:id/roles`, `DELETE /api/auth/users/:id` → Postgres
Tables:
- `users`
- `roles`
- `user_roles`

---

## SCADA (biggest DB flow)

All SCADA endpoints switch behavior based on **demo mode**, coming from `backend/models/system_settings.py` (table: `system_settings`).

### `POST /api/scada/reset` → MSSQL (optional) + Postgres
- Demo mode: reads SCADA values from `services/embedded_emulator.py` (in-memory), not MSSQL.
- Production mode: reads latest SCADA row from **MSSQL** table `ASMArchive_DB5` using `mssql_engine`.
- After reset, it recomputes baseline and updates **active order baseline fields** in **Postgres**:
  - Table: `process_orders` (model `ProcessOrderPG` in `backend/models/process_order_pg.py`)

### `GET /api/scada/scales/status` → MSSQL (prod) + emulator (demo)
- Demo: emulator values + `SCADA_RESET_BASE` (in-memory)
- Production: MSSQL `ASMArchive_DB5`

### `GET /api/scada/readings` → MSSQL (prod) + emulator (demo)
- Demo: emulator values
- Production: MSSQL `ASMArchive_DB5`, then applies `SCADA_RESET_BASE` offsets

### `GET /api/scada/live-monitoring` → MSSQL (prod) + emulator (demo)
- Demo: emulator values
- Production: MSSQL `ASMArchive_DB5`

### `GET /api/scada/history`
- Demo mode: reads **Postgres** table `scada_aggregate_values`
- Production mode: reads/aggregates **MSSQL** `ASMArchive_DB5` into the response (and may rely on persistence job below)

#### SCADA history persistence (not just endpoints)
A scheduled job in `backend/app_scheduler.py` periodically:
- polls SCADA from MSSQL or emulator
- calls `backend/services/scada_persist.py`
- inserts into Postgres table: `scada_aggregate_values`

Table DDL:
- `backend/services/create_scada_table.py`

---

## Orders queue / validation flow (core state machine)
Most `/api/orders/*` endpoints use **Postgres** table:
- `process_orders` (model `ProcessOrderPG` in `backend/models/process_order_pg.py`)

They commonly also involve:
- `error_log`
- `offline_confirmations`
- `scale_overflows`
- `system_logs` (audit trail)

Key connectivity endpoints (Postgres unless stated otherwise):
- `GET /api/sap-sync/orders` → reads `process_orders` (Postgres)
- `POST /api/sap-sync/seed-orders` → inserts/updates `process_orders` (Postgres)

`/api/orders/*` (order_validation state machine):
- `GET /api/orders` → reads `process_orders`
- `POST /api/orders/:po_number/start` → updates `process_orders`
- `POST /api/orders/:po_number/validate` → updates `process_orders`
- `POST /api/orders/:order_id/reject` → updates `process_orders` + writes to `error_log`
- `POST /api/orders/:po_number/stop` → updates `process_orders`
- `GET /api/orders/:po_number/progress` → reads `process_orders` (+ may update baselines in certain flows)
- `POST /api/orders/progress-batch` → reads `process_orders` in batch
- `POST /api/orders/auto-validator/start`, `POST /api/orders/auto-validator/stop`, `GET /api/orders/auto-validator/status` → updates `process_orders` (worker coordination)
- `GET /api/orders/with-conflicts` → reads `process_orders` (conflict detection/scale-lock logic)
- `GET/POST /api/orders/priority` → reads/updates `process_orders` priority fields
- `POST /api/orders/:po_number/manual-confirm` → updates `process_orders` and may write:
  - `scale_overflows` (byproduct overflow)
  - `offline_confirmations` when VPN/SAP is unreachable

Additional model-to-table references:
- `error_log` → `backend/models/error_log.py`
- `offline_confirmations` → `backend/models/offline_confirmation.py`
- `scale_overflows` → `backend/models/scale_overflow.py`
- `system_logs` → `backend/models/user_roles.py` (`SystemLog`)

---

## Process Orders endpoints (`backend/routes/process_orders.py`)

Centered on:
- `process_orders` (Postgres)

Typical connectivity:
- `GET /api/process_orders` → reads `process_orders`
- `POST /api/process_orders/push-confirmation` → reads/updates `process_orders` (+ audit/logging)
- `POST /api/process_orders/manual-confirm` → reads/updates `process_orders` (+ may write `offline_confirmations` and/or `scale_overflows`)
- `GET /api/process_orders/shift-confirmations` → reads `system_logs`

---

## Offline confirmations (VPN disconnected queue)
In `backend/routes/offline_confirmations.py`:

- `GET /api/offline-confirmations` → reads `offline_confirmations` (Postgres)
- `GET /api/offline-confirmations/count` → reads count from `offline_confirmations`
- `PUT /api/offline-confirmations/:id` → updates `offline_confirmations`
- `POST /api/offline-confirmations/send` → reads pending `offline_confirmations`, sends to SAP, updates status
- `GET /api/vpn/status` → checks VPN/SAP reachability (uses system behavior stored in `system_settings`)

---

## Error log / resend / reprocess
In `backend/routes/error_log_routes.py` (table: `error_log`):

- `GET /api/error-log/` → reads `error_log`
- `GET /api/error-log/count` → reads count from `error_log`
- `POST /api/error-log/:id/resend` → reads `error_log` + reads `process_orders` for deduplication; updates `error_log` status
- `POST /api/error-log/:id/reprocess` → reads `error_log`; may insert into `offline_confirmations` when VPN is down; updates error/payload + resolves if successful
- `POST /api/error-log/:id/revalidate` → updates `process_orders.status='Pending'` and restarts validation worker

---

## System logs
In `backend/routes/system_logs.py`:
- `GET /api/system-logs/*` → reads Postgres table `system_logs` via `backend/services/system_logger.py`
- `POST /api/system-logs/manual-sync`, `POST /api/system-logs/end-shift` → writes new rows to `system_logs`
- `POST /api/system-logs/clear` → deletes old rows from `system_logs`
- `POST /api/system-logs/undo/:log_id` → writes revert entries into `system_logs`

---

## System mode / demo reset
In `backend/routes/system_mode_routes.py`:

### `GET /api/system/mode` / `PUT /api/system/mode`
- reads/writes `system_settings` table

### Reset demo data endpoints
- `POST /api/system/reset/kpi-tracking` → deletes `kpi_send_tracking` (Postgres)
- `POST /api/system/reset/scada-aggregate` → deletes `scada_aggregate_values` (Postgres)
- `POST /api/system/reset/kpi-snapshots` → deletes `milling_kpi_snapshots`, `packing_kpi_snapshots` (Postgres)
- `POST /api/system/reset/all-demo-data` → deletes multiple tables above + resets emulator state

---

## KPI endpoints (`backend/routes/kpi_routes.py`)

These endpoints are in **dual-mode**:
- **Demo mode** (checked via `system_settings` in `database.py`): uses the in-memory SCADA emulator
- **Production mode**: reads SCADA/KPI inputs from **MSSQL** `ASMArchive_DB5`

### `GET /api/kpi` (also `GET /api/kpis`)
DB tables touched:
- **Demo mode**: `system_settings` (to determine demo mode) + emulator (no DB SCADA read)
- **Production mode**:
  - **MSSQL**: `ASMArchive_DB5` (baseline + latest data, or ranged aggregation)
  - **Postgres**: `shift_master` (when using “current shift live data” mode)

Notes from handler behavior:
- If no `start/end` provided: fetches current shift from `shift_master`, reads MSSQL baseline at shift start + latest data, computes delta, then calculates KPIs.
- If `start/end` provided: aggregates over the requested time window from MSSQL `ASMArchive_DB5`.

### `GET /api/kpi/historical`
DB tables touched:
- **Production mode** only (in this handler): **MSSQL** `ASMArchive_DB5`

Notes:
- Builds an aggregation SQL query (period grouping or averaging mode) over MSSQL `ASMArchive_DB5`.
- `shifts` query param exists, but shift filtering is noted as “NOT YET IMPLEMENTED” in the handler docstring.

### `GET /api/kpi/shift-history`
DB tables touched (**Postgres** only):
- `shift_master` (model `ShiftMaster`)
- `kpi_send_tracking` (model `KpiSendTracking`)

Behavior:
- Loads shift end times from `shift_master`
- Fetches sent KPI payloads from `kpi_send_tracking` for a given date, then returns shift-ordered chart points.

### `POST /api/kpi/send-milling-to-sap`
DB tables touched:
- **Postgres**:
  - `shift_master` (to get the current milling shift code)
  - `kpi_send_tracking` (duplicate detection + baseline reservation + payload update)
- **MSSQL** (production mode):
  - `ASMArchive_DB5` (to get current SCADA values used for KPI delta/incremental calculation)
- **Demo mode**:
  - no MSSQL SCADA read (uses emulator)

What it writes:
- Inserts a new row into `kpi_send_tracking` (reserve baseline slot)
- Updates that row with the outgoing SAP KPI payload (`kpi_payload_sent`)

### `POST /api/kpi/send-packing-to-sap`
DB tables touched:
- **Postgres**:
  - `shift_master` (to get current packing shift code)
  - `kpi_send_tracking` (duplicate detection + baseline reservation + payload update)
- **MSSQL** (production mode):
  - `ASMArchive_DB5` (to get current SCADA values)
- **Demo mode**:
  - emulator only

What it writes:
- Inserts/updates `kpi_send_tracking` similarly to milling.

### `POST /api/hercules/send-to-sap`
DB tables touched:
- **MSSQL**: `ASMArchive_DB5` (fetches latest record)
- **Postgres**: `system_settings` (indirectly, via `get_mock_sap_mode()` to decide mock vs production SAP posting)

Writes:
- No database writes visible in this handler; it POSTs the payload to SAP.

---

## Shifts endpoints (`backend/routes/shifts.py`)

Blueprint prefix: `/api/shifts`

DB tables touched: **Postgres**
- `shift_master` (model `ShiftMaster`)

### `GET /api/shifts`
- reads `shift_master`

### `POST /api/shifts`
- upserts `shift_master`

### `DELETE /api/shifts/:shift_id`
- deletes from `shift_master`

---

## KPI reports endpoints (`backend/routes/reports_routes.py`)

### `GET /api/reports/kpi-tracking`
DB tables touched:
- **Postgres**: `kpi_send_tracking` (model `KpiSendTracking`)

Behavior:
- filters by `start_date`, `end_date`, optional `shifts`, optional `department`
- returns `kpi_payload_sent` JSON + `shift_code` and metadata

