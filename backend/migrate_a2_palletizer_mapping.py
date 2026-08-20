# backend/migrate_a2_palletizer_mapping.py
"""
A2 — move the packing line mapping into the database.

`CONTRACTS.md` says changes to Workstream A's own tables go in a migrate script
here, not by editing setup_sap_postgres.sql.

WHAT IT DOES

Adds three columns to `palletizer_mapping` and backfills them:

    scada_tag               the SCADA tag for this line, replacing the hardcoded
                            PL_TO_SCADA map in order_validation.py
    bags_per_pallet_actual  = bag_size_kg   (see below)
    bag_weight_kg           = kg_per_pallet (see below)

WHY THE TWO NEW NUMBER COLUMNS

The existing names are transposed. `_convert_packing_delta_to_bags` uses
`bag_size_kg` as the **bags-per-pallet multiplier**, and the data agrees: CKL1
carries `bag_size_kg = 32` with `kg_per_pallet = 45` — that is 32 bags of 45 kg,
not a 32 kg bag. Meanwhile the column actually called `bags_per_pallet` sits
unused at 1 for every row but one.

The old columns are **kept and still written**, because `PalletizerMapping.tsx`
and the `PalletizerMapping` interface in `lib/api.ts` both require all three and
validate them `> 0`. A6 switches the screen to the new names; a later cleanup
drops the old ones. Renaming in place now would break the running UI.

The backfill is a faithful transposition, so every existing row keeps exactly
the conversion factor it has today. Nothing about production maths changes here.

BK10

Reported, not corrected. See the notes it prints.

    PYTHONIOENCODING=utf-8 python migrate_a2_palletizer_mapping.py

Idempotent. Safe to run more than once. Read-only for the old columns.
"""

import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

# The map being retired from routes/order_validation.py. Kept here so the
# backfill has a source; the application no longer holds one.
PL_TO_SCADA_SEED = {
    "PL601": "PL601_TOT",
    "PL602": "PL602_TOT",
    "PL603": "PL603_TOT",
    "PL606": "SL606_TOT",
    "PL607": "SL607_TOT",
}

ADD_COLUMNS = """
ALTER TABLE palletizer_mapping ADD COLUMN IF NOT EXISTS scada_tag VARCHAR(50);
ALTER TABLE palletizer_mapping ADD COLUMN IF NOT EXISTS bags_per_pallet_actual DOUBLE PRECISION;
ALTER TABLE palletizer_mapping ADD COLUMN IF NOT EXISTS bag_weight_kg DOUBLE PRECISION;
COMMENT ON COLUMN palletizer_mapping.scada_tag IS
  'SCADA counter tag for this packing line. Replaced the hardcoded PL_TO_SCADA map (A2).';
COMMENT ON COLUMN palletizer_mapping.bags_per_pallet_actual IS
  'Bags per pallet - the delta multiplier. Correctly-named replacement for bag_size_kg (A2).';
COMMENT ON COLUMN palletizer_mapping.bag_weight_kg IS
  'Weight of one bag in kg. Correctly-named replacement for kg_per_pallet (A2).';
"""


def main():
    from sqlalchemy import text

    from database import postgres_engine

    print("A2 — palletizer_mapping\n")

    with postgres_engine.begin() as conn:
        for statement in [s.strip() for s in ADD_COLUMNS.split(";") if s.strip()]:
            conn.execute(text(statement))
        print("  columns present: scada_tag, bags_per_pallet_actual, bag_weight_kg")

        rows = conn.execute(text("""
            SELECT id, version, palletizer, bag_size_kg, bags_per_pallet, kg_per_pallet,
                   scada_tag, bags_per_pallet_actual, bag_weight_kg
            FROM palletizer_mapping ORDER BY version
        """)).mappings().all()

        unmapped, backfilled = [], 0
        for row in rows:
            tag = PL_TO_SCADA_SEED.get(row["palletizer"])
            if tag is None:
                unmapped.append((row["version"], row["palletizer"]))

            needs = (
                row["scada_tag"] is None
                or row["bags_per_pallet_actual"] is None
                or row["bag_weight_kg"] is None
            )
            if not needs:
                continue

            conn.execute(text("""
                UPDATE palletizer_mapping
                   SET scada_tag              = COALESCE(scada_tag, :tag),
                       bags_per_pallet_actual = COALESCE(bags_per_pallet_actual, bag_size_kg),
                       bag_weight_kg          = COALESCE(bag_weight_kg, kg_per_pallet)
                 WHERE id = :id
            """), {"tag": tag, "id": row["id"]})
            backfilled += 1

        print(f"  backfilled {backfilled} of {len(rows)} row(s)"
              f"{' (already done)' if backfilled == 0 else ''}")

    # ---------------------------------------------------------------- report
    with postgres_engine.connect() as conn:
        rows = conn.execute(text("""
            SELECT version, palletizer, scada_tag, bags_per_pallet_actual, bag_weight_kg
            FROM palletizer_mapping ORDER BY palletizer, version
        """)).mappings().all()

    print(f"\n  {'version':8} {'line':7} {'scada_tag':11} {'bags/pallet':>11} {'bag kg':>8}   pallet kg")
    for r in rows:
        bpp = r["bags_per_pallet_actual"] or 0
        bw = r["bag_weight_kg"] or 0
        print(f"  {r['version']:8} {r['palletizer']:7} {str(r['scada_tag']):11} "
              f"{bpp:>11.0f} {bw:>8.0f}   {bpp * bw:>9,.0f}")

    problems = 0

    if unmapped:
        problems += len(unmapped)
        print("\n  ⚠️  palletizers with no SCADA tag — orders on these versions will not track:")
        for version, palletizer in unmapped:
            print(f"        {version}: '{palletizer}' is not one of "
                  f"{', '.join(sorted(PL_TO_SCADA_SEED))}")

    # ------------------------------------------------------------------ BK10
    siblings = {r["version"]: r for r in rows if r["palletizer"] == "PL607"}
    bk10 = siblings.get("BK10")
    if bk10:
        peers = [v for v in ("BW10", "IW10", "CK10") if v in siblings]
        peer_bpp = {siblings[v]["bags_per_pallet_actual"] for v in peers}
        if peer_bpp and bk10["bags_per_pallet_actual"] not in peer_bpp:
            problems += 1
            print("\n  ⚠️  BK10 does not match its siblings on the same line.")
            print(f"        BK10 : {bk10['bags_per_pallet_actual']:.0f} bags x "
                  f"{bk10['bag_weight_kg']:.0f} kg = "
                  f"{bk10['bags_per_pallet_actual'] * bk10['bag_weight_kg']:,.0f} kg/pallet")
            for v in peers:
                s = siblings[v]
                print(f"        {v} : {s['bags_per_pallet_actual']:.0f} bags x "
                      f"{s['bag_weight_kg']:.0f} kg = "
                      f"{s['bags_per_pallet_actual'] * s['bag_weight_kg']:,.0f} kg/pallet")
            print("        A 1,200 kg bag is not physical, and BK10 is a 10 KG version by name,")
            print("        so the row's values look rotated. NOT corrected here — changing it")
            print("        changes what BK10 orders confirm to SAP. Confirm against a real BK10")
            print("        order first, then:")
            print("")
            print("          UPDATE palletizer_mapping")
            print("             SET bags_per_pallet_actual = 110, bag_weight_kg = 10,")
            print("                 bag_size_kg = 110, kg_per_pallet = 10")
            print("           WHERE version = 'BK10';")

    print(f"\n  {'no issues' if problems == 0 else f'{problems} thing(s) to look at'}.")
    print("  Backfill is a faithful transposition — every row keeps today's conversion factor.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
