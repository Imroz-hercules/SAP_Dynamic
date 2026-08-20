# backend/services/classification_service.py
"""
Canonical order classification - Workstream A.

This module becomes the single source of truth for "which physical scales does
this order read, and with what formula?".

It had three different answers:
  1. routes/order_validation.py  classify_order()          - read the DB     (live)
  2. services/shift_live_update.py MILLING_PV_SPECS:12     - hardcoded       (live, every 60s)
  3. services/auto_validator.py  MILLING_PV_MAPPING:60     - hardcoded       (unreachable)

(1) and (2) are now the same code path - A3 moved the implementation here and
A4 pointed the shift updater at it. (3) is Workstream B's to delete.

They did disagree, on exactly one version. Of the 15 the first two shared, 13
matched; BRF1 existed only in the dict and is retired; and BRF2 resolved to a
DIFFERENT PHYSICAL SCALE depending on which you asked. The database row was the
wrong one - see migrate_fix_brf2_mapping.py, which carries the evidence and the
correction.

CONTRACT (see backend/CONTRACTS.md):
  classify_order(order) must keep returning a dict with the keys
  order_type / equipment / formula / byproduct / packing_info / error,
  and must stay importable from routes.order_validation. Five modules
  import it from there, two of them owned by Workstream B.

STATUS
  A1 (done) - resolve_order_type / resolve_department read `classification_rules`
              instead of hardcoded prefixes.
  A3 (done) - classify_order's body moved here from routes/order_validation.py
              and gained a TTL cache keyed on (order_type, version).
  A4 (done) - services/shift_live_update.py calls classify_order instead of its
              own hardcoded map, so both live implementations agree.
"""
from __future__ import annotations

import copy
import logging
import threading
import time
from typing import Any, Dict, List, Optional

log = logging.getLogger("classification_service")

# How long resolved rules are held before re-reading. Rules change only through
# the CRUD in routes/classification_routes.py, which invalidates explicitly, so
# this is a backstop for writes made directly against the database.
RULES_TTL_SECONDS = 60.0

_rules_cache: Dict[str, Any] = {"rules": None, "read_at": 0.0}
_rules_lock = threading.Lock()


# =============================================================================
# Rule loading
# =============================================================================

def _load_rules() -> List[Dict[str, Any]]:
    """
    Active rules, lowest `priority` first, `*` last within equal priority.

    Returned as plain dicts, not ORM objects: these are cached across threads
    and read outside the session that produced them.
    """
    from models.classification_rule import ClassificationRule, WILDCARD
    from database import PostgresSessionLocal

    with PostgresSessionLocal() as db:
        rows = (
            db.query(ClassificationRule)
              .filter(ClassificationRule.is_active.is_(True))
              .all()
        )
        rules = [r.to_dict() for r in rows]

    # `*` must lose to any explicit match at the same priority, whatever order
    # the database returned.
    rules.sort(key=lambda r: (r["priority"], r["match_value"] == WILDCARD, r["match_value"]))
    return rules


def get_rules(rule_type: Optional[str] = None) -> List[Dict[str, Any]]:
    """
    Active rules, cached. Pass `rule_type` to filter to one kind.

    Falls back to an empty list if the table cannot be read - callers treat that
    as "no rule matched", which surfaces as a classification error rather than a
    wrong answer.
    """
    now = time.time()
    with _rules_lock:
        cached = _rules_cache["rules"]
        fresh = cached is not None and (now - _rules_cache["read_at"]) < RULES_TTL_SECONDS

    if not fresh:
        try:
            cached = _load_rules()
            with _rules_lock:
                _rules_cache["rules"] = cached
                _rules_cache["read_at"] = now
        except Exception as exc:
            log.error("Could not read classification_rules: %s", exc)
            if cached is None:
                return []
            # Keep serving the last good copy rather than failing every order.

    if rule_type is None:
        return list(cached or [])
    return [r for r in (cached or []) if r["rule_type"] == rule_type]


def invalidate_rules_cache() -> None:
    """Drop cached rules so the next lookup re-reads. Called after any rule write."""
    with _rules_lock:
        _rules_cache["rules"] = None
        _rules_cache["read_at"] = 0.0


# =============================================================================
# Resolution
# =============================================================================

def normalise_material(material: str) -> str:
    """
    SAP material codes arrive zero-padded ('000000000013000099').

    Rules are written against the significant digits, so the padding is stripped
    before matching - exactly what the hardcoded classifier did.
    """
    return str(material or "").strip().lstrip("0")


def resolve_order_type(material: str) -> Optional[str]:
    """
    Material code -> 'MILLING' | 'PACKING' | None, via classification_rules.

    Replaces the hardcoded `prefix == "13"` / `"14"` in classify_order.

    Matching is by prefix on the zero-stripped code, so a rule is not limited to
    two characters: '13' and '135' both work, and the more specific one wins if
    it is given a lower priority. A rule with match_value '*' matches anything
    and should carry the highest priority number so it is consulted last.

    Returns None when no rule matches - the caller reports that as an error
    rather than guessing.
    """
    from models.classification_rule import RULE_MATERIAL_PREFIX, WILDCARD

    stripped = normalise_material(material)
    if len(stripped) < 2:
        return None

    for rule in get_rules(RULE_MATERIAL_PREFIX):
        match = rule["match_value"]
        if match == WILDCARD or stripped.startswith(match):
            return rule["result_value"]
    return None


def resolve_department(plant: str) -> Optional[str]:
    """
    Plant code -> 'MILLING' | 'PACKING', via classification_rules.

    ⚠️  NOT WIRED INTO ANYTHING, deliberately. Read this before using it.

    Commit 0 seeded two `plant_department` rules (3130 -> MILLING, * -> PACKING)
    on the assumption that the code derives a department from the plant. It does
    not. Every one of the seven sites in order_validation.py does:

        plant      = get_attr_safe(order, "plant", "3130")     # a DEFAULT plant
        department = "MILLING" if order_type == "MILLING" else "PACKING"

    - department comes from order_type, which comes from the material prefix
    - "3130" is a fallback for orders with no plant, not a routing rule
      (it is now get_default_plant() in routes/order_validation.py)

    And the premise is wrong anyway: `shift_master` holds both MILLING and
    PACKING shifts for plant 3130, so 3130 is not "the milling plant" - it is
    the plant, running two departments. Applying a plant -> department rule
    would reclassify every packing order at 3130 as milling.

    The two seeded rules are therefore deactivated (migrate_a1_classification_rules.py).
    This function stays because the rule type is part of the table's schema and
    the CRUD exposes it: if a second plant is ever added that genuinely runs one
    department, the rule becomes meaningful and this is where it resolves.
    """
    from models.classification_rule import RULE_PLANT_DEPARTMENT, WILDCARD

    value = str(plant or "").strip()
    for rule in get_rules(RULE_PLANT_DEPARTMENT):
        if rule["match_value"] == WILDCARD or rule["match_value"] == value:
            return rule["result_value"]
    return None


# =============================================================================
# Classification  (A3)
# =============================================================================
#
# Moved here from routes/order_validation.py, which now re-exports it. That
# import path is frozen by CONTRACTS.md - routes/scada_routes.py:501 is
# Workstream B's file and imports it from there.
#
# The cache is load-bearing, not an optimisation. The auto-validation worker
# loops roughly once a SECOND per running order (WORKER_WAIT, not the 60s the
# master plan assumed), and every cycle reached this function. Measured before
# the change: 71 scans of palletizer_mapping in 60s for one running PACKING
# order.

CLASSIFICATION_TTL_SECONDS = 45.0

_classify_cache = {}
_classify_lock = threading.Lock()

# Counters, so the cache's effect is measurable without a profiler.
_classify_stats = {"hits": 0, "misses": 0}


def _empty_result(version: str, error: Optional[str] = None) -> Dict[str, Any]:
    """The contract's return shape, with nothing resolved."""
    return {
        "order_type": None,
        "equipment": [],
        "formula": "",
        "version": version,
        "byproduct": {},
        "packing_info": {},
        "error": error,
    }


def classify_order(order: Any) -> Dict[str, Any]:
    """
    Canonical classifier. See CONTRACT above for the required return shape.

    - MILLING: scales, formula and byproduct scale1/2/3 from
      `milling_version_mappings`
    - PACKING: SCADA tag and bag maths from `palletizer_mapping` (A2 moved the
      tag onto the row)

    Results are cached for CLASSIFICATION_TTL_SECONDS, keyed on
    (order_type, version) - nothing else varies the lookup. Mapping writes call
    invalidate_cache(), so an edit in Material Map or Palletizer Mapping takes
    effect on the next order classified rather than after the TTL.

    A copy is returned on every call. Callers pass this dict around and the
    auto-validation worker holds one for the life of its thread, so handing out
    the cached object would let one caller's mutation reach every other.
    """
    material_code = str(getattr(order, "material", "") or "").strip()
    version = str(getattr(order, "version", "") or "").upper().strip()

    # The `version` key of the result has always carried the V-stripped form,
    # on the error paths as well as the successful ones.
    version_clean = version[1:] if (version.startswith("V") and len(version) > 1) else version

    # Cheap, material-specific failures are answered without touching the cache
    # or the database.
    material_stripped = normalise_material(material_code)
    if len(material_stripped) < 2:
        return _empty_result(version_clean, error=f"Invalid material code: {material_code}")

    order_type = resolve_order_type(material_code)
    if not order_type:
        error = (
            f"No classification rule matches material {material_code} "
            f"(prefix '{material_stripped[:2]}'). Add a rule under "
            f"Material Map, or via POST /api/classification/rules."
        )
        log.warning(error)
        return _empty_result(version_clean, error=error)

    # The RAW version is part of the key, not the V-stripped one, so a cached
    # error message still names the version the caller actually passed.
    key = (order_type, version)
    now = time.time()

    with _classify_lock:
        entry = _classify_cache.get(key)
        if entry is not None and (now - entry[0]) < CLASSIFICATION_TTL_SECONDS:
            _classify_stats["hits"] += 1
            return copy.deepcopy(entry[1])
        _classify_stats["misses"] += 1

    result = _classify_uncached(order_type, version)

    with _classify_lock:
        _classify_cache[key] = (now, copy.deepcopy(result))

    return result


def _classify_uncached(order_type: str, version: str) -> Dict[str, Any]:
    """
    The database half. Depends only on (order_type, version), which is what
    makes the cache key correct.
    """
    from database import PostgresSessionLocal

    # Strip a "V" prefix if present ("VBKL1" -> "BKL1"). The "V" means
    # "version"; the code stored in the database is without it.
    version_clean = version
    if version.startswith("V") and len(version) > 1:
        version_clean = version[1:]
        log.debug("Stripped 'V' prefix from version: '%s' -> '%s'", version, version_clean)

    result = _empty_result(version_clean)
    result["order_type"] = order_type

    # =========================================================
    #                        MILLING
    # =========================================================
    if order_type == "MILLING":
        from models.milling_version_mapping import MillingVersionMapping

        if not version_clean:
            result["error"] = "Version is empty or missing for order"
            log.warning(result["error"])
            return result

        try:
            with PostgresSessionLocal() as db:
                mapping = (
                    db.query(MillingVersionMapping)
                      .filter(MillingVersionMapping.version == version_clean)
                      .first()
                )
        except Exception as exc:
            result["error"] = (
                f"Database error querying milling mapping for version "
                f"'{version_clean}' (original: '{version}'): {exc}"
            )
            log.error(result["error"])
            return result

        if not mapping:
            result["error"] = (
                f"No milling mapping found for version '{version_clean}' "
                f"(original: '{version}'). Please add it via /api/milling-mapping"
            )
            log.warning(result["error"])
            return result

        # MAIN SCALE LIST. SQLAlchemy JSON columns should auto-deserialize, but
        # rows written by older code can hold a string.
        scales_raw = mapping.scales
        if scales_raw is None:
            result["equipment"] = []
        elif isinstance(scales_raw, str):
            import json
            try:
                result["equipment"] = json.loads(scales_raw)
            except json.JSONDecodeError:
                result["equipment"] = [s.strip() for s in scales_raw.split(",") if s.strip()]
            log.debug("Parsed scales for %s from a string: %s", version_clean, result["equipment"])
        elif isinstance(scales_raw, list):
            result["equipment"] = scales_raw
        else:
            result["equipment"] = [scales_raw] if scales_raw else []

        result["formula"] = mapping.formula or ""
        result["byproduct"] = {
            "scale1": mapping.scale1,
            "scale2": mapping.scale2,
            "scale3": mapping.scale3,
        }
        return result

    # =========================================================
    #                        PACKING
    # =========================================================
    from models.palletizer_mapping import PalletizerMapping

    try:
        with PostgresSessionLocal() as db:
            mapping = (
                db.query(PalletizerMapping)
                  .filter(PalletizerMapping.version == version_clean)
                  .first()
            )

            if not mapping:
                result["error"] = (
                    f"No palletizer mapping found for version {version_clean} "
                    f"(original: {version})"
                )
                return result

            # A2: the SCADA tag comes from the row, not a hardcoded map. An
            # unmapped line is an error naming the version, instead of an empty
            # equipment list that surfaced later as "No main equipment mapped".
            if not mapping.scada_tag:
                result["error"] = (
                    f"Packing version {version_clean} is mapped to line "
                    f"'{mapping.palletizer}' but that line has no SCADA tag. "
                    f"Set one in Palletizer Mapping."
                )
                log.warning(result["error"])
                return result

            result["equipment"] = [mapping.scada_tag]
            result["formula"] = ""
            result["packing_info"] = {
                # A1: packing_line and bag_size. process_order_pull.py read
                # these off the TOP level of this dict, where they never
                # existed, so both columns were NULL for every order ever
                # pulled and the UI's "Packing Line:" row always rendered blank.
                "packing_line": mapping.palletizer,
                "scada_tag": mapping.scada_tag,

                # A2: correctly-named values. The three below them are the
                # transposed originals, still published because
                # PalletizerMapping.tsx and lib/api.ts read those names.
                "bags_per_pallet_actual": mapping.multiplier(),
                "bag_weight_kg": float(mapping.bag_weight_kg or mapping.kg_per_pallet or 0),
                "bag_size": (
                    str(int(mapping.bag_weight_kg or mapping.kg_per_pallet))
                    if (mapping.bag_weight_kg or mapping.kg_per_pallet) else None
                ),

                "bag_size_kg": float(mapping.bag_size_kg or 0),
                "bags_per_pallet": float(mapping.bags_per_pallet or 0),
                "kg_per_pallet": float(mapping.kg_per_pallet or 0),
                "description": f"{version_clean} → {mapping.palletizer}",
            }
    except Exception as exc:
        log.error("Error querying palletizer mapping for %s (original: %s): %s",
                  version_clean, version, exc)
        result["error"] = f"Database error: {exc}"
        return result

    return result


def invalidate_cache(version: Optional[str] = None) -> None:
    """
    Drop cached classification results.

    Called from the mapping CRUD routes after a write. Without it, an edit in
    Material Map or Palletizer Mapping would not reach running orders for up to
    CLASSIFICATION_TTL_SECONDS.

    Pass a version to drop just that one; pass nothing to drop everything.

    Note: this is the *version -> scales* cache. The *classification rules*
    cache is separate - see invalidate_rules_cache().
    """
    with _classify_lock:
        if version is None:
            _classify_cache.clear()
            return
        wanted = str(version).upper().strip()
        # A version can be cached under both its raw and V-prefixed forms.
        for key in [k for k in _classify_cache if k[1] in (wanted, f"V{wanted}")]:
            _classify_cache.pop(key, None)


def cache_stats() -> Dict[str, Any]:
    """Hit/miss counters and current size. Used by the tests and the debug route."""
    with _classify_lock:
        return {
            "hits": _classify_stats["hits"],
            "misses": _classify_stats["misses"],
            "entries": len(_classify_cache),
            "ttl_seconds": CLASSIFICATION_TTL_SECONDS,
        }


def reset_cache_stats() -> None:
    """Zero the hit/miss counters. Does not drop cached entries."""
    with _classify_lock:
        _classify_stats["hits"] = 0
        _classify_stats["misses"] = 0
