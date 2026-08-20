# Local Dev Setup — running Hercules SFMS on a bare machine

Verified working on Windows Server 2022, 20 Aug 2026. Demo mode: embedded SCADA
emulator + mock SAP, so **neither SQL Server nor the SAP VPN is required**.

One process on port 5000 serves both the API and the UI — the compiled React
bundle is committed at `backend/public/`, so Vite is not needed to run the app.

---

## 1. Python dependencies

`backend/requirements.txt` is accurate but the machine may be missing several:

```bash
python -m pip install psycopg2-binary PyJWT bcrypt APScheduler flask-cors schedule colorlog
```

`pandas`, `numpy`, `openpyxl`, `pyodbc`, `requests`, `python-dateutil`, `SQLAlchemy`,
`Flask` were already present. `pyodbc` imports fine even with no SQL Server installed —
the engine is created lazily and never connected when `MSSQL_ENABLED=false`.

## 2. PostgreSQL

The app needs a real PostgreSQL — it uses `JSONB`, `SERIAL`, `ON CONFLICT`
and `TIMESTAMPTZ`, so there is no SQLite fallback.

If you already have one and know the superuser password, use it. Otherwise a
throwaway cluster on a spare port avoids touching the system instance:

```bash
PGBIN="/c/Program Files/PostgreSQL/17/bin"
printf 'hercules_dev' > pw.txt
"$PGBIN/initdb.exe" -D "C:\\hercules_demo_pg" -U postgres \
    --auth-local=trust --auth-host=scram-sha-256 --pwfile=pw.txt -E UTF8
rm pw.txt
"$PGBIN/pg_ctl.exe" -D "C:\\hercules_demo_pg" -o "-p 5433" \
    -l "C:\\hercules_demo_pg\\server.log" start
```

Then create and seed the schema:

```bash
PGPASSWORD=hercules_dev "$PGBIN/psql.exe" -h 127.0.0.1 -p 5433 -U postgres \
    -d postgres -v ON_ERROR_STOP=1 -f setup_sap_postgres.sql
```

`setup_sap_postgres.sql` is idempotent (`CREATE TABLE IF NOT EXISTS`,
`ON CONFLICT DO NOTHING`) and creates all 25 tables plus seed data, including
the default `admin` / `admin123` login.

Stop the cluster with `pg_ctl -D "C:\hercules_demo_pg" stop`; delete the
directory to remove it entirely.

## 3. `backend/.env`

Gitignored — create it from `backend/.env.example`. Minimum for a demo run:

```
PORT=5000
JWT_SECRET=local-dev-only-not-a-real-secret
POSTGRES_URL=postgresql+psycopg2://postgres:hercules_dev@127.0.0.1:5433/sap
MSSQL_ENABLED=false
```

`MSSQL_ENABLED=false` is what makes a SQL-Server-free run possible. Demo mode
and mock SAP are already the defaults in `system_settings`, so no SAP or VPN
config is needed.

## 4. Start it

```bash
cd backend
PYTHONIOENCODING=utf-8 python app.py
```

**`PYTHONIOENCODING=utf-8` is required on Windows.** The code prints emoji
during import (e.g. `order_validation.py:5637`) and a cp1252 console raises
`UnicodeEncodeError` before the app can start:

```
UnicodeEncodeError: 'charmap' codec can't encode character '\u274c'
```

Then open <http://localhost:5000> and log in as `admin` / `admin123`.

---

## Smoke test

```bash
B=http://127.0.0.1:5000
curl -s $B/api/health
curl -s $B/api/shifts
curl -s $B/api/system/mode
curl -s -X POST $B/api/auth/login -H "Content-Type: application/json" \
     -d '{"username":"admin","password":"admin123"}'
```

Expected: `200` from each; `/api/system/mode` reports `"demo_mode": true` and a
non-zero `emulator_active_scales`; login returns a JWT.

---

## Known gotchas

| Symptom | Cause |
|---|---|
| `UnicodeEncodeError: 'charmap' codec` on startup | Emoji in print statements. Set `PYTHONIOENCODING=utf-8`. |
| `ModuleNotFoundError: No module named 'schedule'` | In `requirements.txt` but easy to miss. Install it. |
| App starts, everything 500s | Postgres unreachable, or `POSTGRES_URL` password wrong. Check `backend/.env`. |
| ODBC / SQL Server errors at startup | `MSSQL_ENABLED` is unset or `true`. Set it to `false` for demo. |
| Port 5000 already bound | Another instance still running. |

---

## Commit 0 verification — 20 Aug 2026

The scaffold commit (three stub blueprints, three models, seed data) was
verified against a live database and a running server, not just by import:

| Check | Result |
|---|---|
| `setup_sap_postgres.sql` applies cleanly | 25 tables created |
| `classification_rules` seeded | 4 rows — prefixes 13/14, plant 3130, `*` catch-all |
| `scada_tags` seeded | 28 rows — 23 active, 5 `SL60x_COUNTER` inactive by design |
| `kpi_config` seeded | 19 rows, ceilings matching current `kpi_routes.py` behaviour |
| `system_settings.mill_nameplate_tph` | `25` (float) |
| App starts with the three new blueprints registered | yes, no startup error |
| `GET /api/classification/rules` | `200 []` |
| `GET /api/scada-config/tags` | `200 []` |
| `GET /api/kpi-config/definitions` | `200 []` |
| `POST` to each of the three | `501 {"error":"Not implemented"}` — stubs behaving as designed |
| Regression: `/api/health`, `/api/time`, `/api/shifts`, `/api/system/mode` | all `200` |
| Regression: login + `/api/auth/me` | `200`, JWT issued, permissions returned |
| Regression: UI bundle at `/` | `200`, `<title>Hercules - SFMS</title>` |
| Emulator producing data | yes — 26 active scales, values incrementing |

Conclusion: commit 0 is additive and inert. It creates its tables, registers its
routes, and changes no existing behaviour.
