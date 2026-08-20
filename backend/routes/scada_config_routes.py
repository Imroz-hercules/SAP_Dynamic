# backend/routes/scada_config_routes.py
"""
SCADA tag registry CRUD - Workstream B.

Commit 0 stub: the blueprint is registered in app.py so the URL prefix is
reserved and nobody has to touch app.py again. Fill in the handlers on
feat/dynamic-plant-config.

Backs the tag list in Frontend/client/src/pages/hercules-sfms/ScadaReadings.tsx
and replaces the hardcoded field lists described in models/scada_tag.py.
"""
from flask import Blueprint, jsonify

scada_config_bp = Blueprint("scada_config", __name__, url_prefix="/api/scada-config")


@scada_config_bp.route("/tags", methods=["GET"])
def list_tags():
    """List SCADA tags, optionally filtered by category. Workstream B."""
    return jsonify([]), 200


@scada_config_bp.route("/tags", methods=["POST"])
def create_tag():
    """Create or update a SCADA tag. Workstream B."""
    return jsonify({"error": "Not implemented"}), 501


@scada_config_bp.route("/tags/<int:tag_id>", methods=["DELETE"])
def delete_tag(tag_id: int):
    """Delete a SCADA tag. Workstream B."""
    return jsonify({"error": "Not implemented"}), 501
