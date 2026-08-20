# backend/test_palletizer_mapping.py
"""
Tests for A2 — packing line mapping in the database.

Standalone script, like the other backend/test_*.py files. Writes a temporary
mapping row and removes it again, including on failure.

    PYTHONIOENCODING=utf-8 python test_palletizer_mapping.py

What it pins down:

  * the hardcoded PL_TO_SCADA map and its three helpers are gone
  * every existing row resolves the same SCADA tag and the same conversion
    factor it did before A2  (the plan's acceptance test)
  * a new line with a new SCADA tag classifies, with no code change
  * a row with no scada_tag is rejected at classification, not left to surface
    later as "No main equipment mapped"
  * a missing multiplier converts 1:1 instead of inventing 32
"""

import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from database import PostgresSessionLocal  # noqa: E402
from models.palletizer_mapping import PalletizerMapping  # noqa: E402
from models.process_order_pg import ProcessOrderPG  # noqa: E402
from routes.order_validation import (  # noqa: E402
    _convert_packing_delta_to_bags,
    classify_order,
)

passed = 0
failed = 0
TEST_VERSIONS = ("ZZ99", "ZZ98")

# What the map used to say. The point of A2 is that the application no longer
# holds this; the test keeps a copy so it can prove nothing moved.
LEGACY_PL_TO_SCADA = {
    "PL601": "PL601_TOT",
    "PL602": "PL602_TOT",
    "PL603": "PL603_TOT",
    "PL606": "SL606_TOT",
    "PL607": "SL607_TOT",
}


def check(name, condition, detail=None):
    global passed, failed
    if condition:
        passed += 1
        print(f"  PASS  {name}")
    else:
        failed += 1
        print(f"  FAIL  {name}" + (f"  - {detail!r}" if detail is not None else ""))


def drop_test_rows():
    with PostgresSessionLocal() as db:
        db.query(PalletizerMapping).filter(
            PalletizerMapping.version.in_(TEST_VERSIONS)
        ).delete(synchronize_session=False)
        db.commit()


def mk_order(version, material="000000000014000001"):
    order = ProcessOrderPG()
    order.order_id = "TEST-A2"
    order.material = material
    order.version = version
    return order


def test_hardcoded_map_is_gone():
    print("\nThe hardcoded map and its helpers are gone")
    import routes.order_validation as ov

    for name in ("PL_TO_SCADA", "_translate_pl_to_scada", "_is_pl_palletizer",
                 "_get_bags_per_pallet_from_palletizer_type"):
        check(f"{name} removed", not hasattr(ov, name))


def test_every_row_is_unchanged():
    print("\nEvery existing row keeps its tag and conversion factor")
    with PostgresSessionLocal() as db:
        rows = db.query(PalletizerMapping).filter(
            PalletizerMapping.version.notin_(TEST_VERSIONS)
        ).order_by(PalletizerMapping.version).all()

        check("there are rows to check", len(rows) > 0, len(rows))

        tag_mismatch, factor_mismatch = [], []
        for row in rows:
            expected_tag = LEGACY_PL_TO_SCADA.get(row.palletizer)
            if row.scada_tag != expected_tag:
                tag_mismatch.append((row.version, expected_tag, row.scada_tag))

            # What the pre-A2 code computed: bag_size_kg if > 1, else
            # bags_per_pallet if > 1, else the hardcoded palletizer standard.
            legacy = float(row.bag_size_kg or 0)
            if legacy <= 1:
                legacy = float(row.bags_per_pallet or 0)
            if legacy <= 1:
                legacy = 32.0 if row.palletizer in ("PL601", "PL602", "PL603") else 1.0

            now = _convert_packing_delta_to_bags(
                row.scada_tag or "", 1.0,
                {"bags_per_pallet_actual": row.multiplier()},
            )
            if abs(now - legacy) > 1e-9:
                factor_mismatch.append((row.version, legacy, now))

        check(f"all {len(rows)} SCADA tags match the old map", not tag_mismatch, tag_mismatch)
        check(f"all {len(rows)} conversion factors unchanged", not factor_mismatch, factor_mismatch)


def test_multiplier_precedence():
    print("\nmultiplier() prefers the correctly-named column")
    row = PalletizerMapping(version="X", palletizer="PL601",
                            bags_per_pallet_actual=48, bag_size_kg=32,
                            bags_per_pallet=1, kg_per_pallet=45)
    check("new column wins", row.multiplier() == 48.0, row.multiplier())

    legacy_only = PalletizerMapping(version="X", palletizer="PL601",
                                    bags_per_pallet_actual=None, bag_size_kg=32,
                                    bags_per_pallet=1, kg_per_pallet=45)
    check("falls back to the legacy column", legacy_only.multiplier() == 32.0,
          legacy_only.multiplier())

    neither = PalletizerMapping(version="X", palletizer="PL601",
                                bags_per_pallet_actual=None, bag_size_kg=0,
                                bags_per_pallet=0, kg_per_pallet=45)
    check("neither set -> 1.0, not an invented 32", neither.multiplier() == 1.0,
          neither.multiplier())


def test_no_invented_multiplier():
    print("\nA missing multiplier converts 1:1 instead of inventing 32")
    # Pre-A2 this returned 100 * 32 = 3200 for any PL60x tag.
    result = _convert_packing_delta_to_bags("PL601_TOT", 100.0, {})
    check("delta passes through unchanged", result == 100.0, result)


def test_new_line_needs_no_code_change():
    print("\nA new line with a new SCADA tag classifies  (acceptance test)")
    with PostgresSessionLocal() as db:
        db.add(PalletizerMapping(
            version="ZZ99", palletizer="PL609", scada_tag="PL609_TOT",
            bags_per_pallet_actual=64, bag_weight_kg=25,
            bag_size_kg=64, bags_per_pallet=1, kg_per_pallet=25,
            description="test_palletizer_mapping.py",
        ))
        db.commit()

    result = classify_order(mk_order("ZZ99"))
    check("no classification error", not result.get("error"), result.get("error"))
    check("order_type is PACKING", result.get("order_type") == "PACKING")
    check("equipment is the new tag", result.get("equipment") == ["PL609_TOT"],
          result.get("equipment"))

    info = result.get("packing_info") or {}
    check("packing_line is the new line", info.get("packing_line") == "PL609", info.get("packing_line"))
    check("scada_tag is published", info.get("scada_tag") == "PL609_TOT")
    check("multiplier is the row's", info.get("bags_per_pallet_actual") == 64.0,
          info.get("bags_per_pallet_actual"))
    check("bag weight is the row's", info.get("bag_weight_kg") == 25.0)
    check("bag_size (A1) follows bag_weight_kg", info.get("bag_size") == "25", info.get("bag_size"))

    bags = _convert_packing_delta_to_bags("PL609_TOT", 3.0, info)
    check("3 pallets convert to 192 bags", bags == 192.0, bags)


def test_missing_scada_tag_is_rejected():
    print("\nA line with no SCADA tag is rejected at classification")
    with PostgresSessionLocal() as db:
        db.add(PalletizerMapping(
            version="ZZ98", palletizer="PL610", scada_tag=None,
            bags_per_pallet_actual=32, bag_weight_kg=45,
            bag_size_kg=32, bags_per_pallet=1, kg_per_pallet=45,
            description="test_palletizer_mapping.py",
        ))
        db.commit()

    result = classify_order(mk_order("ZZ98"))
    check("an error is set", bool(result.get("error")))
    check("equipment stays empty", not result.get("equipment"), result.get("equipment"))
    check(
        "the error names the version and the line",
        "ZZ98" in (result.get("error") or "") and "PL610" in (result.get("error") or ""),
        result.get("error"),
    )


def main():
    print("A2 — packing line mapping")
    try:
        drop_test_rows()
        test_hardcoded_map_is_gone()
        test_every_row_is_unchanged()
        test_multiplier_precedence()
        test_no_invented_multiplier()
        test_new_line_needs_no_code_change()
        test_missing_scada_tag_is_rejected()
    finally:
        drop_test_rows()
        print("\n  (cleaned up test mappings)")

    print(f"\n{passed} passed, {failed} failed")
    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(main())
