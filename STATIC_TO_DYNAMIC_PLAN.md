# Static to Dynamic — Migration Plan

Removing hardcoded plant configuration from Hercules SFMS. Two parallel workstreams with no shared files, no shared functions, and no merge order between them.

| | |
|---|---|
| **Repo** | `Imroz-hercules/SAP_Dynamic` |
| **Base** | `e6cf018` + commit 0 |
| **Branches** | `feat/dynamic-order-routing` · `feat/dynamic-plant-config` |
| **Contracts** | [`backend/CONTRACTS.md`](backend/CONTRACTS.md) |

---

## 0. Where this starts

Most of the dynamic infrastructure already exists. `shift_master`, `milling_version_mappings`, `palletizer_mapping` and `system_settings` are live tables with working CRUD endpoints. What was never finished is deleting the hardcoded copies they were meant to replace — and in two places the hardcoded copy is the one running in production.

So this is a completion job, not a rewrite. Every value below moves from a Python literal into a table or an environment variable, with an endpoint and a screen behind it.

**Everything needed is in the repo.** Seed data, formula definitions and a real SCADA sample are all committed — see [§6 Reference data](#6-reference-data-in-the-repo). Nothing has to be requested from outside the team.

### Already done — not in scope below

**`e6cf018` (Imroz, 20 Aug)** wired `python-dotenv` into `app.py` and `database.py`, moved the DB URLs, SAP host/user/password/client and the JWT secret to environment variables, added `backend/.env.example`, gitignored `.env`, made the Vite dev-proxy target configurable, and added two reference files: `setup_sap_postgres.sql` (full 22-table schema) and `ENDPOINT_TO_DB_MAPPING.md`.

**`2ccc67f` — commit 0** reserves every shared surface so the two branches never touch the same file. Details in [§2](#2-commit-0--done-2ccc67f).

---

## 1. Ground rules

### File ownership is exclusive

Each file belongs to exactly one workstream for the duration. If you need a change in a file you don't own, ask rather than edit — that is the one thing that costs a day.

| Workstream A only | Workstream B only |
|---|---|
| `backend/services/classification_service.py` *(new)* | `backend/models/scada_tag.py` *(new)* |
| `backend/models/classification_rule.py` *(new)* | `backend/models/kpi_config.py` *(new)* |
| `backend/routes/classification_routes.py` *(new)* | `backend/routes/scada_config_routes.py` *(new)* |
| `backend/routes/order_validation.py` | `backend/routes/kpi_config_routes.py` *(new)* |
| `backend/routes/milling_mapping_routes.py` | `backend/services/scale_service.py` |
| `backend/routes/error_log_routes.py` | `backend/services/embedded_emulator.py` |
| `backend/services/shift_live_update.py` | `backend/services/auto_validator.py` *(delete)* |
| `backend/services/process_order_pull.py` | `backend/routes/scada_routes.py` |
| `backend/services/scale_lock_service.py` | `backend/routes/emulator_routes.py` |
| `backend/services/order_validation_service.py` *(delete)* | `backend/routes/kpi_routes.py` |
| `backend/models/milling_version_mapping.py` | `backend/services/kpi_store_flat.py` |
| `backend/models/palletizer_mapping.py` | `backend/services/kpi_incremental.py` |
| `Frontend/…/pages/hercules-sfms/MaterialMap.tsx` | `backend/services/kpi_shift_auto_sync.py` |
| `Frontend/…/pages/hercules-sfms/PalletizerMapping.tsx` | `backend/routes/sap_sync.py` |
| | `backend/services/sap_confirmation.py` |
| | `backend/services/sap_real_client.py` |
| | `backend/config/sap_config.py` |
| | `backend/services/auth_service.py` |
| | `backend/utils/vpn_check.py` |
| | `backend/database.py` · `backend/app.py` |
| | `backend/app_scheduler.py` · `backend/test_imports.py` |
| | `setup_sap_postgres.sql` |
| | `Frontend/…/pages/hercules-sfms/Admin.tsx` |
| | `Frontend/…/pages/hercules-sfms/KpiCalculations.tsx` |
| | `Frontend/…/pages/hercules-sfms/ScadaReadings.tsx` |
| | `Frontend/…/components/TimeFilter.tsx` |

### Frozen interfaces

Two surfaces cross the boundary. Their signatures and return shapes stay as they are — change the implementation behind them freely, not the contract. Also written into `backend/CONTRACTS.md` so it is reviewable in the repo.

| Surface | Owner | Contract |
|---|---|---|
| `services/scale_service` | B | `get_scada_reading`, `calculate_deltas`, `get_multiple_scada_readings`, `sum_dm_readings_for_order` keep their signatures, and `MILLING_FIELDS` / `INPUT_FIELDS` stay importable as lists of tag strings. A imports all of these at `order_validation.py:5599`. Populate the module-level names from `scada_tags` at import time and the existing imports keep resolving. |
| `classify_order(order)` | A | Stays importable as `from routes.order_validation import classify_order` — move the implementation into the service and re-export if you like, but the path stays valid. Return dict keeps the keys `order_type`, `equipment`, `formula`, `byproduct`, `packing_info`, `error`. B's `scada_routes.py:489` calls it. |

### Two practical traps

**Do not commit a frontend build.** The compiled bundle is committed at `backend/public/assets/index-*.js` and is *not* gitignored. If we both run `npm run build` we conflict on it on every push, with a meaningless diff. Nobody commits a build during the sprint — one build at the end, from one machine.

**Migrations get separate files.** Follow the existing convention — a standalone `backend/migrate_<name>.py` per change. Don't add steps to each other's scripts, and don't put migrations in `app.py`; the inline `ALTER TABLE` blocks already in `create_app()` are the pattern we're moving away from.

---

## 2. Commit 0 — done (`2ccc67f`)

Purely additive: 622 insertions, no deletions, no behaviour change. The new blueprints return empty lists or `501`; the new tables are additive and seeded to reproduce today's behaviour. It exists so neither branch ever has to open a shared file.

| What | Why it had to happen first |
|---|---|
| Three stub blueprints registered in `app.py` — `/api/classification`, `/api/scada-config`, `/api/kpi-config` | Both branches add routes. Registering them once removes the only guaranteed `app.py` collision. |
| Three models imported into the `create_all` block | Same reason, same file. |
| Three `CREATE TABLE`s + seed data in `setup_sap_postgres.sql` | That file became canonical in `e6cf018`. Both branches would have appended to it. |
| `backend/CONTRACTS.md` | Frozen interfaces and table ownership, reviewable in the repo instead of in chat. |

Seed data reproduces current behaviour exactly, so a fresh database matches production: material prefixes 13/14, plant 3130, the current `ALLOWED_SCADA_FIELDS`, and the nine KPI ceilings as the code applies them today. Where the repo disagrees with itself, the row is seeded with what the code does now and flagged in a comment for the owner to resolve — see [§5](#5-known-discrepancies-to-resolve).

**After commit 0:** further changes to *your* table go in your own `migrate_*.py`. `setup_sap_postgres.sql` gets reconciled once, at the end, in a single cleanup PR. Merge order between the two branches doesn't matter — the file sets are disjoint, so neither blocks the other.

> **Both feature branches start from `main` *after* commit 0 merges.** Branching off `e6cf018` reintroduces exactly the collisions this commit removes.

---

## 3. Workstream A — Order routing

**Branch** `feat/dynamic-order-routing` · **Owner** Mohamed

One database-backed answer to *"which physical scales does this order read, and with what formula?"* There are currently three answers in three modules, and they disagree.

| ID | Task | Replaces |
|---|---|---|
| **A1** | **Classification rules.** Fill in the CRUD behind `/api/classification` over the seeded `classification_rules` table — material prefix → `order_type`, plant → department. | `prefix == "13"` / `"14"` at `order_validation.py:6247`; `"3130" in plant` plus 14 further `plant, "3130"` defaults |
| **A2** | **Packing line mapping into the database.** Extend `palletizer_mapping` with the SCADA tag per line and rename the two misleading columns. Delete the constant and the 32.0 fallback. Fix the BK10 row — see §5. | `PL_TO_SCADA` at `order_validation.py:5681`; `_get_bags_per_pallet_from_palletizer_type` returning a hardcoded `32.0` at `:5699` |
| **A3** | **Single classifier, with a cache.** Move `classify_order` into `services/classification_service.py` behind a thread-safe TTL cache, re-exported from its current path. It runs once per order per worker cycle (60 s) and once per order on every SAP pull, so an uncached read adds a query per order per minute. Invalidate from the mapping CRUD routes, or edits won't take effect until the TTL expires. | — |
| **A4** | **Point the live shift updater at the classifier.** Delete both constants from `shift_live_update.py` and call the shared service. Reconcile the value differences first. | `MILLING_PV_SPECS` at `shift_live_update.py:12`; `PL_TO_SCADA` at `:30` |
| **A5** | **Validator tuning into settings.** Both constants move to `system_settings`, which already has get/set helpers. Delete the dead `services/order_validation_service.py` — nothing imports it, and its own import of `postgres_session` would fail if anything did. | `TOLERANCE_PCT`, `WORKER_SLEEP_SECONDS` at `order_validation.py:5866–5867`; `RECIPE_MAP` in the dead module |
| **A6** | **Screens for the new rules.** `MaterialMap.tsx` gains the classification-rule editor; `PalletizerMapping.tsx` gains the SCADA-tag column and the renamed fields. | — |

> **Why A4 matters more than it looks.** `update_live_shift_production` is scheduled every 60 seconds from `app_scheduler.py:440` and writes `weight_shift_a/b/c` — the values confirmed to SAP at shift end. It resolves equipment from its own hardcoded map while order validation resolves from the database table. Any version added through `/api/milling-mapping` has never reached it, and a version it doesn't recognise is skipped silently.

---

## 4. Workstream B — Signals and metrics

**Branch** `feat/dynamic-plant-config` · **Owner** Imroz

No SCADA tag, KPI limit, endpoint or credential written into source. Everything a different plant or a different mill line would need to change lives in a table or an environment variable.

| ID | Task | Replaces |
|---|---|---|
| **B1** | **SCADA tag registry.** Fill in the CRUD behind `/api/scada-config` and point every hardcoded list at the seeded `scada_tags` table. Carry per tag: category, reading type (WG hi/lo pair, DM 30-second average, PL/SL counter), source column, rollover limit, and whether it's pollable. | Five field lists at `scale_service.py:725–768`; `ALLOWED_SCADA_FIELDS`; duplicate lists at `scada_routes.py:300` and `:636`; `SCALE_CATEGORIES` and `REALISTIC_STARTING_VALUES` at `embedded_emulator.py:59–87`; `SCADA_KEYS` at `app_scheduler.py:272` |
| **B2** | **Rollover and range limits per tag.** The palletizer wrap-around and the emulator's low-word ceiling become registry columns rather than literals in two modules. | `PALLETIZER_MAX = 100000` at `scale_service.py:1107` (also `:1595`); `LO_MAX = 1000000` at `embedded_emulator.py:425` |
| **B3** | **Close the counter gap.** The five `SL60x_COUNTER` tags are seeded but inactive. Verify them against `Book1.xlsx` and the emulator, then activate — or record why not. | Tags absent from `ALLOWED_SCADA_FIELDS` while `process_orders` carries matching `baseline_sl60x_counter` columns and the scheduler polls `SL601_COUNTER` |
| **B4** | **KPI definitions.** Fill in the CRUD behind `/api/kpi-config` and read the ceilings and display-name maps from the seeded `kpi_config` table. Nameplate rate reads from `system_settings.mill_nameplate_tph`. Resolve the documented-vs-applied ceiling difference first. | `nameplate_tph = 25.0` at `kpi_routes.py:262` and the repeat at `:328`; nine `min(...)` ceilings between `:272` and `:383`; `MILLING_MAP` / `PACKING_MAP` at `kpi_store_flat.py:6` and `:20`; `plant = "3130"` defaults at `kpi_routes.py:858` and `:1145` |
| **B5** | **Finish the config hardening.** `e6cf018` added the plumbing; every secret still survives as the fallback default, so the repo still carries them. Drop the literals, fail fast when a required variable is missing, and scrub the header comment in `setup_sap_postgres.sql`. Then `CORS_ALLOWED_ORIGINS` (`app.py:465`), `SOURCE_TABLE` and the poll intervals (`app_scheduler.py:272–281`). | `os.getenv("SAP_PASSWORD", "P@ssw0rd…")` and the same shape in `database.py`, `auth_service.py`, `sap_config.py`, `sap_confirmation.py`, `sap_real_client.py`, `kpi_shift_auto_sync.py`, `sap_sync.py` |
| **B6** | **Retire `services/auto_validator.py`.** It holds a second, unreachable `classify_order` with its own hardcoded maps. Its only live export is `_convert_to_tons` (imported at `sap_sync.py:317`); the module object is imported at `app.py:365`. Both are your files, so move the function to a shared util and delete the module. | `MILLING_PV_MAPPING` at `auto_validator.py:60`; `PACKING_PV_MAPPING` at `:85`, plus the silent defaults at `:192` and `:196` |
| **B7** | **Screens read their own config.** `Admin.tsx` drops its shift table and calls `/api/shifts`, which already exists and works — `ShiftIndicator.tsx` is a complete reference to copy. `KpiCalculations.tsx` and `ScadaReadings.tsx` take their tag and limit lists from the new endpoints. | `SHIFT_SCHEDULES` at `Admin.tsx:144`; `SHIFT_OPTIONS` at `TimeFilter.tsx:34`; inline tag lists across the three pages |

> **B5 has an ops half.** The SAP, MSSQL and PostgreSQL credentials and the JWT signing key are in a public repository's history, so they stay reachable no matter what the code does next. Removing the fallbacks is the code half; rotating them is the ops half and needs whoever owns those accounts. Neither half is sufficient alone.

---

## 5. Known discrepancies to resolve

All verifiable from the repository — the two CSVs are exports of the live tables and `Book1.xlsx` is a real 10,000-row sample of `ASMArchive_DB5`. Resolve each before the matching code change: the migration has to seed a value, and picking the wrong one fails silently.

### Milling equipment — three sources, three answers · A4, B6

| Version | `milling_version_mappings.csv` | `shift_live_update.py` | `auto_validator.py` | Status |
|---|---|---|---|---|
| **BRF2** | WG501 | WG502 | WG501, WG502, WG503 | **Live conflict** |
| **BRF1** | *absent* | WG501 | WG501, WG503 | Not in DB |
| LWSM | WG101, WG302, DM101, DM102 | matches | WG101, WG302 | No water |
| CWIM CWLM CWMM CWSM | WG201, WG301, DM201–203 | matches | WG201, WG301 | No water |
| BKF1 CKF1 IWF1 IWF2 BRF3 MMCF | single scale + byproducts | matches | byproducts merged in | Double count |
| IWSM SWSM | WG101, WG302 | matches | matches | Agreed |

**BRF2 is the one actually running wrong.** The database says confirmed weight comes off WG501; the scheduled shift updater reads WG502. Different physical scales, so BRF2 shift weights have been going to SAP off the wrong stream. Decide which is correct before A4 lands — the `scada_recipe_name` column in the CSV (`F80 + F95` for BRF2) is the best in-repo evidence.

The `auto_validator` column is listed for completeness. That classifier is unreachable, so its disagreements cause no production symptoms and the module is simply deleted in B6.

### Packing mapping · A2, B6

- The eight `*L1` / `*L2` versions each have a single line in `palletizer_mapping.csv` (CKL1→PL601, CKL2→PL602, …) but `auto_validator` lists both PL601 and PL602 for all of them.
- `KL1` and `KL2` exist only in `auto_validator`; `CK05` exists only in the database.

**Column names don't mean what they say.** `_convert_packing_delta_to_bags` at `order_validation.py:5718` uses `bag_size_kg` as the *bags-per-pallet multiplier*, and the CSV agrees — CKL1 carries `bag_size_kg = 32` with `kg_per_pallet = 45`, i.e. 32 bags of 45 kg. The two columns are transposed relative to their names, and `bags_per_pallet` sits unused at 1.

**One row breaks the pattern.** BK10 is stored as `bag_size_kg = 10, bags_per_pallet = 110, kg_per_pallet = 1200`, where the three comparable 10 kg versions on the same line — BW10, IW10, CK10 — are all `bag_size_kg = 110, kg_per_pallet = 10`. As the code reads it, BK10 converts at 10 bags per pallet instead of 110. Confirm against a real BK10 order before A2 renames anything.

### Packing shift times — three values · B7

| Source | Shift A | Shift B | Coverage |
|---|---|---|---|
| `setup_sap_postgres.sql` (seed) | 07:00 – 19:00 | 19:00 – 07:00 | 24 h |
| `Admin.tsx:150` | 07:30 – 15:30 | 15:30 – 23:30 | 16 h |
| `SHIFT_CODE_SUMMARY.md` | 07:30 – 15:30 | 15:30 – 23:30 | 16 h |

Milling agrees across all three (07:00 / 15:00 / 23:00). Packing does not. A fresh database seeds 12-hour packing shifts while the UI shows 8-hour ones — and shift boundaries drive when confirmations fire, so this needs a decision before B7 makes `Admin.tsx` read from the table.

### SCADA registry gaps · B1, B3

From the column list in `Book1.xlsx`, against `ALLOWED_SCADA_FIELDS`:

- `SL601_COUNTER` … `SL607_COUNTER` exist in the source table and `process_orders` carries matching `baseline_sl60x_counter` columns — but the tags aren't in the allow-list, so `get_scada_reading` returns `None` for all of them. `app_scheduler.SCADA_KEYS` also polls `SL601_COUNTER`, which the service then rejects. Seeded inactive in commit 0 pending B3.
- `WG*_Product`, `WG*_Destination`, `SL60x_Product` and `SL60x_SIZE` are populated at source and unused everywhere. Out of scope now, but they may make some version mapping unnecessary later.
- Source casing is inconsistent — `SL601_Product` against `SL602_PRODUCT`. The registry stores the exact source column rather than deriving it.
- There is no `PL606_TOT` or `PL607_TOT`; those lines report as `SL606_TOT` / `SL607_TOT`. That asymmetry is the whole reason `PL_TO_SCADA` exists, so line identity and tag name stay separate fields.

### KPI ceilings — document against code · B4

`generate_kpi_doc.py` is the authoritative formula reference and disagrees with the implementation twice: it documents a 150 % ceiling for both *Mill Throughput* (line 61) and *Max Utilization of Milling Capacity* (line 387), while `kpi_routes.py` caps both at 100 % (lines 272 and 330). Throughput above nameplate is physically meaningful, so the 100 % cap may be hiding real over-performance. Commit 0 seeded 100 to match current behaviour; change it in B4 if 150 is right.

---

## 6. Reference data in the repo

| File | What it gives you | Used by |
|---|---|---|
| `milling_version_mappings.csv` | Export of the live table — 14 versions with scales, formula and byproduct assignments. Seed source for milling mapping. | A4 |
| `palletizer_mapping.csv` | Export of the live table — 22 versions with line, multiplier and bag weight. | A2 |
| `Book1.xlsx` | 10,000 real rows of `ASMArchive_DB5`, all 63 columns. The definitive tag inventory, and real values to test hi/lo concatenation and rollover against. | B1, B2, B3 |
| `generate_kpi_doc.py` | Every KPI formula, constant, ceiling and a worked example, in source form. | B4 |
| `setup_sap_postgres.sql` | Canonical schema, all 25 tables including the three added in commit 0. Rebuild a clean DB from it. | both |
| `ENDPOINT_TO_DB_MAPPING.md` | Every endpoint mapped to the tables it reads and writes. | both |
| `backend/.env.example` | The variable names the code now reads. | B5 |
| `backend/CONTRACTS.md` | Frozen interfaces, file ownership, table ownership. | both |
| `backend/HARDCODED_SHIFTS_SUMMARY.md` | Prior inventory of the shift constants. It references functions that no longer exist in the live code — history, not a checklist. | context |

---

## 7. Out of scope this round

Named so neither branch drifts into it:

- `backend/services/shift_auto_confirm.py` — unowned. It derives department from plant the same hardcoded way, but it's the shift-end SAP confirmation path and changing it alongside everything else is more risk than the cleanup is worth.
- The single `department = "MILLING" if "3130" in plant` at `sap_confirmation.py:362`. B owns that file for B5 but leaves this line; it moves to A's classification service once both branches merge.
- The five duplicate `sync_interval_routes*.py` files and the unregistered `process_orders_clean.py`. Dead, but deleting them is a separate PR with its own review.
- The commented-out code — 43 % of `order_validation.py`, 52 % of `process_orders.py`. Tempting while you're in there; it makes every diff unreviewable. Separate PR, after this work lands.

---

## 8. Done means

- No literal listed above survives in source — `grep` for each returns only migration seed data and tests.
- Every moved value has an endpoint and a screen, and changing it takes effect without a restart.
- A fresh database seeded from `setup_sap_postgres.sql` produces the same classification, the same shift weights and the same KPI numbers as production does today — except where §5 records a deliberate decision to differ.
- The two frozen interfaces have identical signatures to commit 0.
- One frontend build, committed once, at the end.
