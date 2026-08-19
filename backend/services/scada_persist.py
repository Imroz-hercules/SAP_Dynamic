# backend/services/scada_persist.py
import logging
from sqlalchemy import text
from database import postgres_engine

SCADA_INSERT_SQL = """
INSERT INTO scada_aggregate_values (
  mode, window_start, window_end,
  VALUE_WG101, VALUE_WG201, VALUE_WG202, VALUE_WG301, VALUE_WG302,
  VALUE_WG501, VALUE_WG502, VALUE_WG503,
  VALUE_DM101, VALUE_DM102, VALUE_DM201, VALUE_DM202, VALUE_DM203,
  VALUE_PL601_TOT
) VALUES (
  :mode, :window_start, :window_end,
  :WG101, :WG201, :WG202, :WG301, :WG302,
  :WG501, :WG502, :WG503,
  :DM101, :DM102, :DM201, :DM202, :DM203,
  :PL601_TOT
)
"""

def persist_scada_latest(aggregated: dict):
    """
    aggregated: dict with numeric entries for WG*, DM*, SL* keys.
    """
    params = {
        "mode": "latest",
        "window_start": None,
        "window_end": None,
        "WG101": float(aggregated.get("WG101", 0) or 0),
        "WG201": float(aggregated.get("WG201", 0) or 0),
        "WG202": float(aggregated.get("WG202", 0) or 0),
        "WG301": float(aggregated.get("WG301", 0) or 0),
        "WG302": float(aggregated.get("WG302", 0) or 0),
        "WG501": float(aggregated.get("WG501", 0) or 0),
        "WG502": float(aggregated.get("WG502", 0) or 0),
        "WG503": float(aggregated.get("WG503", 0) or 0),
        "DM101": float(aggregated.get("DM101", 0) or 0),
        "DM102": float(aggregated.get("DM102", 0) or 0),
        "DM201": float(aggregated.get("DM201", 0) or 0),
        "DM202": float(aggregated.get("DM202", 0) or 0),
        "DM203": float(aggregated.get("DM203", 0) or 0),
        "PL601_TOT": float(aggregated.get("PL601_TOT", 0) or 0),
    }

    try:
        with postgres_engine.begin() as pg:
            pg.execute(text(SCADA_INSERT_SQL), params)
    except Exception as e:
        logging.exception("Persist to scada_aggregate_values failed: %s", e)
