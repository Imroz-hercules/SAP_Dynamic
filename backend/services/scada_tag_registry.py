# backend/services/scada_tag_registry.py
"""
SCADA tag registry — Workstream B (B1 / B2).

Single reader for `scada_tags`. Replaces the hardcoded field lists in
scale_service, embedded_emulator, app_scheduler, and scada_routes.

Resolution: database rows (active / pollable filters) with a seed-matching
bootstrap fallback so imports and tests still work if Postgres is empty or
unreachable at import time.

CONTRACT (backend/CONTRACTS.md):
  scale_service.MILLING_FIELDS / INPUT_FIELDS stay importable as lists of tag
  strings. Callers that did `from scale_service import MILLING_FIELDS` hold a
  reference to the list object — so refreshes MUST mutate in place (.clear /
  .extend), never rebind the module name to a new list.
"""
from __future__ import annotations

import logging
import threading
import time
from typing import Any, Dict, List, Optional

log = logging.getLogger("scada_tag_registry")

REGISTRY_TTL_SECONDS = 30.0

_cache: Dict[str, Any] = {"tags": None, "read_at": 0.0}
_lock = threading.Lock()

# Display metadata for SCALE_CATEGORIES (not stored per-row in scada_tags).
CATEGORY_META = {
    "INPUT": {
        "name": "Input Scales (Wheat)",
        "color": "#3b82f6",
        "description": "Wheat input monitoring scales",
    },
    "MILLING": {
        "name": "Milling Scales (Flour/Bran)",
        "color": "#22c55e",
        "description": "Flour and bran production scales",
    },
    "WATER": {
        "name": "Water Meters",
        "color": "#06b6d4",
        "description": "Water dosing meters",
    },
    "PACKING": {
        "name": "Packing Palletizers",
        "color": "#f59e0b",
        "description": "Bag counting palletizers",
    },
    "DAMAGED": {
        "name": "Damaged Bag Counters",
        "color": "#ef4444",
        "description": "Damaged bag quality counters",
    },
}

# Bootstrap = current hardcoded behaviour (setup_sap_postgres.sql seed).
# Used when the DB has no rows or cannot be reached at import.
_BOOTSTRAP: List[Dict[str, Any]] = [
    {"tag": "WG101", "category": "INPUT", "reading_type": "hi_lo", "source_column": "WG101",
     "rollover_max": 1000000.0, "unit": "TON", "is_pollable": True, "is_active": True,
     "emulator_seed": 708000.0, "display_name": "Wheat input - Silo 1", "sort_order": 10},
    {"tag": "WG201", "category": "INPUT", "reading_type": "hi_lo", "source_column": "WG201",
     "rollover_max": 1000000.0, "unit": "TON", "is_pollable": True, "is_active": True,
     "emulator_seed": 319800.0, "display_name": "Wheat input - Silo 2", "sort_order": 11},
    {"tag": "WG202", "category": "INPUT", "reading_type": "hi_lo", "source_column": "WG202",
     "rollover_max": 1000000.0, "unit": "TON", "is_pollable": True, "is_active": True,
     "emulator_seed": 921600.0, "display_name": "Clean wheat - active scale", "sort_order": 12},
    {"tag": "WG301", "category": "INPUT", "reading_type": "hi_lo", "source_column": "WG301",
     "rollover_max": 1000000.0, "unit": "TON", "is_pollable": True, "is_active": True,
     "emulator_seed": 970900.0, "display_name": "Milling screenings", "sort_order": 13},
    {"tag": "WG302", "category": "INPUT", "reading_type": "hi_lo", "source_column": "WG302",
     "rollover_max": 1000000.0, "unit": "TON", "is_pollable": True, "is_active": True,
     "emulator_seed": 791900.0, "display_name": "Pre-clean screenings", "sort_order": 14},
    {"tag": "WG501", "category": "MILLING", "reading_type": "hi_lo", "source_column": "WG501",
     "rollover_max": 1000000.0, "unit": "TON", "is_pollable": True, "is_active": True,
     "emulator_seed": 99400.0, "display_name": "Bakery flour stream", "sort_order": 20},
    {"tag": "WG502", "category": "MILLING", "reading_type": "hi_lo", "source_column": "WG502",
     "rollover_max": 1000000.0, "unit": "TON", "is_pollable": True, "is_active": True,
     "emulator_seed": 535000.0, "display_name": "Cake / IWW flour stream", "sort_order": 21},
    {"tag": "WG503", "category": "MILLING", "reading_type": "hi_lo", "source_column": "WG503",
     "rollover_max": 1000000.0, "unit": "TON", "is_pollable": True, "is_active": True,
     "emulator_seed": 651200.0, "display_name": "Bran stream", "sort_order": 22},
    {"tag": "DM101", "category": "WATER", "reading_type": "average", "source_column": "DM101",
     "rollover_max": None, "unit": "m3", "is_pollable": True, "is_active": True,
     "emulator_seed": 0.0, "display_name": "Water meter 1", "sort_order": 30},
    {"tag": "DM102", "category": "WATER", "reading_type": "average", "source_column": "DM102",
     "rollover_max": None, "unit": "m3", "is_pollable": True, "is_active": True,
     "emulator_seed": 0.0, "display_name": "Water meter 2", "sort_order": 31},
    {"tag": "DM201", "category": "WATER", "reading_type": "average", "source_column": "DM201",
     "rollover_max": None, "unit": "m3", "is_pollable": True, "is_active": True,
     "emulator_seed": 0.0, "display_name": "Water meter 3", "sort_order": 32},
    {"tag": "DM202", "category": "WATER", "reading_type": "average", "source_column": "DM202",
     "rollover_max": None, "unit": "m3", "is_pollable": True, "is_active": True,
     "emulator_seed": 0.0, "display_name": "Water meter 4", "sort_order": 33},
    {"tag": "DM203", "category": "WATER", "reading_type": "average", "source_column": "DM203",
     "rollover_max": None, "unit": "m3", "is_pollable": True, "is_active": True,
     "emulator_seed": 0.0, "display_name": "Water meter 5", "sort_order": 34},
    {"tag": "PL601_TOT", "category": "PACKING", "reading_type": "single", "source_column": "PL601_TOT",
     "rollover_max": 100000.0, "unit": "PALLET", "is_pollable": True, "is_active": True,
     "emulator_seed": 100000.0, "display_name": "Palletizer 1", "sort_order": 40},
    {"tag": "PL602_TOT", "category": "PACKING", "reading_type": "single", "source_column": "PL602_TOT",
     "rollover_max": 100000.0, "unit": "PALLET", "is_pollable": True, "is_active": True,
     "emulator_seed": 1312600.0, "display_name": "Palletizer 2", "sort_order": 41},
    {"tag": "PL603_TOT", "category": "PACKING", "reading_type": "single", "source_column": "PL603_TOT",
     "rollover_max": 100000.0, "unit": "PALLET", "is_pollable": True, "is_active": True,
     "emulator_seed": 1636400.0, "display_name": "Palletizer 3 - bran", "sort_order": 42},
    {"tag": "SL606_TOT", "category": "PACKING", "reading_type": "single", "source_column": "SL606_TOT",
     "rollover_max": 100000.0, "unit": "PALLET", "is_pollable": True, "is_active": True,
     "emulator_seed": 61900.0, "display_name": "Line 6 - 1 KG", "sort_order": 43},
    {"tag": "SL607_TOT", "category": "PACKING", "reading_type": "single", "source_column": "SL607_TOT",
     "rollover_max": 100000.0, "unit": "PALLET", "is_pollable": True, "is_active": True,
     "emulator_seed": 93500.0, "display_name": "Line 7 - 10 KG", "sort_order": 44},
    {"tag": "SL601_DAMAGED", "category": "DAMAGED", "reading_type": "single", "source_column": "SL601_DAMAGED",
     "rollover_max": None, "unit": "BAG", "is_pollable": True, "is_active": True,
     "emulator_seed": 0.0, "display_name": "Line 1 damaged bags", "sort_order": 50},
    {"tag": "SL602_DAMAGED", "category": "DAMAGED", "reading_type": "single", "source_column": "SL602_DAMAGED",
     "rollover_max": None, "unit": "BAG", "is_pollable": True, "is_active": True,
     "emulator_seed": 0.0, "display_name": "Line 2 damaged bags", "sort_order": 51},
    {"tag": "SL603_DAMAGED", "category": "DAMAGED", "reading_type": "single", "source_column": "SL603_DAMAGED",
     "rollover_max": None, "unit": "BAG", "is_pollable": True, "is_active": True,
     "emulator_seed": 0.0, "display_name": "Line 3 damaged bags", "sort_order": 52},
    {"tag": "SL606_DAMAGED", "category": "DAMAGED", "reading_type": "single", "source_column": "SL606_DAMAGED",
     "rollover_max": None, "unit": "BAG", "is_pollable": True, "is_active": True,
     "emulator_seed": 0.0, "display_name": "Line 6 damaged bags", "sort_order": 53},
    {"tag": "SL607_DAMAGED", "category": "DAMAGED", "reading_type": "single", "source_column": "SL607_DAMAGED",
     "rollover_max": None, "unit": "BAG", "is_pollable": True, "is_active": True,
     "emulator_seed": 0.0, "display_name": "Line 7 damaged bags", "sort_order": 54},
    # Counters: seeded inactive (B3). Listed so bootstrap matches the SQL seed.
    {"tag": "SL601_COUNTER", "category": "PACKING", "reading_type": "single", "source_column": "SL601_COUNTER",
     "rollover_max": 100000.0, "unit": "BAG", "is_pollable": True, "is_active": False,
     "emulator_seed": 0.0, "display_name": "Line 1 bag counter", "sort_order": 60},
    {"tag": "SL602_COUNTER", "category": "PACKING", "reading_type": "single", "source_column": "SL602_COUNTER",
     "rollover_max": 100000.0, "unit": "BAG", "is_pollable": True, "is_active": False,
     "emulator_seed": 0.0, "display_name": "Line 2 bag counter", "sort_order": 61},
    {"tag": "SL603_COUNTER", "category": "PACKING", "reading_type": "single", "source_column": "SL603_COUNTER",
     "rollover_max": 100000.0, "unit": "BAG", "is_pollable": True, "is_active": False,
     "emulator_seed": 0.0, "display_name": "Line 3 bag counter", "sort_order": 62},
    {"tag": "SL606_COUNTER", "category": "PACKING", "reading_type": "single", "source_column": "SL606_COUNTER",
     "rollover_max": 100000.0, "unit": "BAG", "is_pollable": True, "is_active": False,
     "emulator_seed": 0.0, "display_name": "Line 6 bag counter", "sort_order": 63},
    {"tag": "SL607_COUNTER", "category": "PACKING", "reading_type": "single", "source_column": "SL607_COUNTER",
     "rollover_max": 100000.0, "unit": "BAG", "is_pollable": True, "is_active": False,
     "emulator_seed": 0.0, "display_name": "Line 7 bag counter", "sort_order": 64},
]

# HI companion seeds for hi_lo tags (emulator uses separate _HI / _LO keys).
_BOOTSTRAP_HI: Dict[str, float] = {
    "WG101": 226847.0, "WG201": 228566.0, "WG202": 232093.0,
    "WG301": 5011.0, "WG302": 1458.0,
    "WG501": 41458.0, "WG502": 26985.0, "WG503": 45646.0,
}

VALID_CATEGORIES = ("INPUT", "MILLING", "WATER", "PACKING", "DAMAGED")
VALID_READING_TYPES = ("hi_lo", "single", "average")


def invalidate_registry_cache() -> None:
    with _lock:
        _cache["tags"] = None
        _cache["read_at"] = 0.0


def _load_from_db() -> Optional[List[Dict[str, Any]]]:
    try:
        from database import PostgresSessionLocal
        from models.scada_tag import ScadaTag

        with PostgresSessionLocal() as db:
            rows = db.query(ScadaTag).order_by(ScadaTag.sort_order, ScadaTag.tag).all()
            if not rows:
                return None
            return [r.to_dict() for r in rows]
    except Exception as exc:
        log.warning("scada_tags load failed, using bootstrap: %s", exc)
        return None


def get_all_tag_rows(*, force: bool = False) -> List[Dict[str, Any]]:
    """All registry rows (active and inactive), cached briefly."""
    now = time.time()
    with _lock:
        if (
            not force
            and _cache["tags"] is not None
            and (now - float(_cache["read_at"])) < REGISTRY_TTL_SECONDS
        ):
            return list(_cache["tags"])

    rows = _load_from_db()
    if rows is None:
        rows = [dict(r) for r in _BOOTSTRAP]

    with _lock:
        _cache["tags"] = rows
        _cache["read_at"] = time.time()
    return list(rows)


def list_tags(
    *,
    category: Optional[str] = None,
    active_only: bool = False,
    pollable_only: bool = False,
) -> List[Dict[str, Any]]:
    rows = get_all_tag_rows()
    out = []
    for row in rows:
        if category and row.get("category") != category:
            continue
        if active_only and not row.get("is_active"):
            continue
        if pollable_only and not row.get("is_pollable"):
            continue
        out.append(row)
    return out


def tags_for_category(category: str, *, active_only: bool = True) -> List[str]:
    return [r["tag"] for r in list_tags(category=category, active_only=active_only)]


def allowed_fields(*, active_only: bool = True) -> List[str]:
    """Logical tags readable via get_scada_reading."""
    return [r["tag"] for r in list_tags(active_only=active_only)]


def poll_keys() -> List[str]:
    """Tags the scheduler should collect (active + pollable)."""
    return [r["tag"] for r in list_tags(active_only=True, pollable_only=True)]


def get_tag_row(tag: str) -> Optional[Dict[str, Any]]:
    for row in get_all_tag_rows():
        if row.get("tag") == tag:
            return row
    return None


def get_rollover_max(tag: str, default: Optional[float] = None) -> Optional[float]:
    row = get_tag_row(tag)
    if not row:
        return default
    value = row.get("rollover_max")
    if value is None:
        return default
    try:
        return float(value)
    except (TypeError, ValueError):
        return default


def get_reading_type(tag: str) -> Optional[str]:
    row = get_tag_row(tag)
    return row.get("reading_type") if row else None


def hi_lo_tags(*, active_only: bool = True) -> List[str]:
    return [
        r["tag"] for r in list_tags(active_only=active_only)
        if r.get("reading_type") == "hi_lo"
    ]


def single_value_tags(*, active_only: bool = True, categories: Optional[tuple] = None) -> List[str]:
    rows = list_tags(active_only=active_only)
    out = []
    for r in rows:
        if r.get("reading_type") == "hi_lo":
            continue
        if categories and r.get("category") not in categories:
            continue
        out.append(r["tag"])
    return out


def packing_rollover_tags(*, active_only: bool = True) -> List[str]:
    """Tags that use palletizer-style rollover maths (PACKING + rollover_max set)."""
    out = []
    for r in list_tags(active_only=active_only, category="PACKING"):
        if r.get("rollover_max") is not None:
            out.append(r["tag"])
    return out


def emulator_raw_keys(*, active_only: bool = True) -> List[str]:
    """
    Keys stored in the embedded emulator's scale_values dict.
    hi_lo tags expand to TAG_LO / TAG_HI; others use the logical tag.
    """
    keys: List[str] = []
    for r in list_tags(active_only=active_only):
        # Damaged counters are not part of the historical emulator set.
        if r.get("category") == "DAMAGED":
            continue
        tag = r["tag"]
        if r.get("reading_type") == "hi_lo":
            keys.append(f"{tag}_LO")
            keys.append(f"{tag}_HI")
        else:
            keys.append(tag)
    return keys


def emulator_category_fields(*, active_only: bool = True) -> Dict[str, List[str]]:
    """INPUT/MILLING/WATER/PACKING -> list of emulator raw keys."""
    result = {"INPUT": [], "MILLING": [], "WATER": [], "PACKING": []}
    for r in list_tags(active_only=active_only):
        cat = r.get("category")
        if cat not in result:
            continue
        tag = r["tag"]
        if r.get("reading_type") == "hi_lo":
            result[cat].extend([f"{tag}_LO", f"{tag}_HI"])
        else:
            result[cat].append(tag)
    return result


def build_scale_categories(*, active_only: bool = True) -> Dict[str, Dict[str, Any]]:
    fields = emulator_category_fields(active_only=active_only)
    out: Dict[str, Dict[str, Any]] = {}
    for cat, meta in CATEGORY_META.items():
        if cat == "DAMAGED":
            continue
        out[cat] = {
            "name": meta["name"],
            "fields": list(fields.get(cat, [])),
            "color": meta["color"],
            "description": meta["description"],
        }
    return out


def realistic_starting_values(*, active_only: bool = True) -> Dict[str, float]:
    values: Dict[str, float] = {}
    for r in list_tags(active_only=active_only):
        if r.get("category") == "DAMAGED":
            continue
        tag = r["tag"]
        seed = float(r.get("emulator_seed") or 0.0)
        if r.get("reading_type") == "hi_lo":
            values[f"{tag}_LO"] = seed
            values[f"{tag}_HI"] = float(_BOOTSTRAP_HI.get(tag, 0.0))
        else:
            values[tag] = seed
    return values


def refresh_consumer_lists() -> None:
    """
    Push the current registry into scale_service and embedded_emulator module
    lists (in-place mutation so existing imports keep working).
    """
    try:
        import services.scale_service as scale_service

        milling = tags_for_category("MILLING")
        packing = tags_for_category("PACKING")
        # Active PACKING tags (including activated COUNTERs from B3). Damaged stays separate.
        packing_fields = [t for t in packing if "DAMAGED" not in t]
        inputs = tags_for_category("INPUT")
        water = tags_for_category("WATER")
        damaged = tags_for_category("DAMAGED")
        allowed = milling + packing_fields + inputs + water + damaged

        _replace_list(scale_service.MILLING_FIELDS, milling)
        _replace_list(scale_service.PACKING_FIELDS, packing_fields)
        _replace_list(scale_service.INPUT_FIELDS, inputs)
        _replace_list(scale_service.WATER_FIELDS, water)
        _replace_list(scale_service.DAMAGED_FIELDS, damaged)
        _replace_list(scale_service.ALLOWED_SCADA_FIELDS, allowed)
    except Exception as exc:
        log.warning("Could not refresh scale_service lists: %s", exc)

    try:
        import services.embedded_emulator as emu

        cats = emulator_category_fields()
        _replace_list(emu.INPUT_FIELDS, cats.get("INPUT", []))
        _replace_list(emu.MILLING_FIELDS, cats.get("MILLING", []))
        _replace_list(emu.WATER_FIELDS, cats.get("WATER", []))
        _replace_list(emu.PACKING_FIELDS, cats.get("PACKING", []))
        keys = emu.INPUT_FIELDS + emu.MILLING_FIELDS + emu.WATER_FIELDS + emu.PACKING_FIELDS
        _replace_list(emu.SCADA_KEYS, keys)

        # SCALE_CATEGORIES is a dict — replace field lists inside.
        built = build_scale_categories()
        for cat, meta in built.items():
            if cat in emu.SCALE_CATEGORIES:
                emu.SCALE_CATEGORIES[cat]["fields"] = list(meta["fields"])
            else:
                emu.SCALE_CATEGORIES[cat] = meta

        seeds = realistic_starting_values()
        emu.REALISTIC_STARTING_VALUES.clear()
        emu.REALISTIC_STARTING_VALUES.update(seeds)
    except Exception as exc:
        log.warning("Could not refresh embedded_emulator lists: %s", exc)

    try:
        import app_scheduler as sched

        keys = poll_keys()
        if hasattr(sched, "SCADA_KEYS"):
            _replace_list(sched.SCADA_KEYS, keys)
    except Exception as exc:
        # app_scheduler may not be imported yet during early bootstrap
        log.debug("app_scheduler not refreshed yet: %s", exc)


def _replace_list(target: list, values: List[str]) -> None:
    target.clear()
    target.extend(values)


# Populate consumers once at import when possible.
def _bootstrap_refresh() -> None:
    try:
        refresh_consumer_lists()
    except Exception as exc:
        log.debug("Initial registry refresh deferred: %s", exc)
