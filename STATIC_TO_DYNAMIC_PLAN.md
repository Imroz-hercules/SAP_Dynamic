# Static to Dynamic — Migration Plan

Removing hardcoded plant configuration from Hercules SFMS. Two parallel workstreams with no shared files, no shared functions, and no merge order between them.

| | |
|---|---|
| **Repo** | `Imroz-hercules/SAP_Dynamic` |
| **Base** | `e6cf018` + commit 0 (PR #1) |
| **Branches** | `feat/dynamic-order-routing` · `feat/dynamic-plant-config` |
| **Contracts** | [`backend/CONTRACTS.md`](backend/CONTRACTS.md) |
| **Line numbers** | Verified against `e6cf018` + commit 0. Re-check after any rebase. |

---

## 1. What "dynamic" means here

The goal is that a plant engineer can change how the system behaves **without a developer and without a redeploy**. Every item below is a capability, not a refactor. The right question for each is *"who can change this today, and where?"*

| # | Capability | Screen | Today |
|---|---|---|---|
| 1 | Shift times, count and codes per plant/department | Admin → Shifts | ✅ **Working** — full CRUD against `/api/shifts` |
| 2 | Which scales a milling version reads, and its formula | Material Map | ⚠️ **Editable, but ignored** by one live consumer |
| 3 | Which line a packing version uses, bags per pallet | Palletizer Mapping | ⚠️ **Editable, but** the line→tag map is still in code |
| 4 | Demo vs production mode, emulator speed and scales | Admin → Demo | ✅ **Working** |
| 5 | Sync schedule (raw data, KPI, process orders) | Admin → System | ✅ **Working** |
| 6 | Which material prefixes and plants mean MILLING vs PACKING | — | ❌ **Not possible** — hardcoded |
| 7 | Which SCADA tags exist, their reading type and rollover | — | ❌ **Not possible** — hardcoded in 6 places |
| 8 | KPI ceilings and the mill nameplate rate | — | ❌ **Not possible** — hardcoded |
| 9 | SAP connection, endpoints, timeouts, poll intervals, MSSQL link | **Engineering** *(new)* | ❌ **Not possible from a screen** — `.env` only; Admin → SAP is a browser-only mock |

**So the work is narrower than it first looks.** Rows 1, 4 and 5 are already done — don't rebuild them. Rows 2 and 3 are half-done. Rows 6, 7, 8 and 9 are the genuinely new capability.

### Engineering page (A8) — one place for plant connection config

There is no Engineering page today. Admin has a **SAP tab that only writes to browser state** — `Admin.tsx:395` says so outright: *"SAP Endpoint Configuration (Demo - stores locally, will connect to backend later)"*. Nothing it saves reaches the backend.

`/engineering` is a new protected screen owned by **Workstream A**. A plant engineer changes runtime configuration there instead of editing `.env` on the server:

| Config group | Fields |
|---|---|
| SAP connection | base URL, mock URL, username, password, client |
| SAP endpoints | orders, milling KPI, packing KPI, Hercules raw, confirm online/offline |
| Timeouts and intervals | SAP timeout, SCADA poll, PO pull |
| SQL Server link | `MSSQL_URL`, `MSSQL_ENABLED` (secrets masked on read) |
| Validator tuning | tolerance %, worker sleep (same values as A5) |

Backend: persist in `system_settings` or a dedicated table; `services/runtime_config.py` is the single reader, resolving **DB → `.env` → documented default**. `.env` stays as first-boot bootstrap.

**Three fields are deliberately excluded** because they cannot work as a live setting — verified in code, not assumed:

| Field | Why it's out |
|---|---|
| `POSTGRES_URL` | `database.py:55` reads it and builds the engine at **import time**, before any DB connection exists. You cannot read the Postgres address out of Postgres. Stays in `.env`. |
| `PORT`, `CORS_ALLOWED_ORIGINS` | Read once at startup (`app.py:756` and `:469`/`:485`). Editing them in the DB changes nothing until a restart, so a screen control would silently do nothing. Stays in `.env`. |
| `JWT_SECRET` | Saving a new value invalidates every session including the engineer's own, mid-save — and it moves a secret from a file with OS permissions into a DB table plus an HTTP endpoint. Rotate it on the server. |


### What this cannot deliver

Say this plainly so nobody promises it to the plant:

**Adding a brand-new WG or DM tag will still need a schema change.** Baselines live in 18 fixed columns on `process_orders` (`baseline_wg101` … `baseline_dm203`), and the lookup is `getattr(order, f"baseline_{tag.lower()}", 0.0)` via `get_attr_safe`, which **swallows the miss and returns `0.0`** (`order_validation.py:6711`, `:5874`). A tag with no matching column silently gets a zero baseline, so `delta = current − 0` = the entire lifetime counter, and that number goes to SAP.

So `scada_tags` makes the **existing** tag set configurable — enable/disable, category, reading type, rollover, source column, emulator seed. It does not make the tag set open-ended. Task **A7** adds the guard that turns that silent failure into a loud one.

PL/SL tags are different: their baselines come from `scale1_qty` / `scale2_qty` / `scale3_qty`, so packing is limited to three concurrent tags per order rather than by column count.

---

## 2. Ground rules

### File ownership is exclusive

Each file belongs to exactly one workstream for the duration. If you need a change in a file you don't own, ask rather than edit.

| Workstream A only | Workstream B only |
|---|---|
| `backend/services/classification_service.py` *(new)* | `backend/models/scada_tag.py` *(new)* |
| `backend/models/classification_rule.py` *(new)* | `backend/models/kpi_config.py` *(new)* |
| `backend/routes/classification_routes.py` *(new)* | `backend/routes/scada_config_routes.py` *(new)* |
| `backend/routes/order_validation.py` | `backend/routes/kpi_config_routes.py` *(new)* |
| `backend/routes/milling_mapping_routes.py` | `backend/services/scale_service.py` |
| `backend/routes/error_log_routes.py` | `backend/services/embedded_emulator.py` |
| `backend/routes/material_routes.py` | `backend/services/scada_persist.py` |
| `backend/services/shift_live_update.py` | `backend/services/create_scada_table.py` |
| `backend/services/process_order_pull.py` | `backend/services/auto_validator.py` *(delete)* |
| `backend/services/scale_lock_service.py` | `backend/models/create_pg_schema.py` *(delete — dead dup)* |
| `backend/services/order_validation_service.py` *(delete)* | `backend/routes/scada_routes.py` |
| `backend/models/milling_version_mapping.py` | `backend/routes/emulator_routes.py` |
| `backend/models/palletizer_mapping.py` | `backend/routes/kpi_routes.py` |
| `Frontend/…/pages/hercules-sfms/MaterialMap.tsx` | `backend/services/kpi_store_flat.py` |
| `Frontend/…/pages/hercules-sfms/PalletizerMapping.tsx` | `backend/services/kpi_incremental.py` |
| `Frontend/…/components/MaterialMappingForm.tsx` | `backend/services/kpi_shift_auto_sync.py` |
| `Frontend/…/pages/hercules-sfms/Engineering.tsx` *(new)* | `backend/routes/sap_sync.py` |
| `Frontend/…/components/hercules-sfms/Sidebar.tsx` | `backend/services/sap_confirmation.py` |
| `backend/routes/engineering_routes.py` *(new)* | `backend/services/sap_real_client.py` |
| `backend/services/runtime_config.py` *(new)* | `backend/config/sap_config.py` |
| | `backend/services/auth_service.py` |
| | `backend/utils/vpn_check.py` |
| | `backend/database.py` · `backend/app.py` |
| | `backend/app_scheduler.py` · `backend/test_imports.py` |
| | `setup_sap_postgres.sql` |
| | `Frontend/…/pages/hercules-sfms/Admin.tsx` |
| | `Frontend/…/pages/hercules-sfms/KpiCalculations.tsx` |
| | `Frontend/…/pages/hercules-sfms/ScadaReadings.tsx` |
| | `Frontend/…/pages/hercules-sfms/LiveMonitor.tsx` |
| | `Frontend/…/components/LiveDataTable.tsx` |
| | `Frontend/…/contexts/ScadaContext.tsx` |
| | `Frontend/…/components/TimeFilter.tsx` |

### Sectioned shared files

Two files are edited by both, but never on the same lines. Commit 0 created the sections.

| File | Rule |
|---|---|
| `Frontend/client/src/lib/api.ts` | Three stub clients were added in commit 0. Fill in **your** block only. |
| `setup_sap_postgres.sql` | All three tables were added in commit 0. Further changes to **your** table go in your own `backend/migrate_*.py`. Reconciled once at the end. |

### No change expected

`Frontend/…/components/ShiftIndicator.tsx` already reads `/api/shifts` correctly and is the reference implementation for B6. Leave it alone.

### Frozen interfaces

| Surface | Owner | Contract |
|---|---|---|
| `services/scale_service` | B | `get_scada_reading`, `calculate_deltas`, `get_multiple_scada_readings`, `sum_dm_readings_for_order` keep their signatures, and `MILLING_FIELDS` / `INPUT_FIELDS` stay importable as lists of tag strings. A imports all of these at `order_validation.py:5599`. Populate the module-level names from `scada_tags` at import time and existing imports keep resolving. |
| `classify_order(order)` | A | Stays importable as `from routes.order_validation import classify_order`. Return dict keeps the keys `order_type`, `equipment`, `formula`, `byproduct`, `packing_info`, `error`. B's `scada_routes.py:489` calls it. |
| `services/runtime_config` | A | `get_setting(key)`, `get_sap_config()`, `get_mssql_config()` — resolves DB → `.env` → documented default. B may **call** it; A owns the module. Added by A8. |

### Two practical traps

**Do not commit a frontend build.** The compiled bundle is committed at `backend/public/assets/index-*.js` and is *not* gitignored. If we both run `npm run build` we conflict on it on every push. One build at the end, from one machine.

**Migrations get separate files.** A standalone `backend/migrate_<name>.py` per change. Don't add steps to each other's scripts, and don't put migrations in `app.py`.

---

## 3. Commit 0 — done (PR #1)

Purely additive, no behaviour change. Exists so neither branch ever opens a shared file.

| What | Collision it removes |
|---|---|
| Three stub blueprints registered in `app.py` — `/api/classification`, `/api/scada-config`, `/api/kpi-config` | Both branches register blueprints |
| Three models imported into the `create_all` block | Same file |
| Three `CREATE TABLE`s + seed data in `setup_sap_postgres.sql` | Both branches add tables |
| Three stub clients in `Frontend/client/src/lib/api.ts` | Both branches add API clients |
| `backend/CONTRACTS.md` | Contract reviewable in the repo |

Seed data reproduces current behaviour, so a fresh DB matches production. Where the repo disagrees with itself, the row is seeded with **what the code does today** and flagged in a comment — see §6.

> **Both feature branches start from `main` *after* commit 0 merges.** Branching off `e6cf018` reintroduces the collisions it removes.

---

## 4. Workstream A — Order routing and plant config

**Branch** `feat/dynamic-order-routing` · **Owner** Mohamed

Delivers capabilities **6** and **9**, and finishes **2** and **3**.

| ID | Task | Acceptance |
|---|---|---|
| **A1** | **Classification rules.** Implement CRUD behind `/api/classification/rules` over the seeded `classification_rules` table. Replace `prefix == "13"` / `"14"` (`order_validation.py:6247`) and the 16 `plant, "3130"` defaults with lookups. | Adding a rule for prefix `15` → MILLING routes a `15…` order without a code change. |
| **A2** | **Packing line mapping into the database.** Add the SCADA tag per line to `palletizer_mapping`; delete `PL_TO_SCADA` (`order_validation.py:5681`) and the hardcoded `32.0` fallback (`:5699`). Rename the two transposed columns — see §6. Fix the BK10 row. | A new packing line is added through the screen, with no code edit, and its orders track. |
| **A3** | **Single classifier, with a cache.** Move `classify_order` into `services/classification_service.py` behind a thread-safe TTL cache, re-exported from its current path. It runs once per order per worker cycle (60 s) and once per order on every SAP pull, so an uncached read adds a query per order per minute. Invalidate from the mapping CRUD routes. | Editing a mapping in Material Map takes effect within one worker cycle. No increase in query count under load. |
| **A4** | **Point the live shift updater at the classifier.** Delete `MILLING_PV_SPECS` (`shift_live_update.py:12`) and `PL_TO_SCADA` (`:30`); call the shared service. **Reconcile the value differences first — §6.** | A version added through Material Map produces shift weights. An unknown version logs an error instead of silently writing nothing. |
| **A5** | **Validator tuning into settings.** `TOLERANCE_PCT` and `WORKER_SLEEP_SECONDS` (`order_validation.py:5866–5867`) move to `system_settings`. Delete the dead `services/order_validation_service.py` — nothing imports it, and its own import of `postgres_session` would fail if anything did. | Changing the worker interval takes effect on the next cycle without a restart. |
| **A6** | **Screens.** `MaterialMap.tsx` and `PalletizerMapping.tsx` **already do full CRUD** against their endpoints — do not rebuild that. Add the classification-rule editor to Material Map, and the SCADA-tag column plus renamed fields to Palletizer Mapping. Also `material_routes.py:59` hardcodes `'PL601'` as the default packing line; drive it from the rules. | An admin can add a classification rule and a packing line from the UI. |
| **A8** | **Engineering page.** Build `/engineering` behind `AdminGuard`, add the nav entry in `Sidebar.tsx`, and implement `GET`/`PUT /api/engineering/settings` plus `POST /api/engineering/test-sap`. Add `services/runtime_config.py` as the single reader (DB → `.env` → default). Seed keys from the current `.env.example`. **Retire the browser-only Admin → SAP form** so there is one source of truth. Excludes `POSTGRES_URL`, `PORT`, `CORS`, `JWT_SECRET` — see §1. | An engineer changes the SAP URL, client or timeout, saves, and the next SAP call uses it with no redeploy and no `.env` edit. Secrets are masked on read. |
| **A7** | **Baseline guard.** `_get_baseline_for_tag` (`order_validation.py:6711`) falls through to `get_attr_safe(order, f"baseline_{tag}", 0.0)`, which returns `0.0` for any tag with no column. Make an unknown tag raise or return `None` and fail the order loudly. | An order referencing an unmapped tag is rejected with a clear error instead of reporting its full lifetime counter as production. |

> **A4 is the one with a live symptom.** `update_live_shift_production` is scheduled every 60 s from `app_scheduler.py:440` and writes `weight_shift_a/b/c` — the values confirmed to SAP at shift end. It resolves equipment from its own hardcoded map while order validation uses the database. Any version added through `/api/milling-mapping` has never reached it.

> **A7 protects B's work.** Without it, the tag registry hands B a way to configure a tag that produces silently wrong SAP confirmations. Land it before B activates any new tag.

---

## 5. Workstream B — Signals and metrics

**Branch** `feat/dynamic-plant-config` · **Owner** Imroz

Delivers capabilities **7** and **8**, and finishes **9**.

| ID | Task | Acceptance |
|---|---|---|
| **B1** | **SCADA tag registry.** Implement CRUD behind `/api/scada-config/tags` and point every hardcoded list at `scada_tags`: five field lists (`scale_service.py:725–768`), `ALLOWED_SCADA_FIELDS` (`:768`), the duplicated lists (`scada_routes.py:300`, `:636`), `SCALE_CATEGORIES` / `REALISTIC_STARTING_VALUES` (`embedded_emulator.py:59–87`), and `SCADA_KEYS` (`app_scheduler.py:272`). | Disabling a tag in the registry removes it from polling, the emulator and the readings API, with no code change. |
| **B2** | **Rollover and range limits per tag.** `PALLETIZER_MAX = 100000` (`scale_service.py:1107`, also `:1595`) and `LO_MAX = 1000000` (`embedded_emulator.py:425`) become registry columns. | Changing a rollover value changes delta maths without a deploy. |
| **B3** | **Close the counter gap.** The five `SL60x_COUNTER` tags are seeded **inactive**. They exist in `ASMArchive_DB5` and `process_orders` has matching `baseline_sl60x_counter` columns, but they are absent from `ALLOWED_SCADA_FIELDS`, so reads return `None` — while `app_scheduler.SCADA_KEYS` polls `SL601_COUNTER` anyway. Verify against `Book1.xlsx`, then activate or record why not. **Do not activate before A7 lands.** | Either the counters read real values, or a comment records the reason they stay off. |
| **B4** | **KPI definitions.** Implement CRUD behind `/api/kpi-config/definitions`; read ceilings and display-name maps from `kpi_config`. Nameplate reads `system_settings.mill_nameplate_tph`. Replaces `nameplate_tph = 25.0` (`kpi_routes.py:262`, repeated `:328`), the nine `min(...)` ceilings (`:272–:383`), `MILLING_MAP` / `PACKING_MAP` (`kpi_store_flat.py:6`, `:20`), and the `plant = "3130"` defaults (`:858`, `:1145`). Resolve the documented-vs-applied difference first — §6. | Changing a ceiling changes the reported KPI on the next refresh. |
| **B5** | **Finish the config hardening.** *(Independent of A8 — see sequencing note.)* `e6cf018` added the plumbing; every secret still survives as the fallback default, so the repo still carries them. Drop the literals, fail fast on a missing required variable, scrub the header comment in `setup_sap_postgres.sql`. Then `CORS_ALLOWED_ORIGINS` (`app.py:472`), `SOURCE_TABLE` and the poll intervals (`app_scheduler.py:280–281`). | Starting with no `.env` fails with a named-variable error, not a silent connection to production. |
| **B6** | **Admin shifts fallback.** The shifts tab **already does full CRUD** against `/api/shifts` — do not rebuild it. `SHIFT_SCHEDULES` (`Admin.tsx:144`) is only the `useState` initial value (`:453`), so a failed or empty fetch silently shows hardcoded times that disagree with the seed. Remove the fallback, show a real empty/error state. Same for `SHIFT_OPTIONS` (`TimeFilter.tsx:34`). | With the API down, the screen says so instead of showing plausible wrong times. |
| **B7** | **Screens read the registry.** `KpiCalculations.tsx` and `ScadaReadings.tsx` take their tag and limit lists from the new endpoints. `KpiCalculations.tsx:914–929` also displays **fabricated fallback numbers** (`100.00`, `36.42`, `66.92`, `13.41`, `19.67`, `12.01`…) when `kpiData` is null — an operator cannot tell those from real readings. Replace with an explicit no-data state. | No screen ever shows a number that isn't measured. |
| **B8** | **SCADA persistence path.** `scada_persist.py` hardcodes 14 tags in both the `INSERT` and the params dict, and `create_scada_table.py` hardcodes the same 14 `VALUE_*` columns. **`PL602_TOT`, `PL603_TOT`, `SL606_TOT` and `SL607_TOT` are collected by the scheduler and then silently dropped.** Drive both from the registry. Delete `models/create_pg_schema.py` — a dead duplicate that nothing imports. | Every pollable tag reaches `scada_aggregate_values`. |
| **B9** | **Live monitoring screens.** `LiveMonitor.tsx` (23 hardcoded tags) and `LiveDataTable.tsx` (16) list tags inline. Drive from `scadaConfigApi`. `ScadaContext.tsx` also hardcodes the business-name mapping (`cleaningScale`, `dryWheatScale`, …) mirroring `scada_routes.py:768–782`; move that mapping into the registry's `display_name`. | Adding a tag to the registry makes it appear on the live screens. |

> **Sequencing: A8 and B5 stay independent.** B5 hardens the `.env` path now and does **not** wait on `runtime_config.py`. Once both branches land, one small follow-up PR switches the SAP/MSSQL consumers to read through `runtime_config`. Making B5 depend on A8 would block B entirely and put A into B's files, which is the one thing this split exists to prevent.

> **B5 has an ops half.** The credentials and JWT key are in a public repository's history, so they stay reachable regardless of what the code does. Removing the fallbacks is the code half; rotating them is the ops half and needs whoever owns those accounts.

---

## 6. Discrepancies to resolve before coding

All verifiable from the repository — the CSVs are exports of the live tables and `Book1.xlsx` is a real 10,000-row sample of `ASMArchive_DB5`. Each one has to be decided before the migration seeds a value, because picking wrong fails silently.

### Milling equipment — three sources, three answers · A4, B-delete

| Version | `milling_version_mappings.csv` | `shift_live_update.py` | `auto_validator.py` | Status |
|---|---|---|---|---|
| **BRF2** | WG501 | **WG502** | WG501, WG502, WG503 | **Live conflict** |
| **BRF1** | *absent* | WG501 | WG501, WG503 | Not in DB |
| LWSM | WG101, WG302, DM101, DM102 | matches | WG101, WG302 | No water |
| CWIM CWLM CWMM CWSM | WG201, WG301, DM201–203 | matches | WG201, WG301 | No water |
| BKF1 CKF1 IWF1 IWF2 BRF3 MMCF | single scale + byproducts | matches | byproducts merged | Double count |
| IWSM SWSM | WG101, WG302 | matches | matches | Agreed |

**RESOLVED — the database row is the wrong one, not `shift_live_update`.** Earlier revisions of this plan assumed the opposite. Two independent checks against repo data settle it, and BRF2 is the only version that fails either.

*Stream identity.* `Book1.xlsx` shows `WG501_Product = F80` in all 10,000 rows and `WG502_Product` = `F70` or `IWW`, tracking `WG202_Product` (the mill recipe). So a recipe written `X + Y` puts X on WG501 and Y on WG502 — confirmed across two different recipes in real data. The stream names come from `auto_validator.py:75-81`, which annotates BRF2 as `BAKERY + BRAWNY + BRAN` (WG501/WG502/WG503) and BRF3 as `BRAWNY + CAKE + BRAN`. Together these fix the product codes: **F80 = Bakery, F70 = Cake, F95 = Brawny, IWW = IWW.**

Every version confirms off the stream carrying its own product:

| Version | Recipe | Stream layout | Its product | Expected | DB says |
|---|---|---|---|---|---|
| BKF1 | F80 | WG501=Bakery | Bakery | WG501 | WG501 ✓ |
| CKF1 | F80+F70 | WG501=Bakery, WG502=Cake | Cake | WG502 | WG502 ✓ |
| IWF1 | F80+IWW | WG501=Bakery, WG502=IWW | IWW | WG502 | WG502 ✓ |
| IWF2 | F70+IWW | WG501=Cake, WG502=IWW | IWW | WG502 | WG502 ✓ |
| BRF3 | F95+F70 | WG501=Brawny, WG502=Cake | Brawny | WG501 | WG501 ✓ |
| MMCF | F80+F70 | WG501=Bakery, WG502=Cake | Cake | WG502 | WG502 ✓ |
| **BRF2** | **F80+F95** | **WG501=Bakery, WG502=Brawny** | **Brawny** | **WG502** | **WG501 ✗** |

*Byproduct coverage.* Every two-flour version tracks three streams (main + two byproducts). BRF2 tracks only two — `scales=["WG501"], scale1=WG503` — leaving WG502 unaccounted. It is the only under-covered row.

The deprecated hardcoded map (`order_validation.py:5790`, `:5815`) has BRF2 as main WG502 with byproducts WG501 + WG503, which passes both checks. `shift_live_update.py:25` agrees.

**So the fix is a data correction, not a code change.** Update the `milling_version_mappings` row for BRF2 to `scales=["WG502"]`, `formula="WG502"`, `scale1="WG501"`, `scale2="WG503"` — then A4 converges the two implementations onto a row that is finally right.

**Impact:** order validation reads the database, so BRF2 orders have been confirming the **Bakery** stream's weight as if it were Brawny production. Worth checking with the mill how long that row has been wrong and whether past BRF2 confirmations need correcting in SAP.

(The same DB edit that broke BRF2 also *fixed* BRF3 — the old hardcoded map had BRF3 with main WG501 and byproduct1 also WG501, a duplicate. So the table was being actively corrected; BRF2 looks like collateral damage from that pass.)

The `auto_validator` column is listed for completeness only — that classifier is unreachable, so its disagreements cause no production symptoms and the module is deleted.

### Packing mapping · A2

- The eight `*L1` / `*L2` versions each have a single line in `palletizer_mapping.csv` (CKL1→PL601, CKL2→PL602, …) but `auto_validator` lists both PL601 and PL602 for all of them.
- `KL1` and `KL2` exist only in `auto_validator`; `CK05` exists only in the database.

**The column names are transposed.** `_convert_packing_delta_to_bags` (`order_validation.py:5718`) uses `bag_size_kg` as the *bags-per-pallet multiplier*, and the CSV agrees — CKL1 carries `bag_size_kg = 32` with `kg_per_pallet = 45`, i.e. 32 bags of 45 kg. `bags_per_pallet` sits unused at 1.

**BK10 breaks the pattern.** Stored as `bag_size_kg = 10, bags_per_pallet = 110, kg_per_pallet = 1200`, where BW10, IW10 and CK10 — same line, same bag weight — are all `bag_size_kg = 110, kg_per_pallet = 10`. As the code reads it, BK10 converts at 10 bags per pallet instead of 110.

### Packing shift times — three values · B6

| Source | Shift A | Shift B | Coverage |
|---|---|---|---|
| `setup_sap_postgres.sql` (seed) | 07:00 – 19:00 | 19:00 – 07:00 | 24 h |
| `Admin.tsx:151` | 07:30 – 15:30 | 15:30 – 23:30 | 16 h |
| `SHIFT_CODE_SUMMARY.md` | 07:30 – 15:30 | 15:30 – 23:30 | 16 h |

Milling agrees everywhere (07:00 / 15:00 / 23:00). Packing does not. Shift boundaries decide when confirmations fire, so this needs a decision before B6 removes the fallback.

### KPI ceilings — document against code · B4

`generate_kpi_doc.py` documents a 150 % ceiling for both *Mill Throughput* (line 61) and *Max Utilization of Milling Capacity* (line 387); `kpi_routes.py` caps both at 100 % (`:272`, `:330`). Throughput above nameplate is physically meaningful, so the 100 % cap may be hiding real over-performance. Commit 0 seeded **100** to match current behaviour.

### SCADA registry gaps · B1, B3, B9

From the column list in `Book1.xlsx`, against `ALLOWED_SCADA_FIELDS`:

- `SL601_COUNTER` … `SL607_COUNTER` exist at source and have matching `baseline_sl60x_counter` columns, but aren't in the allow-list, so reads return `None`. The scheduler polls `SL601_COUNTER` anyway.
- `PL602_TOT`, `PL603_TOT`, `SL606_TOT`, `SL607_TOT` are polled but dropped by `scada_persist.py`.
- `WG*_Product`, `WG*_Destination`, `SL60x_Product`, `SL60x_SIZE` are populated at source and unused everywhere.
- Source casing is inconsistent — `SL601_Product` vs `SL602_PRODUCT`. Store the exact source column, don't derive it.
- There is no `PL606_TOT` or `PL607_TOT`; those lines report as `SL606_TOT` / `SL607_TOT`. That asymmetry is why `PL_TO_SCADA` exists, so line identity and tag name stay separate fields.

---

## 7. Endpoint contracts

Agreed in commit 0 so both sides can build against them without waiting. Stubs exist in `backend/routes/*_routes.py` and `Frontend/client/src/lib/api.ts`.

```
GET    /api/classification/rules              -> ClassificationRule[]
POST   /api/classification/rules              <- ClassificationRuleRequest  -> {success, message}
DELETE /api/classification/rules/:id                                        -> {success, message}

GET    /api/scada-config/tags?category=       -> ScadaTag[]
POST   /api/scada-config/tags                 <- ScadaTagRequest            -> {success, message}
DELETE /api/scada-config/tags/:id                                           -> {success, message}

GET    /api/engineering/settings              -> EngineeringSettings (secrets masked)
PUT    /api/engineering/settings              <- EngineeringSettingsRequest -> {success, message}
POST   /api/engineering/test-sap              <- optional subset            -> {success, message, detail}

GET    /api/kpi-config/definitions?department= -> KpiDefinition[]
POST   /api/kpi-config/definitions             <- KpiDefinitionRequest      -> {success, message}
DELETE /api/kpi-config/definitions/:id                                      -> {success, message}
```

TypeScript interfaces for all three are in `lib/api.ts`. POST is upsert — include `id` to update.

---

## 8. Reference data in the repo

| File | What it gives you | Used by |
|---|---|---|
| `milling_version_mappings.csv` | Export of the live table — 14 versions with scales, formula, byproducts. | A4 |
| `palletizer_mapping.csv` | Export of the live table — 22 versions with line, multiplier, bag weight. | A2 |
| `Book1.xlsx` | 10,000 real rows of `ASMArchive_DB5`, all 63 columns. Definitive tag inventory; real values to test hi/lo concatenation and rollover. | B1, B2, B3, B8 |
| `generate_kpi_doc.py` | Every KPI formula, constant, ceiling and a worked example, in source. | B4 |
| `setup_sap_postgres.sql` | Canonical schema, 25 tables. Rebuild a clean DB from it. | both |
| `ENDPOINT_TO_DB_MAPPING.md` | Every endpoint mapped to the tables it reads and writes. | both |
| `backend/.env.example` | The variable names the code reads. | B5 |
| `backend/CONTRACTS.md` | Frozen interfaces, file and table ownership. | both |
| `ShiftIndicator.tsx` | Working reference for reading `/api/shifts`. | B6 |
| `backend/HARDCODED_SHIFTS_SUMMARY.md` | Prior inventory. References functions that no longer exist — history, not a checklist. | context |

---

## 9. Out of scope this round

- `backend/services/shift_auto_confirm.py` — unowned. It derives department from plant the same hardcoded way, but it is the shift-end SAP confirmation path; changing it alongside everything else is more risk than the cleanup is worth.
- The single `department = "MILLING" if "3130" in plant` at `sap_confirmation.py:355`. B owns that file for B5 but leaves this line; it moves to A's classification service once both branches merge.
- The five duplicate `sync_interval_routes*.py` files and the unregistered `process_orders_clean.py`. Dead, but a separate PR.
- The commented-out code — 43 % of `order_validation.py`, 52 % of `process_orders.py`. It makes every diff unreviewable. Separate PR, after this lands.
- `WG*_Product` / `WG*_Destination` / `SL60x_SIZE` — populated at source, unused. They may make some version mapping unnecessary later; not now.

---

## 10. Done means

- No literal listed above survives in source — `grep` for each returns only migration seed data and tests.
- Every capability in §1 marked ❌ or ⚠️ is editable from a screen, and takes effect without a restart.
- A fresh database seeded from `setup_sap_postgres.sql` produces the same classification, the same shift weights and the same KPI numbers as production does today — except where §6 records a deliberate decision to differ.
- No screen displays a number that isn't measured.
- An order referencing an unmapped tag fails loudly (A7).
- The two frozen interfaces have identical signatures to commit 0.
- One frontend build, committed once, at the end.
