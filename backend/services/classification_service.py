# backend/services/classification_service.py
"""
Canonical order classification - Workstream A.

Commit 0 stub. This module becomes the single source of truth for
"which physical scales does this order read, and with what formula?".

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
"""
from __future__ import annotations

from typing import Any, Dict, Optional


def resolve_order_type(material: str) -> Optional[str]:
    """Material code -> 'MILLING' | 'PACKING' | None, via classification_rules."""
    raise NotImplementedError("Workstream A")


def resolve_department(plant: str) -> Optional[str]:
    """Plant code -> 'MILLING' | 'PACKING', via classification_rules."""
    raise NotImplementedError("Workstream A")


def classify_order(order: Any) -> Dict[str, Any]:
    """Canonical classifier. See CONTRACT above for the required return shape."""
    raise NotImplementedError("Workstream A")


def invalidate_cache(version: Optional[str] = None) -> None:
    """
    Drop cached classification results.

    classify_order runs once per order per worker cycle (60s) and once per order
    on every SAP pull, so it needs a TTL cache to avoid adding a query per order
    per minute. Call this from the mapping CRUD routes after a write, otherwise
    an edit in MaterialMap will not take effect until the TTL expires.
    """
    raise NotImplementedError("Workstream A")
