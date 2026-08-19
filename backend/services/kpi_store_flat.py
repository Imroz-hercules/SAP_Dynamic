# backend/services/kpi_store_split.py
from database import postgres_engine
from sqlalchemy import text

# Map API keys -> model columns (simplified based on core KPIs)
MILLING_MAP = {
    "Mill Throughput (%)":          "mill_throughput_pct",
    "Mill Time Efficiency (%)":     "mill_time_efficiency_pct",
    "Total Utilization (%)":        "total_utilization_pct",
    "Milling Gain (%)":             "milling_gain_pct",
    "Milling Screening (%)":        "milling_screening_pct",
    "Water Consumption (m³)":       "water_consumption_m3",
    "Flour Extraction (%)":         "flour_extraction_pct",
    "Bran Extraction (%)":          "bran_extraction_pct",
    "Milling Loss (%)":             "milling_loss_pct",
    "Net Hours (hrs)":              "net_hours_hrs",
    "Downtime (hrs)":               "downtime_hrs",
}

PACKING_MAP = {
    "Daily Packing Output (bags)":     "daily_packing_output_bags",
    "Downtime (hrs)":                  "downtime_hrs",
    "Machine Utilization (%)":         "machine_utilization_pct",
    "Net Hours (hrs)":                 "net_hours_hrs",
    "Packing Line Capacity (bags/hr)": "packing_line_capacity_bags_hr",
}

def _build_insert(table: str, cols: list):
    placeholders = ", ".join(["%s"] * len(cols))
    columns = ", ".join(cols)
    return f"INSERT INTO {table} ({columns}) VALUES ({placeholders})"

def store_split_tables(payload: dict, mode: str = "latest"):
    milling = payload.get("milling_kpis", {}) or {}
    packing = payload.get("packing_kpis", {}) or {}

    # Milling row
    milling_cols = ["mode"]
    milling_vals = [mode]
    for k, col in MILLING_MAP.items():
        milling_cols.append(col)
        milling_vals.append(milling.get(k))

    # Packing row
    packing_cols = []
    packing_vals = []
    for k, col in PACKING_MAP.items():
        packing_cols.append(col)
        packing_vals.append(packing.get(k))

    sql_milling = _build_insert("milling_kpi_snapshots", milling_cols)
    sql_packing = _build_insert("packing_kpi_snapshots", packing_cols)

    with postgres_engine.begin() as pg:
        pg.exec_driver_sql(sql_milling, tuple(milling_vals))
        pg.exec_driver_sql(sql_packing, tuple(packing_vals))
