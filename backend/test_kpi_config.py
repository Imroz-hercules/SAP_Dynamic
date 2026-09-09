# backend/test_kpi_config.py
"""
Tests for Workstream B — KPI config registry (B4).

    PYTHONIOENCODING=utf-8 python test_kpi_config.py

Also collected by pytest. It previously was not: every check lived inside
main(), so the file defined no test_* function at all and the graded gate
ran none of it -- B4's only regression suite was invisible to CI (found
2026-09-08). The checks are split into test_* functions so pytest collects
them, and backend/conftest.py turns a moved `failed` counter into a real
failure. main() still calls them in the same order, so the standalone
runner's output is unchanged.
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


def _registry():
    from services import kpi_config_registry as reg
    reg.invalidate_kpi_config_cache()
    return reg


def test_ceilings():
    """Ceilings come from kpi_config, seeded at 100 to match live code (not the 150 in docs)."""
    reg = _registry()
    print("\nCeilings (seeded at 100 to match live code, not 150 docs)")
    check("mill_throughput ceiling is 100", reg.get_max_value("mill_throughput_pct") == 100.0,
          reg.get_max_value("mill_throughput_pct"))
    check("clamp applies ceiling", reg.clamp("mill_throughput_pct", 150.0) == 100.0,
          reg.clamp("mill_throughput_pct", 150.0))
    check("uncapped key passes through", reg.clamp("milling_loss_pct", 55.5) == 55.5)


def test_nameplate():
    """Nameplate reads system_settings.mill_nameplate_tph, replacing the literal 25.0."""
    reg = _registry()
    print("\nNameplate")
    np = reg.get_nameplate_tph()
    check("nameplate is a positive float", isinstance(np, float) and np > 0, np)


def test_display_maps():
    """Display-name maps come from the registry, replacing MILLING_MAP / PACKING_MAP."""
    reg = _registry()
    print("\nDisplay maps")
    milling = reg.display_to_column_map("MILLING")
    packing = reg.display_to_column_map("PACKING")
    check("milling map has Mill Throughput", "Mill Throughput (%)" in milling, milling)
    check("packing map has Daily Packing Output",
          "Daily Packing Output (bags)" in packing, packing)


def main():
    print("=" * 60)
    print("Workstream B - KPI config registry tests")
    print("=" * 60)

    test_ceilings()
    test_nameplate()
    test_display_maps()

    print("\n" + "-" * 60)
    print(f"Result: {passed} passed, {failed} failed")
    print("-" * 60)
    return 0 if failed == 0 else 1


if __name__ == "__main__":
    sys.exit(main())
