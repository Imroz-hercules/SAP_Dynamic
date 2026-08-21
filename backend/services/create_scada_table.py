# backend/services/create_scada_table.py
"""
Create scada_aggregate_values and ensure VALUE_* columns for registry tags.

Workstream B8: base table is created with the historical core columns; then
ensure_value_columns() adds any active+pollable tags from scada_tags (including
PL602_TOT / PL603_TOT / SL606_TOT / SL607_TOT that used to be dropped).
"""
from sqlalchemy import text
from database import postgres_engine

SCADA_CREATE_TABLE_SQL = """
CREATE TABLE IF NOT EXISTS scada_aggregate_values (
    id SERIAL PRIMARY KEY,
    mode VARCHAR(50) NOT NULL,
    window_start TIMESTAMP,
    window_end TIMESTAMP,
    VALUE_WG101 FLOAT,
    VALUE_WG201 FLOAT,
    VALUE_WG202 FLOAT,
    VALUE_WG301 FLOAT,
    VALUE_WG302 FLOAT,
    VALUE_WG501 FLOAT,
    VALUE_WG502 FLOAT,
    VALUE_WG503 FLOAT,
    VALUE_DM101 FLOAT,
    VALUE_DM102 FLOAT,
    VALUE_DM201 FLOAT,
    VALUE_DM202 FLOAT,
    VALUE_DM203 FLOAT,
    VALUE_PL601_TOT FLOAT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
)
"""


def create_scada_schema():
    """
    Creates the scada_aggregate_values table in Postgres if it doesn't exist,
    then adds VALUE_* columns for every registry poll tag.
    Safe to call multiple times.
    """
    try:
        with postgres_engine.begin() as pg:
            pg.execute(text(SCADA_CREATE_TABLE_SQL))
        try:
            from services.scada_persist import ensure_value_columns, _persist_tags
            ensure_value_columns(_persist_tags())
        except Exception as e:
            print(f"Warning: could not extend SCADA columns from registry: {e}")
        print("SCADA table schema created/verified successfully")
    except Exception as e:
        print(f"Error creating SCADA table schema: {e}")
        raise
