# backend/routes/kpi_config_routes.py
"""
KPI definition CRUD - Workstream B (B4).

Implements /api/kpi-config/definitions against models.kpi_config.KpiConfig.
"""
from flask import Blueprint, jsonify, request
from sqlalchemy.exc import IntegrityError

from database import PostgresSessionLocal
from models.kpi_config import KpiConfig
from services.kpi_config_registry import (
    VALID_DEPARTMENTS,
    invalidate_kpi_config_cache,
)

kpi_config_bp = Blueprint("kpi_config", __name__, url_prefix="/api/kpi-config")


def _as_bool(value, default=True):
    if value is None:
        return default
    if isinstance(value, bool):
        return value
    if isinstance(value, (int, float)):
        return bool(value)
    if isinstance(value, str):
        lowered = value.strip().lower()
        if lowered in ("true", "1", "yes"):
            return True
        if lowered in ("false", "0", "no"):
            return False
    return None


def _validate(payload):
    if not isinstance(payload, dict):
        return None, "Body must be a JSON object"

    kpi_key = str(payload.get("kpi_key") or "").strip()
    display_name = str(payload.get("display_name") or "").strip()
    department = str(payload.get("department") or "").strip().upper()

    if not kpi_key:
        return None, "kpi_key is required"
    if len(kpi_key) > 64:
        return None, "kpi_key is limited to 64 characters"
    if not display_name:
        return None, "display_name is required"
    if len(display_name) > 128:
        return None, "display_name is limited to 128 characters"
    if department not in VALID_DEPARTMENTS:
        return None, f"department must be one of {', '.join(VALID_DEPARTMENTS)}"

    target_column = payload.get("target_column")
    if target_column is not None:
        target_column = str(target_column).strip()[:64] or None

    max_value = payload.get("max_value", None)
    if max_value is not None and max_value != "":
        try:
            max_value = float(max_value)
        except (TypeError, ValueError):
            return None, "max_value must be a number or null"
    else:
        max_value = None

    unit = payload.get("unit")
    if unit is not None:
        unit = str(unit).strip()[:16] or None

    is_active = _as_bool(payload.get("is_active"), True)
    if is_active is None:
        return None, "is_active must be true or false"

    sort_order = payload.get("sort_order", 0)
    try:
        sort_order = int(sort_order)
    except (TypeError, ValueError):
        return None, "sort_order must be a whole number"

    cleaned = {
        "kpi_key": kpi_key,
        "display_name": display_name,
        "department": department,
        "target_column": target_column,
        "max_value": max_value,
        "unit": unit,
        "is_active": is_active,
        "sort_order": sort_order,
    }
    if payload.get("id") is not None:
        try:
            cleaned["id"] = int(payload["id"])
        except (TypeError, ValueError):
            return None, "id must be a whole number"
    return cleaned, None


@kpi_config_bp.route("/definitions", methods=["GET"])
def list_definitions():
    department = request.args.get("department")
    if department:
        department = department.strip().upper()
        if department not in VALID_DEPARTMENTS:
            return jsonify({
                "error": f"department must be one of {', '.join(VALID_DEPARTMENTS)}"
            }), 400
    try:
        with PostgresSessionLocal() as db:
            query = db.query(KpiConfig)
            if department:
                query = query.filter(KpiConfig.department == department)
            rows = query.order_by(KpiConfig.sort_order, KpiConfig.kpi_key).all()
            return jsonify([r.to_dict() for r in rows]), 200
    except Exception as exc:
        return jsonify({"error": f"Could not read KPI definitions: {exc}"}), 500


@kpi_config_bp.route("/definitions", methods=["POST"])
def upsert_definition():
    cleaned, error = _validate(request.get_json(silent=True))
    if cleaned is None:
        return jsonify({"error": error}), 400

    try:
        with PostgresSessionLocal() as db:
            existing = None
            if "id" in cleaned:
                existing = db.query(KpiConfig).filter(KpiConfig.id == cleaned["id"]).first()
            if existing is None:
                existing = (
                    db.query(KpiConfig)
                    .filter(KpiConfig.kpi_key == cleaned["kpi_key"])
                    .first()
                )

            fields = {k: v for k, v in cleaned.items() if k != "id"}
            if existing:
                for key, value in fields.items():
                    setattr(existing, key, value)
                row = existing
                created = False
            else:
                row = KpiConfig(**fields)
                db.add(row)
                created = True

            db.commit()
            db.refresh(row)
            payload = row.to_dict()
    except IntegrityError as exc:
        return jsonify({"error": f"Definition conflicts: {exc.orig}"}), 409
    except Exception as exc:
        return jsonify({"error": f"Could not save definition: {exc}"}), 500

    invalidate_kpi_config_cache()
    return jsonify({
        "success": True,
        "message": "created" if created else "updated",
        **payload,
    }), 201 if created else 200


@kpi_config_bp.route("/definitions/<int:config_id>", methods=["DELETE"])
def delete_definition(config_id: int):
    try:
        with PostgresSessionLocal() as db:
            row = db.query(KpiConfig).filter(KpiConfig.id == config_id).first()
            if not row:
                return jsonify({"error": f"No definition with id {config_id}"}), 404
            payload = row.to_dict()
            db.delete(row)
            db.commit()
    except Exception as exc:
        return jsonify({"error": f"Could not delete definition: {exc}"}), 500

    invalidate_kpi_config_cache()
    return jsonify({"success": True, "message": "deleted", "deleted": payload}), 200
