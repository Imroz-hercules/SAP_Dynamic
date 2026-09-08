# backend/services/packing_capacity.py
"""
Per-line packing configuration for the tons/hour KPI, read from the database.

WHAT THIS REPLACES

``routes/kpi_routes.py`` converted bag counts to tons with five literals::

    pl601_tons = PL601 * 0.045  # 45 KG bags
    pl602_tons = PL602 * 0.045  # 45 KG bags
    pl603_tons = PL603 * 0.040  # 40 KG bran bags
    pl606_tons = PL606 * 0.001  # 1 KG bags
    pl607_tons = PL607 * 0.010  # 10 KG bags

Two things were wrong with that, both measured on 2026-09-08.

1. THE WEIGHTS DISAGREED WITH THE DATABASE. ``palletizer_mapping.bag_weight_kg``
   is per *version*, not per line: PL603 has versions at 25 kg and 40 kg, and
   PL607 has 5 kg, 10 kg and one row at 1200 kg. The literal applied 40 kg to
   every PL603 bag, overstating the 25 kg version's tonnage by 60%.

2. TWO LINES CONTRIBUTED NOTHING AT ALL. The code read ``PL606_TOT`` and
   ``PL607_TOT`` from the SCADA row. Those tags do not exist -- the registry and
   the live payload both call them ``SL606_TOT`` and ``SL607_TOT`` -- so
   ``row.get(...)`` returned the 0.0 default every time and two whole packing
   lines were silently missing from the capacity figure.

``palletizer_mapping`` already carries the right answer for both: ``scada_tag``
says which counter backs a line (A2 added it), and ``bag_weight_kg`` says what a
bag on that line weighs. This module reads them, so correcting a bag weight in
the Palletizer Mapping screen now changes the KPI instead of being contradicted
by a literal.

The value flows to SAP as ``PACKING_CAPACITY_TON`` (``kpi_routes.py`` payloads),
so a wrong number here is the exact failure the migration exists to prevent.

WHEN A LINE HAS MORE THAN ONE BAG WEIGHT

``calc_kpis_from_row`` receives a bare SCADA snapshot -- tag values only, no
order and no version -- so when two versions on one line use different bag
weights there is genuinely nothing in scope to choose between them. Rather than
silently pick, this module:

  * uses the weight when a line has exactly one,
  * otherwise reports the ambiguity to ``error_log`` (deduped, so the polling
    KPI routes do not write a row per call) and uses the line's MOST COMMON
    weight, breaking a tie by taking the SMALLEST.

Smallest-on-a-tie is deliberate: this number becomes a capacity reported to SAP,
and understating capacity is the less damaging error. The rule is deterministic
and derived from the data rather than from a literal, and the operator is told
which line is ambiguous so the mapping can be corrected.

That rule also keeps the known-bad BK10 row out of the arithmetic: PL607's
1200 kg row is a single outlier against three rows at 10 kg, so the mode is
10 kg and the 1200 stays out -- while still being reported. It is recorded in
WORKSTREAM_B_STATUS.md as a data question for the mill, and this module does not
attempt to correct it.
"""

import logging
import threading
import time
from collections import Counter
from typing import Any, Dict, List, Optional

log = logging.getLogger(__name__)

TTL_SECONDS = 60.0

_cache: Dict[str, Any] = {"lines": None, "read_at": 0.0}
_lock = threading.Lock()

_reported = set()
_reported_lock = threading.Lock()


def _resolve_weight(palletizer: str, weights: List[float]) -> Optional[float]:
    """The bag weight to use for a line, reporting the choice when it is not obvious."""
    usable = [w for w in weights if w is not None and w > 0]
    if not usable:
        _report(
            palletizer,
            f"packing line '{palletizer}' has no usable bag_weight_kg in "
            f"palletizer_mapping, so it cannot be converted from bags to tons "
            f"and is left out of the packing capacity KPI",
        )
        return None

    distinct = sorted(set(usable))
    if len(distinct) == 1:
        return distinct[0]

    counts = Counter(usable)
    top = max(counts.values())
    chosen = min(w for w, c in counts.items() if c == top)
    _report(
        palletizer,
        f"packing line '{palletizer}' has more than one bag weight configured "
        f"in palletizer_mapping ({', '.join(f'{w:g} kg' for w in distinct)}). "
        f"The packing capacity KPI is calculated from a SCADA snapshot that "
        f"carries no order or version, so it cannot tell which one ran. Using "
        f"{chosen:g} kg (the most common, smallest on a tie). Give the line a "
        f"single bag weight, or split the counter per version, to make this "
        f"exact.",
    )
    return chosen


def _report(palletizer: str, message: str) -> None:
    """Put a configuration problem in front of an operator, once per process."""
    with _reported_lock:
        if palletizer in _reported:
            return
        _reported.add(palletizer)

    log.warning(message)
    try:
        from services.error_logger import log_order_error

        log_order_error(
            po_number="",
            error_type="configuration_error",
            error_message=message,
            payload={"palletizer": palletizer},
            source="packing_capacity",
        )
    except Exception as exc:  # never let reporting break the KPI
        log.debug("Could not write packing-capacity notice to error_log: %s", exc)


def _load() -> List[Dict[str, Any]]:
    from database import PostgresSessionLocal
    from models.palletizer_mapping import PalletizerMapping

    by_line: Dict[str, Dict[str, Any]] = {}
    with PostgresSessionLocal() as db:
        for row in db.query(PalletizerMapping).all():
            line = (row.palletizer or "").strip()
            if not line:
                continue
            entry = by_line.setdefault(line, {"palletizer": line, "tags": [], "weights": []})
            if row.scada_tag:
                entry["tags"].append(row.scada_tag.strip())
            entry["weights"].append(row.bag_weight_kg)

    lines = []
    for line, entry in sorted(by_line.items()):
        tags = sorted(set(entry["tags"]))
        if not tags:
            _report(line, f"packing line '{line}' has no scada_tag in palletizer_mapping, "
                          f"so its counter cannot be found and it is left out of the "
                          f"packing capacity KPI")
            continue
        if len(tags) > 1:
            _report(line, f"packing line '{line}' maps to more than one SCADA tag "
                          f"({', '.join(tags)}); using {tags[0]}")
        weight = _resolve_weight(line, entry["weights"])
        if weight is None:
            continue
        lines.append({"palletizer": line, "scada_tag": tags[0], "bag_weight_kg": float(weight)})
    return lines


def packing_lines(*, force: bool = False) -> List[Dict[str, Any]]:
    """
    Each packing line as ``{palletizer, scada_tag, bag_weight_kg}``.

    Lines that cannot be resolved are omitted and reported, never guessed.
    Returns an empty list if the database is unreachable -- the caller then
    reports no packing capacity rather than a number built from literals.
    """
    now = time.time()
    with _lock:
        cached = _cache["lines"]
        if not force and cached is not None and (now - float(_cache["read_at"])) < TTL_SECONDS:
            return list(cached)

    try:
        lines = _load()
    except Exception as exc:
        log.warning("Could not read palletizer_mapping for packing capacity: %s", exc)
        lines = []

    with _lock:
        _cache["lines"] = lines
        _cache["read_at"] = time.time()
    return list(lines)


def total_packing_tons(row: Dict[str, Any]) -> float:
    """
    Tons packed across every configured line, from a SCADA snapshot.

    ``row`` is the same dict ``calc_kpis_from_row`` works on. A tag missing from
    it contributes nothing, exactly as before -- but the tag names now come from
    palletizer_mapping, so SL606_TOT/SL607_TOT are actually found.
    """
    total = 0.0
    for line in packing_lines():
        try:
            bags = float(row.get(line["scada_tag"], 0.0) or 0.0)
        except (TypeError, ValueError):
            bags = 0.0
        total += bags * line["bag_weight_kg"] / 1000.0
    return total


def invalidate_cache() -> None:
    """Drop the cached mapping; call after editing palletizer_mapping."""
    with _lock:
        _cache["lines"] = None
        _cache["read_at"] = 0.0


def clear_reported() -> None:
    """Forget dedupe state so a recurring configuration problem reports again."""
    with _reported_lock:
        _reported.clear()
