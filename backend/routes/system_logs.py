# backend/routes/system_logs.py
from flask import Blueprint, jsonify, request
from datetime import datetime, timedelta
from typing import Optional
import logging

from services.system_logger import system_logger

log = logging.getLogger(__name__)

system_logs_bp = Blueprint("system_logs", __name__, url_prefix="/api/system-logs")

@system_logs_bp.route("/", methods=["GET"])
def get_logs():
    """
    Get system logs with filtering options.
    
    Query Parameters:
        - limit: Maximum number of logs (default: 1000)
        - offset: Number of logs to skip (default: 0)
        - source: Filter by source (SAP, Hercules, SCADA, Operator)
        - status: Filter by status (Success, Error, Warning, InProgress)
        - operator: Filter by operator name
        - start_date: Filter logs after this date (ISO format)
        - end_date: Filter logs before this date (ISO format)
    """
    try:
        # Parse query parameters
        limit = int(request.args.get('limit', 100))
        offset = int(request.args.get('offset', 0))
        source_filter = request.args.get('source')
        status_filter = request.args.get('status')
        operator_filter = request.args.get('operator')
        
        # Parse date filters
        start_date = None
        end_date = None
        
        if request.args.get('start_date'):
            try:
                start_date = datetime.fromisoformat(request.args.get('start_date').replace('Z', '+00:00'))
            except ValueError:
                return jsonify({
                    "ok": False,
                    "message": "Invalid start_date format. Use ISO format (e.g., 2025-01-01T00:00:00Z)"
                }), 400
        
        if request.args.get('end_date'):
            try:
                end_date = datetime.fromisoformat(request.args.get('end_date').replace('Z', '+00:00'))
            except ValueError:
                return jsonify({
                    "ok": False,
                    "message": "Invalid end_date format. Use ISO format (e.g., 2025-01-01T23:59:59Z)"
                }), 400
        
        # Get logs
        logs = system_logger.get_logs(
            limit=limit,
            offset=offset,
            source_filter=source_filter,
            status_filter=status_filter,
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
        log.error(f"Failed to get logs: {e}")
        return jsonify({
            "ok": False,
            "message": f"Failed to retrieve logs: {str(e)}"
        }), 500

@system_logs_bp.route("/shift/<date>", methods=["GET"])
def get_shift_logs(date: str):
    """
    Get logs for a specific shift date.
    
    Args:
        date: Date in YYYY-MM-DD format
    """
    try:
        # Parse date
        try:
            shift_date = datetime.strptime(date, "%Y-%m-%d")
        except ValueError:
            return jsonify({
                "ok": False,
                "message": "Invalid date format. Use YYYY-MM-DD format"
            }), 400
        
        # Get shift logs
        logs = system_logger.get_shift_logs(shift_date)
        
        return jsonify({
            "ok": True,
            "shift_date": date,
            "logs": logs,
            "count": len(logs)
        })
        
    except Exception as e:
        log.error(f"Failed to get shift logs: {e}")
        return jsonify({
            "ok": False,
            "message": f"Failed to retrieve shift logs: {str(e)}"
        }), 500

@system_logs_bp.route("/manual-sync", methods=["POST"])
def trigger_manual_sync():
    """
    Trigger manual sync and log the event.
    """
    try:
        data = request.get_json() or {}
        operator = data.get('operator', 'Unknown Operator')
        
        # Log manual sync trigger
        log_id = system_logger.log_event(
            source="Operator",
            action="Manual Sync Triggered",
            status="InProgress",
            operator=operator,
            metadata={"triggered_by": "api", "timestamp": datetime.now().isoformat()}
        )
        
        return jsonify({
            "ok": True,
            "message": "Manual sync triggered successfully",
            "log_id": log_id,
            "operator": operator
        })
        
    except Exception as e:
        log.error(f"Failed to trigger manual sync: {e}")
        return jsonify({
            "ok": False,
            "message": f"Failed to trigger manual sync: {str(e)}"
        }), 500

@system_logs_bp.route("/end-shift", methods=["POST"])
def end_shift():
    """
    End shift and sync to SAP.
    """
    try:
        data = request.get_json() or {}
        operator = data.get('operator', 'Unknown Operator')
        
        # Log shift end
        log_id = system_logger.log_event(
            source="Hercules",
            action="Shift End Sync to SAP",
            status="InProgress",
            operator=operator,
            metadata={"triggered_by": "api", "timestamp": datetime.now().isoformat()}
        )
        
        return jsonify({
            "ok": True,
            "message": "Shift ended and sync initiated",
            "log_id": log_id,
            "operator": operator
        })
        
    except Exception as e:
        log.error(f"Failed to end shift: {e}")
        return jsonify({
            "ok": False,
            "message": f"Failed to end shift: {str(e)}"
        }), 500

@system_logs_bp.route("/undo/<int:log_id>", methods=["POST"])
def undo_action(log_id: int):
    """
    Undo a specific action by creating a revert log entry.
    """
    try:
        data = request.get_json() or {}
        operator = data.get('operator', 'Unknown Operator')
        
        # Get the original log entry
        logs = system_logger.get_logs(limit=1, offset=0)
        original_log = None
        for log_entry in logs:
            if log_entry['id'] == log_id:
                original_log = log_entry
                break
        
        if not original_log:
            return jsonify({
                "ok": False,
                "message": "Original log entry not found"
            }), 404
        
        # Create undo log entry
        undo_log_id = system_logger.log_event(
            source="Operator",
            action=f"Undo: {original_log['action']}",
            status="Reverted",
            operator=operator,
            details=f"Reverted action from log ID {log_id}",
            metadata={
                "original_log_id": log_id,
                "original_action": original_log['action'],
                "original_source": original_log['source'],
                "timestamp": datetime.now().isoformat()
            }
        )
        
        return jsonify({
            "ok": True,
            "message": "Action reverted successfully",
            "undo_log_id": undo_log_id,
            "original_log_id": log_id
        })
        
    except Exception as e:
        log.error(f"Failed to undo action: {e}")
        return jsonify({
            "ok": False,
            "message": f"Failed to undo action: {str(e)}"
        }), 500

@system_logs_bp.route("/export", methods=["GET"])
def export_logs():
    """
    Export logs to CSV format.
    """
    try:
        # Get all logs (with reasonable limit)
        logs = system_logger.get_logs(limit=10000, offset=0)
        
        # Convert to CSV format
        csv_lines = ["Timestamp,Source,Action,Status,Operator,Details,Duration (ms),Error Code"]
        
        for log_entry in logs:
            csv_line = [
                log_entry.get('timestamp', ''),
                log_entry.get('source', ''),
                log_entry.get('action', ''),
                log_entry.get('status', ''),
                log_entry.get('operator', ''),
                log_entry.get('details', '').replace(',', ';').replace('\n', ' '),
                log_entry.get('duration_ms', ''),
                log_entry.get('error_code', '')
            ]
            csv_lines.append(','.join(f'"{str(field)}"' for field in csv_line))
        
        csv_content = '\n'.join(csv_lines)
        
        return jsonify({
            "ok": True,
            "csv_content": csv_content,
            "count": len(logs)
        })
        
    except Exception as e:
        log.error(f"Failed to export logs: {e}")
        return jsonify({
            "ok": False,
            "message": f"Failed to export logs: {str(e)}"
        }), 500

@system_logs_bp.route("/clear", methods=["POST"])
def clear_logs():
    """
    Clear old logs (admin function).
    """
    try:
        data = request.get_json() or {}
        older_than_days = data.get('older_than_days', 30)
        
        if older_than_days < 1:
            return jsonify({
                "ok": False,
                "message": "older_than_days must be at least 1"
            }), 400
        
        deleted_count = system_logger.clear_logs(older_than_days)
        
        return jsonify({
            "ok": True,
            "message": f"Cleared {deleted_count} logs older than {older_than_days} days",
            "deleted_count": deleted_count
        })
        
    except Exception as e:
        log.error(f"Failed to clear logs: {e}")
        return jsonify({
            "ok": False,
            "message": f"Failed to clear logs: {str(e)}"
        }), 500

@system_logs_bp.route("/stats", methods=["GET"])
def get_log_stats():
    """
    Get log statistics for dashboard.
    """
    try:
        # Get logs from last 24 hours
        end_date = datetime.now()
        start_date = end_date - timedelta(days=1)
        
        logs = system_logger.get_logs(
            start_date=start_date,
            end_date=end_date,
            limit=10000
        )
        
        # Calculate statistics
        total_logs = len(logs)
        success_count = len([log for log in logs if log['status'] == 'Success'])
        error_count = len([log for log in logs if log['status'] == 'Error'])
        warning_count = len([log for log in logs if log['status'] == 'Warning'])
        
        # Group by source
        source_stats = {}
        for log_entry in logs:
            source = log_entry['source']
            if source not in source_stats:
                source_stats[source] = 0
            source_stats[source] += 1
        
        # Group by operator
        operator_stats = {}
        for log_entry in logs:
            operator = log_entry['operator']
            if operator:
                if operator not in operator_stats:
                    operator_stats[operator] = 0
                operator_stats[operator] += 1
        
        return jsonify({
            "ok": True,
            "stats": {
                "total_logs": total_logs,
                "success_count": success_count,
                "error_count": error_count,
                "warning_count": warning_count,
                "source_stats": source_stats,
                "operator_stats": operator_stats,
                "period": "24 hours"
            }
        })
        
    except Exception as e:
        log.error(f"Failed to get log stats: {e}")
        return jsonify({
            "ok": False,
            "message": f"Failed to get log statistics: {str(e)}"
        }), 500
