# Workstream B — status and what's pending

**Updated 21 Aug 2026.** Reflects code on Desktop `SAP_Dynamic` plus migrates
applied on the E: demo machine. Supersedes the 20 Aug “not started” snapshot.

Full task descriptions stay in [`STATIC_TO_DYNAMIC_PLAN.md`](STATIC_TO_DYNAMIC_PLAN.md)
§5. This file is the live delta: what is done, what is left, and what is shared.

---

## Where things stand

| | |
|---|---|
| **Workstream A** | ✅ complete — all 8 tasks, merged to `main` |
| **Workstream B** | ✅ **core complete** (B1–B6, B8; B7/B9 mostly done) |
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
| **B7** | Screens read registry | ⚠️ Partial | Fake KPI numbers removed. **Left:** drive `ScadaReadings.tsx` from `scadaConfigApi`; optional tag/KPI CRUD editor UI (APIs exist, no dedicated screen yet) |
| **B8** | SCADA persistence path | ✅ Done | `scada_persist` / schema columns from registry; dead `create_pg_schema.py` removed |
| **B9** | Live monitoring screens | ⚠️ Mostly done | `LiveMonitor` + `LiveDataTable` use registry. **Left (polish):** `ScadaContext` / `scada_routes` business names (`cleaningScale`, …) → `display_name` |

---

## Remaining (code polish)

1. **B7** — `ScadaReadings.tsx` from `scadaConfigApi` (and/or dynamic fields from context).
2. **Optional** — Admin/Engineering UI for SCADA tag + KPI definition CRUD (backend ready).
3. **B9 polish** — map registry `display_name` into live aggregate labels instead of hardcoded API keys in `ScadaContext` / `scada_routes`.
4. **Optional B5** — expose scheduler and make `SCADA_POLL_INTERVAL_SEC` / `PO_PULL_INTERVAL_HOURS` live; otherwise leave read-only as today.

---

## Remaining (process / ship)

- [ ] Commit & push Workstream B on `feat/dynamic-plant-config` (if not already).
- [ ] Sync Desktop ↔ `E:\sap\SAP_Dynamic` so both trees match.
- [ ] On E: with Postgres up, re-run:

```bash
cd backend
for t in test_runtime_config test_shift_live_update test_classification_cache \
         test_classification_rules test_palletizer_mapping test_baseline_guard \
         test_validator_interval test_scada_config test_kpi_config; do
  python $t.py
done
python check_unmapped_tags.py
```

- [ ] **Do not** run `npm run build` until the agreed single end-of-sprint build.

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
