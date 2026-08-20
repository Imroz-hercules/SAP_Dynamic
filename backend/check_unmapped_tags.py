# backend/check_unmapped_tags.py
"""
Pre-deploy check for A7 (baseline guard).

A7 turns a silent wrong number into a halted order: a scale tag with no
``baseline_*`` column now raises instead of reading 0.0. That is the right
behaviour, but it means a mapping that was quietly producing garbage will start
stopping orders the moment A7 ships.

Run this against the target database **before deploying** to find those cases
while they are still a config problem rather than a production incident.

    PYTHONIOENCODING=utf-8 python check_unmapped_tags.py

Exit code 0 = nothing would break. Exit code 1 = findings to fix first.
Read-only; it never writes.
"""

import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from services import baseline_guard  # noqa: E402

# Orders in these states are finished; a bad mapping cannot hurt them any more.
TERMINAL_STATUSES = {"validated", "rejected", "completed", "confirmed"}

findings = []


def finding(scope, name, detail):
    findings.append((scope, name, detail))


def check_milling_mappings(db, MillingVersionMapping):
    """Every milling scale must have a baseline column — main and byproduct."""
    rows = db.query(MillingVersionMapping).all()
    print(f"  milling_version_mappings: {len(rows)} row(s)")

    for row in rows:
        version = row.version

        scales = row.scales
        if isinstance(scales, str):
            import json
            try:
                scales = json.loads(scales)
            except json.JSONDecodeError:
                scales = [s.strip() for s in scales.split(",") if s.strip()]
        scales = scales or []

        for tag in scales:
            if not baseline_guard.has_baseline_column(tag):
                finding(
                    "milling mapping",
                    version,
                    f"main scale '{tag}' has no baseline_{str(tag).lower()} column "
                    f"— orders on this version will HALT",
                )

        for slot in ("scale1", "scale2", "scale3"):
            tag = getattr(row, slot, None)
            if tag and not baseline_guard.has_baseline_column(tag):
                finding(
                    "milling mapping",
                    version,
                    f"byproduct {slot} '{tag}' has no baseline column "
                    f"— reported, order continues (byproducts do not drive confirmed_qty)",
                )


def check_packing_mappings(db, PalletizerMapping):
    """
    Packing tags (PL60x_TOT / SL60x_TOT) have no baseline column by design —
    they are read from the order's scale1 slot, which is set to the tag at order
    start. So the thing to check is that the line resolves to a tag at all; a
    row with no scada_tag yields empty equipment.

    A2 moved that tag out of the hardcoded PL_TO_SCADA map and onto the row.
    """
    rows = db.query(PalletizerMapping).all()
    print(f"  palletizer_mapping:       {len(rows)} row(s)")

    for row in rows:
        if not row.scada_tag:
            finding(
                "packing mapping",
                row.version,
                f"line '{row.palletizer}' has no scada_tag — orders on this "
                f"version will be rejected at classification",
            )
        if not (row.bags_per_pallet_actual or row.bag_size_kg or 0) > 1:
            finding(
                "packing mapping",
                row.version,
                f"no bags-per-pallet multiplier — the SCADA delta would be "
                f"confirmed as bags 1:1",
            )


def check_live_orders(db, ProcessOrder, classify_order):
    """
    Classify every non-terminal order the way the app does and check the tags it
    would actually read a baseline for. This is the direct answer to "would A7
    stop anything that is running right now?".
    """
    orders = db.query(ProcessOrder).all()
    live = [o for o in orders if str(o.status or "").strip().lower() not in TERMINAL_STATUSES]
    print(f"  process_orders:           {len(orders)} row(s), {len(live)} non-terminal")

    for order in live:
        try:
            classification = classify_order(order)
        except Exception as exc:
            finding("order", order.order_id, f"classify_order raised: {exc}")
            continue

        if classification.get("error"):
            finding("order", order.order_id, f"classification error: {classification['error']}")
            continue

        slots = {
            str(getattr(order, s, "") or "").upper()
            for s in ("scale1", "scale2", "scale3")
        }
        slots.discard("")

        for tag in classification.get("equipment") or []:
            tag_upper = str(tag).upper()
            if baseline_guard.has_baseline_column(tag_upper):
                continue
            if tag_upper in slots:
                continue  # packing tag resolved through its scale slot — fine
            finding(
                "order",
                order.order_id,
                f"status={order.status} version={order.version} tag '{tag_upper}' has "
                f"neither a baseline column nor a scale slot — this order will HALT",
            )


def main():
    print("A7 pre-deploy check — scale tags without a baseline\n")

    columns = sorted(baseline_guard.baseline_columns())
    print(f"Baseline columns on process_orders ({len(columns)}):")
    print("  " + ", ".join(c.replace("baseline_", "") for c in columns))
    print()

    from database import PostgresSessionLocal
    from models.milling_version_mapping import MillingVersionMapping
    from models.palletizer_mapping import PalletizerMapping
    from models.process_order_pg import ProcessOrderPG
    from routes.order_validation import classify_order

    print("Checking:")
    with PostgresSessionLocal() as db:
        check_milling_mappings(db, MillingVersionMapping)
        check_packing_mappings(db, PalletizerMapping)
        check_live_orders(db, ProcessOrderPG, classify_order)

    print()
    if not findings:
        print("PASS — no scale tag is missing a baseline. A7 will not stop anything.")
        return 0

    print(f"FAIL — {len(findings)} finding(s):\n")
    width = max(len(scope) for scope, _, _ in findings)
    for scope, name, detail in findings:
        print(f"  [{scope.ljust(width)}] {name}: {detail}")
    print("\nFix these before deploying A7.")
    return 1


if __name__ == "__main__":
    sys.exit(main())
