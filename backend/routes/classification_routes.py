# backend/routes/classification_routes.py
"""
Classification rules CRUD - Workstream A.

Commit 0 stub: the blueprint is registered in app.py so the URL prefix is
reserved and nobody has to touch app.py again. Fill in the handlers on
feat/dynamic-order-routing.

Backs the rule editor in Frontend/client/src/pages/hercules-sfms/MaterialMap.tsx.
"""
from flask import Blueprint, jsonify

classification_bp = Blueprint("classification", __name__, url_prefix="/api/classification")


@classification_bp.route("/rules", methods=["GET"])
def list_rules():
    """List classification rules. Workstream A."""
    return jsonify([]), 200


@classification_bp.route("/rules", methods=["POST"])
def create_rule():
    """Create or update a classification rule. Workstream A."""
    return jsonify({"error": "Not implemented"}), 501


@classification_bp.route("/rules/<int:rule_id>", methods=["DELETE"])
def delete_rule(rule_id: int):
    """Delete a classification rule. Workstream A."""
    return jsonify({"error": "Not implemented"}), 501
