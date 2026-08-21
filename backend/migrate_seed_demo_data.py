# backend/migrate_seed_demo_data.py
"""
Seed an empty demo Postgres with the commit-0 / plan reference data.

Your DB had:
  scada_tags empty          → B1/B3 printed MISS for every tag
  palletizer_mapping 0 rows → A2 backfilled nothing
  milling_version_mappings 0 → check_unmapped_tags is a vacuous PASS

This script fills:
  * scada_tags     (28 rows from setup_sap_postgres.sql)
  * kpi_config     (19 rows)
  * classification_rules (material-prefix seed, if empty)
  * milling_version_mappings  from ../milling_version_mappings.csv
  * palletizer_mapping        from ../palletizer_mapping.csv

Idempotent (ON CONFLICT / skip if version exists). Always writes.

    python migrate_seed_demo_data.py

Then:
    python migrate_a2_palletizer_mapping.py
    python migrate_b1_emulator_seeds.py --apply
    python migrate_b3_activate_counters.py --apply
    python check_unmapped_tags.py

Or simply:  python setup_demo_migrations.py
"""
from __future__ import annotations

import csv
import json
import os
import sys
from pathlib import Path

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

REPO_ROOT = Path(__file__).resolve().parent.parent

SCADA_TAGS = [
    # tag, category, reading_type, source_column, rollover_max, unit, is_active, sort_order, display_name
    ("WG101", "INPUT", "hi_lo", "WG101", 1000000, "TON", True, 10, "Wheat input - Silo 1"),
    ("WG201", "INPUT", "hi_lo", "WG201", 1000000, "TON", True, 11, "Wheat input - Silo 2"),
    ("WG202", "INPUT", "hi_lo", "WG202", 1000000, "TON", True, 12, "Clean wheat - active scale"),
    ("WG301", "INPUT", "hi_lo", "WG301", 1000000, "TON", True, 13, "Milling screenings"),
    ("WG302", "INPUT", "hi_lo", "WG302", 1000000, "TON", True, 14, "Pre-clean screenings"),
    ("WG501", "MILLING", "hi_lo", "WG501", 1000000, "TON", True, 20, "Bakery flour stream"),
    ("WG502", "MILLING", "hi_lo", "WG502", 1000000, "TON", True, 21, "Cake / IWW flour stream"),
    ("WG503", "MILLING", "hi_lo", "WG503", 1000000, "TON", True, 22, "Bran stream"),
    ("DM101", "WATER", "average", "DM101", None, "m3", True, 30, "Water meter 1"),
    ("DM102", "WATER", "average", "DM102", None, "m3", True, 31, "Water meter 2"),
    ("DM201", "WATER", "average", "DM201", None, "m3", True, 32, "Water meter 3"),
    ("DM202", "WATER", "average", "DM202", None, "m3", True, 33, "Water meter 4"),
    ("DM203", "WATER", "average", "DM203", None, "m3", True, 34, "Water meter 5"),
    ("PL601_TOT", "PACKING", "single", "PL601_TOT", 100000, "PALLET", True, 40, "Palletizer 1"),
    ("PL602_TOT", "PACKING", "single", "PL602_TOT", 100000, "PALLET", True, 41, "Palletizer 2"),
    ("PL603_TOT", "PACKING", "single", "PL603_TOT", 100000, "PALLET", True, 42, "Palletizer 3 - bran"),
    ("SL606_TOT", "PACKING", "single", "SL606_TOT", 100000, "PALLET", True, 43, "Line 6 - 1 KG"),
    ("SL607_TOT", "PACKING", "single", "SL607_TOT", 100000, "PALLET", True, 44, "Line 7 - 10 KG"),
    ("SL601_DAMAGED", "DAMAGED", "single", "SL601_DAMAGED", None, "BAG", True, 50, "Line 1 damaged bags"),
    ("SL602_DAMAGED", "DAMAGED", "single", "SL602_DAMAGED", None, "BAG", True, 51, "Line 2 damaged bags"),
    ("SL603_DAMAGED", "DAMAGED", "single", "SL603_DAMAGED", None, "BAG", True, 52, "Line 3 damaged bags"),
    ("SL606_DAMAGED", "DAMAGED", "single", "SL606_DAMAGED", None, "BAG", True, 53, "Line 6 damaged bags"),
    ("SL607_DAMAGED", "DAMAGED", "single", "SL607_DAMAGED", None, "BAG", True, 54, "Line 7 damaged bags"),
    ("SL601_COUNTER", "PACKING", "single", "SL601_COUNTER", 100000, "BAG", False, 60, "Line 1 bag counter"),
    ("SL602_COUNTER", "PACKING", "single", "SL602_COUNTER", 100000, "BAG", False, 61, "Line 2 bag counter"),
    ("SL603_COUNTER", "PACKING", "single", "SL603_COUNTER", 100000, "BAG", False, 62, "Line 3 bag counter"),
    ("SL606_COUNTER", "PACKING", "single", "SL606_COUNTER", 100000, "BAG", False, 63, "Line 6 bag counter"),
    ("SL607_COUNTER", "PACKING", "single", "SL607_COUNTER", 100000, "BAG", False, 64, "Line 7 bag counter"),
]

KPI_CONFIG = [
    ("mill_throughput_pct", "Mill Throughput (%)", "MILLING", "mill_throughput_pct", 100, "%", 10),
    ("mill_time_efficiency_pct", "Mill Time Efficiency (%)", "MILLING", "mill_time_efficiency_pct", 100, "%", 11),
    ("total_utilization_pct", "Total Utilization (%)", "MILLING", "total_utilization_pct", 100, "%", 12),
    ("milling_gain_pct", "Milling Gain (%)", "MILLING", "milling_gain_pct", 120, "%", 13),
    ("milling_screening_pct", "Milling Screening (%)", "MILLING", "milling_screening_pct", 20, "%", 14),
    ("flour_extraction_pct", "Flour Extraction (%)", "MILLING", "flour_extraction_pct", 85, "%", 15),
    ("bran_extraction_pct", "Bran Extraction (%)", "MILLING", "bran_extraction_pct", 25, "%", 16),
    ("milling_loss_pct", "Milling Loss (%)", "MILLING", "milling_loss_pct", None, "%", 17),
    ("water_consumption_m3", "Water Consumption (m3)", "MILLING", "water_consumption_m3", None, "m3", 18),
    ("milling_net_hours_hrs", "Net Hours (hrs)", "MILLING", "net_hours_hrs", None, "hrs", 19),
    ("milling_downtime_hrs", "Downtime (hrs)", "MILLING", "downtime_hrs", None, "hrs", 20),
    ("max_utilization_milling_capacity_pct", "Max Utilization of Milling Capacity (%)", "MILLING", None, 100, "%", 21),
    ("pre_cleaning_screening_pct", "Pre Cleaning Screening (%)", "MILLING", None, 20, "%", 22),
    ("first_break_capacity_tph", "1st Break Capacity per Hour (t/h)", "MILLING", None, 30, "t/h", 23),
    ("packing_line_capacity_bags_hr", "Packing Line Capacity (bags/hr)", "PACKING", "packing_line_capacity_bags_hr", 2000, "bags/hr", 30),
    ("daily_packing_output_bags", "Daily Packing Output (bags)", "PACKING", "daily_packing_output_bags", 100000, "bags", 31),
    ("machine_utilization_pct", "Machine Utilization (%)", "PACKING", "machine_utilization_pct", 100, "%", 32),
    ("packing_net_hours_hrs", "Net Hours (hrs)", "PACKING", "net_hours_hrs", None, "hrs", 33),
    ("packing_downtime_hrs", "Downtime (hrs)", "PACKING", "downtime_hrs", None, "hrs", 34),
]

# Material-prefix rules matching A1 seed (plant_department rules stay deactivated in SQL)
CLASSIFICATION_RULES = [
    ("material_prefix", "13", "MILLING", 10, "Wheat / milling materials"),
    ("material_prefix", "14", "PACKING", 10, "Packing materials"),
    ("material_prefix", "15", "MILLING", 10, "Extended milling prefix"),
    ("material_prefix", "17", "MILLING", 10, "Extended milling prefix"),
    ("material_prefix", "*", "PACKING", 1000, "Fallback"),
]


def seed_scada_tags(db) -> int:
    from models.scada_tag import ScadaTag

    added = 0
    for tag, cat, rtype, src, roll, unit, active, sort, name in SCADA_TAGS:
        existing = db.query(ScadaTag).filter(ScadaTag.tag == tag).first()
        if existing:
            continue
        db.add(ScadaTag(
            tag=tag,
            category=cat,
            reading_type=rtype,
            source_column=src,
            rollover_max=roll,
            unit=unit,
            is_pollable=True,
            is_active=active,
            emulator_seed=0,
            display_name=name,
            sort_order=sort,
        ))
        added += 1
    db.commit()
    total = db.query(ScadaTag).count()
    print(f"  scada_tags: +{added} inserted, {total} total")
    return total


def seed_kpi_config(db) -> int:
    from models.kpi_config import KpiConfig

    added = 0
    for key, display, dept, col, mx, unit, sort in KPI_CONFIG:
        existing = db.query(KpiConfig).filter(KpiConfig.kpi_key == key).first()
        if existing:
            continue
        db.add(KpiConfig(
            kpi_key=key,
            display_name=display,
            department=dept,
            target_column=col,
            max_value=mx,
            unit=unit,
            is_active=True,
            sort_order=sort,
        ))
        added += 1
    db.commit()
    total = db.query(KpiConfig).count()
    print(f"  kpi_config: +{added} inserted, {total} total")
    return total


def seed_classification_rules(db) -> int:
    try:
        from models.classification_rule import ClassificationRule
    except Exception as exc:
        print(f"  classification_rules: skipped ({exc})")
        return 0

    added = 0
    for rtype, match, result, priority, desc in CLASSIFICATION_RULES:
        existing = (
            db.query(ClassificationRule)
            .filter(
                ClassificationRule.rule_type == rtype,
                ClassificationRule.match_value == match,
            )
            .first()
        )
        if existing:
            continue
        db.add(ClassificationRule(
            rule_type=rtype,
            match_value=match,
            result_value=result,
            priority=priority,
            is_active=True,
            description=desc,
        ))
        added += 1
    db.commit()
    total = db.query(ClassificationRule).count()
    print(f"  classification_rules: +{added} inserted, {total} total")
    return total


def _empty(val):
    if val is None:
        return None
    s = str(val).strip()
    if s == "" or s.upper() == "NULL":
        return None
    return s


def seed_milling_csv(db) -> int:
    from models.milling_version_mapping import MillingVersionMapping

    path = REPO_ROOT / "milling_version_mappings.csv"
    if not path.exists():
        print(f"  milling_version_mappings: CSV missing at {path}")
        return db.query(MillingVersionMapping).count()

    added = 0
    with path.open(newline="", encoding="utf-8") as fh:
        for row in csv.DictReader(fh):
            version = _empty(row.get("version"))
            if not version:
                continue
            if db.query(MillingVersionMapping).filter(MillingVersionMapping.version == version).first():
                continue
            scales_raw = _empty(row.get("scales")) or "[]"
            try:
                scales = json.loads(scales_raw.replace("'", '"'))
            except Exception:
                scales = []
            kwargs = {
                "version": version,
                "scales": scales,
                "formula": _empty(row.get("formula")),
                "scale1": _empty(row.get("scale1")),
                "scale2": _empty(row.get("scale2")),
                "description": _empty(row.get("description")),
            }
            # scale3 / scada_recipe_name may or may not exist on the model
            for optional in ("scale3", "scada_recipe_name"):
                if hasattr(MillingVersionMapping, optional) and _empty(row.get(optional)):
                    kwargs[optional] = _empty(row.get(optional))
            db.add(MillingVersionMapping(**kwargs))
            added += 1
    db.commit()
    total = db.query(MillingVersionMapping).count()
    print(f"  milling_version_mappings: +{added} from CSV, {total} total")
    return total


def seed_palletizer_csv(db) -> int:
    from models.palletizer_mapping import PalletizerMapping

    path = REPO_ROOT / "palletizer_mapping.csv"
    if not path.exists():
        print(f"  palletizer_mapping: CSV missing at {path}")
        return db.query(PalletizerMapping).count()

    added = 0
    with path.open(newline="", encoding="utf-8") as fh:
        for row in csv.DictReader(fh):
            version = _empty(row.get("version"))
            if not version:
                continue
            if db.query(PalletizerMapping).filter(PalletizerMapping.version == version).first():
                continue
            kwargs = {
                "version": version,
                "palletizer": _empty(row.get("palletizer")) or "PL601",
                "bag_size_kg": float(row["bag_size_kg"]) if _empty(row.get("bag_size_kg")) else None,
                "bags_per_pallet": float(row["bags_per_pallet"]) if _empty(row.get("bags_per_pallet")) else None,
                "kg_per_pallet": float(row["kg_per_pallet"]) if _empty(row.get("kg_per_pallet")) else None,
                "description": _empty(row.get("description")),
            }
            db.add(PalletizerMapping(**kwargs))
            added += 1
    db.commit()
    total = db.query(PalletizerMapping).count()
    print(f"  palletizer_mapping: +{added} from CSV, {total} total")
    return total


def ensure_tables():
    from database import PostgresBase, postgres_engine, Base
    # Import models so metadata knows the tables
    import models.scada_tag  # noqa: F401
    import models.kpi_config  # noqa: F401
    try:
        import models.classification_rule  # noqa: F401
    except Exception:
        pass
    import models.milling_version_mapping  # noqa: F401
    import models.palletizer_mapping  # noqa: F401
    # PalletizerMapping is declared on Base (legacy), but lives in Postgres.
    PostgresBase.metadata.create_all(bind=postgres_engine)
    Base.metadata.create_all(bind=postgres_engine)


def main() -> int:
    from database import PostgresSessionLocal
    from services.scada_tag_registry import invalidate_registry_cache, refresh_consumer_lists
    from services.kpi_config_registry import invalidate_kpi_config_cache

    print("Seed demo data (empty-DB bootstrap)\n")
    ensure_tables()

    with PostgresSessionLocal() as db:
        seed_scada_tags(db)
        seed_kpi_config(db)
        seed_classification_rules(db)
        seed_milling_csv(db)
        seed_palletizer_csv(db)

    invalidate_registry_cache()
    invalidate_kpi_config_cache()
    try:
        refresh_consumer_lists()
    except Exception as exc:
        print(f"  (registry refresh deferred: {exc})")

    print(
        "\nDone. Next:\n"
        "  python migrate_a2_palletizer_mapping.py\n"
        "  python migrate_b1_emulator_seeds.py --apply\n"
        "  python migrate_b3_activate_counters.py --apply\n"
        "  python check_unmapped_tags.py\n"
    )
    return 0


if __name__ == "__main__":
    sys.exit(main())
