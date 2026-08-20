# backend/test_classification_cache.py
"""
Tests for A3 — one classifier, with a cache.

Standalone script, like the other backend/test_*.py files. Read-only against
the mapping tables except for one temporary row it removes again.

    PYTHONIOENCODING=utf-8 python test_classification_cache.py

What it pins down:

  * the frozen import path still works and resolves to the moved function
  * classification is unchanged for every real version, MILLING and PACKING
  * repeated calls hit the cache instead of the database
  * the cache key is (order_type, version) and nothing else
  * a mapping edit is visible immediately, because the CRUD invalidates
  * callers cannot corrupt each other by mutating the returned dict
  * update_order_scales accepts a classification instead of re-deriving one
"""

import os
import sys
import time

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from database import PostgresSessionLocal  # noqa: E402
from models.milling_version_mapping import MillingVersionMapping  # noqa: E402
from models.palletizer_mapping import PalletizerMapping  # noqa: E402
from models.process_order_pg import ProcessOrderPG  # noqa: E402
from services import classification_service as cs  # noqa: E402

passed = 0
failed = 0
TEST_VERSION = "ZC01"


def check(name, condition, detail=None):
    global passed, failed
    if condition:
        passed += 1
        print(f"  PASS  {name}")
    else:
        failed += 1
        print(f"  FAIL  {name}" + (f"  - {detail!r}" if detail is not None else ""))


def mk(material, version):
    order = ProcessOrderPG()
    order.order_id = "TEST-A3"
    order.material = material
    order.version = version
    return order


def drop_test_rows():
    with PostgresSessionLocal() as db:
        db.query(PalletizerMapping).filter(
            PalletizerMapping.version == TEST_VERSION
        ).delete(synchronize_session=False)
        db.commit()
    cs.invalidate_cache()


def test_frozen_import_path():
    print("\nThe import path CONTRACTS.md freezes still works")
    from routes.order_validation import classify_order as via_routes

    check("importable from routes.order_validation", callable(via_routes))
    check("same object as the service's", via_routes is cs.classify_order)
    check("implementation lives in the service",
          via_routes.__module__ == "services.classification_service",
          via_routes.__module__)


def test_every_real_version_classifies():
    print("\nEvery real version classifies, MILLING and PACKING")
    cs.invalidate_cache()
    with PostgresSessionLocal() as db:
        milling = db.query(MillingVersionMapping).all()
        packing = db.query(PalletizerMapping).all()

        bad = []
        for m in milling:
            r = cs.classify_order(mk("000000000013000001", m.version))
            if r.get("error") or r.get("order_type") != "MILLING" or not r.get("equipment"):
                bad.append((m.version, r.get("error")))
        check(f"all {len(milling)} milling versions resolve", not bad, bad)

        bad = []
        for p in packing:
            r = cs.classify_order(mk("000000000014000001", p.version))
            if r.get("error") or r.get("order_type") != "PACKING" or not r.get("equipment"):
                bad.append((p.version, r.get("error")))
            elif r["equipment"] != [p.scada_tag]:
                bad.append((p.version, f"equipment {r['equipment']} != [{p.scada_tag}]"))
        check(f"all {len(packing)} packing versions resolve to their scada_tag", not bad, bad)


def test_repeat_calls_hit_the_cache():
    print("\nRepeated calls are served from the cache")
    cs.invalidate_cache()
    cs.reset_cache_stats()

    order = mk("000000000014000001", "CKL1")
    first = cs.classify_order(order)
    stats_after_first = cs.cache_stats()

    for _ in range(50):
        cs.classify_order(order)
    stats = cs.cache_stats()

    check("the first call is a miss", stats_after_first["misses"] == 1, stats_after_first)
    check("the next 50 are hits", stats["hits"] == 50, stats)
    check("only one miss in total", stats["misses"] == 1, stats)
    check("the answer is unchanged", cs.classify_order(order)["equipment"] == first["equipment"])


def test_cache_key_is_order_type_and_version():
    print("\nThe cache key is (order_type, version) and nothing else")
    cs.invalidate_cache()
    cs.reset_cache_stats()

    # Same version, different material codes with the same order_type: one entry.
    cs.classify_order(mk("000000000014000001", "CKL1"))
    cs.classify_order(mk("000000000014999999", "CKL1"))
    check("a different material on the same version reuses the entry",
          cs.cache_stats()["hits"] == 1, cs.cache_stats())

    # Different version: a separate entry.
    cs.classify_order(mk("000000000014000001", "BKL1"))
    check("a different version is a separate entry",
          cs.cache_stats()["entries"] == 2, cs.cache_stats())

    # Different order_type on the same version string: separate again.
    cs.classify_order(mk("000000000013000001", "BKF1"))
    check("a different order_type is a separate entry",
          cs.cache_stats()["entries"] == 3, cs.cache_stats())


def test_returned_dict_is_a_copy():
    print("\nCallers cannot corrupt each other through the returned dict")
    cs.invalidate_cache()

    first = cs.classify_order(mk("000000000014000001", "CKL1"))
    first["equipment"].append("SABOTAGE")
    first["packing_info"]["bags_per_pallet_actual"] = 999999
    first["order_type"] = "NONSENSE"

    second = cs.classify_order(mk("000000000014000001", "CKL1"))
    check("equipment is intact", second["equipment"] == ["PL601_TOT"], second["equipment"])
    check("packing_info is intact",
          second["packing_info"]["bags_per_pallet_actual"] == 32.0,
          second["packing_info"]["bags_per_pallet_actual"])
    check("order_type is intact", second["order_type"] == "PACKING", second["order_type"])


def test_invalidate_makes_an_edit_visible():
    print("\nA mapping edit is visible immediately, not after the TTL")
    with PostgresSessionLocal() as db:
        db.add(PalletizerMapping(
            version=TEST_VERSION, palletizer="PL601", scada_tag="PL601_TOT",
            bags_per_pallet_actual=32, bag_weight_kg=45,
            bag_size_kg=32, bags_per_pallet=1, kg_per_pallet=45,
            description="test_classification_cache.py",
        ))
        db.commit()
    cs.invalidate_cache()

    before = cs.classify_order(mk("000000000014000001", TEST_VERSION))
    check("the new version resolves", before["equipment"] == ["PL601_TOT"], before["equipment"])

    # Cache an unrelated version too, so the targeted invalidation below has
    # something it must NOT drop.
    cs.classify_order(mk("000000000014000001", "CKL1"))

    # Change the line behind the cache's back.
    with PostgresSessionLocal() as db:
        row = db.query(PalletizerMapping).filter(
            PalletizerMapping.version == TEST_VERSION).first()
        row.palletizer = "PL603"
        row.scada_tag = "PL603_TOT"
        db.commit()

    stale = cs.classify_order(mk("000000000014000001", TEST_VERSION))
    check("still cached until invalidated", stale["equipment"] == ["PL601_TOT"], stale["equipment"])

    cs.invalidate_cache(TEST_VERSION)
    fresh = cs.classify_order(mk("000000000014000001", TEST_VERSION))
    check("visible immediately after invalidate_cache(version)",
          fresh["equipment"] == ["PL603_TOT"], fresh["equipment"])

    # Targeted invalidation must not have dropped anything else.
    cs.reset_cache_stats()
    cs.classify_order(mk("000000000014000001", "CKL1"))
    check("other versions stayed cached", cs.cache_stats()["hits"] == 1, cs.cache_stats())


def test_ttl_expires():
    print("\nThe TTL expires (checked by moving the clock, not by waiting)")
    cs.invalidate_cache()
    cs.reset_cache_stats()
    order = mk("000000000014000001", "CKL1")
    cs.classify_order(order)
    cs.classify_order(order)
    check("second call was a hit", cs.cache_stats()["hits"] == 1)

    # Age the entry past the TTL.
    with cs._classify_lock:
        for key, (stamp, value) in list(cs._classify_cache.items()):
            cs._classify_cache[key] = (stamp - cs.CLASSIFICATION_TTL_SECONDS - 1, value)

    cs.classify_order(order)
    check("an aged entry is re-read", cs.cache_stats()["misses"] == 2, cs.cache_stats())


def test_update_order_scales_takes_a_classification():
    print("\nupdate_order_scales uses the classification it is given")
    import inspect

    from routes.order_validation import update_order_scales

    sig = inspect.signature(update_order_scales)
    check("it accepts a classification argument", "classification" in sig.parameters,
          list(sig.parameters))
    check("and it is optional",
          sig.parameters["classification"].default is None)

    # Passing one must not classify again.
    cs.invalidate_cache()
    cs.reset_cache_stats()
    order = mk("000000000014000001", "CKL1")
    order.order_type = "PACKING"
    order.scale1 = "PL601_TOT"
    classification = cs.classify_order(order)          # 1 miss
    cs.reset_cache_stats()

    update_order_scales(order, {"PL601_TOT": {"delta": 2.0}}, classification)
    stats = cs.cache_stats()
    check("no extra classify when one is passed",
          stats["hits"] == 0 and stats["misses"] == 0, stats)

    # Omitting it still works, by classifying.
    update_order_scales(order, {"PL601_TOT": {"delta": 2.0}})
    stats = cs.cache_stats()
    check("it still classifies when not given one",
          stats["hits"] + stats["misses"] == 1, stats)


def main():
    print("A3 — one classifier, with a cache")
    try:
        drop_test_rows()
        test_frozen_import_path()
        test_every_real_version_classifies()
        test_repeat_calls_hit_the_cache()
        test_cache_key_is_order_type_and_version()
        test_returned_dict_is_a_copy()
        test_invalidate_makes_an_edit_visible()
        test_ttl_expires()
        test_update_order_scales_takes_a_classification()
    finally:
        drop_test_rows()
        print("\n  (cleaned up; cache cleared)")

    print(f"\n{passed} passed, {failed} failed")
    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(main())
