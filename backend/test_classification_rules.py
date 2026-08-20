# backend/test_classification_rules.py
"""
Tests for A1 — classification rules.

Standalone script, like the other backend/test_*.py files. Writes to
`classification_rules` and cleans up after itself, including on failure.

    PYTHONIOENCODING=utf-8 python test_classification_rules.py

What it pins down:

  * the four seeded rules reproduce today's behaviour exactly
  * the substring bug is gone — '13' inside a code no longer matches
  * a new rule routes a new prefix with no code change  (the acceptance test)
  * priority ordering, and '*' losing to an explicit match
  * the cache, and invalidation on write
  * classify_order reports an unmatched material instead of guessing
"""

import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from database import PostgresSessionLocal  # noqa: E402
from models.classification_rule import (  # noqa: E402
    RULE_MATERIAL_PREFIX,
    ClassificationRule,
)
from services.classification_service import (  # noqa: E402
    get_rules,
    invalidate_rules_cache,
    normalise_material,
    resolve_department,
    resolve_order_type,
)

passed = 0
failed = 0
TEST_PREFIXES = ("15", "13999", "9")


def check(name, condition, detail=None):
    global passed, failed
    if condition:
        passed += 1
        print(f"  PASS  {name}")
    else:
        failed += 1
        print(f"  FAIL  {name}" + (f"  - {detail!r}" if detail is not None else ""))


def add_rule(match_value, result_value, priority=100):
    with PostgresSessionLocal() as db:
        existing = (
            db.query(ClassificationRule)
              .filter(
                  ClassificationRule.rule_type == RULE_MATERIAL_PREFIX,
                  ClassificationRule.match_value == match_value,
              ).first()
        )
        if existing:
            existing.result_value = result_value
            existing.priority = priority
            existing.is_active = True
        else:
            db.add(ClassificationRule(
                rule_type=RULE_MATERIAL_PREFIX,
                match_value=match_value,
                result_value=result_value,
                priority=priority,
                is_active=True,
                description="test_classification_rules.py",
            ))
        db.commit()
    invalidate_rules_cache()


def drop_test_rules():
    with PostgresSessionLocal() as db:
        db.query(ClassificationRule).filter(
            ClassificationRule.rule_type == RULE_MATERIAL_PREFIX,
            ClassificationRule.match_value.in_(TEST_PREFIXES),
        ).delete(synchronize_session=False)
        db.commit()
    invalidate_rules_cache()


def test_seeded_rules_reproduce_today():
    print("\nThe seeded rules reproduce the hardcoded behaviour")

    # Real shapes: SAP sends 18-char zero-padded codes.
    cases = [
        ("000000000013000099", "MILLING"),
        ("000000000014000099", "PACKING"),
        ("13000001",           "MILLING"),
        ("14000001",           "PACKING"),
        ("0000000000130001",   "MILLING"),
    ]
    for material, expected in cases:
        got = resolve_order_type(material)
        check(f"{material} -> {expected}", got == expected, got)

    check("an unknown prefix returns None", resolve_order_type("000000000099000001") is None)
    check("a too-short code returns None", resolve_order_type("0000001") is None)
    check("an empty code returns None", resolve_order_type("") is None)
    check("None returns None", resolve_order_type(None) is None)


def test_substring_bug_is_gone():
    print("\nThe substring bug is gone (see plan §0.5)")

    # material_routes.py used `if '13' in material_code`. These all contain "13"
    # but are not milling materials.
    for material in ("000000000014130001", "000000000014001300", "14000013"):
        got = resolve_order_type(material)
        check(f"{material} is PACKING, not MILLING (contains '13')", got == "PACKING", got)

    # And the zero padding itself must not be matched against.
    check(
        "normalise strips the SAP padding",
        normalise_material("000000000013000099") == "13000099",
        normalise_material("000000000013000099"),
    )


def test_new_prefix_needs_no_code_change():
    print("\nA new prefix routes with no code change  (acceptance test)")

    check("15… is unmatched before the rule", resolve_order_type("000000000015000001") is None)

    add_rule("15", "MILLING", priority=10)

    check(
        "15… classifies as MILLING after inserting one row",
        resolve_order_type("000000000015000001") == "MILLING",
        resolve_order_type("000000000015000001"),
    )
    check("and 13/14 still behave", (
        resolve_order_type("000000000013000001") == "MILLING"
        and resolve_order_type("000000000014000001") == "PACKING"
    ))


def test_priority_and_specificity():
    print("\nPriority ordering")

    # A longer, more specific prefix with a lower priority number must win.
    add_rule("13999", "PACKING", priority=1)
    check(
        "a more specific rule at lower priority wins",
        resolve_order_type("000000000013999001") == "PACKING",
        resolve_order_type("000000000013999001"),
    )
    check(
        "other 13… codes are unaffected",
        resolve_order_type("000000000013000001") == "MILLING",
    )

    # '*' must be consulted last even when its priority ties.
    add_rule("*", "PACKING", priority=10)
    check(
        "'*' loses to an explicit match at the same priority",
        resolve_order_type("000000000013000001") == "MILLING",
        resolve_order_type("000000000013000001"),
    )
    check(
        "'*' still catches everything else",
        resolve_order_type("000000000077000001") == "PACKING",
        resolve_order_type("000000000077000001"),
    )
    with PostgresSessionLocal() as db:
        db.query(ClassificationRule).filter(
            ClassificationRule.rule_type == RULE_MATERIAL_PREFIX,
            ClassificationRule.match_value == "*",
        ).delete(synchronize_session=False)
        db.commit()
    invalidate_rules_cache()


def test_inactive_rules_are_skipped():
    print("\nInactive rules are skipped")
    add_rule("9", "MILLING", priority=1)
    check("active rule matches", resolve_order_type("900000001") == "MILLING")

    with PostgresSessionLocal() as db:
        row = db.query(ClassificationRule).filter(
            ClassificationRule.rule_type == RULE_MATERIAL_PREFIX,
            ClassificationRule.match_value == "9",
        ).first()
        row.is_active = False
        db.commit()
    invalidate_rules_cache()

    check("deactivated rule no longer matches", resolve_order_type("900000001") is None)


def test_cache():
    print("\nRules are cached, and invalidated on write")
    invalidate_rules_cache()
    first = get_rules(RULE_MATERIAL_PREFIX)
    check("rules load", len(first) >= 2, len(first))

    # Write behind the cache's back.
    with PostgresSessionLocal() as db:
        db.add(ClassificationRule(
            rule_type=RULE_MATERIAL_PREFIX, match_value="15", result_value="PACKING",
            priority=10, is_active=True, description="test_classification_rules.py",
        ))
        try:
            db.commit()
        except Exception:
            db.rollback()
            db.query(ClassificationRule).filter(
                ClassificationRule.rule_type == RULE_MATERIAL_PREFIX,
                ClassificationRule.match_value == "15",
            ).update({"result_value": "PACKING"}, synchronize_session=False)
            db.commit()

    check(
        "a direct write is not seen while cached",
        resolve_order_type("000000000015000001") == "MILLING",
        resolve_order_type("000000000015000001"),
    )
    invalidate_rules_cache()
    check(
        "and is seen once invalidated",
        resolve_order_type("000000000015000001") == "PACKING",
        resolve_order_type("000000000015000001"),
    )


def test_plant_department_is_deactivated():
    print("\nThe plant_department rules are deactivated (see the A1 doc)")
    check(
        "resolve_department('3130') is None",
        resolve_department("3130") is None,
        resolve_department("3130"),
    )
    check("resolve_department('9999') is None", resolve_department("9999") is None)


def test_classify_order_reports_unmatched():
    print("\nclassify_order reports an unmatched material instead of guessing")
    from routes.order_validation import classify_order
    from models.process_order_pg import ProcessOrderPG

    order = ProcessOrderPG()
    order.order_id = "TEST-A1"
    order.material = "000000000099000001"
    order.version = "BKF1"

    result = classify_order(order)
    check("order_type is None", result.get("order_type") is None, result.get("order_type"))
    check("an error is set", bool(result.get("error")))
    check(
        "the error names the material and points at the fix",
        "99000001" in (result.get("error") or "")
        and "classification" in (result.get("error") or "").lower(),
        result.get("error"),
    )


def main():
    print("A1 — classification rules")
    try:
        drop_test_rules()
        test_seeded_rules_reproduce_today()
        test_substring_bug_is_gone()
        test_new_prefix_needs_no_code_change()
        test_priority_and_specificity()
        test_inactive_rules_are_skipped()
        test_cache()
        test_plant_department_is_deactivated()
        test_classify_order_reports_unmatched()
    finally:
        drop_test_rules()
        remaining = [r["match_value"] for r in get_rules(RULE_MATERIAL_PREFIX)]
        print(f"\n  (cleaned up; material_prefix rules remaining: {remaining})")

    print(f"\n{passed} passed, {failed} failed")
    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(main())
