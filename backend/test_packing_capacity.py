# backend/test_packing_capacity.py
"""
Tests for services/packing_capacity.py — per-line bag weights and tags from the DB.

    PYTHONIOENCODING=utf-8 python test_packing_capacity.py

Also collected by pytest. The pure-logic tests need no database: they drive the
module's own row cache directly, the same seam test_scada_config.py uses, so CI
runs them. The one test that reads palletizer_mapping skips without Postgres.

WHAT THIS PINS DOWN

routes/kpi_routes.py converted bags to tons with five literals and read two tag
names that do not exist. Measured 2026-09-08:

  * palletizer_mapping.bag_weight_kg is per VERSION. PL603 has a 25 kg version;
    the literal applied 40 kg to every PL603 bag, overstating it by 60%.
  * the code read "PL606_TOT"/"PL607_TOT". The registry and the live payload call
    them SL606_TOT/SL607_TOT, so row.get() returned its 0.0 default and two whole
    packing lines contributed nothing to the capacity figure.

The result is sent to SAP as PACKING_CAPACITY_TON, so both were wrong numbers
that looked like data.
"""

import os
import sys
import time

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


def _seed(rows):
    """Put a known line set in the module cache, bypassing the database."""
    from services import packing_capacity as pc

    with pc._lock:
        pc._cache["lines"] = rows
        pc._cache["read_at"] = time.time()
    return pc


def _restore():
    from services import packing_capacity as pc

    pc.invalidate_cache()
    pc.clear_reported()


def test_tons_use_the_configured_weight():
    """Tons = bags x the line's own bag weight, not a literal."""
    print("\nTons from configured weights")
    pc = _seed([
        {"palletizer": "PL601", "scada_tag": "PL601_TOT", "bag_weight_kg": 45.0},
        {"palletizer": "PL603", "scada_tag": "PL603_TOT", "bag_weight_kg": 25.0},
    ])
    try:
        tons = pc.total_packing_tons({"PL601_TOT": 1000.0, "PL603_TOT": 1000.0})
        check("45 kg + 25 kg over 1000 bags each = 70 t", abs(tons - 70.0) < 1e-9, tons)

        # The old literal used 40 kg for PL603 regardless of the mapping.
        old = 1000.0 * 0.045 + 1000.0 * 0.040
        check("differs from the old hardcoded result", abs(tons - old) > 1e-6, (tons, old))
    finally:
        _restore()


def test_line_six_and_seven_are_not_silently_zero():
    """The regression that made two lines contribute nothing."""
    print("\nSL606/SL607 tag names")
    pc = _seed([
        {"palletizer": "PL606", "scada_tag": "SL606_TOT", "bag_weight_kg": 1.0},
        {"palletizer": "PL607", "scada_tag": "SL607_TOT", "bag_weight_kg": 10.0},
    ])
    try:
        row = {"SL606_TOT": 5000.0, "SL607_TOT": 2000.0}
        tons = pc.total_packing_tons(row)
        check("SL606+SL607 contribute (5 t + 20 t)", abs(tons - 25.0) < 1e-9, tons)
        check("contribution is not zero", tons > 0, tons)

        # What the old code did: it looked for PL606_TOT/PL607_TOT, which the
        # payload never contains, so both fell to the 0.0 default.
        old = row.get("PL606_TOT", 0.0) * 0.001 + row.get("PL607_TOT", 0.0) * 0.010
        check("the old tag names produced exactly 0", old == 0.0, old)
    finally:
        _restore()


def test_missing_tag_contributes_nothing():
    """A configured line whose counter is absent adds nothing, and does not raise."""
    print("\nMissing / unusable counters")
    pc = _seed([
        {"palletizer": "PL601", "scada_tag": "PL601_TOT", "bag_weight_kg": 45.0},
        {"palletizer": "PL602", "scada_tag": "PL602_TOT", "bag_weight_kg": 45.0},
    ])
    try:
        check("absent tag adds nothing",
              abs(pc.total_packing_tons({"PL601_TOT": 100.0}) - 4.5) < 1e-9)
        check("None value is treated as zero",
              abs(pc.total_packing_tons({"PL601_TOT": 100.0, "PL602_TOT": None}) - 4.5) < 1e-9)
        check("non-numeric value does not raise",
              abs(pc.total_packing_tons({"PL601_TOT": "oops"}) - 0.0) < 1e-9)
        check("empty row is zero, not an error",
              pc.total_packing_tons({}) == 0.0)
    finally:
        _restore()


def test_ambiguous_weight_rule():
    """Most common weight wins; ties take the smallest; the outlier stays out."""
    print("\nAmbiguous bag weights")
    from services import packing_capacity as pc

    pc.clear_reported()
    try:
        # PL607 as it really is: 5 kg x2, 10 kg x3, and the BK10 1200 kg row.
        check("mode wins over an outlier",
              pc._resolve_weight("ZZ_MODE", [5.0, 5.0, 10.0, 10.0, 10.0, 1200.0]) == 10.0)
        pc.clear_reported()
        check("the 1200 kg BK10 row is not used",
              pc._resolve_weight("ZZ_OUT", [10.0, 10.0, 1200.0]) != 1200.0)
        pc.clear_reported()
        # PL603 as it really is: one row at 25, one at 40.
        check("a tie takes the smaller (understate, never overstate)",
              pc._resolve_weight("ZZ_TIE", [25.0, 40.0]) == 25.0)
        pc.clear_reported()
        check("a single weight is used as-is",
              pc._resolve_weight("ZZ_ONE", [45.0, 45.0]) == 45.0)
        pc.clear_reported()
        check("no usable weight returns None rather than a guess",
              pc._resolve_weight("ZZ_NONE", [None, 0.0]) is None)
    finally:
        _restore()


def test_reads_the_real_mapping():
    """Against a real database, every line resolves to a tag the registry knows."""
    print("\nAgainst palletizer_mapping (skips without Postgres)")
    try:
        from database import PostgresSessionLocal
        from models.palletizer_mapping import PalletizerMapping

        with PostgresSessionLocal() as db:
            db.query(PalletizerMapping).first()
    except Exception as exc:
        print(f"  SKIP  no database: {exc}")
        return

    from services import packing_capacity as pc
    from services.scada_tag_registry import poll_keys

    pc.invalidate_cache()
    lines = pc.packing_lines(force=True)
    check("at least one packing line resolves", len(lines) >= 1, len(lines))

    known = set(poll_keys())
    for line in lines:
        check(f"{line['palletizer']} -> {line['scada_tag']} is a registry tag",
              line["scada_tag"] in known, sorted(known))
        check(f"{line['palletizer']} has a positive bag weight",
              line["bag_weight_kg"] > 0, line["bag_weight_kg"])

    tags = [l["scada_tag"] for l in lines]
    check("no line uses the non-existent PL606_TOT/PL607_TOT",
          "PL606_TOT" not in tags and "PL607_TOT" not in tags, tags)
    _restore()


def main():
    print("=" * 60)
    print("Packing capacity — bag weights and tags from the database")
    print("=" * 60)

    test_tons_use_the_configured_weight()
    test_line_six_and_seven_are_not_silently_zero()
    test_missing_tag_contributes_nothing()
    test_ambiguous_weight_rule()
    test_reads_the_real_mapping()

    print("\n" + "-" * 60)
    print(f"Result: {passed} passed, {failed} failed")
    print("-" * 60)
    return 0 if failed == 0 else 1


if __name__ == "__main__":
    sys.exit(main())
