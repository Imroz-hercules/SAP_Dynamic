# Static to Dynamic — Migration Plan

Removing hardcoded plant configuration from Hercules SFMS. Two workstreams, run **sequentially — A first, then B** (agreed 20 Aug 2026). File ownership is still exclusive; see §2 for why it still matters even without parallel work.

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
| Validator tuning | auto-validator cycle interval (`auto_validator_interval_seconds`, live since A5). **Not** a tolerance % — A5 found the tolerance constant was dead and the worker applies none. |

Backend: persist in `system_settings` or a dedicated table; `services/runtime_config.py` is the single reader, resolving **DB → `.env` → documented default**. `.env` stays as first-boot bootstrap.

**Three fields are deliberately excluded** because they cannot work as a live setting — verified in code, not assumed:

| Field | Why it's out |
|---|---|
| `POSTGRES_URL` | `database.py:55` reads it and builds the engine at **import time**, before any DB connection exists. You cannot read the Postgres address out of Postgres. Stays in `.env`. |
| `PORT`, `CORS_ALLOWED_ORIGINS` | Read once at startup (`app.py:756` and `:469`/`:485`). Editing them in the DB changes nothing until a restart, so a screen control would silently do nothing. Stays in `.env`. |
| `JWT_SECRET` | Saving a new value invalidates every session including the engineer's own, mid-save — and it moves a secret from a file with OS permissions into a DB table plus an HTTP endpoint. Rotate it on the server. |


### What this cannot deliver

Say this plainly so nobody promises it to the plant:

**Adding a brand-new WG or DM tag will still need a schema change.** Baselines live in 18 fixed columns on `process_orders` (`baseline_wg101` … `baseline_dm203`). The lookup used to be `getattr(order, f"baseline_{tag.lower()}", 0.0)` via `get_attr_safe`, which **swallowed the miss and returned `0.0`**, so a tag with no matching column silently got a zero baseline — `delta = current − 0` = the entire lifetime counter, and that number went to SAP.

So `scada_tags` makes the **existing** tag set configurable — enable/disable, category, reading type, rollover, source column, emulator seed. It does not make the tag set open-ended.

> **A7 is done (20 Aug 2026).** That silent zero is now a hard failure: an unmapped tag raises, the order is halted with an operator-visible entry in `error_log`, and no SAP payload is built. `backend/services/baseline_guard.py` owns the rule and derives the valid column set from the model. Run `backend/check_unmapped_tags.py` against a database to list any mapping that would halt — all 14 milling and 21 packing production versions currently pass.
>
> **This matters for Workstream B.** If B adds a tag to `scada_tags` and someone maps a version to it, orders on that version will now **stop** rather than report a wrong number, until a `baseline_<tag>` column exists on `process_orders`. Adding a tag to the registry is not by itself enough to make it usable for confirmed-weight production.

PL/SL tags are different: their baselines come from `scale1_qty` / `scale2_qty` / `scale3_qty`, so packing is limited to three concurrent tags per order rather than by column count.

---

## 2. Ground rules

### Execution order

**A runs to completion, then B starts.** That removes the merge-conflict risk the
original split was built around, but three things still matter:

1. **File ownership still holds.** B's task list cites exact line numbers in
   files A does not own. If A edits them anyway, B's plan goes stale before B
   has read it. Stay in your own files; if a task genuinely needs a change
   outside them, record it in the handover.
2. **`backend/app.py` is the known exception.** A8 registers the Engineering
   blueprint there, which shifts B5's cited `app.py:472` (CORS). **B must
   re-verify every line number before starting** — the two plans were written
   against the tree at commit 0.
3. **The frozen interfaces are still binding.** They now protect B's future
   work rather than B's concurrent work, which is a weaker guarantee but the
   same rule: don't change the shape, only what's behind it.

### File ownership

Each file belongs to exactly one workstream. If you need a change in a file you
don't own, note it rather than making it silently.

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
| ~~`backend/services/order_validation_service.py`~~ *(deleted, A5)* | `backend/routes/scada_routes.py` |
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
| **A1** ✅ | **Classification rules — done 20 Aug 2026.** CRUD behind `/api/classification/rules` (plus `GET /resolve?material=` so the editor can preview a change). `resolve_order_type` in `services/classification_service.py` replaces the hardcoded prefixes in both `classify_order` and `material_routes.py`. Matching is by prefix on the zero-stripped code, so rules are not limited to two characters; `*` is consulted last. The 7 live `plant, "3130"` defaults now read `system_settings.default_plant`. **The `plant_department` seed rules are deactivated** — the code derives department from `order_type`, not from plant, and `shift_master` holds *both* departments at plant 3130, so the rule would be wrong. See `migrate_a1_classification_rules.py`. | ✅ Verified live: a `15…` material reported no match, one POST added the rule, and a real order on that prefix then started as MILLING — no restart, no code change. |
| **A2** ✅ | **Packing line mapping into the database — done 20 Aug 2026.** `scada_tag` is now a column on `palletizer_mapping`; `PL_TO_SCADA`, `_translate_pl_to_scada`, `_is_pl_palletizer` and the hardcoded `32.0` fallback are deleted. Added `bags_per_pallet_actual` and `bag_weight_kg` with the correct meanings — **the three old columns are kept and still written**, because `PalletizerMapping.tsx` and `lib/api.ts` require them; A6 switches the screen, a later cleanup drops them. POST accepts either naming. All 21 existing rows verified to resolve the same tag and the same conversion factor as before. **BK10 is reported, not corrected** — see §6. | ✅ A new line (PL612 / PL612_TOT) added through the API classified and started an order with no code change. ⚠️ **Half of this needs B1:** a genuinely new tag returns `None` from `get_scada_reading` until it is in `ALLOWED_SCADA_FIELDS` / `scada_tags`. |
| **A3** ✅ | **Single classifier, with a cache — done 20 Aug 2026.** `classify_order` moved into `services/classification_service.py` behind a 45 s TTL cache keyed on `(order_type, version)`; `routes/order_validation.py` re-exports it, so the path CONTRACTS.md freezes still works. **The plan's premise was wrong in A's favour:** the worker loops roughly once a **second**, not once per 60 s, and `update_order_scales` re-derived a classification its caller already held — so this was load-bearing, not an optimisation. Invalidation is wired into all five mapping writes (`milling-mapping` POST/PATCH/DELETE, `palletizer-mapping` POST/DELETE). | ✅ Measured on a running instance, one PACKING order, Postgres scan counters over 60 s: `palletizer_mapping` **71 → 2**. Editing a mapping through the API reached the next order immediately, well inside the TTL. |
| **A4** ✅ | **Live shift updater on the classifier — done 20 Aug 2026.** `MILLING_PV_SPECS`, the second `PL_TO_SCADA`, `get_equipment_for_order` and the local formula evaluator are deleted; the loop calls the shared (cached) classifier. **Reconciled before deleting:** of the 15 shared versions, 13 matched exactly, BRF1 was dict-only and is retired, and **BRF2 was the single disagreement — the database row was the wrong one**, corrected by `migrate_fix_brf2_mapping.py` (dry-run by default; see §6). Also replaced a third copy of the packing conversion and a local `eval()` on a database-supplied formula string. | ✅ Version ZS02, added through the API and in no hardcoded map, produced `weight_shift_c` on the next 60 s tick. An unmapped version now writes a `configuration_error` to `error_log` within one tick instead of silently writing nothing. |
| **A5** ✅ | **Validator tuning into settings — done 20 Aug 2026.** `TOLERANCE_PCT` and `WORKER_SLEEP_SECONDS` turned out to be **dead** — defined and read nowhere — and neither described real behaviour: the worker sleeps 1 s, not 60, and applies no tolerance. Migrating them would have shipped two controls that changed nothing, so they were deleted. The **live** interval (`WORKER_WAIT = 1`, local to `auto_validation_worker`) now reads `system_settings.auto_validator_interval_seconds` once per cycle, clamped to 0.1–60 s. `services/order_validation_service.py` deleted — it raised `ImportError` on `from database import postgres_session`, so nothing could ever have imported it. | ✅ Verified on a running instance: changing the value took a live worker from ~1 Hz to ~0.17 Hz with no restart (picked up within the 10 s read-cache). |
| **A6** ✅ | **Screens — done 20 Aug 2026.** New `ClassificationRuleEditor.tsx` on Material Map, with a **live preview**: type a material code and see what it resolves to right now. Palletizer Mapping shows `scada_tag` and the correctly-named numbers — the old labels were actively misleading (the form's own placeholder said *"Bag Size (KG) e.g. 45"* for the field used as the **bags-per-pallet multiplier**, which is 32 for that version). `MaterialMappingForm.getMaterialType` used `includes('13')` — the frontend twin of A1's substring bug — and offered PL604/PL605, which have no mapping. Both fixed from the data. `material_routes.py`'s `'PL601'` default now comes from the data. **Two client fixes in the shared `lib/api.ts`:** `classificationApi`'s return types were written against a stub and did not match the A1 backend; and **`getJSON` now attaches the bearer token** like `apiFetch` — this affects Workstream B's clients in the same file too. | ✅ Verified in a browser against the running backend: added, edited and deleted a rule through the UI; a `17…` material resolved to MILLING immediately; the preview showed `000000000014130001 → PACKING`, the exact material the old substring test called MILLING. |
| **A8** | **Engineering page.** Build `/engineering` behind `AdminGuard`, add the nav entry in `Sidebar.tsx`, and implement `GET`/`PUT /api/engineering/settings` plus `POST /api/engineering/test-sap`. Add `services/runtime_config.py` as the single reader (DB → `.env` → default). Seed keys from the current `.env.example`. **Retire the browser-only Admin → SAP form** so there is one source of truth. Excludes `POSTGRES_URL`, `PORT`, `CORS`, `JWT_SECRET` — see §1. | An engineer changes the SAP URL, client or timeout, saves, and the next SAP call uses it with no redeploy and no `.env` edit. Secrets are masked on read. |
| **A7** ✅ | **Baseline guard — done 20 Aug 2026.** `_get_baseline_for_tag` fell through to `get_attr_safe(order, f"baseline_{tag}", 0.0)`, returning `0.0` for any tag with no column. Now raises `UnmappedTagError` (`services/baseline_guard.py`); the worker halts the order, `get_progress` returns 400, and the reason lands in `error_log`. Same guard applied to the duplicate lookup in `shift_live_update.py`. | ✅ An order referencing an unmapped tag is halted with a clear error and no SAP payload, instead of reporting its full lifetime counter as production. |

> ~~**A4 is the one with a live symptom.**~~ **Fixed 20 Aug 2026.** `update_live_shift_production` resolved equipment from its own hardcoded map while order validation used the database, so any version added through `/api/milling-mapping` never reached it. Both now use the same classifier.

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
| **B5** | **Finish the config hardening + consume `runtime_config`.** *(A8 has already landed by the time B starts.)* `e6cf018` added the plumbing; every secret still survives as the fallback default, so the repo still carries them. Drop the literals, fail fast on a missing required variable, scrub the header comment in `setup_sap_postgres.sql`. Then `CORS_ALLOWED_ORIGINS` (`app.py:472`), `SOURCE_TABLE` and the poll intervals (`app_scheduler.py:280–281`). | Starting with no `.env` fails with a named-variable error, not a silent connection to production. |
| **B6** | **Admin shifts fallback.** The shifts tab **already does full CRUD** against `/api/shifts` — do not rebuild it. `SHIFT_SCHEDULES` (`Admin.tsx:144`) is only the `useState` initial value (`:453`), so a failed or empty fetch silently shows hardcoded times that disagree with the seed. Remove the fallback, show a real empty/error state. Same for `SHIFT_OPTIONS` (`TimeFilter.tsx:34`). | With the API down, the screen says so instead of showing plausible wrong times. |
| **B7** | **Screens read the registry.** `KpiCalculations.tsx` and `ScadaReadings.tsx` take their tag and limit lists from the new endpoints. `KpiCalculations.tsx:914–929` also displays **fabricated fallback numbers** (`100.00`, `36.42`, `66.92`, `13.41`, `19.67`, `12.01`…) when `kpiData` is null — an operator cannot tell those from real readings. Replace with an explicit no-data state. | No screen ever shows a number that isn't measured. |
| **B8** | **SCADA persistence path.** `scada_persist.py` hardcodes 14 tags in both the `INSERT` and the params dict, and `create_scada_table.py` hardcodes the same 14 `VALUE_*` columns. **`PL602_TOT`, `PL603_TOT`, `SL606_TOT` and `SL607_TOT` are collected by the scheduler and then silently dropped.** Drive both from the registry. Delete `models/create_pg_schema.py` — a dead duplicate that nothing imports. | Every pollable tag reaches `scada_aggregate_values`. |
| **B9** | **Live monitoring screens.** `LiveMonitor.tsx` (23 hardcoded tags) and `LiveDataTable.tsx` (16) list tags inline. Drive from `scadaConfigApi`. `ScadaContext.tsx` also hardcodes the business-name mapping (`cleaningScale`, `dryWheatScale`, …) mirroring `scada_routes.py:768–782`; move that mapping into the registry's `display_name`. | Adding a tag to the registry makes it appear on the live screens. |

> **Sequencing note.** Because A completes before B starts, B5 can consume `runtime_config.py` directly — A8 will already have landed. The earlier workaround (B5 hardening `.env` independently, with a follow-up PR to switch consumers) is no longer needed; fold it into B5.

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

> **Done in code, pending in production (20 Aug 2026).** `backend/migrate_fix_brf2_mapping.py` carries the evidence and applies the correction. It is a **dry run by default** and needs `--apply`, because it changes which physical scale BRF2 orders confirm to SAP. Applied to the demo database so A4 could be tested; **still to be confirmed with the mill and applied in production.** BRF2 is the only version whose classification changed anywhere in Workstream A.

**Impact:** order validation reads the database, so BRF2 orders have been confirming the **Bakery** stream's weight as if it were Brawny production. Worth checking with the mill how long that row has been wrong and whether past BRF2 confirmations need correcting in SAP.

(The same DB edit that broke BRF2 also *fixed* BRF3 — the old hardcoded map had BRF3 with main WG501 and byproduct1 also WG501, a duplicate. So the table was being actively corrected; BRF2 looks like collateral damage from that pass.)

The `auto_validator` column is listed for completeness only — that classifier is unreachable, so its disagreements cause no production symptoms and the module is deleted.

### Packing mapping · A2

- The eight `*L1` / `*L2` versions each have a single line in `palletizer_mapping.csv` (CKL1→PL601, CKL2→PL602, …) but `auto_validator` lists both PL601 and PL602 for all of them.
- `KL1` and `KL2` exist only in `auto_validator`; `CK05` exists only in the database.

**The column names are transposed.** `_convert_packing_delta_to_bags` (`order_validation.py:5718`) uses `bag_size_kg` as the *bags-per-pallet multiplier*, and the CSV agrees — CKL1 carries `bag_size_kg = 32` with `kg_per_pallet = 45`, i.e. 32 bags of 45 kg. `bags_per_pallet` sits unused at 1.

**BK10 breaks the pattern.** Stored as `bag_size_kg = 10, bags_per_pallet = 110, kg_per_pallet = 1200`, where BW10, IW10 and CK10 — same line, same bag weight — are all `bag_size_kg = 110, kg_per_pallet = 10`. As the code reads it, BK10 converts at 10 bags per pallet instead of 110.

> **Still open after A2.** In the new columns that reads as 10 bags × 1,200 kg = **12,000 kg per pallet**, against 110 × 10 = 1,100 for its three siblings. A 1,200 kg bag is not physical and BK10 is a 10 KG version by name, so the values look rotated. **Not corrected** — changing it changes what BK10 orders confirm to SAP. `migrate_a2_palletizer_mapping.py` prints the evidence and the exact `UPDATE`. Confirm against a real BK10 order, then run it.

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
- **A hands over to B with:** a re-verified line-number pass over B's cited files, a note of anything A changed outside its own file set, and the app starting clean (see the smoke test in the local setup notes).
- Every capability in §1 marked ❌ or ⚠️ is editable from a screen, and takes effect without a restart.
- A fresh database seeded from `setup_sap_postgres.sql` produces the same classification, the same shift weights and the same KPI numbers as production does today — except where §6 records a deliberate decision to differ.
- No screen displays a number that isn't measured.
- An order referencing an unmapped tag fails loudly (A7).
- The two frozen interfaces have identical signatures to commit 0.
- One frontend build, committed once, at the end.
