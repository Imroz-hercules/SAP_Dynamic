# backend/setup_demo_migrations.py
"""
One-shot demo setup for Workstream B (no SQL Server required).

Runs, in order:
  1. migrate_a2_palletizer_mapping.py   — adds scada_tag columns (fixes check_unmapped_tags)
  2. migrate_b1_emulator_seeds.py       — emulator_seed values on scada_tags
  3. migrate_b3_activate_counters.py    — activate SL60x_COUNTER tags
  4. check_unmapped_tags.py             — A7 pre-deploy check

Prerequisites
  * Postgres running and POSTGRES_URL set in backend/.env
  * MSSQL_ENABLED=false  (demo uses the embedded SCADA emulator)
  * Tables seeded (setup_sap_postgres.sql) — if milling_version_mappings is 0 rows,
    load the SQL seed first

Usage (from backend/, with venv active):

    python setup_demo_migrations.py

Then start:
    python app.py
    python demo_sap_server.py          # from repo root or wherever it lives
    cd ../Frontend && npx vite --port 5173
"""
from __future__ import annotations

import os
import runpy
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))


def _banner(title: str) -> None:
    print("\n" + "=" * 60)
    print(title)
    print("=" * 60)


def main() -> int:
    from pathlib import Path
    from dotenv import load_dotenv

    load_dotenv(Path(__file__).resolve().parent / ".env")

    mssql = os.getenv("MSSQL_ENABLED", "true").strip().lower()
    if mssql in ("1", "true", "yes", "on"):
        print(
            "WARNING: MSSQL_ENABLED is true.\n"
            "For demo/mock without SQL Server, set in backend/.env:\n"
            "  MSSQL_ENABLED=false\n"
            "Continuing migrations anyway (they only touch Postgres)..."
        )

    postgres = os.getenv("POSTGRES_URL", "").strip()
    if not postgres:
        print("ERROR: POSTGRES_URL is not set in backend/.env")
        return 1

    here = Path(__file__).resolve().parent

    # --- 1. A2 (always writes columns; no --apply flag) ---------------------
    _banner("1/4  A2 — palletizer_mapping columns")
    sys.argv = ["migrate_a2_palletizer_mapping.py"]
    try:
        runpy.run_path(str(here / "migrate_a2_palletizer_mapping.py"), run_name="__main__")
    except SystemExit as exc:
        if exc.code not in (0, None):
            print(f"A2 failed with exit {exc.code}")
            return int(exc.code or 1)
    except Exception as exc:
        print(f"A2 failed: {exc}")
        return 1

    # --- 2. B1 emulator seeds -----------------------------------------------
    _banner("2/4  B1 — emulator seeds (--apply)")
    sys.argv = ["migrate_b1_emulator_seeds.py", "--apply"]
    try:
        runpy.run_path(str(here / "migrate_b1_emulator_seeds.py"), run_name="__main__")
    except SystemExit as exc:
        if exc.code not in (0, None):
            return int(exc.code or 1)
    except Exception as exc:
        print(f"B1 failed: {exc}")
        return 1

    # --- 3. B3 activate counters --------------------------------------------
    _banner("3/4  B3 — activate SL60x_COUNTER (--apply)")
    sys.argv = ["migrate_b3_activate_counters.py", "--apply"]
    try:
        runpy.run_path(str(here / "migrate_b3_activate_counters.py"), run_name="__main__")
    except SystemExit as exc:
        if exc.code not in (0, None):
            return int(exc.code or 1)
    except Exception as exc:
        print(f"B3 failed: {exc}")
        return 1

    # --- 4. Unmapped-tag check ----------------------------------------------
    _banner("4/4  check_unmapped_tags.py")
    sys.argv = ["check_unmapped_tags.py"]
    try:
        runpy.run_path(str(here / "check_unmapped_tags.py"), run_name="__main__")
    except SystemExit as exc:
        code = int(exc.code or 0)
        if code != 0:
            print(
                "\ncheck_unmapped_tags exited non-zero.\n"
                "If milling_version_mappings showed 0 rows, seed the DB first:\n"
                "  psql -U postgres -f ../setup_sap_postgres.sql\n"
            )
            return code
    except Exception as exc:
        print(f"check_unmapped_tags failed: {exc}")
        print(
            "\nIf the error is missing columns or 0 mapping rows, seed Postgres:\n"
            "  psql -U postgres -f ../setup_sap_postgres.sql\n"
            "then re-run: python setup_demo_migrations.py\n"
        )
        return 1

    _banner("Demo migrations complete")
    print(
        "Next:\n"
        "  1. Confirm backend/.env has MSSQL_ENABLED=false\n"
        "  2. PYTHONIOENCODING=utf-8 python app.py\n"
        "  3. python demo_sap_server.py   (mock SAP :6000)\n"
        "  4. cd ../Frontend && npx vite --port 5173\n"
    )
    return 0


if __name__ == "__main__":
    sys.exit(main())
