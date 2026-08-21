# Workstream B — status and what's pending

**For Imroz.** Written 20 Aug 2026, against `main` @ `9694ec8`.

Every state below was **checked against the code today**, not copied from the
plan. Where something has moved since the plan was written, it says so.

Full task descriptions stay in [`STATIC_TO_DYNAMIC_PLAN.md`](STATIC_TO_DYNAMIC_PLAN.md)
§5. This file is the delta: what's true now, and what changed under you while
Workstream A ran.

---

## Where things stand

| | |
|---|---|
| **Workstream A** | ✅ complete — all 8 tasks, merged to `main` |
| **Workstream B** | ⬜ not started — no commits yet |
| Backend tests | 178 assertions across 7 `backend/test_*.py` suites, all passing |
| App | starts clean in demo mode, `GET /api/health` → 200 |

We agreed A runs to completion first, then you start. That's done, so **you're
clear to begin.**

---

## Read this first — five things that changed under you

### 1. Two line numbers in your task list have moved

Both because of A8, both in files A was allowed to touch. The rest of your
citations were re-verified and are **unchanged**.

| Your plan says | Actually now | Task |
|---|---|---|
| `app.py:472` `CORS_ALLOWED_ORIGINS` | **`app.py:477`** | B5 |
| `kpi_routes.py:262` `nameplate_tph = 25.0` | **`kpi_routes.py:279`** | B4 |
| `kpi_routes.py:858` `plant = "3130"` | **`:875`** | B4 |
| `kpi_routes.py:1145` `plant = "3130"` | **`:1162`** | B4 |

`app.py` gained one blueprint import and one registration (A8's Engineering
routes) — the exception we agreed when we went sequential. In `kpi_routes.py`,
four module-level `os.getenv` credential lines became resolver functions, so
everything below `:55` shifted by about **+17**.

**Verified unchanged:** `app_scheduler.py:272`, `scale_service.py:768`,
`:1107`, `:1595`, `embedded_emulator.py:425`, `scada_routes.py:300`, `:636`,
`kpi_store_flat.py:6`, `:20`, `Admin.tsx:144`, `TimeFilter.tsx:34`.

### 2. Most of B5's code half is already done

A8 needed the same thing B5 does, so it built it. `services/runtime_config.py`
is the single reader, resolving **database → `.env` → documented default**.

**Done:** all six SAP config read sites go through it, and

```
grep -rn 'P@ssw0rdP@ssw0rd\|"99999"' --include=*.py backend/
  -> 0 results
```

The SAP credential literals are **gone from the Python source**, and a test
asserts it so they can't come back.

**Still yours:**

- `database.py` still has 2 credential literals as fallback defaults (MSSQL and
  Postgres) — `runtime_config` deliberately does not cover `POSTGRES_URL`,
  because the engine is built at import, before any connection exists.
- **Fail fast on a missing required variable.** `runtime_config.missing_required()`
  already tells you which are unset; nothing acts on it at startup yet.
- `SOURCE_TABLE` — **`app_scheduler.py:278`**.
- `CORS_ALLOWED_ORIGINS` — `app.py:477`.
- The poll intervals — see item 5.
- Scrub the credentials from `setup_sap_postgres.sql`'s header comment
  (5 mentions).
- **The ops half is untouched:** those credentials are in this repository's git
  history. Removing them from source doesn't undo that. They need rotating on
  the accounts.

### 3. ⚠️ A7 constrains B1 and B3 — please read before activating a tag

A7 closed a silent failure: a scale tag with no `baseline_<tag>` column on
`process_orders` used to read a baseline of `0.0`, making the delta the scale's
**entire lifetime counter**, which then went to SAP as production.

It now raises, halts the order, and writes to `error_log`.

**What that means for you:** adding a tag to `scada_tags` is **not enough** to
make it usable for confirmed-weight production. Baselines live in 18 fixed
columns. A tag with no column will now **stop orders** rather than report a
wrong number.

```bash
cd backend && python check_unmapped_tags.py
```

lists any mapping or live order that would halt. It currently passes on all 14
milling and 21 packing production versions. Run it after any registry change.

This is the reason the plan says **"do not activate the SL60x_COUNTER tags
before A7 lands"** — A7 has landed, so you're clear, but check the columns
exist first. They do for `SL601`–`SL607` (`baseline_sl60x_counter`).

### 4. `getJSON` in `lib/api.ts` now attaches the bearer token

A6 changed the shared helper to behave like `apiFetch`. **This affects your
`scadaConfigApi` and `kpiConfigApi`**, which use it.

The config routes are unprotected today, so nothing changes behaviourally — it
means those clients keep working if any route later gains auth. Nothing for you
to do; just so it isn't a surprise in the diff.

### 5. The poll intervals are still yours, and the Engineering page says so

A8's Engineering page shows `SCADA_POLL_INTERVAL_SEC` and
`PO_PULL_INTERVAL_HOURS` **read-only**, with a note saying a restart is needed
and that making them live is B5.

Why they were left: APScheduler bakes the interval into the job at
registration, and the `sched` object is a **local variable** inside
`start_scheduler()` — nothing outside can reach it to call `reschedule_job`.
Making them live means exposing the scheduler, which is in your file.

If you decide not to do it, the page already tells the engineer the truth. If
you do, the page will pick them up once they're marked editable in
`services/runtime_config.py`.

---

## Your tasks — verified state

Nothing below has been started. The "verified" column is what I checked today.

| # | Task | Verified state today |
|---|---|---|
| **B1** | SCADA tag registry | `routes/scada_config_routes.py` still returns the 2 commit-0 stub responses. `scada_tags` is seeded: **28 tags, 23 active, 5 inactive**. `ALLOWED_SCADA_FIELDS` is still the hardcoded tuple at `scale_service.py:768`. |
| **B2** | Rollover / range per tag | `PALLETIZER_MAX = 100000` still at `scale_service.py:1107` **and** `:1595` (two copies). `LO_MAX = 1000000` at `embedded_emulator.py:425`. |
| **B3** | Close the counter gap | Confirmed still open: `SL601_COUNTER` is **not** in `ALLOWED_SCADA_FIELDS`, so reads return `None` — **while `app_scheduler.py` polls it anyway.** All five `SL60x_COUNTER` rows are seeded `is_active = false`. |
| **B4** | KPI definitions | `routes/kpi_config_routes.py` still stubs. `kpi_config` seeded with **19 rows**. `nameplate_tph = 25.0` now at **`kpi_routes.py:279`**. |
| **B5** | Config hardening | **Largely done by A8** — see item 2 above for exactly what's left. |
| **B6** | Admin shifts fallback | `SHIFT_SCHEDULES` still at `Admin.tsx:144`, `SHIFT_OPTIONS` at `TimeFilter.tsx:34`. Both unchanged. |
| **B7** | Screens read the registry | Unchanged. Note the pattern: A6 removed the same class of fabricated fallback from `MaterialMappingForm` — worth reading that commit before you do `KpiCalculations.tsx:914–929`. |
| **B8** | SCADA persistence path | Confirmed still broken: `scada_persist.py` hardcodes **14** tags, and **`PL602_TOT`, `PL603_TOT`, `SL606_TOT` and `SL607_TOT` appear in it zero times** — the scheduler collects them and they are silently dropped. |
| **B9** | Live monitoring screens | Unchanged. |

### One thing in `Admin.tsx` you'll see and should ignore

A8 added a comment block marking the dead SAP form (the one whose own comment
said *"Demo - stores locally, will connect to backend later"*). It was **not
deleted on purpose** — `Admin.tsx` is your file for B6, and removing ~100 lines
would have shifted every line number your task list cites.

Delete it whenever suits you, or leave it for the cleanup PR. The real screen
is now `/engineering`.

---

## Suggested order

Only a suggestion — the dependencies are what matter:

1. **B1** first. B2, B3, B7, B8 and B9 all read the registry it builds.
2. **B3** right after, while B1 is fresh — and run `check_unmapped_tags.py`.
3. **B8** next: it's the one with a live symptom (four tags collected and
   thrown away).
4. **B5** any time — it's mostly independent, and now mostly small.
5. **B4**, then **B6**, **B7**, **B9** — the screens last, same as A did.

---

## Not yours, but worth knowing

Three things are outstanding that neither of us can close alone:

1. **BRF2** — the `milling_version_mappings` row was wrong; A4 corrected it in
   the demo database only. `backend/migrate_fix_brf2_mapping.py` carries the
   evidence and is a **dry run by default**. It needs confirming with someone
   who knows the mill before production, because BRF2 orders have been
   confirming the Bakery stream's weight as Brawny production.
2. **BK10** — `backend/migrate_a2_palletizer_mapping.py` reports it: 10 bags ×
   1,200 kg, where its three siblings on the same line are 110 × 10. Not
   corrected. Same reason.
3. **One frontend build, from one machine, at the end** — per
   `CONTRACTS.md`. A6's and A8's screens exist in source but are **not in the
   committed bundle**, so they don't appear in the served app yet. Don't run
   `npm run build` while you're working; we'd conflict on the bundle on every
   push.

---

## Running it

Demo mode — embedded SCADA emulator and mock SAP, no SQL Server, no VPN.

```bash
# Postgres
"C:\Program Files\PostgreSQL\17\bin\pg_ctl.exe" -D "<your data dir>" -o "-p 5433" start

cd backend && PYTHONIOENCODING=utf-8 python app.py      # :5000, admin / admin123
cd Frontend && npm install && npx vite --port 5173      # proxies /api to :5000
cd backend && python demo_sap_server.py                 # mock SAP on :6000
```

`PYTHONIOENCODING=utf-8` is required — the code prints emoji at import and a
cp1252 console dies before the app starts.

The backend tests are standalone scripts, not pytest:

```bash
cd backend
for t in test_runtime_config test_shift_live_update test_classification_cache \
         test_classification_rules test_palletizer_mapping test_baseline_guard \
         test_validator_interval; do python $t.py | tail -1; done
python check_unmapped_tags.py
```

Please run them before you push — they're the only thing that will tell you if
something in A's half broke.

---

Anything here that doesn't match what you find, tell me — I'd rather fix the
document than have you work around it.
