# backend/migrate_fix_brf2_mapping.py
"""
A4 prerequisite — correct the BRF2 row in `milling_version_mappings`.

    PYTHONIOENCODING=utf-8 python migrate_fix_brf2_mapping.py            # dry run
    PYTHONIOENCODING=utf-8 python migrate_fix_brf2_mapping.py --apply
    PYTHONIOENCODING=utf-8 python migrate_fix_brf2_mapping.py --revert

Dry run by default, on purpose. This changes which physical scale BRF2 orders
confirm to SAP. **Confirm with someone who knows the mill before applying it in
production**, and ask how long the row has been wrong — past BRF2 confirmations
may need correcting.

--------------------------------------------------------------------------
WHY
--------------------------------------------------------------------------
Two implementations disagree about BRF2, and only about BRF2:

    services/shift_live_update.py   BRF2 -> WG502     (writes weight_shift_*)
    milling_version_mappings row    BRF2 -> WG501     (drives confirmed_qty)

Of the 15 versions the two share, 13 match exactly. The other exception is
BRF1, which exists only in the hardcoded dict and is retired.

Two independent checks against real data single out the database row as the
wrong one.

1. STREAM IDENTITY.  Book1.xlsx (10,000 rows of ASMArchive_DB5) has
   WG501_Product = F80 in every row, while WG502_Product is F70 or IWW,
   tracking WG202_Product (the mill recipe). So a recipe written "X + Y" puts
   X on WG501 and Y on WG502 - confirmed across two different recipes in real
   data.

   The stream names come from auto_validator.py:75-81, which annotates
   BRF2 as BAKERY + BRAWNY + BRAN and BRF3 as BRAWNY + CAKE + BRAN. Together
   those fix the product codes:

       F80 = Bakery    F70 = Cake    F95 = Brawny    IWW = IWW

   Every version confirms off the stream carrying its own product:

       version  recipe    WG501    WG502    its product  expects  db says
       BKF1     F80       Bakery   -        Bakery       WG501    WG501  ok
       CKF1     F80+F70   Bakery   Cake     Cake         WG502    WG502  ok
       IWF1     F80+IWW   Bakery   IWW      IWW          WG502    WG502  ok
       IWF2     F70+IWW   Cake     IWW      IWW          WG502    WG502  ok
       BRF3     F95+F70   Brawny   Cake     Brawny       WG501    WG501  ok
       MMCF     F80+F70   Bakery   Cake     Cake         WG502    WG502  ok
       BRF2     F80+F95   Bakery   Brawny   Brawny       WG502    WG501  WRONG

2. BYPRODUCT COVERAGE.  Every two-flour version tracks three streams: one main
   plus two byproducts. BRF2 tracks only two - scales=["WG501"], scale1=WG503 -
   leaving WG502 unaccounted for. It is the only under-covered row.

The deprecated hardcoded map in order_validation.py, and shift_live_update.py,
both have BRF2 as main WG502 with byproducts WG501 + WG503, which passes both
checks.

(The same edit that broke BRF2 appears to have *fixed* BRF3 - the old map had
BRF3 with main WG501 and byproduct1 also WG501, a duplicate. So the table was
being actively corrected and BRF2 looks like collateral damage from that pass.)

--------------------------------------------------------------------------
IMPACT
--------------------------------------------------------------------------
Order validation reads the database, so BRF2 orders have been confirming the
**Bakery** stream's weight as if it were Brawny production.

A4 makes shift_live_update read the database too. Applied in the wrong order,
A4 would propagate the wrong value to the one implementation that currently has
it right - which is why this script exists and why A4 lists it as a
prerequisite.
"""

import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

VERSION = "BRF2"

CORRECTED = {
    "scales": '["WG502"]',
    "formula": "WG502",
    "scale1": "WG501",
    "scale2": "WG503",
    "scale3": None,
}

# What the row holds today, per milling_version_mappings.csv. Used by --revert
# and to recognise an already-applied migration.
ORIGINAL = {
    "scales": '["WG501"]',
    "formula": "WG501",
    "scale1": "WG503",
    "scale2": None,
    "scale3": None,
}


def show(label, row):
    print(f"    {label:9} scales={row['scales']:<12} formula={str(row['formula']):<8} "
          f"scale1={str(row['scale1']):<7} scale2={str(row['scale2']):<7}")


def main(apply=False, revert=False):
    import json

    from sqlalchemy import text

    from database import postgres_engine

    target = ORIGINAL if revert else CORRECTED
    action = "revert" if revert else "correct"

    with postgres_engine.connect() as conn:
        row = conn.execute(text("""
            SELECT id, version, scales, formula, scale1, scale2, scale3
            FROM milling_version_mappings WHERE version = :v
        """), {"v": VERSION}).mappings().first()

    if not row:
        print(f"  No {VERSION} row in milling_version_mappings — nothing to do.")
        print("  (If this database has not been seeded, that is expected.)")
        return 0

    current = {
        "scales": json.dumps(row["scales"]) if not isinstance(row["scales"], str) else row["scales"],
        "formula": row["formula"],
        "scale1": row["scale1"],
        "scale2": row["scale2"],
        "scale3": row["scale3"],
    }
    # Normalise whitespace so '["WG501"]' and '["WG501"]' compare equal.
    current["scales"] = json.dumps(json.loads(current["scales"]))

    print(f"  BRF2 today:")
    show("current", current)
    print(f"  After {action}:")
    show("target", target)

    same = all(str(current[k]) == str(target[k]) for k in target)
    if same:
        print(f"\n  Already {'reverted' if revert else 'corrected'} — nothing to do.")
        return 0

    if not apply:
        print("\n  DRY RUN — nothing written.")
        print("  This changes which physical scale BRF2 orders confirm to SAP.")
        print("  Confirm with the mill first, then re-run with --apply.")
        print("\n  Equivalent SQL:\n")
        print("    UPDATE milling_version_mappings")
        print(f"       SET scales   = '{target['scales']}',")
        print(f"           formula  = '{target['formula']}',")
        print(f"           scale1   = '{target['scale1']}',")
        print(f"           scale2   = {'NULL' if target['scale2'] is None else chr(39)+target['scale2']+chr(39)},")
        print(f"           scale3   = NULL")
        print(f"     WHERE version  = '{VERSION}';")
        return 0

    with postgres_engine.begin() as conn:
        conn.execute(text("""
            UPDATE milling_version_mappings
               SET scales = CAST(:scales AS json), formula = :formula,
                   scale1 = :scale1, scale2 = :scale2, scale3 = :scale3
             WHERE version = :v
        """), {**target, "v": VERSION})

    print(f"\n  APPLIED. BRF2 now confirms off {target['formula']}.")
    if not revert:
        print("  Drop the classification cache, or restart the app, so running")
        print("  orders pick it up: the mapping CRUD invalidates automatically,")
        print("  but a direct database edit does not.")
    return 0


if __name__ == "__main__":
    apply_flag = "--apply" in sys.argv
    revert_flag = "--revert" in sys.argv
    if apply_flag and revert_flag:
        print("Pass --apply or --revert, not both.")
        sys.exit(2)
    print(f"BRF2 mapping — {'revert' if revert_flag else 'correction'}\n")
    sys.exit(main(apply=apply_flag or revert_flag, revert=revert_flag))
