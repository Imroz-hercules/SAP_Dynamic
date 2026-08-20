# backend/services/classification_service.py
"""
Canonical order classification - Workstream A.

This module becomes the single source of truth for "which physical scales does
this order read, and with what formula?".

Today that question has three different answers:
  1. routes/order_validation.py  classify_order()          - reads the DB   (live)
  2. services/shift_live_update.py MILLING_PV_SPECS:12     - hardcoded      (live, every 60s)
  3. services/auto_validator.py  MILLING_PV_MAPPING:60     - hardcoded      (unreachable)

They disagree. See the reconciliation table in the migration plan before
collapsing them - BRF2 in particular resolves to a different physical scale
depending on which one you ask.

CONTRACT (see backend/CONTRACTS.md):
  classify_order(order) must keep returning a dict with the keys
  order_type / equipment / formula / byproduct / packing_info / error,
  and must stay importable from routes.order_validation. Five modules
  import it from there, two of them owned by Workstream B.

STATUS
  A1 (done) - resolve_order_type / resolve_department read `classification_rules`
              instead of hardcoded prefixes.
  A3 (next) - classify_order's body moves here from routes/order_validation.py
              and gains a TTL cache keyed on (order_type, version).
"""
from __future__ import annotations

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
# A3 - not yet implemented
# =============================================================================

def classify_order(order: Any) -> Dict[str, Any]:
    """Canonical classifier. See CONTRACT above for the required return shape."""
    raise NotImplementedError("Workstream A - task A3")


def invalidate_cache(version: Optional[str] = None) -> None:
    """
    Drop cached classification results.

    classify_order runs roughly once per second per running order (the worker
    loop interval, not the 60s originally assumed) and once per order on every
    SAP pull, so it needs a TTL cache to avoid a query per order per second.
    Call this from the mapping CRUD routes after a write, otherwise an edit in
    MaterialMap will not take effect until the TTL expires.

    Note: this is for the *version -> scales* cache, added in A3. The
    *classification rules* cache is separate and already live - see
    invalidate_rules_cache().
    """
    raise NotImplementedError("Workstream A - task A3")
