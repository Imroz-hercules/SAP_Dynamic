# backend/test_baseline_guard.py
"""
Tests for A7 — the baseline guard.

Standalone script, matching the other backend/test_*.py files (this repo has no
pytest setup). Needs the PostgreSQL connection from .env because the models
import an engine, but it writes nothing and starts no server.

    PYTHONIOENCODING=utf-8 python test_baseline_guard.py

What it pins down:

  * a tag WITH a column and a NULL value reads 0.0   (baseline not captured yet)
  * a tag WITH a column and a value reads that value
  * a tag with NO column raises instead of reading 0.0
  * packing tags still resolve through scale1/2/3
  * a packing tag that is not in any scale slot raises
  * get_current_production converts the raise into a config_error result
"""

import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from services import baseline_guard  # noqa: E402
from services.baseline_guard import UnmappedTagError  # noqa: E402

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


def expect_raises(name, fn, tag_expected=None):
    global passed, failed
    try:
        value = fn()
    except UnmappedTagError as exc:
        if tag_expected and exc.tag != tag_expected:
            failed += 1
            print(f"  FAIL  {name} — raised for '{exc.tag}', expected '{tag_expected}'")
            return None
        passed += 1
        print(f"  PASS  {name}")
        return exc
    except Exception as exc:
        failed += 1
        print(f"  FAIL  {name} — raised {type(exc).__name__}: {exc}")
        return None
    failed += 1
    print(f"  FAIL  {name} — returned {value!r} instead of raising")
    return None


def make_order(**kwargs):
    """A transient ProcessOrderPG. Never added to a session, never written."""
    from models.process_order_pg import ProcessOrderPG

    order = ProcessOrderPG()
    order.order_id = kwargs.pop("order_id", "TEST-0001")
    order.material = kwargs.pop("material", "000000000013000001")
    order.version = kwargs.pop("version", "BKF1")
    for key, value in kwargs.items():
        setattr(order, key, value)
    return order


def test_column_set():
    print("\nColumn set derived from the model")
    columns = baseline_guard.baseline_columns()

    check("18 per-tag baseline columns", len(columns) == 18, f"got {len(columns)}")
    check("WG501 has a column", baseline_guard.has_baseline_column("WG501"))
    check("DM203 has a column", baseline_guard.has_baseline_column("dm203"))
    check("SL601_COUNTER has a column", baseline_guard.has_baseline_column("SL601_COUNTER"))
    check("WG999 has none", not baseline_guard.has_baseline_column("WG999"))
    check("PL601_TOT has none", not baseline_guard.has_baseline_column("PL601_TOT"))
    check(
        "the JSON snapshot columns are excluded",
        not any(c.endswith("_start") or c.endswith("flags") for c in columns),
        sorted(columns),
    )


def test_three_cases():
    print("\nThe three cases A7 has to tell apart")
    from routes.order_validation import _get_baseline_for_tag

    order = make_order(baseline_wg501=None, baseline_wg502=1234.5)

    check(
        "column present, value NULL -> 0.0",
        _get_baseline_for_tag(order, "WG501") == 0.0,
    )
    check(
        "column present, value set -> that value",
        _get_baseline_for_tag(order, "WG502") == 1234.5,
        _get_baseline_for_tag(order, "WG502"),
    )
    exc = expect_raises(
        "no column at all -> raises",
        lambda: _get_baseline_for_tag(order, "WG999"),
        tag_expected="WG999",
    )
    if exc:
        check(
            "the message names the tag and the order",
            "WG999" in exc.operator_message() and "TEST-0001" in exc.operator_message(),
            exc.operator_message(),
        )
        check(
            "the message says why it matters",
            "lifetime counter" in exc.operator_message(),
            exc.operator_message(),
        )


def test_packing_scale_slots():
    print("\nPacking tags resolve through the scale slots")
    from routes.order_validation import _get_baseline_for_tag

    order = make_order(
        version="CKL1",
        material="000000000014000001",
        scale1="PL601_TOT",
        scale1_qty=880.0,
        scale2=None,
        scale3=None,
    )

    check(
        "the assigned packing tag reads its slot",
        _get_baseline_for_tag(order, "PL601_TOT") == 880.0,
        _get_baseline_for_tag(order, "PL601_TOT"),
    )

    # This is the case A7 exists for. The palletizer for a version can be changed
    # from the Palletizer Mapping screen while an order is running: classification
    # then returns PL602_TOT while scale1 still holds PL601_TOT. There is no
    # baseline_pl602_tot column, so this used to read 0.0 and report the whole
    # lifetime pallet count as this order's output — multiplied by 32 bags each.
    exc = expect_raises(
        "a packing tag in no slot raises (mapping changed mid-order)",
        lambda: _get_baseline_for_tag(order, "PL602_TOT"),
        tag_expected="PL602_TOT",
    )
    if exc:
        check(
            "the message names the slots it checked",
            "scale1=PL601_TOT" in exc.operator_message(),
            exc.operator_message(),
        )

    expect_raises(
        "an unknown packing tag raises",
        lambda: _get_baseline_for_tag(order, "PL999_TOT"),
        tag_expected="PL999_TOT",
    )


def test_get_current_production_reports_config_error():
    print("\nget_current_production turns the raise into a result callers check")
    from routes.order_validation import get_current_production, check_order_completion

    order = make_order(current_shift="A", baseline_shift_a_start=None)
    classification = {
        "order_type": "MILLING",
        "equipment": ["WG501", "WG999"],
        "formula": "WG501-WG999",
        "byproduct": {},
        "packing_info": {},
        "error": None,
    }

    result = get_current_production(order, classification, use_shift_baselines=False)

    check("config_error is set", result.get("config_error") is True, result)
    check("the offending tag is named", result.get("unmapped_tag") == "WG999", result)
    check("total is 0.0, not a lifetime counter", result.get("total") == 0.0, result)
    check("error text is present", bool(result.get("error")))

    completion = check_order_completion(order, classification)
    check("check_order_completion propagates it", completion.get("config_error") is True, completion)
    check("and does not claim completion", completion.get("is_complete") is False, completion)


def test_packing_main_tag_is_not_a_byproduct():
    """
    Regression, found while building A2.

    PACKING stores its MAIN tag in the scale1 slot. The byproduct check read it
    with read_baseline_column, which knows nothing about scale slots, so every
    packing order reported a configuration_error that was not one - the exact
    false-alarm noise A7 exists to avoid.
    """
    print("\nA packing order's main tag is not reported as an unmapped byproduct")
    from routes.order_validation import get_current_production

    baseline_guard.clear_reported()
    order = make_order(
        version="CKL1", material="000000000014000001",
        scale1="PL601_TOT", scale1_qty=880.0,
        current_shift="A", baseline_shift_a_start=None,
    )
    classification = {
        "order_type": "PACKING", "equipment": ["PL601_TOT"], "formula": "",
        "byproduct": {}, "packing_info": {"bags_per_pallet_actual": 32.0}, "error": None,
    }
    result = get_current_production(order, classification, use_shift_baselines=False)

    check("no config_error", not result.get("config_error"), result.get("config_error"))
    check("nothing reported unmapped", result.get("byproduct_unmapped") == [],
          result.get("byproduct_unmapped"))
    check("the slot value is used as the baseline",
          result.get("byproduct_baselines", {}).get("PL601_TOT") == 880.0,
          result.get("byproduct_baselines"))

    # A genuinely unmapped MILLING byproduct must still be reported.
    milling = make_order(version="BKF1", scale1="WG999",
                         current_shift="A", baseline_shift_a_start=None)
    result = get_current_production(
        milling,
        {"order_type": "MILLING", "equipment": ["WG501"], "formula": "WG501",
         "byproduct": {}, "packing_info": {}, "error": None},
        use_shift_baselines=False,
    )
    check("a real unmapped byproduct still reports",
          result.get("byproduct_unmapped") == ["WG999"], result.get("byproduct_unmapped"))


def test_report_dedupe():
    print("\nReporting is deduped (the worker ticks once a second)")
    baseline_guard.clear_reported()
    error = UnmappedTagError("WG999", po_number="TEST-DEDUPE")

    first = baseline_guard.report_unmapped_tag(error, source="unit-test")
    second = baseline_guard.report_unmapped_tag(error, source="unit-test")
    other_source = baseline_guard.report_unmapped_tag(error, source="unit-test-2")

    check("first report goes through", first is True)
    check("the repeat is suppressed", second is False)
    check("a different source still reports", other_source is True)

    baseline_guard.clear_reported("TEST-DEDUPE")
    check(
        "clear_reported lets it report again",
        baseline_guard.report_unmapped_tag(error, source="unit-test") is True,
    )
    baseline_guard.clear_reported()


def main():
    print("A7 — baseline guard")

    test_column_set()
    test_three_cases()
    test_packing_scale_slots()
    test_get_current_production_reports_config_error()
    test_packing_main_tag_is_not_a_byproduct()
    test_report_dedupe()

    print(f"\n{passed} passed, {failed} failed")
    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(main())
