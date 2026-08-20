# Workstream A — Implementation Plan

Branch `feat/dynamic-order-routing` · Owner Mohamed · Base `main` @ commit 0 merged

Companion to [`STATIC_TO_DYNAMIC_PLAN.md`](STATIC_TO_DYNAMIC_PLAN.md). That file
says *what* and *why*. This one says *how*, in the order it should be built,
with the exact line numbers and the test that proves each step.

Every line number below was verified against the working tree on 20 Aug 2026,
after commit 0 merged. Re-check after any rebase.

---

## 0. Findings from the deep read that change the plan

Five things turned up that contradict the master plan. **Read these before
starting — three of them change what the tasks actually are.**

### 0.1 The worker ticks every 1 second, not 60

`STATIC_TO_DYNAMIC_PLAN.md` says `classify_order` runs "once per order per
worker cycle (60 s)". That is wrong. The real loop interval is
`WORKER_WAIT = 1` (`order_validation.py:8861`), used at `:8902`, `:8986`,
`:9591`, `:10112`, `:10114`.

Worse, `auto_validation_worker` calls `update_order_scales` at `:10003`, and
`update_order_scales` calls `classify_order` again at `:6983` for PACKING
orders — **even though the caller already holds a `classification` dict**. So
today a running PACKING order issues a `milling_version_mappings` /
`palletizer_mapping` query roughly **once per second**.

This makes A3's cache load-bearing rather than an optimisation, and it means
there is an easy win available: pass the existing `classification` into
`update_order_scales` instead of re-deriving it.

### 0.2 `TOLERANCE_PCT` and `WORKER_SLEEP_SECONDS` are dead

A5 in the master plan says to move them into `system_settings`. Don't. Grep
across the whole backend finds **no read sites at all** — only the definitions
at `order_validation.py:5866–5867` and their commented-out twins at `:182–183`.

They should be **deleted**, not migrated. Migrating a dead constant into a
settings table creates a control that does nothing — the same mistake we
already rejected for `PORT` and `CORS` on the Engineering page.

### 0.3 There is a third dead block

The master plan says lines 1–5583 and 13720–14531 are dead. There is a third:
**7235–7504**, a commented-out superseded copy of `end_shift_and_confirm`. The
live one starts at 7505.

This matters for counting: the plant `"3130"` hardcode appears **7 times in
live code**, not the 14–16 the master plan claims. Every other hit is in a dead
block.

(The deep-read agent reported 9, counting `:13814` and `:14226` — but both sit
inside the `_DEPRECATED_OLD_STEP_CODE` string literal at 13720–14531. Verified
by grep: 7.)

### 0.4 `process_order_pull.py` reads keys that do not exist

`process_order_pull.py:113–116` does:

```python
classification = classify_order(mock_order)
order_type   = classification.get("order_type")
packing_line = classification.get("packing_line")   # never exists
bag_size     = classification.get("bag_size")       # never exists
```

`classify_order` returns `packing_info: {bag_size_kg, bags_per_pallet, kg_per_pallet, description}`.
There is no `packing_line` key and no `bag_size` key. Both are therefore
**always `None`**, and both are written to the DB that way at `:140–142`.

So `process_orders.packing_line` and `process_orders.bag_size` have been NULL
for every order ever pulled from SAP. Fix as part of A1.

### 0.5 `material_routes.py` uses a substring match, not a prefix match

`material_routes.py:46,56,58` does `if '13' in material_code`. Everywhere else
uses `material.lstrip('0')[:2] == "13"`. A material code containing "13"
anywhere — including inside the zero padding or mid-code — matches. Fix under A1
when the rule moves to the database.

### 0.6 Two smaller notes

- `scale_lock_service.recalculate_conflict_group_priorities` (which imports
  `classify_order` at `:1148`) is **unreachable** — its only call site is
  commented out at `sap_sync.py:711–712`. Don't spend time optimising it.
- `services/classification_service.py` already exists as a stub from commit 0
  with the four function signatures and the caching requirement in its
  docstring. Build into it; don't create a new module.

---

## 1. Build order

Dependencies run left to right. Each step ends green before the next starts.

```
A1 classification rules ─┬─► A3 classifier + cache ─┬─► A4 shift_live_update
                         │                          └─► A6 screens
A2 packing mapping ──────┘
A7 baseline guard  (independent — do early, it protects everything)
A5 delete dead constants (independent — trivial)
A8 Engineering page (independent of A1–A7 — largest single item, do last)
```

Recommended sequence: **A7 → A5 → A1 → A2 → A3 → A4 → A6 → A8.**

A7 first because it converts a silent wrong-number failure into a loud one, and
everything after it benefits from that safety net. A5 second because it is a
five-minute deletion that removes noise from every later diff.

---

## 2. Task detail

### A7 — Baseline guard *(do first)*

**Problem.** `_get_baseline_for_tag` (`order_validation.py:6711–6735`) ends with:

```python
baseline_attr = f"baseline_{tag.lower()}"
return float(get_attr_safe(order, baseline_attr, 0.0) or 0.0)
```

`get_attr_safe` (`:5874`) swallows `AttributeError` and returns the default. So a
tag with no matching column returns `0.0`, indistinguishable from "baseline not
yet captured". `delta = current − 0` becomes the scale's entire lifetime counter,
which flows through `calculate_deltas` → `per_tag_delta` →
`evaluate_formula_using_deltas` → `confirmed_qty` → the SAP payload.

**Change.** Distinguish the three cases:
- tag has a column, value is NULL → `0.0` (legitimate, not yet captured)
- tag has a column with a value → that value
- **tag has no column at all → raise / return `None` and fail the order loudly**

Callers to update: `:6791`, `:6798`, `:6803` (all in `get_current_production`)
and `:11777` (in `get_progress`).

The valid column set is fixed and known — 18 `baseline_*` columns on
`ProcessOrderPG`. Derive it from the model rather than hardcoding a list:
`{c.name for c in ProcessOrderPG.__table__.columns if c.name.startswith("baseline_")}`.

**Test.** Unit: call `_get_baseline_for_tag(order, "PL999_TOT")` and assert it
raises rather than returning `0.0`. Integration: start an order whose mapping
names a nonexistent tag; assert the order is rejected with a clear error and no
SAP payload is built.

---

### A5 — Delete dead constants *(trivial)*

Delete `TOLERANCE_PCT` and `WORKER_SLEEP_SECONDS` (`order_validation.py:5866–5867`).
Delete `backend/services/order_validation_service.py` entirely — nothing imports
it, and its own `from database import postgres_session` would fail if anything
did (no such symbol exists in `database.py`).

**Test.** `grep -rn "TOLERANCE_PCT\|WORKER_SLEEP_SECONDS\|order_validation_service" backend/`
returns nothing outside comments. App still starts.

---

### A1 — Classification rules

**Table** `classification_rules` already exists and is seeded (commit 0):

| rule_type | match_value | result_value | priority |
|---|---|---|---|
| material_prefix | 13 | MILLING | 10 |
| material_prefix | 14 | PACKING | 10 |
| plant_department | 3130 | MILLING | 10 |
| plant_department | * | PACKING | 99 |

**Backend.** Fill in `routes/classification_routes.py` (stub from commit 0,
blueprint already registered at `app.py:588`). GET/POST/DELETE over the table.
POST is upsert on `(rule_type, match_value)`.

Implement `resolve_order_type(material)` and `resolve_department(plant)` in
`services/classification_service.py`. Rules ordered by `priority ASC`, `*` last.

**Call sites to convert:**

| Site | Current | Notes |
|---|---|---|
| `order_validation.py:6240–6253` | `prefix == "13"` / `"14"` | the canonical one |
| `material_routes.py:46,56,58` | `'13' in material_code` | **also fix the substring bug — see §0.5** |
| `process_order_pull.py:113–116` | reads `packing_line` / `bag_size` | **also fix the nonexistent keys — see §0.4** |
| 7 × `get_attr_safe(order, "plant", "3130")` | `:6644, :7604, :7630, :7849, :8174, :8924, :10502` | all feed `get_current_shift` / `get_next_shift`. Verified by grep against the live ranges only. |

**Test.** Insert a rule `material_prefix 15 → MILLING`; assert a material
`000000000001500001` classifies as MILLING with no code change. Assert the four
seeded rules reproduce today's behaviour exactly for a sample of real material
codes taken from the `process_orders` table.

---

### A2 — Packing line mapping into the database

**Change.** Add a `scada_tag` column to `palletizer_mapping`, populated from the
current `PL_TO_SCADA` map. Then delete:
- `PL_TO_SCADA` (`order_validation.py:5681–5687`)
- `_translate_pl_to_scada` (`:5907`) — sole callers `:6341`, `:15627`
- `_is_pl_palletizer` (`:5689`) and `_get_bags_per_pallet_from_palletizer_type`
  (`:5699`, the hardcoded `32.0`) — both only used inside
  `_convert_packing_delta_to_bags` (`:5718`)

`_convert_packing_delta_to_bags` has three callers: `:6850`
(`get_current_production`), `:7001` (`update_order_scales`), `:7212`
(`calculate_shift_weight`).

**Column rename.** `bag_size_kg` actually holds *bags per pallet* and
`kg_per_pallet` holds the *bag weight* — see §6 of the master plan. Rename to
`bags_per_pallet_actual` and `bag_weight_kg`, or add correctly-named columns and
deprecate the old ones. **Do not rename without a data migration** — the
frontend `PalletizerMapping.tsx` and `lib/api.ts` `PalletizerMapping` interface
both use the current names.

**Data fix.** BK10 is stored `bag_size_kg=10, bags_per_pallet=110, kg_per_pallet=1200`
where BW10/IW10/CK10 — same line, same bag weight — are all
`bag_size_kg=110, kg_per_pallet=10`. Confirm against a real BK10 order before
correcting.

**Test.** Add a packing line through the UI with a new SCADA tag; assert an order
on that version tracks. Assert every one of the 22 existing rows produces the
same conversion factor before and after.

---

### A3 — One classifier, with a cache

**Change.** Move the body of `classify_order` (`order_validation.py:6203–6356`)
into `services/classification_service.py`, and re-export from the old location:

```python
from services.classification_service import classify_order   # noqa: F401
```

The contract in `backend/CONTRACTS.md` requires
`from routes.order_validation import classify_order` to keep working —
`scada_routes.py:489` (Imroz's file) depends on it.

**Cache.** Key on `(order_type, version_clean)` — the DB lookup varies on
nothing else. Thread-safe (workers are threads): `threading.Lock` around a plain
dict, or `cachetools.TTLCache`. TTL 30–60 s. Wire `invalidate_cache()` into the
POST/PATCH/DELETE handlers of `milling_mapping_routes.py` and the
`palletizer-mapping` routes (`order_validation.py:15732`, `:15805`) so an edit in
Material Map takes effect immediately.

**Also fix the redundant re-derivation.** `update_order_scales` (`:6954`) calls
`classify_order` at `:6983` although every caller already has the dict.
Add an optional `classification=None` parameter and pass it from `:10003`
(worker loop) and `:12193` (`get_progress`). This alone removes roughly one
query per second per running PACKING order.

**Hot call sites** (measure before and after):

| Site | Frequency |
|---|---|
| `:6983` via `:10003` | ~1/s per running PACKING order |
| `:11670` `get_progress` | per request, ×2 for PACKING via `:12193` |
| `:12498` `get_progress_batch` | per order per request — dashboard polls this |
| `:8558`, `:8578` `_schedule_next_orders_after_completion` | N calls per completion event |
| `process_order_pull.py:113` | per SAP order, every `PO_PULL_INTERVAL_HOURS` |

**Test.** Count queries against `milling_version_mappings` over 60 s with one
PACKING order running, before and after. Expect a fall from ~60 to ~2. Assert
that editing a mapping is reflected within one TTL window.

---

### A4 — Point the live shift updater at the classifier

**This is the one with a live production symptom.** `update_live_shift_production`
runs every 60 s from `app_scheduler.py:440` and writes `weight_shift_a/b/c` — the
values confirmed to SAP at shift end — resolving equipment from its own
hardcoded `MILLING_PV_SPECS` (`shift_live_update.py:12–28`) while validation
uses the database.

**Reconcile first.** Per §6 of the master plan, **BRF2** resolves to WG501 in the
database and WG502 in this dict. Different physical scales. Decide which is
correct before changing code — `scada_recipe_name` (`F80 + F95` for BRF2) is the
best in-repo evidence. **BRF1** exists in the dict but not in the database.

**Change.** Delete `MILLING_PV_SPECS` and `PL_TO_SCADA`
(`shift_live_update.py:12–36`), delete `get_equipment_for_order` (`:39–77`), and
call the shared classifier.

**Also fix the silent skip.** When a version is not in the dict,
`get_equipment_for_order` returns `([], "", order_type)`, and `:143–145` logs a
warning and `continue`s — `weight_shift_*` is never written and nothing surfaces.
After the change, an unresolvable version must raise or write an error state.

**Test.** Add a version through Material Map that is not in the old dict; assert
`weight_shift_*` is written for an order on it. Assert an unknown version
produces a visible error rather than a silent skip. Regression: for every version
in `milling_version_mappings.csv`, assert the equipment list and formula the new
path produces match what the old dict produced — except BRF2, where the change
is deliberate and must be recorded.

---

### A6 — Screens

`MaterialMap.tsx` and `PalletizerMapping.tsx` **already do full CRUD** against
`/api/milling-mapping` and `/api/orders/palletizer-mapping` respectively. Do not
rebuild that.

- `MaterialMap.tsx` — add the classification-rule editor, using
  `classificationApi` (already written in `lib/api.ts` by commit 0).
- `PalletizerMapping.tsx` — add the `scada_tag` column and the renamed fields.
- `MaterialMappingForm.tsx` — one hardcoded tag; drive from the rules.

**Note on auth.** `getJSON` in `lib/api.ts` does **not** attach the bearer token,
unlike `apiRequest` (`queryClient.ts:38`) and `apiFetch` (`apiConfig.ts:78`).
`classificationApi` uses `getJSON`, so if the classification routes require auth,
these calls will 401. Decide whether the routes are protected and make the client
match.

**Test.** Add, edit and delete a rule through the UI; confirm it persists and
that an order reclassifies accordingly.

---

### A8 — Engineering page *(largest item, do last)*

Full scope in §1 of the master plan. Key implementation notes from the deep read:

**What `runtime_config.py` can actually serve.** Values read at *import* time
cannot become live settings without a restart. Verified import-time reads:

| Value | Where |
|---|---|
| All 9 `SAP_CONFIG` entries | `config/sap_config.py:5–13` |
| SAP creds (4 more copies) | `kpi_shift_auto_sync.py:32–35`, `sap_sync.py:326–329`, `kpi_routes.py:55–58` |
| VPN check target | `vpn_check.py:8` — a bare literal, no env var |
| Postgres / MSSQL engines | `database.py:50`, `:58` |
| Poll intervals | `app_scheduler.py:280–281`, baked into `add_job` |

**Already per-call and safe to redirect:** `is_mssql_enabled()` (`database.py:33`),
`get_demo_mode()` / `get_mock_sap_mode()` (`:72`, `:85`), the `mock_mode`
property (`sap_confirmation.py:69`), and `get_sap_url`'s client read
(`kpi_routes.py:85`).

**One trap:** `sap_confirmation.py:2481` creates a module-level singleton
`sap_confirmation_service = SAPConfirmationService()`, freezing its credentials
at import even though the class is re-instantiated per-request elsewhere.
`offline_confirmations.py` uses that singleton.

**Poll intervals need reschedule logic.** APScheduler jobs are registered with
literal `seconds=` / `hours=` arguments. Changing a stored value does nothing
without `sched.reschedule_job(...)`, which does not exist in this codebase. Either
implement it or leave intervals out of the page.

**Two inconsistencies to resolve before centralising:**
1. `kpi_shift_auto_sync.py:83,174,279` passes `client="200"`, ignoring
   `SAP_CLIENT` entirely; everything else uses `250`.
2. Mock mode is not applied uniformly. `sap_real_client.py` and `sap_sync.py`
   contain **no mock branch at all** — toggling "Mock SAP" does not stop order
   pull from hitting the real SAP endpoint. Confirm whether that is intended
   before the page presents it as one global switch.

**`get_setting` cannot store JSON.** `models/system_settings.py` coerces
`boolean` / `integer` / `float` only; `value_type="json"` falls through and
returns a raw string. Parse in `runtime_config.py` or extend the helper.

**Retiring the Admin → SAP form is easier than it looks.** `saveSapEndpoints`
(`Admin.tsx:1238`) and `testSapConnection` (`:1277`) are **never called by any
button**, and the six endpoint state variables have no rendered inputs. Only the
mock/real toggle and the sync-interval field are real, and both already hit the
backend. So most of that tab is already dead code.

**`getJSON` sends no auth token.** The Engineering page handles secrets. Its
client must attach the bearer token — use `apiRequest` or `apiFetch`, or fix
`getJSON`.

**Test.** Change the SAP base URL on the page, save, trigger a confirmation, and
assert the outbound request uses the new URL with no restart. Assert `GET`
returns secrets masked. Assert an unset required value produces a named error
rather than a silent fallback to a committed literal.

---

## 3. Test strategy

There is no test suite in this repo — the `backend/test_*.py` files are
standalone scripts, not pytest. Rather than retrofit a framework mid-migration,
each task above states its own executable check.

**Baseline first.** Before touching anything, capture current behaviour from a
running instance so every change can be diffed against it:

```bash
# with the app running on :5000
curl -s localhost:5000/api/orders/debug/scale-mappings   > /tmp/before_scale_mappings.json
curl -s localhost:5000/api/orders/debug/packing-mappings > /tmp/before_packing_mappings.json
```

Those two debug routes (`order_validation.py:15543`, `:15611`) dump exactly the
classification output this workstream is changing. They are the cheapest
regression harness available — capture before, compare after, and any unintended
change shows up immediately.

**Local environment.** See [`LOCAL_DEV_SETUP.md`](LOCAL_DEV_SETUP.md) — demo mode
with the embedded emulator, no SQL Server, no VPN.

---

## 4. Risks

| Risk | Mitigation |
|---|---|
| BRF2 decision is wrong → wrong weights to SAP | Decide before A4; record the decision in the commit message |
| Cache TTL hides a mapping edit | Explicit `invalidate_cache()` on every mapping write; short TTL |
| Renaming palletizer columns breaks the frontend | Add new columns, migrate data, deprecate old ones; don't rename in place |
| A7 turns a silent failure into a hard failure on live orders | Ship A7 with a clear operator-facing message, and check no current order references an unmapped tag before deploying |
| `classify_order` signature drifts | `backend/CONTRACTS.md` — the return keys are load-bearing for four other modules, two of them Imroz's |
