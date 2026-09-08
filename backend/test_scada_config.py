# backend/test_scada_config.py
"""
Tests for Workstream B — SCADA tag registry (B1 / B2).

Standalone script, like the other backend/test_*.py files.

    PYTHONIOENCODING=utf-8 python test_scada_config.py

What it pins down:

  * registry returns the seeded active tags (or bootstrap)
  * ALLOWED_SCADA_FIELDS / MILLING_FIELDS stay importable lists
  * inactive tags are excluded from allowed + poll sets
  * rollover_max is read from the registry (B2)
  * CRUD round-trip via the route helpers / DB (when Postgres is up)
  * in-place list mutation keeps imported aliases current
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


def test_contract_lists():
    print("\nFrozen scale_service lists")
    from services.scale_service import (
        MILLING_FIELDS,
        INPUT_FIELDS,
        ALLOWED_SCADA_FIELDS,
        PACKING_FIELDS,
    )

    check("MILLING_FIELDS is a list", isinstance(MILLING_FIELDS, list))
    check("INPUT_FIELDS is a list", isinstance(INPUT_FIELDS, list))
    check("ALLOWED_SCADA_FIELDS is a list", isinstance(ALLOWED_SCADA_FIELDS, list))
    check("WG501 in MILLING_FIELDS", "WG501" in MILLING_FIELDS, MILLING_FIELDS)
    check("WG101 in INPUT_FIELDS", "WG101" in INPUT_FIELDS, INPUT_FIELDS)
    check("PL601_TOT in PACKING_FIELDS", "PL601_TOT" in PACKING_FIELDS, PACKING_FIELDS)
    # The module list must agree with the registry's own active filter.
    #
    # This used to assert that SL601_COUNTER specifically was absent, which
    # only held while that tag happened to be inactive -- B3 activates it on
    # purpose, and the check then failed for a reason with nothing to do with
    # the behaviour being tested. The invariant below is the real contract and
    # does not depend on any single row's current state.
    from services.scada_tag_registry import allowed_fields

    check(
        "ALLOWED_SCADA_FIELDS matches registry active set",
        sorted(ALLOWED_SCADA_FIELDS) == sorted(allowed_fields(active_only=True)),
        sorted(set(ALLOWED_SCADA_FIELDS) ^ set(allowed_fields(active_only=True))),
    )


def test_registry_filters():
    print("\nRegistry active / poll filters")
    from services import scada_tag_registry as reg

    reg.invalidate_registry_cache()
    active = reg.allowed_fields(active_only=True)
    all_tags = [r["tag"] for r in reg.get_all_tag_rows()]
    poll = reg.poll_keys()

    check("at least 23 active tags (seed)", len(active) >= 20, len(active))
    check("counters present in full registry", "SL601_COUNTER" in all_tags, all_tags)
    check("PL602_TOT is pollable when active", "PL602_TOT" in poll, poll)

    _check_inactive_tag_is_hidden(reg)


def _check_inactive_tag_is_hidden(reg):
    """
    An inactive tag must be invisible to BOTH allowed_fields() and poll_keys().

    Asserted against a fixture row created and dropped here, not against a
    seeded tag. The previous version used SL601_COUNTER, which B3 activates
    deliberately ("close the counter gap"), so B1's test and B3's migration
    contradicted each other: applying B3 turned this suite red without any
    behaviour regressing. A test must not depend on a production row's
    mutable state.
    """
    try:
        from database import PostgresSessionLocal
        from models.scada_tag import ScadaTag

        # Importing proves the modules exist, not that a database answers. CI
        # points POSTGRES_URL at sqlite:///:memory: where scada_tags does not
        # exist, so probe with a real query the way test_crud_roundtrip does --
        # otherwise this raises OperationalError mid-test instead of skipping.
        with PostgresSessionLocal() as probe:
            probe.query(ScadaTag).first()
    except Exception as exc:
        print(f"  SKIP  inactive-tag filter -- no database: {exc}")
        return

    fixture = "ZZ_B1_INACTIVE_FIXTURE"
    try:
        with PostgresSessionLocal() as db:
            stale = db.query(ScadaTag).filter(ScadaTag.tag == fixture).first()
            if stale:
                db.delete(stale)
                db.commit()
            db.add(ScadaTag(
                tag=fixture,
                category="PACKING",
                reading_type="single",
                source_column=fixture,
                unit="BAG",
                is_pollable=True,      # pollable, so only is_active can hide it
                is_active=False,
                emulator_seed=0,
                display_name="B1 inactive fixture",
                sort_order=9999,
            ))
            db.commit()

        reg.invalidate_registry_cache()
        check("inactive tag excluded from allowed_fields()",
              fixture not in reg.allowed_fields(active_only=True))
        check("inactive tag excluded from poll_keys()",
              fixture not in reg.poll_keys())
        check("inactive tag still visible in full registry",
              fixture in [r["tag"] for r in reg.get_all_tag_rows()])
    finally:
        try:
            with PostgresSessionLocal() as db:
                row = db.query(ScadaTag).filter(ScadaTag.tag == fixture).first()
                if row:
                    db.delete(row)
                    db.commit()
            reg.invalidate_registry_cache()
        except Exception:
            pass


def test_rollover():
    print("\nRollover from registry (B2)")
    from services.scada_tag_registry import get_rollover_max

    check("PL601_TOT rollover is 100000", get_rollover_max("PL601_TOT") == 100000.0,
          get_rollover_max("PL601_TOT"))
    check("WG501 LO rollover is 1000000", get_rollover_max("WG501") == 1000000.0,
          get_rollover_max("WG501"))
    check("DM101 has no rollover", get_rollover_max("DM101") is None,
          get_rollover_max("DM101"))


def test_inplace_refresh():
    print("\nIn-place list mutation")
    from services.scale_service import MILLING_FIELDS, ALLOWED_SCADA_FIELDS
    from services import scada_tag_registry as reg

    alias_milling = MILLING_FIELDS
    alias_allowed = ALLOWED_SCADA_FIELDS
    before_id_m = id(MILLING_FIELDS)
    before_id_a = id(ALLOWED_SCADA_FIELDS)

    reg.refresh_consumer_lists()

    from services.scale_service import MILLING_FIELDS as M2, ALLOWED_SCADA_FIELDS as A2
    check("MILLING_FIELDS identity preserved", id(M2) == before_id_m)
    check("ALLOWED_SCADA_FIELDS identity preserved", id(A2) == before_id_a)
    check("imported alias still same list", alias_milling is M2)
    check("allowed alias still same list", alias_allowed is A2)
    check("WG502 still present after refresh", "WG502" in alias_milling, alias_milling)


def test_crud_roundtrip():
    print("\nCRUD against Postgres (skip if unreachable)")
    try:
        from database import PostgresSessionLocal
        from models.scada_tag import ScadaTag
        from services.scada_tag_registry import invalidate_registry_cache, refresh_consumer_lists

        with PostgresSessionLocal() as db:
            db.query(ScadaTag).first()
    except Exception as exc:
        print(f"  SKIP  CRUD — Postgres not available: {exc}")
        return

    from database import PostgresSessionLocal
    from models.scada_tag import ScadaTag
    from services.scada_tag_registry import (
        invalidate_registry_cache,
        refresh_consumer_lists,
        allowed_fields,
    )
    from services.scale_service import ALLOWED_SCADA_FIELDS

    test_tag = "ZZ_B1_TEST_TAG"
    try:
        with PostgresSessionLocal() as db:
            existing = db.query(ScadaTag).filter(ScadaTag.tag == test_tag).first()
            if existing:
                db.delete(existing)
                db.commit()

            row = ScadaTag(
                tag=test_tag,
                category="PACKING",
                reading_type="single",
                source_column=test_tag,
                rollover_max=50000,
                unit="BAG",
                is_pollable=True,
                is_active=True,
                emulator_seed=0,
                display_name="B1 test tag",
                sort_order=9999,
            )
            db.add(row)
            db.commit()
            db.refresh(row)
            tag_id = row.id

        invalidate_registry_cache()
        refresh_consumer_lists()
        check("new active tag in allowed_fields()", test_tag in allowed_fields(),
              allowed_fields())
        check("new active tag in ALLOWED_SCADA_FIELDS module list",
              test_tag in ALLOWED_SCADA_FIELDS, list(ALLOWED_SCADA_FIELDS)[-5:])

        with PostgresSessionLocal() as db:
            row = db.query(ScadaTag).filter(ScadaTag.id == tag_id).first()
            row.is_active = False
            db.commit()

        invalidate_registry_cache()
        refresh_consumer_lists()
        check("disabled tag removed from allowed_fields()",
              test_tag not in allowed_fields(), allowed_fields())
        check("disabled tag removed from module ALLOWED list",
              test_tag not in ALLOWED_SCADA_FIELDS, ALLOWED_SCADA_FIELDS)
    finally:
        try:
            with PostgresSessionLocal() as db:
                row = db.query(ScadaTag).filter(ScadaTag.tag == test_tag).first()
                if row:
                    db.delete(row)
                    db.commit()
            invalidate_registry_cache()
            refresh_consumer_lists()
        except Exception:
            pass


def test_active_filter_without_a_database():
    """
    is_active filtering, tested with NO database at all.

    Why this exists, and why it is not redundant with the checks above. The B1
    regression -- allowed_fields() ignoring is_active, so a deactivated tag keeps
    being read and keeps reaching the SAP delta -- was caught only by checks that
    need Postgres. CI has none (POSTGRES_URL=sqlite:///:memory:), so those are
    deselected, and re-running the mutation on 2026-09-08 confirmed the graded
    gate came back GREEN with the bug present. A gate that cannot catch the
    regression it was built for is decoration.

    The registry caches its rows in a module-level dict and only reloads on a
    miss, so seeding that cache injects a known row set without touching a
    database. This is pure logic and runs anywhere.
    """
    print("\nActive/pollable filtering (no database)")
    from services import scada_tag_registry as reg

    rows = [
        {"tag": "ZZ_ON", "category": "PACKING", "reading_type": "single",
         "source_column": "ZZ_ON", "rollover_max": None, "unit": "BAG",
         "is_pollable": True, "is_active": True, "emulator_seed": 0.0,
         "display_name": "active", "sort_order": 1},
        {"tag": "ZZ_OFF", "category": "PACKING", "reading_type": "single",
         "source_column": "ZZ_OFF", "rollover_max": None, "unit": "BAG",
         "is_pollable": True, "is_active": False, "emulator_seed": 0.0,
         "display_name": "deactivated", "sort_order": 2},
        {"tag": "ZZ_NOPOLL", "category": "PACKING", "reading_type": "single",
         "source_column": "ZZ_NOPOLL", "rollover_max": None, "unit": "BAG",
         "is_pollable": False, "is_active": True, "emulator_seed": 0.0,
         "display_name": "not pollable", "sort_order": 3},
    ]

    saved_rows, saved_at = reg._cache["tags"], reg._cache["read_at"]
    try:
        with reg._lock:
            reg._cache["tags"] = rows
            reg._cache["read_at"] = time.time()

        active = reg.allowed_fields(active_only=True)
        poll = reg.poll_keys()
        every = [r["tag"] for r in reg.get_all_tag_rows()]

        check("active tag is in allowed_fields()", "ZZ_ON" in active, active)
        check("INACTIVE tag is excluded from allowed_fields()",
              "ZZ_OFF" not in active, active)
        check("INACTIVE tag is excluded from poll_keys()", "ZZ_OFF" not in poll, poll)
        check("unpollable tag is excluded from poll_keys()",
              "ZZ_NOPOLL" not in poll, poll)
        check("inactive tag is still visible in the full registry",
              "ZZ_OFF" in every, every)
        check("allowed_fields(active_only=False) sees everything",
              "ZZ_OFF" in reg.allowed_fields(active_only=False),
              reg.allowed_fields(active_only=False))
    finally:
        with reg._lock:
            reg._cache["tags"], reg._cache["read_at"] = saved_rows, saved_at
        reg.invalidate_registry_cache()


def main():
    print("=" * 60)
    print("Workstream B — SCADA tag registry tests")
    print("=" * 60)
    test_contract_lists()
    test_registry_filters()
    test_active_filter_without_a_database()
    test_rollover()
    test_inplace_refresh()
    test_crud_roundtrip()
    print("\n" + "-" * 60)
    print(f"Result: {passed} passed, {failed} failed")
    print("-" * 60)
    return 0 if failed == 0 else 1


if __name__ == "__main__":
    sys.exit(main())
