import time
import logging
from sqlalchemy.orm import sessionmaker
from database import postgres_engine
from services.scale_service import get_current_scale_value
from models.process_order_pg import ProcessOrderPG as ProcessOrder

SessionLocal = sessionmaker(bind=postgres_engine, autoflush=False, autocommit=False, future=True)
log = logging.getLogger(__name__)

class OrderAccumulator:
    def __init__(self, poll_interval=5, tolerance_pct=0.5):
        self.poll_interval = poll_interval
        self.tolerance_pct = tolerance_pct

    def tick(self):
        """Run one accumulation check cycle (used by APScheduler)."""
        try:
            with SessionLocal() as db:
                order = (
                    db.query(ProcessOrder)
                    .filter(ProcessOrder.status.in_(["Open", "Pending", "Planned"]))
                    .order_by(ProcessOrder.hercules_priority.asc(), ProcessOrder.id.asc())
                    .first()
                )
                if not order:
                    return

                # Ensure baseline exists
                if not hasattr(order, "baseline_wg202") or order.baseline_wg202 is None:
                    baseline = get_current_scale_value() or 0.0
                    order.baseline_wg202 = baseline
                    db.add(order)
                    db.commit()
                    log.info(f"[ACC] Baseline set {baseline} for order {order.order_id}")
                    return

                # Current reading
                current_val = get_current_scale_value() or 0.0
                delta = current_val - (order.baseline_wg202 or 0.0)

                expected_tons = float(order.quantity or 0)
                tolerance_amt = expected_tons * (self.tolerance_pct / 100.0)

                if delta >= (expected_tons - tolerance_amt):
                    order.status = "Confirmed"
                    order.confirmed_qty = expected_tons
                    order.baseline_wg202 = current_val  # prepare for next order
                    db.add(order)
                    db.commit()
                    log.info(f"[ACC] Order {order.order_id} confirmed (expected {expected_tons}, actual {delta})")

        except Exception as e:
            log.error(f"[ACC] Tick error: {e}")

    def run(self):
        """Standalone infinite loop (for dev or CLI run)."""
        log.info("Starting accumulator infinite loop...")
        while True:
            self.tick()
            time.sleep(self.poll_interval)
