# backend/routes/kpi_config_routes.py
"""
KPI definition CRUD - Workstream B.

Commit 0 stub: the blueprint is registered in app.py so the URL prefix is
reserved and nobody has to touch app.py again. Fill in the handlers on
feat/dynamic-plant-config.

Backs the limits editor in
Frontend/client/src/pages/hercules-sfms/KpiCalculations.tsx.
"""
from flask import Blueprint, jsonify

kpi_config_bp = Blueprint("kpi_config", __name__, url_prefix="/api/kpi-config")


@kpi_config_bp.route("/definitions", methods=["GET"])
def list_definitions():
    """List KPI definitions and their ceilings. Workstream B."""
    return jsonify([]), 200


@kpi_config_bp.route("/definitions", methods=["POST"])
def upsert_definition():
    """Create or update a KPI definition. Workstream B."""
    return jsonify({"error": "Not implemented"}), 501


@kpi_config_bp.route("/definitions/<int:config_id>", methods=["DELETE"])
def delete_definition(config_id: int):
    """Delete a KPI definition. Workstream B."""
    return jsonify({"error": "Not implemented"}), 501
