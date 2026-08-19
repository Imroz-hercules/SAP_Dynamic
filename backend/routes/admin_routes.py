# backend/routes/admin_routes.py
"""Admin-only API routes (e.g. user activity log)."""
from flask import Blueprint, jsonify, request
from datetime import datetime
import logging

from services.system_logger import system_logger
from services.auth_service import require_admin

log = logging.getLogger(__name__)

admin_bp = Blueprint("admin", __name__, url_prefix="/api/admin")


@admin_bp.route("/activity-log", methods=["GET"])
@require_admin
def get_activity_log():
    """
    Get operator activity log (admin only).
    Returns system_logs where source='Operator' (priority change, validate, reject, pause, sync).

    Query Parameters:
        - limit: Max number of logs (default: 200)
        - offset: Number to skip (default: 0)
        - operator: Filter by operator username
        - start_date: ISO format
        - end_date: ISO format
    """
    try:
        limit = int(request.args.get('limit', 200))
        offset = int(request.args.get('offset', 0))
        operator_filter = request.args.get('operator')
        start_date = None
        end_date = None

        if request.args.get('start_date'):
            try:
                start_date = datetime.fromisoformat(
                    request.args.get('start_date').replace('Z', '+00:00')
                )
            except ValueError:
                return jsonify({
                    "ok": False,
                    "message": "Invalid start_date. Use ISO format (e.g. 2025-01-01T00:00:00Z)"
                }), 400
        if request.args.get('end_date'):
            try:
                end_date = datetime.fromisoformat(
                    request.args.get('end_date').replace('Z', '+00:00')
                )
            except ValueError:
                return jsonify({
                    "ok": False,
                    "message": "Invalid end_date. Use ISO format."
                }), 400

        logs = system_logger.get_logs(
            limit=limit,
            offset=offset,
            source_filter='Operator',
            status_filter=None,
            operator_filter=operator_filter,
            start_date=start_date,
            end_date=end_date
        )

        return jsonify({
            "ok": True,
            "logs": logs,
            "count": len(logs),
            "limit": limit,
            "offset": offset
        })
    except Exception as e:
        log.error(f"Failed to get activity log: {e}")
        return jsonify({
            "ok": False,
            "message": str(e)
        }), 500
