# backend/migrate_packing_capacity_ceiling.py
"""
Give "Packing Line Capacity (tons/hr)" a ceiling row in kpi_config.

WHY

routes/kpi_routes.py capped this KPI with a bare literal::

    # Cap at reasonable maximum (50 t/h)
    packing_line_capacity_tons_per_hour = min(packing_line_capacity_tons_per_hour, 50.0)

Every other KPI in that same function goes through ``kpi_config_registry.clamp()``
and takes its ceiling from ``kpi_config`` (B4), including this one's sibling
``packing_line_capacity_bags_hr``. This one did not, so the number could not be
adjusted without a redeploy.

The code now calls ``kpi_clamp("packing_line_capacity_tph", ...)``. ``clamp()``
passes a value through unchanged when the key has no ``max_value``, so WITHOUT
this row the 50 t/h cap silently disappears rather than becoming configurable.
That is why this migration exists and why it should be applied together with the
code change.

    python migrate_packing_capacity_ceiling.py            # dry run
    python migrate_packing_capacity_ceiling.py --apply
"""

import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from dotenv import load_dotenv

load_dotenv()

KPI_KEY = "packing_line_capacity_tph"
DISPLAY = "Packing Line Capacity (tons/hr)"
MAX_VALUE = 50.0
UNIT = "t/h"
DEPARTMENT = "PACKING"


def main(apply: bool) -> int:
    from database import PostgresSessionLocal
    from models.kpi_config import KpiConfig

    with PostgresSessionLocal() as db:
        existing = db.query(KpiConfig).filter(KpiConfig.kpi_key == KPI_KEY).first()
        if existing:
            print(f"  OK    {KPI_KEY} already present (max_value={existing.max_value})")
            print("\nNothing to do.")
            return 0

        sibling = (
            db.query(KpiConfig)
            .filter(KpiConfig.kpi_key == "packing_line_capacity_bags_hr")
            .first()
        )
        sort_order = (sibling.sort_order + 1) if sibling and sibling.sort_order else 90

        print(f"  WOULD create {KPI_KEY}")
        print(f"          display_name = {DISPLAY!r}")
        print(f"          max_value    = {MAX_VALUE}  (was the literal 50.0 in kpi_routes.py)")
        print(f"          department   = {DEPARTMENT}, unit = {UNIT}, sort_order = {sort_order}")

        if not apply:
            print("\nDry run - re-run with --apply to write.")
            return 0

        db.add(
            KpiConfig(
                kpi_key=KPI_KEY,
                display_name=DISPLAY,
                department=DEPARTMENT,
                target_column=None,
                max_value=MAX_VALUE,
                unit=UNIT,
                is_active=True,
                sort_order=sort_order,
            )
        )
        db.commit()
        print("\nApplied.")

    from services.kpi_config_registry import invalidate_kpi_config_cache

    invalidate_kpi_config_cache()
    print("kpi_config cache invalidated.")
    return 0


if __name__ == "__main__":
    sys.exit(main("--apply" in sys.argv))
