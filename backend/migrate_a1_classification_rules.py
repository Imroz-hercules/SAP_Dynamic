# backend/migrate_a1_classification_rules.py
"""
A1 — correct the `plant_department` seed rules.

`CONTRACTS.md` says changes to Workstream A's own tables go in a migrate script
here, not by editing setup_sap_postgres.sql. This is that script.

WHAT IT DOES

Deactivates the two `plant_department` rules seeded in commit 0:

    3130 -> MILLING   (priority 10)
    *    -> PACKING   (priority 99)

WHY

They encode a rule the system does not implement, and which would be wrong if
it did. Every one of the seven relevant sites in order_validation.py reads:

    plant      = get_attr_safe(order, "plant", ...)      # a DEFAULT plant
    department = "MILLING" if order_type == "MILLING" else "PACKING"

The department comes from `order_type`, which comes from the material prefix.
The plant is only used to pick rows out of `shift_master`.

And the premise is false: `shift_master` holds shifts for BOTH departments at
plant 3130 —

    3130 | MILLING | A/B/C
    3130 | PACKING | A/B

so 3130 is not "the milling plant". It is the plant, running two departments.
Applying `3130 -> MILLING` would reclassify every packing order as milling.

Left in the table rather than deleted, because the rule type is real: if a
second plant is added that genuinely runs a single department, re-activating a
row here is all it takes. `resolve_department()` already resolves them.

The `material_prefix` rules are untouched — those are live and correct.

    PYTHONIOENCODING=utf-8 python migrate_a1_classification_rules.py [--revert]

Idempotent. Safe to run more than once.
"""

import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

NOTE = (
    "INACTIVE (A1): the code derives department from order_type, not from plant, "
    "and shift_master has both departments at 3130. Re-activate only if a plant "
    "is added that runs a single department."
)


def main(revert=False):
    from database import PostgresSessionLocal
    from models.classification_rule import RULE_PLANT_DEPARTMENT, ClassificationRule

    with PostgresSessionLocal() as db:
        rows = (
            db.query(ClassificationRule)
              .filter(ClassificationRule.rule_type == RULE_PLANT_DEPARTMENT)
              .order_by(ClassificationRule.priority)
              .all()
        )

        if not rows:
            print("No plant_department rules found — nothing to do.")
            return 0

        target = bool(revert)
        changed = 0
        for row in rows:
            was = bool(row.is_active)
            if was == target:
                print(f"  unchanged  {row.match_value:>6} -> {row.result_value:<8} "
                      f"(already {'active' if was else 'inactive'})")
                continue
            row.is_active = target
            if not target:
                row.description = NOTE
            changed += 1
            print(f"  {'ACTIVATED ' if target else 'DEACTIVATED'} "
                  f"{row.match_value:>6} -> {row.result_value}")

        db.commit()

    print(f"\n{changed} rule(s) changed, {len(rows) - changed} already correct.")
    if not revert and changed:
        print("resolve_department() now returns None for every plant, which is "
              "accurate: this system has no plant -> department rule.")
    return 0


if __name__ == "__main__":
    revert = "--revert" in sys.argv
    print(f"A1 — {'re-activating' if revert else 'deactivating'} plant_department rules\n")
    sys.exit(main(revert=revert))
