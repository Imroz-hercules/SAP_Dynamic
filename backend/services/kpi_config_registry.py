# backend/services/kpi_config_registry.py
"""
KPI definition registry — Workstream B (B4).

Reads kpi_config for ceilings and display-name → column maps.
"""
from __future__ import annotations

import logging
import threading
import time
from typing import Any, Dict, List, Optional

log = logging.getLogger("kpi_config_registry")

REGISTRY_TTL_SECONDS = 30.0

_cache: Dict[str, Any] = {"rows": None, "read_at": 0.0}
_lock = threading.Lock()

# Bootstrap matching setup_sap_postgres.sql seed (100% caps — matches live code, not the 150% docs).
_BOOTSTRAP: List[Dict[str, Any]] = [
    {"kpi_key": "mill_throughput_pct", "display_name": "Mill Throughput (%)", "department": "MILLING",
     "target_column": "mill_throughput_pct", "max_value": 100.0, "unit": "%", "is_active": True, "sort_order": 10},
    {"kpi_key": "mill_time_efficiency_pct", "display_name": "Mill Time Efficiency (%)", "department": "MILLING",
     "target_column": "mill_time_efficiency_pct", "max_value": 100.0, "unit": "%", "is_active": True, "sort_order": 11},
    {"kpi_key": "total_utilization_pct", "display_name": "Total Utilization (%)", "department": "MILLING",
     "target_column": "total_utilization_pct", "max_value": 100.0, "unit": "%", "is_active": True, "sort_order": 12},
    {"kpi_key": "milling_gain_pct", "display_name": "Milling Gain (%)", "department": "MILLING",
     "target_column": "milling_gain_pct", "max_value": 120.0, "unit": "%", "is_active": True, "sort_order": 13},
    {"kpi_key": "milling_screening_pct", "display_name": "Milling Screening (%)", "department": "MILLING",
     "target_column": "milling_screening_pct", "max_value": 20.0, "unit": "%", "is_active": True, "sort_order": 14},
    {"kpi_key": "flour_extraction_pct", "display_name": "Flour Extraction (%)", "department": "MILLING",
     "target_column": "flour_extraction_pct", "max_value": 85.0, "unit": "%", "is_active": True, "sort_order": 15},
    {"kpi_key": "bran_extraction_pct", "display_name": "Bran Extraction (%)", "department": "MILLING",
     "target_column": "bran_extraction_pct", "max_value": 25.0, "unit": "%", "is_active": True, "sort_order": 16},
    {"kpi_key": "milling_loss_pct", "display_name": "Milling Loss (%)", "department": "MILLING",
     "target_column": "milling_loss_pct", "max_value": None, "unit": "%", "is_active": True, "sort_order": 17},
    {"kpi_key": "water_consumption_m3", "display_name": "Water Consumption (m3)", "department": "MILLING",
     "target_column": "water_consumption_m3", "max_value": None, "unit": "m3", "is_active": True, "sort_order": 18},
    {"kpi_key": "milling_net_hours_hrs", "display_name": "Net Hours (hrs)", "department": "MILLING",
     "target_column": "net_hours_hrs", "max_value": None, "unit": "hrs", "is_active": True, "sort_order": 19},
    {"kpi_key": "milling_downtime_hrs", "display_name": "Downtime (hrs)", "department": "MILLING",
     "target_column": "downtime_hrs", "max_value": None, "unit": "hrs", "is_active": True, "sort_order": 20},
    {"kpi_key": "max_utilization_milling_capacity_pct", "display_name": "Max Utilization of Milling Capacity (%)",
     "department": "MILLING", "target_column": None, "max_value": 100.0, "unit": "%", "is_active": True, "sort_order": 21},
    {"kpi_key": "pre_cleaning_screening_pct", "display_name": "Pre Cleaning Screening (%)", "department": "MILLING",
     "target_column": None, "max_value": 20.0, "unit": "%", "is_active": True, "sort_order": 22},
    {"kpi_key": "first_break_capacity_tph", "display_name": "1st Break Capacity per Hour (t/h)", "department": "MILLING",
     "target_column": None, "max_value": 30.0, "unit": "t/h", "is_active": True, "sort_order": 23},
    {"kpi_key": "packing_line_capacity_bags_hr", "display_name": "Packing Line Capacity (bags/hr)", "department": "PACKING",
     "target_column": "packing_line_capacity_bags_hr", "max_value": 2000.0, "unit": "bags/hr", "is_active": True, "sort_order": 30},
    {"kpi_key": "daily_packing_output_bags", "display_name": "Daily Packing Output (bags)", "department": "PACKING",
     "target_column": "daily_packing_output_bags", "max_value": 100000.0, "unit": "bags", "is_active": True, "sort_order": 31},
    {"kpi_key": "machine_utilization_pct", "display_name": "Machine Utilization (%)", "department": "PACKING",
     "target_column": "machine_utilization_pct", "max_value": 100.0, "unit": "%", "is_active": True, "sort_order": 32},
    {"kpi_key": "packing_net_hours_hrs", "display_name": "Net Hours (hrs)", "department": "PACKING",
     "target_column": "net_hours_hrs", "max_value": None, "unit": "hrs", "is_active": True, "sort_order": 33},
    {"kpi_key": "packing_downtime_hrs", "display_name": "Downtime (hrs)", "department": "PACKING",
     "target_column": "downtime_hrs", "max_value": None, "unit": "hrs", "is_active": True, "sort_order": 34},
]

VALID_DEPARTMENTS = ("MILLING", "PACKING")


def invalidate_kpi_config_cache() -> None:
    with _lock:
        _cache["rows"] = None
        _cache["read_at"] = 0.0


def _load_from_db() -> Optional[List[Dict[str, Any]]]:
    try:
        from database import PostgresSessionLocal
        from models.kpi_config import KpiConfig

        with PostgresSessionLocal() as db:
            rows = db.query(KpiConfig).order_by(KpiConfig.sort_order, KpiConfig.kpi_key).all()
            if not rows:
                return None
            return [r.to_dict() for r in rows]
    except Exception as exc:
        log.warning("kpi_config load failed, using bootstrap: %s", exc)
        return None


def get_all_definitions(*, force: bool = False) -> List[Dict[str, Any]]:
    now = time.time()
    with _lock:
        if (
            not force
            and _cache["rows"] is not None
            and (now - float(_cache["read_at"])) < REGISTRY_TTL_SECONDS
        ):
            return list(_cache["rows"])

    rows = _load_from_db()
    if rows is None:
        rows = [dict(r) for r in _BOOTSTRAP]

    with _lock:
        _cache["rows"] = rows
        _cache["read_at"] = time.time()
    return list(rows)


def list_definitions(
    *,
    department: Optional[str] = None,
    active_only: bool = False,
) -> List[Dict[str, Any]]:
    rows = get_all_definitions()
    out = []
    for row in rows:
        if department and row.get("department") != department:
            continue
        if active_only and not row.get("is_active"):
            continue
        out.append(row)
    return out


def get_by_key(kpi_key: str) -> Optional[Dict[str, Any]]:
    for row in get_all_definitions():
        if row.get("kpi_key") == kpi_key:
            return row
    return None


def get_max_value(kpi_key: str) -> Optional[float]:
    row = get_by_key(kpi_key)
    if not row or not row.get("is_active"):
        return None
    value = row.get("max_value")
    if value is None:
        return None
    try:
        return float(value)
    except (TypeError, ValueError):
        return None


def clamp(kpi_key: str, value: float) -> float:
    """Apply registry ceiling when set; otherwise return value unchanged."""
    ceiling = get_max_value(kpi_key)
    if ceiling is None:
        return value
    return min(float(value), ceiling)


def get_nameplate_tph() -> float:
    try:
        from models.system_settings import get_setting
        value = get_setting("mill_nameplate_tph", 25.0)
        return float(value if value is not None else 25.0)
    except Exception:
        return 25.0


def display_to_column_map(department: str) -> Dict[str, str]:
    """
    Build MILLING_MAP / PACKING_MAP shape: display_name -> target_column.
    Also accepts the historical m³ spelling for water.
    """
    mapping: Dict[str, str] = {}
    for row in list_definitions(department=department, active_only=True):
        col = row.get("target_column")
        name = row.get("display_name")
        if col and name:
            mapping[name] = col
            # Historical alias in kpi_store_flat
            if name == "Water Consumption (m3)":
                mapping["Water Consumption (m³)"] = col
    return mapping
