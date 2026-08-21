# backend/migrate_b1_emulator_seeds.py
"""
B1 — populate scada_tags.emulator_seed from the historical
REALISTIC_STARTING_VALUES map (LO word for hi_lo tags).

Dry-run by default. Pass --apply to write.

    python migrate_b1_emulator_seeds.py
    python migrate_b1_emulator_seeds.py --apply
"""
from __future__ import annotations

import argparse
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

# LO (or single) seed values matching embedded_emulator.REALISTIC_STARTING_VALUES
SEEDS = {
    "WG101": 708000.0,
    "WG201": 319800.0,
    "WG202": 921600.0,
    "WG301": 970900.0,
    "WG302": 791900.0,
    "WG501": 99400.0,
    "WG502": 535000.0,
    "WG503": 651200.0,
    "DM101": 0.0,
    "DM102": 0.0,
    "DM201": 0.0,
    "DM202": 0.0,
    "DM203": 0.0,
    "PL601_TOT": 100000.0,
    "PL602_TOT": 1312600.0,
    "PL603_TOT": 1636400.0,
    "SL606_TOT": 61900.0,
    "SL607_TOT": 93500.0,
}


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--apply", action="store_true")
    args = parser.parse_args()

    from database import PostgresSessionLocal
    from models.scada_tag import ScadaTag
    from services.scada_tag_registry import invalidate_registry_cache, refresh_consumer_lists

    with PostgresSessionLocal() as db:
        updated = 0
        for tag, seed in SEEDS.items():
            row = db.query(ScadaTag).filter(ScadaTag.tag == tag).first()
            if not row:
                print(f"  MISS  {tag} — not in scada_tags")
                continue
            current = float(row.emulator_seed or 0)
            if current == seed:
                print(f"  OK    {tag} already {seed}")
                continue
            print(f"  SET   {tag}: {current} -> {seed}")
            if args.apply:
                row.emulator_seed = seed
                updated += 1
        if args.apply:
            db.commit()
            invalidate_registry_cache()
            refresh_consumer_lists()
            print(f"\nApplied {updated} seed updates.")
        else:
            print("\nDry run — re-run with --apply to write.")


if __name__ == "__main__":
    main()
