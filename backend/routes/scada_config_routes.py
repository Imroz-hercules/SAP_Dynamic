# backend/routes/scada_config_routes.py
"""
SCADA tag registry CRUD - Workstream B (B1).

Implements /api/scada-config/tags against models.scada_tag.ScadaTag.
Every write invalidates the registry cache and refreshes consumer lists in
scale_service / embedded_emulator / app_scheduler.
"""
from flask import Blueprint, jsonify, request
from sqlalchemy.exc import IntegrityError

from database import PostgresSessionLocal
from models.scada_tag import ScadaTag
from services.scada_tag_registry import (
    VALID_CATEGORIES,
    VALID_READING_TYPES,
    invalidate_registry_cache,
    refresh_consumer_lists,
)

scada_config_bp = Blueprint("scada_config", __name__, url_prefix="/api/scada-config")


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
    """Return (cleaned dict, None) or (None, error message)."""
    if not isinstance(payload, dict):
        return None, "Body must be a JSON object"

    tag = str(payload.get("tag") or "").strip()
    category = str(payload.get("category") or "").strip().upper()
    reading_type = str(payload.get("reading_type") or "").strip().lower()

    if not tag:
        return None, "tag is required"
    if len(tag) > 50:
        return None, "tag is limited to 50 characters"
    if category not in VALID_CATEGORIES:
        return None, f"category must be one of {', '.join(VALID_CATEGORIES)}"
    if reading_type not in VALID_READING_TYPES:
        return None, f"reading_type must be one of {', '.join(VALID_READING_TYPES)}"

    source_column = payload.get("source_column")
    if source_column is not None:
        source_column = str(source_column).strip()[:64] or None
    else:
        source_column = tag

    rollover_max = payload.get("rollover_max", None)
    if rollover_max is not None and rollover_max != "":
        try:
            rollover_max = float(rollover_max)
            if rollover_max <= 0:
                return None, "rollover_max must be positive when set"
        except (TypeError, ValueError):
            return None, "rollover_max must be a number or null"
    else:
        rollover_max = None

    unit = payload.get("unit")
    if unit is not None:
        unit = str(unit).strip()[:16] or None

    is_pollable = _as_bool(payload.get("is_pollable"), True)
    if is_pollable is None:
        return None, "is_pollable must be true or false"

    is_active = _as_bool(payload.get("is_active"), True)
    if is_active is None:
        return None, "is_active must be true or false"

    emulator_seed = payload.get("emulator_seed", 0)
    try:
        emulator_seed = float(emulator_seed if emulator_seed is not None else 0)
    except (TypeError, ValueError):
        return None, "emulator_seed must be a number"

    display_name = payload.get("display_name")
    if display_name is not None:
        display_name = str(display_name).strip()[:100] or None

    sort_order = payload.get("sort_order", 0)
    try:
        sort_order = int(sort_order)
    except (TypeError, ValueError):
        return None, "sort_order must be a whole number"

    cleaned = {
        "tag": tag,
        "category": category,
        "reading_type": reading_type,
        "source_column": source_column,
        "rollover_max": rollover_max,
        "unit": unit,
        "is_pollable": is_pollable,
        "is_active": is_active,
        "emulator_seed": emulator_seed,
        "display_name": display_name,
        "sort_order": sort_order,
    }

    # Optional id for upsert-by-id (also accepted via unique tag match).
    if payload.get("id") is not None:
        try:
            cleaned["id"] = int(payload["id"])
        except (TypeError, ValueError):
            return None, "id must be a whole number"

    return cleaned, None


def _after_write():
    invalidate_registry_cache()
    refresh_consumer_lists()


@scada_config_bp.route("/tags", methods=["GET"])
def list_tags():
    """
    List SCADA tags. Optional ?category= filter.
    Inactive tags are included so the editor can re-enable them.
    """
    category = request.args.get("category")
    if category:
        category = category.strip().upper()
        if category not in VALID_CATEGORIES:
            return jsonify({
                "error": f"category must be one of {', '.join(VALID_CATEGORIES)}"
            }), 400

    try:
        with PostgresSessionLocal() as db:
            query = db.query(ScadaTag)
            if category:
                query = query.filter(ScadaTag.category == category)
            rows = query.order_by(ScadaTag.sort_order, ScadaTag.tag).all()
            return jsonify([r.to_dict() for r in rows]), 200
    except Exception as exc:
        return jsonify({"error": f"Could not read SCADA tags: {exc}"}), 500


@scada_config_bp.route("/tags", methods=["POST"])
def create_or_update_tag():
    """Create or update a SCADA tag (upsert by id or unique tag name)."""
    cleaned, error = _validate(request.get_json(silent=True))
    if cleaned is None:
        return jsonify({"error": error}), 400

    try:
        with PostgresSessionLocal() as db:
            existing = None
            if "id" in cleaned:
                existing = db.query(ScadaTag).filter(ScadaTag.id == cleaned["id"]).first()
            if existing is None:
                existing = db.query(ScadaTag).filter(ScadaTag.tag == cleaned["tag"]).first()

            fields = {k: v for k, v in cleaned.items() if k != "id"}

            if existing:
                # Tag rename must stay unique
                if fields["tag"] != existing.tag:
                    clash = (
                        db.query(ScadaTag)
                        .filter(ScadaTag.tag == fields["tag"], ScadaTag.id != existing.id)
                        .first()
                    )
                    if clash:
                        return jsonify({"error": f"tag '{fields['tag']}' already exists"}), 409
                for key, value in fields.items():
                    setattr(existing, key, value)
                row = existing
                created = False
            else:
                row = ScadaTag(**fields)
                db.add(row)
                created = True

            db.commit()
            db.refresh(row)
            payload = row.to_dict()
    except IntegrityError as exc:
        return jsonify({"error": f"Tag conflicts with an existing one: {exc.orig}"}), 409
    except Exception as exc:
        return jsonify({"error": f"Could not save tag: {exc}"}), 500

    _after_write()
    return jsonify({"success": True, "message": "created" if created else "updated", **payload}), (
        201 if created else 200
    )


@scada_config_bp.route("/tags/<int:tag_id>", methods=["DELETE"])
def delete_tag(tag_id: int):
    """Delete a SCADA tag by id."""
    try:
        with PostgresSessionLocal() as db:
            row = db.query(ScadaTag).filter(ScadaTag.id == tag_id).first()
            if not row:
                return jsonify({"error": f"No tag with id {tag_id}"}), 404
            payload = row.to_dict()
            db.delete(row)
            db.commit()
    except Exception as exc:
        return jsonify({"error": f"Could not delete tag: {exc}"}), 500

    _after_write()
    return jsonify({"success": True, "message": "deleted", "deleted": payload}), 200
