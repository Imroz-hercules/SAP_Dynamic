# backend/models/process_order_pg.py
from sqlalchemy import Column, Integer, String, Float, DateTime, Boolean, Index, JSON
from sqlalchemy.sql import func
from database import postgres_engine, PostgresBase


class ProcessOrderPG(PostgresBase):
    """PostgreSQL version of ProcessOrder with Shift-Based Tracking"""
    __tablename__ = "process_orders"

    # =========================================================================
    # CORE ORDER FIELDS
    # =========================================================================
    id         = Column(Integer, primary_key=True, autoincrement=True)
    order_id   = Column(String(50), nullable=False, index=True)      # Order ID (PROCESS_ORDER from SAP)
    material   = Column(String(100), nullable=False)                 # Material (MATERIAL from SAP)
    version    = Column(String(20), nullable=False, default="v1.0")  # Version (VERSION from SAP)
    batch      = Column(String(50), nullable=True)                   # Batch (generated or from SAP)
    quantity   = Column(Float, nullable=False, default=0.0)          # Quantity (TOTAL_QTY from SAP)
    unit       = Column(String(10), nullable=False, default="KG")    # Unit (UOM from SAP)
    status     = Column(String(20), nullable=False, default="Open")  # Status (Open/Pending/InProgress/Validated/Rejected)
    priority   = Column(Integer, nullable=False, default=0)          # Priority for queue order (1=highest)
    date       = Column(DateTime(timezone=True), nullable=False, server_default=func.now())
    created_at = Column(DateTime(timezone=True), nullable=False, server_default=func.now())
    updated_at = Column(DateTime(timezone=True), nullable=False, server_default=func.now())
    
    # =========================================================================
    # SAP API FIELDS
    # =========================================================================
    plant          = Column(String(50), nullable=True)        # Plant (PLANT from SAP)
    confirmed_qty  = Column(Float, nullable=True, default=0.0)  # Total Confirmed Quantity
    material_desc  = Column(String(200), nullable=True)       # Material Description
    sap_created_on = Column(DateTime(timezone=True), nullable=True)  # CREATED_ON from SAP
    uom            = Column(String(10), nullable=True)        # Unit of Measure
    sap_order_id   = Column(String(50), nullable=True)        # SAP Order ID
    total_qty      = Column(Float, nullable=True)             # Total Quantity
    priority_id    = Column(Integer, nullable=True)           # Priority ID from SAP (display only)
    hercules_priority = Column(Integer, nullable=True, default=0)  # Queue order; drag/Hercules only. SAP does not change this.

    # =========================================================================
    # VALIDATION FIELDS
    # =========================================================================
    expected_weight   = Column(Float, nullable=True, default=0.0)     # Expected weight for validation
    validation_method = Column(String(20), nullable=True)             # 'Auto' or 'Manual'
    confirmed_text    = Column(String(500), nullable=True)            # Optional text for manual processing
    scrap             = Column(Float, nullable=True, default=0.0)     # Damaged qty during production
    last_confirmed_qty = Column(Float, nullable=True, default=0.0)    # Last confirmed quantity
    is_final_sent     = Column(Boolean, nullable=True, default=False) # Final confirmation sent flag
    
    # =========================================================================
    # ORDER CLASSIFICATION FIELDS
    # =========================================================================
    order_type    = Column(String(50), nullable=True)       # MILLING, PACKING
    packing_line  = Column(String(10), nullable=True)       # SL601, SL607, etc.
    bag_size      = Column(String(10), nullable=True)       # 45, 10, 01, etc.

    # =========================================================================
    # SCALE ASSIGNMENT COLUMNS (Dynamic per-order scale mapping)
    # =========================================================================
    scale1     = Column(String(50), nullable=True)          # First scale tag (e.g., "WG501")
    scale1_qty = Column(Float, nullable=True, default=0.0)  # Quantity for scale1
    
    scale2     = Column(String(50), nullable=True)          # Second scale tag
    scale2_qty = Column(Float, nullable=True, default=0.0)  # Quantity for scale2
    
    scale3     = Column(String(50), nullable=True)          # Third scale tag
    scale3_qty = Column(Float, nullable=True, default=0.0)  # Quantity for scale3

    # =========================================================================
    # BASELINE COLUMNS FOR VALIDATION (SCADA Baselines)
    # =========================================================================
    
    # PACKING: Bag counter baselines (from ASMReporting_5 SL*_COUNTER columns)
    baseline_sl601_counter = Column(Float, nullable=True, default=0.0)  # Packing Line 1 (45 KG bags)
    baseline_sl602_counter = Column(Float, nullable=True, default=0.0)  # Packing Line 2 (45 KG bags)
    baseline_sl603_counter = Column(Float, nullable=True, default=0.0)  # Packing Line 3 (40 KG BRAN)
    baseline_sl606_counter = Column(Float, nullable=True, default=0.0)  # Packing Line 6 (01 KG mini bags)
    baseline_sl607_counter = Column(Float, nullable=True, default=0.0)  # Packing Line 7 (10 KG bags)
    
    # MILLING: Flour/Bran output baselines (from ASMReporting_5 WG* columns)
    baseline_wg101 = Column(Float, nullable=True, default=0.0)  # WG101 Scale output (TON)
    baseline_wg201 = Column(Float, nullable=True, default=0.0)  # WG201 Scale output (TON)
    baseline_wg202 = Column(Float, nullable=True, default=0.0)  # WG202 Clean Wheat input (TON)
    baseline_wg301 = Column(Float, nullable=True, default=0.0)  # WG301 Screenings (TON)
    baseline_wg302 = Column(Float, nullable=True, default=0.0)  # WG302 Screenings (TON)
    baseline_wg501 = Column(Float, nullable=True, default=0.0)  # WG501 Bakery Flour output (TON)
    baseline_wg502 = Column(Float, nullable=True, default=0.0)  # WG502 Cake/IWW Flour output (TON)
    baseline_wg503 = Column(Float, nullable=True, default=0.0)  # WG503 Bran output (TON)
    
    # WATER DOSING METER BASELINES (from ASMReporting_5 DM* columns)
    baseline_dm101 = Column(Float, nullable=True, default=0.0)  # DM101 Water meter baseline
    baseline_dm102 = Column(Float, nullable=True, default=0.0)  # DM102 Water meter baseline
    baseline_dm201 = Column(Float, nullable=True, default=0.0)  # DM201 Water meter baseline
    baseline_dm202 = Column(Float, nullable=True, default=0.0)  # DM202 Water meter baseline
    baseline_dm203 = Column(Float, nullable=True, default=0.0)  # DM203 Water meter baseline
    
    # BASELINE FIXED FLAGS (track if baseline has been set - prevents re-baselining)
    # Stored as JSON for flexibility: {"dm201": true, "wg201": true, ...}
    baseline_fixed_flags = Column(JSON, nullable=True, default=dict)  # Flags to prevent re-baselining

    # =========================================================================
    # ✨ NEW SHIFT-BASED TRACKING FIELDS
    # =========================================================================
    
    # SHIFT IDENTIFICATION (Independent from Priority)
    current_shift      = Column(String(1), nullable=True)   # Current shift: 'A', 'B', or 'C'
    shift_start_time   = Column(DateTime(timezone=True), nullable=True)  # When current shift started
    shift_end_time     = Column(DateTime(timezone=True), nullable=True)  # When current shift ended
    
    # PER-SHIFT WEIGHT PRODUCED (Production tracking)
    weight_shift_a     = Column(Float, nullable=True, default=0.0)  # Weight produced in Shift A
    weight_shift_b     = Column(Float, nullable=True, default=0.0)  # Weight produced in Shift B
    weight_shift_c     = Column(Float, nullable=True, default=0.0)  # Weight produced in Shift C
    
    # PER-SHIFT CONFIRMED TO SAP (Confirmation tracking)
    confirmed_shift_a  = Column(Float, nullable=True, default=0.0)  # Weight confirmed to SAP from Shift A
    confirmed_shift_b  = Column(Float, nullable=True, default=0.0)  # Weight confirmed to SAP from Shift B
    confirmed_shift_c  = Column(Float, nullable=True, default=0.0)  # Weight confirmed to SAP from Shift C
    
    # SHIFT CONFIRMATION STATUS FLAGS
    shift_a_confirmed  = Column(Boolean, nullable=True, default=False)  # TRUE when Shift A confirmed to SAP
    shift_b_confirmed  = Column(Boolean, nullable=True, default=False)  # TRUE when Shift B confirmed to SAP
    shift_c_confirmed  = Column(Boolean, nullable=True, default=False)  # TRUE when Shift C confirmed to SAP
    
    # OVERFLOW HANDLING (Weight beyond target)
    overflow_weight    = Column(Float, nullable=True, default=0.0)      # Weight beyond target (for next order)
    is_target_reached  = Column(Boolean, nullable=True, default=False)  # TRUE when exact target met (no tolerance)
    
    # SHIFT METADATA
    total_shifts_used     = Column(Integer, nullable=True, default=0)  # Number of shifts used for this order
    last_shift_completed  = Column(String(1), nullable=True)           # Last shift that was completed ('A'/'B'/'C')
    
    # SHIFT BASELINE TRACKING (JSON for flexibility - stores baselines per shift)
    baseline_shift_a_start = Column(JSON, nullable=True)  # Baselines captured at Shift A start
    baseline_shift_b_start = Column(JSON, nullable=True)  # Baselines captured at Shift B start
    baseline_shift_c_start = Column(JSON, nullable=True)  # Baselines captured at Shift C start
    
    # LAST SCADA VALUES (JSON for dynamic equipment tracking)
    # Stores last SCADA reading per equipment tag: {"dm201": 160.0, "wg101": 100.0, ...}
    # Note: Column must be added via migration script (migrate_add_last_scada_values.py)
    last_scada_values = Column(JSON, nullable=True)  # Last SCADA values for delta calculation

    # =========================================================================
    # INDEXES FOR PERFORMANCE
    # =========================================================================
    __table_args__ = (
        Index("idx_process_order_order_id", "order_id"),
        Index("idx_process_order_status", "status"),
        Index("idx_process_order_date", "date"),
        Index("idx_process_order_priority", "priority"),
        Index("idx_process_order_type", "order_type"),
        Index("idx_current_shift", "current_shift"),
        Index("idx_shift_confirmed", "shift_a_confirmed", "shift_b_confirmed", "shift_c_confirmed"),
        Index("idx_target_reached", "is_target_reached"),
    )

    def __repr__(self):
        return f"<ProcessOrder(id={self.id}, order_id={self.order_id}, status={self.status}, current_shift={self.current_shift})>"

    def to_dict(self):
        """Convert order to dictionary for API responses"""
        return {
            "id": self.id,
            "order_id": self.order_id,
            "material": self.material,
            "version": self.version,
            "batch": self.batch,
            "quantity": self.quantity,
            "unit": self.unit,
            "status": self.status,
            "priority": self.hercules_priority if self.hercules_priority is not None else self.priority,
            "hercules_priority": self.hercules_priority,
            "date": self.date.isoformat() if self.date else None,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None,
            "plant": self.plant,
            "confirmed_qty": self.confirmed_qty,
            "material_desc": self.material_desc,
            "sap_created_on": self.sap_created_on.isoformat() if self.sap_created_on else None,
            "uom": self.uom,
            "sap_order_id": self.sap_order_id,
            "total_qty": self.total_qty,
            "priority_id": self.priority_id,
            "expected_weight": self.expected_weight,
            "validation_method": self.validation_method,
            "confirmed_text": self.confirmed_text,
            "scrap": self.scrap,
            "last_confirmed_qty": self.last_confirmed_qty,
            "is_final_sent": self.is_final_sent,
            "order_type": self.order_type,
            "packing_line": self.packing_line,
            "bag_size": self.bag_size,
            "scale1": self.scale1,
            "scale1_qty": self.scale1_qty,
            "scale2": self.scale2,
            "scale2_qty": self.scale2_qty,
            "scale3": self.scale3,
            "scale3_qty": self.scale3_qty,
            # Baselines
            "baseline_sl601_counter": self.baseline_sl601_counter,
            "baseline_sl602_counter": self.baseline_sl602_counter,
            "baseline_sl603_counter": self.baseline_sl603_counter,
            "baseline_sl606_counter": self.baseline_sl606_counter,
            "baseline_sl607_counter": self.baseline_sl607_counter,
            "baseline_wg101": self.baseline_wg101,
            "baseline_wg201": self.baseline_wg201,
            "baseline_wg202": self.baseline_wg202,
            "baseline_wg301": self.baseline_wg301,
            "baseline_wg302": self.baseline_wg302,
            "baseline_wg501": self.baseline_wg501,
            "baseline_wg502": self.baseline_wg502,
            "baseline_wg503": self.baseline_wg503,
            # Shift-based fields
            "current_shift": self.current_shift,
            "shift_start_time": self.shift_start_time.isoformat() if self.shift_start_time else None,
            "shift_end_time": self.shift_end_time.isoformat() if self.shift_end_time else None,
            "weight_shift_a": self.weight_shift_a,
            "weight_shift_b": self.weight_shift_b,
            "weight_shift_c": self.weight_shift_c,
            "confirmed_shift_a": self.confirmed_shift_a,
            "confirmed_shift_b": self.confirmed_shift_b,
            "confirmed_shift_c": self.confirmed_shift_c,
            "shift_a_confirmed": self.shift_a_confirmed,
            "shift_b_confirmed": self.shift_b_confirmed,
            "shift_c_confirmed": self.shift_c_confirmed,
            "overflow_weight": self.overflow_weight,
            "is_target_reached": self.is_target_reached,
            "total_shifts_used": self.total_shifts_used,
            "last_shift_completed": self.last_shift_completed,
            "baseline_shift_a_start": self.baseline_shift_a_start,
            "baseline_shift_b_start": self.baseline_shift_b_start,
            "baseline_shift_c_start": self.baseline_shift_c_start,
        }


def create_process_order_pg_schema():
    """Create the process_orders table in PostgreSQL"""
    PostgresBase.metadata.create_all(bind=postgres_engine, tables=[ProcessOrderPG.__table__])
    print("✅ Created/Updated process_orders table in PostgreSQL with shift-based tracking")


# Export for easy importing
__all__ = ['ProcessOrderPG', 'create_process_order_pg_schema']
