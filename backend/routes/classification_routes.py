# backend/routes/classification_routes.py
"""
Classification rules CRUD - Workstream A (task A1).

The blueprint is registered in app.py, so the URL prefix was reserved in
commit 0 and nobody has to touch app.py again.

Backs the rule editor in Frontend/client/src/pages/hercules-sfms/MaterialMap.tsx
and the `classificationApi` client already written in lib/api.ts.

Every write invalidates the resolver cache in services/classification_service.py,
so a rule change takes effect on the next order classified rather than after the
TTL expires.
"""
from flask import Blueprint, jsonify, request
from sqlalchemy.exc import IntegrityError

from database import PostgresSessionLocal
from models.classification_rule import (
    RULE_MATERIAL_PREFIX,
    RULE_PLANT_DEPARTMENT,
    WILDCARD,
    ClassificationRule,
)
from services.classification_service import invalidate_rules_cache, resolve_order_type

classification_bp = Blueprint("classification", __name__, url_prefix="/api/classification")

VALID_RULE_TYPES = (RULE_MATERIAL_PREFIX, RULE_PLANT_DEPARTMENT)
VALID_RESULTS = ("MILLING", "PACKING")


def _validate(payload):
    """Return (cleaned dict, None) or (None, error message)."""
    if not isinstance(payload, dict):
        return None, "Body must be a JSON object"

    rule_type = str(payload.get("rule_type") or "").strip()
    match_value = str(payload.get("match_value") or "").strip()
    result_value = str(payload.get("result_value") or "").strip().upper()

    if rule_type not in VALID_RULE_TYPES:
        return None, f"rule_type must be one of {', '.join(VALID_RULE_TYPES)}"
    if not match_value:
        return None, "match_value is required"
    if len(match_value) > 32:
        return None, "match_value is limited to 32 characters"
    if result_value not in VALID_RESULTS:
        return None, f"result_value must be one of {', '.join(VALID_RESULTS)}"

    # A material prefix is matched against the zero-stripped code, so a leading
    # zero can never match and is almost certainly a mistake.
    if rule_type == RULE_MATERIAL_PREFIX and match_value != WILDCARD:
        if not match_value.isdigit():
            return None, "match_value for a material prefix must be digits (or '*')"
        if match_value.startswith("0"):
            return None, (
                "match_value cannot start with 0 - material codes are matched "
                "with leading zeros stripped, so it would never match"
            )

    priority = payload.get("priority", 100)
    try:
        priority = int(priority)
    except (TypeError, ValueError):
        return None, "priority must be a whole number"

    is_active = payload.get("is_active", True)
    if not isinstance(is_active, bool):
        return None, "is_active must be true or false"

    description = payload.get("description")
    if description is not None:
        description = str(description)[:255]

    return {
        "rule_type": rule_type,
        "match_value": match_value,
        "result_value": result_value,
        "priority": priority,
        "is_active": is_active,
        "description": description,
    }, None


@classification_bp.route("/rules", methods=["GET"])
def list_rules():
    """
    All rules, in the order the resolver consults them.

    Optional ?rule_type= filter. Inactive rules are included so the editor can
    show and re-enable them; the resolver skips them.
    """
    rule_type = request.args.get("rule_type")
    try:
        with PostgresSessionLocal() as db:
            query = db.query(ClassificationRule)
            if rule_type:
                query = query.filter(ClassificationRule.rule_type == rule_type)
            rows = query.all()

        rules = [r.to_dict() for r in rows]
        rules.sort(key=lambda r: (
            r["rule_type"],
            r["priority"],
            r["match_value"] == WILDCARD,
            r["match_value"],
        ))
        return jsonify(rules), 200
    except Exception as exc:
        return jsonify({"error": f"Could not read classification rules: {exc}"}), 500


@classification_bp.route("/rules", methods=["POST"])
def create_rule():
    """
    Create a rule, or update the existing one with the same
    (rule_type, match_value) - that pair carries a unique constraint.
    """
    cleaned, error = _validate(request.get_json(silent=True))
    if cleaned is None:
        return jsonify({"error": error}), 400

    try:
        with PostgresSessionLocal() as db:
            existing = (
                db.query(ClassificationRule)
                  .filter(
                      ClassificationRule.rule_type == cleaned["rule_type"],
                      ClassificationRule.match_value == cleaned["match_value"],
                  )
                  .first()
            )

            if existing:
                for key, value in cleaned.items():
                    setattr(existing, key, value)
                rule = existing
                created = False
            else:
                rule = ClassificationRule(**cleaned)
                db.add(rule)
                created = True

            db.commit()
            db.refresh(rule)
            payload = rule.to_dict()
    except IntegrityError as exc:
        return jsonify({"error": f"Rule conflicts with an existing one: {exc.orig}"}), 409
    except Exception as exc:
        return jsonify({"error": f"Could not save rule: {exc}"}), 500

    invalidate_rules_cache()
    return jsonify(payload), 201 if created else 200


@classification_bp.route("/rules/<int:rule_id>", methods=["DELETE"])
def delete_rule(rule_id: int):
    """Delete a rule. Deleting the last rule of a type is refused."""
    try:
        with PostgresSessionLocal() as db:
            rule = db.query(ClassificationRule).filter(ClassificationRule.id == rule_id).first()
            if not rule:
                return jsonify({"error": f"No rule with id {rule_id}"}), 404

            remaining = (
                db.query(ClassificationRule)
                  .filter(
                      ClassificationRule.rule_type == rule.rule_type,
                      ClassificationRule.id != rule_id,
                      ClassificationRule.is_active.is_(True),
                  )
                  .count()
            )
            if bool(rule.is_active) and remaining == 0:
                return jsonify({
                    "error": (
                        f"Refusing to delete the last active '{rule.rule_type}' rule - "
                        f"no order could be classified. Add a replacement first."
                    )
                }), 409

            payload = rule.to_dict()
            db.delete(rule)
            db.commit()
    except Exception as exc:
        return jsonify({"error": f"Could not delete rule: {exc}"}), 500

    invalidate_rules_cache()
    return jsonify({"deleted": payload}), 200


@classification_bp.route("/resolve", methods=["GET"])
def resolve():
    """
    What would a material classify as? `?material=000000000013000099`.

    Exists so the rule editor can show the effect of a change without starting
    an order, and so the acceptance test has something to assert against.
    """
    material = request.args.get("material")
    if not material:
        return jsonify({"error": "material is required"}), 400

    from services.classification_service import normalise_material

    order_type = resolve_order_type(material)
    return jsonify({
        "material": material,
        "normalised": normalise_material(material),
        "order_type": order_type,
        "matched": order_type is not None,
    }), 200
