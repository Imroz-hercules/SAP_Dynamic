# backend/services/baseline_guard.py
"""
Baseline column guard — Workstream A, task A7.

Production in this system is a delta:

    production = current SCADA reading − baseline captured when the order started

Baselines live in a fixed set of ``baseline_*`` columns on ``process_orders``,
so a scale tag only *has* a baseline if a column exists for it.

Before this module the lookup was::

    float(get_attr_safe(order, f"baseline_{tag.lower()}", 0.0) or 0.0)

``get_attr_safe`` swallows the ``AttributeError``, so a tag with no column
returned ``0.0`` — indistinguishable from "baseline not captured yet". The
delta then becomes ``current − 0``, i.e. the scale's entire lifetime counter,
and that number flows through ``calculate_deltas`` → ``per_tag_delta`` →
``evaluate_formula_using_deltas`` → ``confirmed_qty`` → the SAP payload.

This module makes the three cases distinguishable:

===========================  ==========================================
column exists, value NULL    ``0.0`` — legitimate, not yet captured
column exists, has a value   that value
no column for the tag        ``UnmappedTagError``
===========================  ==========================================

Callers turn the exception into a halted order plus an operator-visible row in
``error_log``, instead of a silently wrong number reaching SAP.

The column set is derived from ``ProcessOrderPG`` rather than hardcoded, so it
stays correct if a migration adds or removes a baseline column.
"""

import logging
import threading

log = logging.getLogger(__name__)

BASELINE_PREFIX = "baseline_"

# ``baseline_*`` columns that are not per-tag values and must never be treated
# as one. The three ``_start`` columns hold a JSON snapshot of every tag's
# baseline at shift start; ``fixed_flags`` records which tags are pinned.
_NON_TAG_BASELINE_COLUMNS = frozenset({
    "baseline_fixed_flags",
    "baseline_shift_a_start",
    "baseline_shift_b_start",
    "baseline_shift_c_start",
})

_columns_cache = None
_columns_lock = threading.Lock()

_reported = set()
_reported_lock = threading.Lock()


class UnmappedTagError(RuntimeError):
    """
    A scale tag has no baseline on this order.

    Raised instead of returning a zero baseline, which would make the delta the
    scale's whole lifetime counter.
    """

    def __init__(self, tag, po_number=None, reason=None):
        self.tag = str(tag or "").upper()
        self.po_number = po_number
        self.reason = reason or (
            f"scale tag '{self.tag}' has no baseline column on process_orders"
        )
        super().__init__(self.operator_message())

    def operator_message(self):
        """One sentence an operator can act on, safe to show in the UI."""
        where = f"Order {self.po_number}: " if self.po_number else ""
        return (
            f"{where}{self.reason}. Production for this order cannot be "
            f"calculated — without a baseline the delta would be the scale's "
            f"entire lifetime counter, not this order's output. Either correct "
            f"the version mapping so it uses a scale that has a baseline, or "
            f"restart the order so a fresh baseline is captured for '{self.tag}'."
        )


def baseline_columns():
    """
    The per-tag ``baseline_*`` column names, read off the model once and cached.

    Derived rather than hardcoded so a migration that adds a column is picked up
    without editing this file.
    """
    global _columns_cache
    if _columns_cache is None:
        with _columns_lock:
            if _columns_cache is None:
                from models.process_order_pg import ProcessOrderPG

                _columns_cache = frozenset(
                    c.name
                    for c in ProcessOrderPG.__table__.columns
                    if c.name.startswith(BASELINE_PREFIX)
                    and c.name not in _NON_TAG_BASELINE_COLUMNS
                )
    return _columns_cache


def baseline_column_for(tag):
    """Column name backing ``tag``, or ``None`` when the tag has no column."""
    name = f"{BASELINE_PREFIX}{str(tag or '').strip().lower()}"
    return name if name in baseline_columns() else None


def has_baseline_column(tag):
    """True when ``tag`` has a ``baseline_*`` column of its own."""
    return baseline_column_for(tag) is not None


def read_baseline_column(order, tag, po_number=None, reason=None):
    """
    Read ``tag``'s baseline off ``order``.

    Returns ``0.0`` when the column exists but is NULL — that is a real state,
    meaning the baseline has not been captured yet.

    Raises ``UnmappedTagError`` when no column backs the tag at all.
    """
    column = baseline_column_for(tag)
    if column is None:
        raise UnmappedTagError(tag, po_number=po_number, reason=reason)
    return float(getattr(order, column, None) or 0.0)


def report_unmapped_tag(error, source, extra=None):
    """
    Put an ``UnmappedTagError`` in front of an operator.

    Writes to ``error_log``, which ProcessOrderValidation.tsx already polls and
    counts, so the failure shows up in the UI rather than only in stdout.

    Deduped per ``(po_number, tag, source)`` for the life of the process: the
    auto-validation worker ticks once a second and would otherwise write a row
    per second until someone noticed.

    Returns True when this call actually reported, False when it was a repeat.
    """
    key = (error.po_number, error.tag, source)
    with _reported_lock:
        if key in _reported:
            return False
        _reported.add(key)

    log.error("%s [source=%s]", error.operator_message(), source)
    try:
        from services.error_logger import log_order_error

        payload = {
            "tag": error.tag,
            "known_baseline_columns": sorted(baseline_columns()),
        }
        if extra:
            payload.update(extra)

        log_order_error(
            po_number=error.po_number or "",
            error_type="configuration_error",
            error_message=error.operator_message(),
            payload=payload,
            source=source,
        )
    except Exception as exc:  # never let logging break the caller
        log.exception("Failed to write unmapped-tag error to error_log: %s", exc)
    return True


def clear_reported(po_number=None):
    """
    Forget dedupe state so a later recurrence reports again.

    Call after a mapping is corrected. With no argument, clears everything.
    """
    with _reported_lock:
        if po_number is None:
            _reported.clear()
            return
        for key in [k for k in _reported if k[0] == po_number]:
            _reported.discard(key)
