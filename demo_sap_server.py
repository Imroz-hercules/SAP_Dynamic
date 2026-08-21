"""
Shim — demo SAP mock lives in backend/demo_sap_server.py.

Prefer:
  cd backend
  python demo_sap_server.py
"""
from pathlib import Path
import runpy
import sys

_target = Path(__file__).resolve().parent / "backend" / "demo_sap_server.py"
if not _target.exists():
    print(f"Missing {_target}")
    sys.exit(1)
runpy.run_path(str(_target), run_name="__main__")
