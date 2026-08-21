# backend/migrate_b3_activate_counters.py
"""
B3 — close the SL60x_COUNTER gap.

Evidence (STATIC_TO_DYNAMIC_PLAN.md §6 + WORKSTREAM_B_STATUS.md):
  * Columns exist on process_orders: baseline_sl601_counter … baseline_sl607_counter
  * Tags exist in ASMArchive_DB5 (Book1.xlsx inventory in the plan)
  * A7 baseline guard is live — unmapped tags halt rather than lie
  * They were seeded is_active=false only because ALLOWED_SCADA_FIELDS omitted them

This migration flips the five counter rows to active so registry-driven
ALLOWED_SCADA_FIELDS / poll_keys include them. Dry-run by default.

    python migrate_b3_activate_counters.py
    python migrate_b3_activate_counters.py --apply

After --apply, run: python check_unmapped_tags.py
"""
from __future__ import annotations

import argparse
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

COUNTERS = (
    "SL601_COUNTER",
    "SL602_COUNTER",
    "SL603_COUNTER",
    "SL606_COUNTER",
    "SL607_COUNTER",
)

BASELINE_ATTRS = (
    "baseline_sl601_counter",
    "baseline_sl602_counter",
    "baseline_sl603_counter",
    "baseline_sl606_counter",
    "baseline_sl607_counter",
)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--apply", action="store_true")
    args = parser.parse_args()

    from models.process_order_pg import ProcessOrderPG
    from database import PostgresSessionLocal
    from models.scada_tag import ScadaTag
    from services.scada_tag_registry import invalidate_registry_cache, refresh_consumer_lists
    from services import baseline_guard

    print("Baseline columns on ProcessOrderPG:")
    cols = baseline_guard.baseline_columns()
    for attr in BASELINE_ATTRS:
        ok = attr in cols or hasattr(ProcessOrderPG, attr)
        print(f"  {'OK' if ok else 'MISS'}  {attr}")
        if not ok:
            print("Refusing to activate — baseline column missing. Abort.")
            return 1

    with PostgresSessionLocal() as db:
        for tag in COUNTERS:
            row = db.query(ScadaTag).filter(ScadaTag.tag == tag).first()
            if not row:
                print(f"  MISS  {tag} — not in scada_tags (seed first)")
                continue
            print(
                f"  {'SET' if args.apply else 'WOULD'}  {tag}: "
                f"is_active={row.is_active} -> True, is_pollable={row.is_pollable}"
            )
            if args.apply:
                row.is_active = True
                row.is_pollable = True
        if args.apply:
            db.commit()
            invalidate_registry_cache()
            refresh_consumer_lists()
            print("\nApplied. Run: python check_unmapped_tags.py")
        else:
            print("\nDry run — re-run with --apply to write.")
    return 0


if __name__ == "__main__":
    sys.exit(main() or 0)
