# backend/test_kpi_config.py
"""
Tests for Workstream B — KPI config registry (B4).

    PYTHONIOENCODING=utf-8 python test_kpi_config.py
"""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

passed = 0
failed = 0


def check(name, condition, detail=None):
    global passed, failed
    if condition:
        passed += 1
        print(f"  PASS  {name}")
    else:
        failed += 1
        print(f"  FAIL  {name}" + (f"  - {detail!r}" if detail is not None else ""))


def main():
    print("=" * 60)
    print("Workstream B — KPI config registry tests")
    print("=" * 60)

    from services.kpi_config_registry import (
        clamp,
        get_max_value,
        get_nameplate_tph,
        display_to_column_map,
        invalidate_kpi_config_cache,
    )

    invalidate_kpi_config_cache()

    print("\nCeilings (seeded at 100 to match live code, not 150 docs)")
    check("mill_throughput ceiling is 100", get_max_value("mill_throughput_pct") == 100.0,
          get_max_value("mill_throughput_pct"))
    check("clamp applies ceiling", clamp("mill_throughput_pct", 150.0) == 100.0,
          clamp("mill_throughput_pct", 150.0))
    check("uncapped key passes through", clamp("milling_loss_pct", 55.5) == 55.5)

    print("\nNameplate")
    np = get_nameplate_tph()
    check("nameplate is a positive float", isinstance(np, float) and np > 0, np)

    print("\nDisplay maps")
    milling = display_to_column_map("MILLING")
    packing = display_to_column_map("PACKING")
    check("milling map has Mill Throughput", "Mill Throughput (%)" in milling, milling)
    check("packing map has Daily Packing Output",
          "Daily Packing Output (bags)" in packing, packing)

    print("\n" + "-" * 60)
    print(f"Result: {passed} passed, {failed} failed")
    print("-" * 60)
    return 0 if failed == 0 else 1


if __name__ == "__main__":
    sys.exit(main())
