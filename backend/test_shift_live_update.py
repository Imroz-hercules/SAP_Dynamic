# backend/test_shift_live_update.py
"""
Tests for A4 — the live shift updater reads the classifier, not its own map.

Standalone script, like the other backend/test_*.py files. Writes one temporary
order and one temporary mapping, and removes both.

    PYTHONIOENCODING=utf-8 python test_shift_live_update.py

What it pins down:

  * the hardcoded dicts and the local resolver are gone
  * for every version, the equipment and formula the new path produces match
    what the old dict produced — except BRF2, where the change is deliberate
  * a version added through the API produces shift weights, which the old dict
    could never do
  * an unresolvable version is reported, not silently skipped
  * the formula evaluator no longer returns the SUM of the streams when a
    formula fails to parse
"""

import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from database import PostgresSessionLocal  # noqa: E402
from models.milling_version_mapping import MillingVersionMapping  # noqa: E402
from models.process_order_pg import ProcessOrderPG  # noqa: E402
from services import classification_service as cs  # noqa: E402
from services import shift_live_update as slu  # noqa: E402

passed = 0
failed = 0
TEST_VERSION = "ZS01"
TEST_ORDER = "900000900"

# The dict A4 deleted, kept here so the regression can prove nothing moved.
# services/shift_live_update.py no longer holds a copy.
OLD_MILLING_PV_SPECS = {
    "LWSM": {"scales": ["WG101", "WG302", "DM101", "DM102"], "formula": "WG101-WG302+DM101+DM102"},
    "IWSM": {"scales": ["WG101", "WG302"], "formula": "WG101-WG302"},
    "SWSM": {"scales": ["WG101", "WG302"], "formula": "WG101-WG302"},
    "CWIM": {"scales": ["WG201", "WG301", "DM201", "DM202", "DM203"], "formula": "WG201-WG301+DM201+DM202+DM203"},
    "CWLM": {"scales": ["WG201", "WG301", "DM201", "DM202", "DM203"], "formula": "WG201-WG301+DM201+DM202+DM203"},
    "CWMM": {"scales": ["WG201", "WG301", "DM201", "DM202", "DM203"], "formula": "WG201-WG301+DM201+DM202+DM203"},
    "CWSM": {"scales": ["WG201", "WG301", "DM201", "DM202", "DM203"], "formula": "WG201-WG301+DM201+DM202+DM203"},
    "BKF1": {"scales": ["WG501"], "formula": "WG501"},
    "CKF1": {"scales": ["WG502"], "formula": "WG502"},
    "IWF1": {"scales": ["WG502"], "formula": "WG502"},
    "IWF2": {"scales": ["WG502"], "formula": "WG502"},
    "BRF1": {"scales": ["WG501"], "formula": "WG501"},
    "BRF2": {"scales": ["WG502"], "formula": "WG502"},
    "BRF3": {"scales": ["WG501"], "formula": "WG501"},
    "MMCF": {"scales": ["WG502"], "formula": "WG502"},
}

# BRF1 is retired: it was only ever in the dict, never in the database, so
# classify_order has always rejected it.
RETIRED = {"BRF1"}


def check(name, condition, detail=None):
    global passed, failed
    if condition:
        passed += 1
        print(f"  PASS  {name}")
    else:
        failed += 1
        print(f"  FAIL  {name}" + (f"  - {detail!r}" if detail is not None else ""))


def canon(formula):
    """Formulas differ only by parentheses between the two sources."""
    return "".join(str(formula or "").split()).replace("(", "").replace(")", "")


def mk(material, version):
    order = ProcessOrderPG()
    order.order_id = "TEST-A4"
    order.material = material
    order.version = version
    return order


def cleanup():
    with PostgresSessionLocal() as db:
        db.query(ProcessOrderPG).filter(
            ProcessOrderPG.order_id == TEST_ORDER).delete(synchronize_session=False)
        db.query(MillingVersionMapping).filter(
            MillingVersionMapping.version == TEST_VERSION).delete(synchronize_session=False)
        db.commit()
    cs.invalidate_cache()
    slu.clear_reported()


def test_hardcoded_map_is_gone():
    print("\nThe hardcoded map and the local resolver are gone")
    for name in ("MILLING_PV_SPECS", "PL_TO_SCADA", "get_equipment_for_order"):
        check(f"{name} removed", not hasattr(slu, name))
    check("classify_order is imported instead", hasattr(slu, "classify_order"))


def test_regression_against_the_old_dict():
    print("\nEvery version resolves as the old dict did, except BRF2")
    cs.invalidate_cache()

    mismatches, brf2 = [], None
    for version, spec in sorted(OLD_MILLING_PV_SPECS.items()):
        result = cs.classify_order(mk("000000000013000001", version))

        if version in RETIRED:
            check(f"{version} is retired and rejected", bool(result.get("error")),
                  result.get("error"))
            continue

        equipment = result.get("equipment") or []
        formula = result.get("formula") or ""
        same = equipment == spec["scales"] and canon(formula) == canon(spec["formula"])

        if version == "BRF2":
            brf2 = (equipment, formula, same)
            continue
        if not same:
            mismatches.append((version, spec["scales"], equipment, spec["formula"], formula))

    checked = len(OLD_MILLING_PV_SPECS) - len(RETIRED) - 1
    check(f"all {checked} other versions match the old dict exactly", not mismatches, mismatches)

    # BRF2 is the deliberate change. After migrate_fix_brf2_mapping.py the
    # database agrees with the old dict; before it, it did not.
    check("BRF2 now resolves to WG502, agreeing with the deleted dict",
          brf2 is not None and brf2[0] == ["WG502"], brf2)
    if brf2 and brf2[0] != ["WG502"]:
        print("        (run: python migrate_fix_brf2_mapping.py --apply)")


def test_brf2_byproducts():
    print("\nBRF2 now tracks three streams, like every other two-flour version")
    result = cs.classify_order(mk("000000000013000001", "BRF2"))
    byproduct = result.get("byproduct") or {}
    check("main is WG502", result.get("equipment") == ["WG502"], result.get("equipment"))
    check("byproducts are WG501 and WG503",
          (byproduct.get("scale1"), byproduct.get("scale2")) == ("WG501", "WG503"),
          byproduct)

    brf3 = cs.classify_order(mk("000000000013000001", "BRF3"))
    check("BRF3 is unchanged (main WG501, byproducts WG502 + WG503)",
          brf3.get("equipment") == ["WG501"]
          and (brf3.get("byproduct") or {}).get("scale1") == "WG502",
          brf3.get("byproduct"))


def test_a_new_version_produces_shift_weights():
    print("\nA version the old dict never had produces shift weights")
    with PostgresSessionLocal() as db:
        db.add(MillingVersionMapping(
            version=TEST_VERSION, scales=["WG501"], formula="WG501",
            scale1="WG503", description="test_shift_live_update.py",
        ))
        db.add(ProcessOrderPG(
            order_id=TEST_ORDER, material="000000000013000900", version=TEST_VERSION,
            quantity=50000, unit="KG", status="InProgress", plant="3130",
            expected_weight=50000, confirmed_qty=0, current_shift="A",
            baseline_shift_a_start={"WG501": 0.0}, weight_shift_a=0.0,
        ))
        db.commit()
    cs.invalidate_cache()

    check(f"{TEST_VERSION} was never in the old dict", TEST_VERSION not in OLD_MILLING_PV_SPECS)

    slu.update_live_shift_production()

    with PostgresSessionLocal() as db:
        order = db.query(ProcessOrderPG).filter(
            ProcessOrderPG.order_id == TEST_ORDER).first()
        weight = float(order.weight_shift_a or 0.0)
        errors_for_order = 0
        from models.error_log import ErrorLog
        errors_for_order = db.query(ErrorLog).filter(
            ErrorLog.po_number == TEST_ORDER).count()

    # The emulator's WG501 reading is whatever it is; the point is that the
    # order was processed rather than skipped, and nothing was reported.
    check("the order was not reported as unresolvable", errors_for_order == 0, errors_for_order)
    check("weight_shift_a is a number", isinstance(weight, float), weight)


def test_unresolvable_version_is_reported():
    print("\nAn unresolvable version is reported, not silently skipped")
    from models.error_log import ErrorLog

    slu.clear_reported()
    with PostgresSessionLocal() as db:
        order = db.query(ProcessOrderPG).filter(
            ProcessOrderPG.order_id == TEST_ORDER).first()
        order.version = "NOSUCH"
        db.commit()
    cs.invalidate_cache()

    slu.update_live_shift_production()

    with PostgresSessionLocal() as db:
        rows = db.query(ErrorLog).filter(ErrorLog.po_number == TEST_ORDER).all()
        messages = [r.error_message for r in rows]
        sources = {r.source for r in rows}

    check("an error_log row was written", len(rows) >= 1, len(rows))
    check("source is shift_live_update", "shift_live_update" in sources, sources)
    check("the message names the version",
          any("NOSUCH" in (m or "") for m in messages), messages[:1])
    check("the message says production is not being recorded",
          any("NOT being recorded" in (m or "") for m in messages), messages[:1])

    # And it must not write a row every cycle.
    before = len(rows)
    slu.update_live_shift_production()
    with PostgresSessionLocal() as db:
        after = db.query(ErrorLog).filter(ErrorLog.po_number == TEST_ORDER).count()
    check("the repeat is deduped, not written again", after == before, (before, after))

    with PostgresSessionLocal() as db:
        db.query(ErrorLog).filter(ErrorLog.po_number == TEST_ORDER).delete(
            synchronize_session=False)
        db.commit()


def test_formula_evaluator_is_the_shared_one():
    print("\nThe formula evaluator no longer sums the streams on failure")
    # The old local evaluator fell back to sum(deltas). For a subtraction
    # formula that turns 70 into 130 - a plausible wrong number.
    deltas = {"WG101": 100.0, "WG302": 30.0}
    check("a good formula still evaluates",
          slu.evaluate_formula_using_deltas("WG101-WG302", deltas) == 70.0,
          slu.evaluate_formula_using_deltas("WG101-WG302", deltas))
    check("a malformed formula returns 0.0, not the sum",
          slu.evaluate_formula_using_deltas("WG101-", deltas) == 0.0,
          slu.evaluate_formula_using_deltas("WG101-", deltas))
    check("a formula with Python in it returns 0.0",
          slu.evaluate_formula_using_deltas('__import__("os").getpid()', deltas) == 0.0)
    check("parenthesised formulas work",
          slu.evaluate_formula_using_deltas("(WG101-WG302)+(WG101)", deltas) == 170.0,
          slu.evaluate_formula_using_deltas("(WG101-WG302)+(WG101)", deltas))


def main():
    print("A4 — live shift updater")
    try:
        cleanup()
        test_hardcoded_map_is_gone()
        test_regression_against_the_old_dict()
        test_brf2_byproducts()
        test_a_new_version_produces_shift_weights()
        test_unresolvable_version_is_reported()
        test_formula_evaluator_is_the_shared_one()
    finally:
        cleanup()
        print("\n  (cleaned up test order and mapping)")

    print(f"\n{passed} passed, {failed} failed")
    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(main())
