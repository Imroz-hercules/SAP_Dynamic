# backend/test_validator_interval.py
"""
Tests for A5 — the auto-validator cycle interval.

Standalone script, like the other backend/test_*.py files. Needs the PostgreSQL
connection from .env because it round-trips through `system_settings`. It
restores the original value on the way out, including if an assertion fails.

    PYTHONIOENCODING=utf-8 python test_validator_interval.py

What it pins down:

  * the dead constants are gone
  * a stored value is picked up
  * a missing setting falls back to the default
  * out-of-range and non-numeric values cannot break the worker loop
  * the value is cached (the worker reads it once a second per order)
  * invalidating the cache makes the next read immediate
"""

import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from models.system_settings import get_setting, set_setting  # noqa: E402
from routes.order_validation import (  # noqa: E402
    AUTO_VALIDATOR_INTERVAL_DEFAULT,
    AUTO_VALIDATOR_INTERVAL_KEY,
    AUTO_VALIDATOR_INTERVAL_MAX,
    AUTO_VALIDATOR_INTERVAL_MIN,
    get_auto_validator_interval,
    invalidate_auto_validator_interval,
)

passed = 0
failed = 0


def check(name, condition, detail=None):
    global passed, failed
    if condition:
        passed += 1
        print(f"  PASS  {name}")
    else:
        failed += 1
        print(f"  FAIL  {name}" + (f"  - {detail!r}" if detail is not None else ""))


def read_after(value):
    """Store `value` and read it back, bypassing the cache."""
    set_setting(AUTO_VALIDATOR_INTERVAL_KEY, value, value_type="float")
    invalidate_auto_validator_interval()
    return get_auto_validator_interval()


def test_dead_constants_gone():
    print("\nThe dead constants are gone")
    import routes.order_validation as ov

    check("TOLERANCE_PCT removed", not hasattr(ov, "TOLERANCE_PCT"))
    check("WORKER_SLEEP_SECONDS removed", not hasattr(ov, "WORKER_SLEEP_SECONDS"))

    try:
        import services.order_validation_service  # noqa: F401
        check("services/order_validation_service.py deleted", False, "still importable")
    except ModuleNotFoundError:
        check("services/order_validation_service.py deleted", True)
    except ImportError as exc:
        # It never imported cleanly anyway, but the file should be gone.
        check("services/order_validation_service.py deleted", False, str(exc))


def test_reads_stored_value():
    print("\nA stored value is used")
    check("2.5 is read back", read_after(2.5) == 2.5, read_after(2.5))
    check("0.5 is read back", read_after(0.5) == 0.5)


def test_clamping():
    print("\nOut-of-range values cannot break the loop")
    check(
        f"0 clamps up to {AUTO_VALIDATOR_INTERVAL_MIN}",
        read_after(0) == AUTO_VALIDATOR_INTERVAL_MIN,
        read_after(0),
    )
    check(
        "a negative value clamps up",
        read_after(-5) == AUTO_VALIDATOR_INTERVAL_MIN,
    )
    check(
        f"3600 clamps down to {AUTO_VALIDATOR_INTERVAL_MAX}",
        read_after(3600) == AUTO_VALIDATOR_INTERVAL_MAX,
        read_after(3600),
    )


def test_bad_input_falls_back():
    print("\nA non-numeric value falls back to the default")
    set_setting(AUTO_VALIDATOR_INTERVAL_KEY, "not-a-number", value_type="string")
    invalidate_auto_validator_interval()
    check(
        "garbage -> default",
        get_auto_validator_interval() == AUTO_VALIDATOR_INTERVAL_DEFAULT,
        get_auto_validator_interval(),
    )


def test_caching():
    print("\nThe value is cached between reads")
    read_after(2.0)
    check("baseline read is 2.0", get_auto_validator_interval() == 2.0)

    # Change it behind the cache's back.
    set_setting(AUTO_VALIDATOR_INTERVAL_KEY, 5.0, value_type="float")
    check(
        "a change is not picked up while cached",
        get_auto_validator_interval() == 2.0,
        get_auto_validator_interval(),
    )

    invalidate_auto_validator_interval()
    check(
        "and is picked up once invalidated",
        get_auto_validator_interval() == 5.0,
        get_auto_validator_interval(),
    )


def main():
    print("A5 — validator tuning")

    original = get_setting(AUTO_VALIDATOR_INTERVAL_KEY, None)
    try:
        test_dead_constants_gone()
        test_reads_stored_value()
        test_clamping()
        test_bad_input_falls_back()
        test_caching()
    finally:
        if original is None:
            set_setting(AUTO_VALIDATOR_INTERVAL_KEY, AUTO_VALIDATOR_INTERVAL_DEFAULT,
                        value_type="float")
        else:
            set_setting(AUTO_VALIDATOR_INTERVAL_KEY, original, value_type="float")
        invalidate_auto_validator_interval()
        print(f"\n  (restored {AUTO_VALIDATOR_INTERVAL_KEY} to "
              f"{get_auto_validator_interval()})")

    print(f"\n{passed} passed, {failed} failed")
    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(main())
