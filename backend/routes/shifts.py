from flask import Blueprint, request, jsonify
from models.shift_master import ShiftMaster
from database import postgres_engine, PostgresSessionLocal
from datetime import datetime

shifts_bp = Blueprint("shifts", __name__, url_prefix="/api/shifts")


# ----------------------------------------------
# GET ALL SHIFTS
# ----------------------------------------------
@shifts_bp.route("", methods=["GET"])
def list_shifts():
    try:
        with PostgresSessionLocal() as db:
            rows = db.query(ShiftMaster).order_by(
                ShiftMaster.plant.asc(),
                ShiftMaster.department.asc(),
                ShiftMaster.sort_order.asc()
            ).all()

            result = []
            for r in rows:
                # Handle start_time
                if hasattr(r.start_time, 'strftime'):
                    start_time_str = r.start_time.strftime("%H:%M")
                elif isinstance(r.start_time, str):
                    start_time_str = r.start_time[:5]
                else:
                    start_time_str = str(r.start_time)[:5]

                # Handle end_time
                if hasattr(r.end_time, 'strftime'):
                    end_time_str = r.end_time.strftime("%H:%M")
                elif isinstance(r.end_time, str):
                    end_time_str = r.end_time[:5]
                else:
                    end_time_str = str(r.end_time)[:5]

                result.append({
                    "id": r.id,
                    "plant": r.plant,
                    "department": r.department,
                    "shift_code": r.shift_code,
                    "start_time": start_time_str,
                    "end_time": end_time_str,
                    "sort_order": r.sort_order
                })

            return jsonify(result)
    except Exception as e:
        return jsonify({"success": False, "message": f"Error fetching shifts: {str(e)}"}), 500


# ----------------------------------------------
# CREATE OR UPDATE SHIFT
# ----------------------------------------------
@shifts_bp.route("", methods=["POST"])
def save_shift():
    data = request.json
    required = ["plant", "department", "shift_code", "start_time", "end_time", "sort_order"]
    if not all(k in data for k in required):
        return jsonify({"success": False, "message": "Missing required fields"}), 400

    try:
        # Parse time strings to Time objects
        start_time = datetime.strptime(data["start_time"], "%H:%M").time()
        end_time = datetime.strptime(data["end_time"], "%H:%M").time()
    except ValueError as e:
        return jsonify({"success": False, "message": f"Invalid time format. Use HH:MM format. Error: {str(e)}"}), 400

    try:
        with PostgresSessionLocal() as db:
            # UPDATE
            if "id" in data:
                shift = db.query(ShiftMaster).filter(ShiftMaster.id == data["id"]).first()
                if not shift:
                    return jsonify({"success": False, "message": "Shift not found"}), 404
            else:
                # CREATE
                shift = ShiftMaster()

            shift.plant = data["plant"]
            shift.department = data["department"]
            shift.shift_code = data["shift_code"]
            shift.start_time = start_time
            shift.end_time = end_time
            shift.sort_order = data["sort_order"]

            db.add(shift)
            db.commit()
            return jsonify({"success": True, "id": shift.id})
    except Exception as e:
        return jsonify({"success": False, "message": f"Error saving shift: {str(e)}"}), 500


# ----------------------------------------------
# DELETE SHIFT
# ----------------------------------------------
@shifts_bp.route("/<int:shift_id>", methods=["DELETE"])
def delete_shift(shift_id):
    try:
        with PostgresSessionLocal() as db:
            shift = db.query(ShiftMaster).filter(ShiftMaster.id == shift_id).first()
            if not shift:
                return jsonify({"success": False, "message": "Shift not found"}), 404

            db.delete(shift)
            db.commit()
            return jsonify({"success": True})
    except Exception as e:
        return jsonify({"success": False, "message": f"Error deleting shift: {str(e)}"}), 500

