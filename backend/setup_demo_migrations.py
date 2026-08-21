# backend/setup_demo_migrations.py
"""
One-shot demo setup for Workstream B (no SQL Server required).

Runs, in order:
  0. migrate_seed_demo_data.py          — fill empty scada_tags / kpi / mappings
  1. migrate_a2_palletizer_mapping.py   — adds scada_tag columns
  2. migrate_b1_emulator_seeds.py       — emulator_seed values on scada_tags
  3. migrate_b3_activate_counters.py    — activate SL60x_COUNTER tags
  4. check_unmapped_tags.py             — A7 pre-deploy check

Prerequisites
  * Postgres running and POSTGRES_URL set in backend/.env
  * MSSQL_ENABLED=false  (demo uses the embedded SCADA emulator)
  * Repo CSVs at ../milling_version_mappings.csv and ../palletizer_mapping.csv

Usage (from backend/, with venv active):

    python setup_demo_migrations.py
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


def _run(script: str, argv: list) -> int:
    from pathlib import Path
    here = Path(__file__).resolve().parent
    path = here / script
    if not path.exists():
        print(f"ERROR: missing {path}")
        return 1
    sys.argv = argv
    try:
        runpy.run_path(str(path), run_name="__main__")
    except SystemExit as exc:
        return int(exc.code or 0)
    except Exception as exc:
        print(f"{script} failed: {exc}")
        return 1
    return 0


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

    steps = [
        ("0/5  Seed empty tables (scada_tags, kpi, mappings)",
         "migrate_seed_demo_data.py", ["migrate_seed_demo_data.py"]),
        ("1/5  A2 — palletizer_mapping columns",
         "migrate_a2_palletizer_mapping.py", ["migrate_a2_palletizer_mapping.py"]),
        ("2/5  B1 — emulator seeds (--apply)",
         "migrate_b1_emulator_seeds.py", ["migrate_b1_emulator_seeds.py", "--apply"]),
        ("3/5  B3 — activate SL60x_COUNTER (--apply)",
         "migrate_b3_activate_counters.py", ["migrate_b3_activate_counters.py", "--apply"]),
        ("4/5  check_unmapped_tags.py",
         "check_unmapped_tags.py", ["check_unmapped_tags.py"]),
    ]

    for title, script, argv in steps:
        _banner(title)
        code = _run(script, argv)
        if code != 0:
            print(f"\nStopped at {script} (exit {code})")
            return code

    _banner("Demo migrations complete")
    print(
        "Next:\n"
        "  1. Confirm backend/.env has MSSQL_ENABLED=false\n"
        "  2. PYTHONIOENCODING=utf-8 python app.py\n"
        "  3. python demo_sap_server.py   (from backend/; mock SAP :6000)\n"
        "  4. cd ../Frontend && npx vite --port 5173\n"
    )
    return 0


if __name__ == "__main__":
    sys.exit(main())
