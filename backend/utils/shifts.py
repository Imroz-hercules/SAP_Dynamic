from datetime import datetime, timedelta
from models.shift_master import ShiftMaster


# ------------------------------------------------------------
# GET CURRENT SHIFT — Uses DB timings (Start/End)
# ------------------------------------------------------------
def get_current_shift(plant: str, department: str, db):
    now = datetime.now().time()

    # --------------------------------------------------
    # MILLING → use plant + department
    # PACKING → ignore plant, use department only
    # --------------------------------------------------
    if department.upper() == "PACKING":
        shifts = db.query(ShiftMaster).filter(
            ShiftMaster.department == department
        ).order_by(ShiftMaster.sort_order.asc()).all()
    else:
        # MILLING
        shifts = db.query(ShiftMaster).filter(
            ShiftMaster.plant == plant,
            ShiftMaster.department == department
        ).order_by(ShiftMaster.sort_order.asc()).all()

    for s in shifts:
        start = s.start_time
        end = s.end_time

        # Convert string to time if necessary
        if isinstance(start, str):
            try:
                start = datetime.strptime(start, "%H:%M:%S").time()
            except ValueError:
                # Handle cases like "07:00" without seconds
                start = datetime.strptime(start, "%H:%M").time()
        
        if isinstance(end, str):
            try:
                end = datetime.strptime(end, "%H:%M:%S").time()
            except ValueError:
                end = datetime.strptime(end, "%H:%M").time()

        # Normal shift (e.g., 07:00 → 15:00)
        if start < end:
            if start <= now < end:
                return s

        # Overnight shift (e.g., 23:00 → 07:00)
        else:
            if now >= start or now < end:
                return s

    return None


# ------------------------------------------------------------
# GET NEXT SHIFT IN SEQUENCE (A → B → C → A)
# ------------------------------------------------------------
def get_next_shift(current_code: str, plant: str, department: str, db):
    # PACKING → ignore plant
    if department.upper() == "PACKING":
        shifts = db.query(ShiftMaster).filter(
            ShiftMaster.department == department
        ).order_by(ShiftMaster.sort_order.asc()).all()
    else:
        # MILLING → keep plant filter
        shifts = db.query(ShiftMaster).filter(
            ShiftMaster.plant == plant,
            ShiftMaster.department == department
        ).order_by(ShiftMaster.sort_order.asc()).all()

    for i, s in enumerate(shifts):
        if s.shift_code == current_code:
            return shifts[(i + 1) % len(shifts)]

    return None


# ------------------------------------------------------------
# BUILD COMPLETE SHIFT END DATETIME FROM SHIFT MASTER
# ------------------------------------------------------------
def compute_shift_end_datetime(shift_row, start_dt=None):
    """
    Returns correct END datetime:
    If shift crosses midnight, adds +1 day.
    """
    if start_dt is None:
        start_dt = datetime.now()

    end_time = shift_row.end_time
    
    # Convert string to time if necessary
    if isinstance(end_time, str):
        try:
            end_time = datetime.strptime(end_time, "%H:%M:%S").time()
        except ValueError:
            end_time = datetime.strptime(end_time, "%H:%M").time()

    start_time_val = shift_row.start_time
    if isinstance(start_time_val, str):
        try:
            start_time_val = datetime.strptime(start_time_val, "%H:%M:%S").time()
        except ValueError:
            start_time_val = datetime.strptime(start_time_val, "%H:%M").time()

    # Build end datetime using the same date as shift start
    end_dt = datetime.combine(start_dt.date(), end_time)

    # If overnight shift (end_time < start_time) → next day
    if end_time < start_time_val:
        end_dt += timedelta(days=1)

    return end_dt


# ------------------------------------------------------------
# CHECK IF CURRENT SHIFT SHOULD END
# ------------------------------------------------------------
def is_shift_ended(order, shift_row):
    """
    Uses saved order.shift_start_time + shift master timings
    to decide if the shift has ended.
    """
    now = datetime.now()

    start_dt = order.shift_start_time
    if not start_dt:
        return False  # shift never started → cannot end

    end_dt = compute_shift_end_datetime(shift_row, start_dt)

    return now >= end_dt
