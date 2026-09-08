# Workstream B — status and what's pending

**Updated 8 Sep 2026.** Both workstreams are code-complete, verified together on
one machine, and the single end-of-sprint frontend build has been taken.
Supersedes the 21 Aug snapshot.

Full task descriptions stay in [`STATIC_TO_DYNAMIC_PLAN.md`](STATIC_TO_DYNAMIC_PLAN.md)
§5. This file is the live delta: what is done, what is left, and what is shared.

---

## Where things stand

| | |
|---|---|
| **Workstream A** | ✅ complete — all 8 tasks, merged to `main` |
| **Workstream B** | ✅ **complete** — B1–B9 |
| Branch | Prefer `feat/dynamic-plant-config` (create/push if not yet on remote) |
| Demo DB (E:) | Seeded: 28 `scada_tags`, 19 `kpi_config`, 14 milling + 21 packing mappings; A7 `check_unmapped_tags` **PASS** |
| App (demo) | `MSSQL_ENABLED=false` — embedded SCADA emulator + `backend/demo_sap_server.py` (:6000) |

---

## Task status (verified against code)

| # | Task | Status | Notes |
|---|---|---|---|
| **B1** | SCADA tag registry | ✅ Done | CRUD `/api/scada-config/tags`; `scada_tag_registry.py` drives `scale_service`, emulator, scheduler, `scada_routes` |
| **B2** | Rollover / range per tag | ✅ Done | `get_rollover_max()` from `scada_tags.rollover_max` (packing + LO) |
| **B3** | Close the counter gap | ✅ Done | `migrate_b3_activate_counters.py --apply`; counters active; baselines exist; A7 PASS |
| **B4** | KPI definitions | ✅ Done | CRUD `/api/kpi-config/definitions`; ceilings + nameplate via `kpi_config_registry`; plant default from `get_default_plant()` |
| **B5** | Config hardening | ✅ Mostly done | No Postgres/MSSQL credential fallbacks; startup `missing_required()`; `CORS_ALLOWED_ORIGINS` / `SCADA_SOURCE_TABLE` from env; SQL header scrubbed. **Optional skip:** live poll-interval reschedule (Engineering still read-only — OK) |
| **B6** | Admin shifts fallback | ✅ Done | No fabricated `SHIFT_SCHEDULES` / `SHIFT_OPTIONS`; empty/error when API fails |
| **B7** | Screens read registry | ✅ Done | `ScadaReadings.tsx` now takes its rows from `scadaConfigApi` and shows **NO DATA** rather than `0` before the first successful fetch. Verified 18/18 registry tags match the `rawSignals` keys the API returns. Optional tag/KPI CRUD editor UI still not built (APIs exist) |
| **B8** | SCADA persistence path | ✅ Done | `scada_persist` / schema columns from registry; dead `create_pg_schema.py` removed |
| **B9** | Live monitoring screens | ✅ Effectively done | `LiveMonitor` + `LiveDataTable` use the registry. The hardcoded business names still exist in `scada_routes.py`, but **no screen reads them any more** (grep, 8 Sep) — they are dead pass-through. See the note below before deleting them |

---

## Remaining

1. **Optional** — Admin/Engineering UI for SCADA tag + KPI definition CRUD (backend ready,
   and now admin-only for writes — see the security note below).
2. **Optional B5** — expose scheduler and make `SCADA_POLL_INTERVAL_SEC` /
   `PO_PULL_INTERVAL_HOURS` live; otherwise leave read-only as today.
3. **Mapping routes still have no authentication.** `palletizer_mapping` and
   `milling_version_mappings` can be rewritten by anyone who reaches the backend.
   The config routes were fixed (below); these are a larger surface with more
   callers and are left recorded rather than changed in the same pass.
4. **Frontend type check is red** — 58 pre-existing semantic errors, see below.

---

## Three things found on 8 Sep that are worth reading before you touch this again

**1. The business-name fields in `scada_routes.py` are mislabelled, not just hardcoded.**
B9 called this "polish". It is not. Each of these is a raw counter served under a
name that means something else entirely:

| Field shown on screen | Actually the value of | Registry name for that tag |
|---|---|---|
| `totalRunningTime` | `WG202` | Clean wheat — active scale (TON) |
| `totalFlour` | `WG302` | Pre-clean screenings |
| `packingStdCapacity` | `PL602_TOT` | Palletizer 2 |
| `packingGoodOutput` | `PL603_TOT` | Palletizer 3 — bran |
| `packingPlannedOutput` | `PL602_TOT` | Palletizer 2 *(again)* |

`scada_routes.py:799` even carries the comment "Using PL602_TOT as planned output".
A "Total Running Time" reading in tons is the same plausible-wrong-number defect
the rest of this migration exists to remove. B7 stopped rendering all of them, so
nothing shows these today — but the fields are still built and returned by the
API, and they must not be reintroduced onto a screen. Deleting them from
`scada_routes.py` is safe (nothing reads them) and is the right follow-up.

**2. The graded test gate could not fail.** Every `test_*.py` in this backend counts
failures in a `failed` variable instead of raising — 0 `assert` statements across
24 files against 197 `check()` calls — so under pytest a failing suite still exited
0. Proven with two mutations, one per workstream (A7's baseline guard returning
`0.0`; `allowed_fields()` ignoring `is_active`): both left `pytest -q` green.
`backend/conftest.py` now fails any test whose module's counter moved, and both
mutations go red. Do not delete that file; `nexus.verdict.json` holds it out.

`test_kpi_config.py` was worse: every check lived inside `main()`, so it defined no
`test_*` function and **the gate ran none of B4's regression suite**. Split into
`test_*` functions on 8 Sep.

**3. B1's test and B3's migration contradicted each other.** Three checks in
`test_scada_config.py` used `SL601_COUNTER` as their fixture for "an inactive tag
is excluded", but B3 activates that tag deliberately. Applying B3 turned the suite
red without anything regressing. The checks now build and drop their own fixture
row, so they no longer depend on a production row's mutable state — and they still
catch the mutation.

Related: the `_BOOTSTRAP` list in `scada_tag_registry.py` (the fallback used when
the database is unreachable) still said those five counters were inactive, so a
brief outage would have silently dropped every packing bag counter. Bootstrap and
database are now compared directly and agree on all 28 tags and 19 KPI rows.

---

## Security: config writes are now admin-only

`POST /api/scada-config/tags` returned **HTTP 201 with no token at all** (measured
8 Sep, then cleaned up). Anyone who could reach the backend could add a tag,
deactivate a real one, or change a KPI ceiling — and a deactivated tag drops out
of `allowed_fields()` and `poll_keys()`, so its readings stop arriving and the
delta that reaches SAP is computed without it.

`services/config_guard.py` now rejects non-admin writes on both config blueprints;
**GET is deliberately unchanged**, because the screens build their tag and KPI
lists from it. `getJSON` has attached the bearer token since A6, so the admin
screens keep working. Covered by `backend/test_config_auth.py`, which needs no
database and fails if the guard is removed or unwired.

---

## Remaining (process / ship)

- [x] Workstream B merged and verified alongside A on one machine (8 Sep).
- [x] **The single end-of-sprint frontend build has been taken** (8 Sep) and copied
      to `backend/public/`. Confirmed the shipped bundle contains the new code
      (`NO DATA`, `scada-config/tags`) and none of the fabricated KPI literals
      (`36.42`, `66.92`, `13.41`, `19.67`, `12.01` — all zero literal matches).
      Do not take another one casually; the rule stands for the next sprint.
- [ ] Sync Desktop ↔ `E:\sap\SAP_Dynamic` so both trees match.

Full check, with Postgres up — **212 assertions, 0 failed** on 8 Sep:

```bash
cd backend
for t in test_runtime_config test_shift_live_update test_classification_cache \
         test_classification_rules test_palletizer_mapping test_baseline_guard \
         test_validator_interval test_scada_config test_kpi_config \
         test_config_auth; do
  python $t.py
done
python check_unmapped_tags.py          # A7 pre-deploy: PASS
python -m pytest -q -p no:cacheprovider   # the graded gate: 53 passed, 17 deselected
```

The last line is the one CI grades. Run it as well as the loop — they are not
the same thing, and until 8 Sep the loop could be red while pytest was green.

---

## Not yours alone (unchanged)

1. **BRF2** — `migrate_fix_brf2_mapping.py` (dry-run by default); confirm with mill before production.
2. **BK10** — packing row looks rotated (10 × 1200 vs siblings 110 × 10); A2 reports it, does not correct.
3. **Ops** — rotate credentials that remain in git history.
4. **One frontend build**, from one machine, at the end (`CONTRACTS.md`).

---

## Demo / mock (no SQL Server)

```bash
# backend/.env
MSSQL_ENABLED=false
POSTGRES_URL=postgresql+psycopg2://USER:PASS@localhost:5432/sap

# One-shot seed + A2/B1/B3 + A7 check (if DB was empty)
python setup_demo_migrations.py
# or stepwise: migrate_seed_demo_data.py → migrate_a2… → migrate_b1… --apply → migrate_b3… --apply → check_unmapped_tags.py

PYTHONIOENCODING=utf-8 python app.py          # :5000
python demo_sap_server.py                     # :6000 (reads POSTGRES_URL; DB name demo_server)
# Frontend
cd ../Frontend && npx vite --port 5173
```

Login (SQL seed): `admin` / `admin123`.

---

## Helper scripts added for B

| Script | Purpose |
|---|---|
| `migrate_seed_demo_data.py` | Fill empty `scada_tags` / `kpi_config` / rules / mappings from plan seed + CSVs |
| `migrate_b1_emulator_seeds.py` | Set `emulator_seed` from historical REALISTIC values |
| `migrate_b3_activate_counters.py` | Activate `SL60x_COUNTER` rows |
| `setup_demo_migrations.py` | Runs seed → A2 → B1 → B3 → `check_unmapped_tags` |
| `test_scada_config.py` / `test_kpi_config.py` | B regression scripts (PASS/FAIL style like A’s) |
| `backend/demo_sap_server.py` | Mock SAP (:6000); credentials from `.env` |

---

## Handover notes from A (still true)

- A7: unmapped tags **halt** orders — run `check_unmapped_tags.py` after registry changes.
- A8: most SAP config hardening already done via `runtime_config.py`.
- `getJSON` attaches the bearer token — `scadaConfigApi` / `kpiConfigApi` benefit.
- Poll intervals stay restart-bound unless optional B5 live reschedule is done.

Anything here that does not match what you find on disk, update this file rather than working around it.
