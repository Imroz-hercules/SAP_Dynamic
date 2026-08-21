# backend/services/scada_persist.py
"""
Persist latest SCADA poll into scada_aggregate_values.

Workstream B8: column set is driven by the scada_tags registry (active +
pollable). Missing VALUE_* columns are added on the fly so tags that used to
be collected and silently dropped (PL602_TOT, PL603_TOT, SL606_TOT, SL607_TOT,
and any later registry additions) actually land in Postgres.
"""
import logging
import re
from sqlalchemy import text
from database import postgres_engine

log = logging.getLogger("scada_persist")

_SAFE_TAG = re.compile(r"^[A-Za-z][A-Za-z0-9_]*$")


def _persist_tags():
    try:
        from services.scada_tag_registry import poll_keys
        keys = poll_keys()
        if keys:
            return keys
    except Exception as exc:
        log.warning("registry unavailable for persist tags: %s", exc)
    # Bootstrap matching the historical INSERT (pre-B8)
    return [
        "WG101", "WG201", "WG202", "WG301", "WG302",
        "WG501", "WG502", "WG503",
        "DM101", "DM102", "DM201", "DM202", "DM203",
        "PL601_TOT", "PL602_TOT", "PL603_TOT",
        "SL606_TOT", "SL607_TOT",
    ]


def _column_name(tag: str) -> str:
    return f"VALUE_{tag}"


def ensure_value_columns(tags) -> None:
    """ADD COLUMN IF NOT EXISTS for each tag's VALUE_* column."""
    if postgres_engine is None:
        return
    with postgres_engine.begin() as pg:
        for tag in tags:
            if not _SAFE_TAG.match(tag):
                log.warning("Skipping unsafe SCADA tag for DDL: %r", tag)
                continue
            col = _column_name(tag)
            pg.execute(text(
                f'ALTER TABLE scada_aggregate_values '
                f'ADD COLUMN IF NOT EXISTS "{col}" DOUBLE PRECISION'
            ))


def persist_scada_latest(aggregated: dict):
    """
    aggregated: dict with numeric entries keyed by logical tag (WG501, PL601_TOT, …).
    """
    if postgres_engine is None:
        log.warning("PostgreSQL engine not configured; skipping SCADA insert.")
        return

    tags = [t for t in _persist_tags() if _SAFE_TAG.match(t)]
    if not tags:
        log.warning("No SCADA tags to persist.")
        return

    try:
        ensure_value_columns(tags)
    except Exception as e:
        log.exception("Could not ensure scada_aggregate_values columns: %s", e)
        return

    cols = ["mode", "window_start", "window_end"] + [_column_name(t) for t in tags]
    placeholders = [":mode", ":window_start", ":window_end"] + [f":{t}" for t in tags]
    sql = (
        "INSERT INTO scada_aggregate_values ("
        + ", ".join(f'"{c}"' if c.startswith("VALUE_") else c for c in cols)
        + ") VALUES ("
        + ", ".join(placeholders)
        + ")"
    )

    params = {
        "mode": "latest",
        "window_start": None,
        "window_end": None,
    }
    for tag in tags:
        try:
            params[tag] = float(aggregated.get(tag, 0) or 0)
        except (TypeError, ValueError):
            params[tag] = 0.0

    try:
        with postgres_engine.begin() as pg:
            pg.execute(text(sql), params)
    except Exception as e:
        logging.exception("Persist to scada_aggregate_values failed: %s", e)
