# backend/conftest.py
"""
Make the counting test suites actually fail under pytest.

THE PROBLEM THIS SOLVES

Every test file in this backend reports failure by incrementing a counter, not
by raising:

    def check(name, condition, detail=None):
        global passed, failed
        if condition:
            passed += 1
        else:
            failed += 1          # <- nothing raises
            print(f"  FAIL  {name}")

Run directly, that is fine: `main()` returns 1 and the shell sees a non-zero
exit. Run under pytest — which is what CI grades — the test function returns
normally, so pytest records PASSED no matter how many checks failed.

Measured, not assumed (2026-09-08). Two independent mutations, one in each
workstream:

    A7  services/baseline_guard.py — unmapped tag returns 0.0 instead of raising
        (this is the exact silent-wrong-number bug A7 exists to prevent)
          python test_baseline_guard.py   ->  22 passed, 6 failed, exit 1
          python -m pytest -q             ->  exit 0   GREEN

    B1  services/scada_tag_registry.py — allowed_fields() ignores is_active
          python test_scada_config.py     ->  22 passed, 2 failed, exit 1
          python -m pytest -q             ->  exit 0   GREEN

A survey of the tree at that date found **0 `assert` statements across 24
test files**, against 197 `check()` calls. So the CI gate was decorative for
every test in the repository, on both sides of the migration.

THE FIX

An autouse fixture reads the test module's own `failed` counter before and
after each test, and fails the test if it moved. That means:

  * no test file is edited — 197 checks keep their exact current behaviour,
    and the standalone runners still print their full pass/fail summary rather
    than stopping at the first failure;
  * a suite that does not use the counter convention is simply unaffected;
  * pytest now sees what the runner has always seen.

`failed` is read off the module rather than imported, so this works for every
suite that follows the convention and silently skips any that does not.

WHAT THIS DELIBERATELY DOES NOT FIX

Several older files in this repo (test_sap_*.py, test_shift_data.py,
test_system_logging.py, …) `return True`/`return False` instead of asserting;
a returning-False test still passes. pytest warns (PytestReturnNotNoneWarning)
and pytest.ini currently ignores that warning. Those files are pre-existing,
are mostly ignored or deselected in pytest.ini already, and none of them cover
migration work. Fixing them means rewriting 25 files in someone else's project.
Recorded here rather than silently changed.
"""

import pytest

COUNTER = "failed"


def _counter(module) -> int:
    """The module's failure counter, or 0 if it does not use the convention."""
    value = getattr(module, COUNTER, 0)
    return value if isinstance(value, int) else 0


@pytest.fixture(autouse=True)
def fail_on_counted_check_failures(request):
    """
    Fail the test if its module's `failed` counter moved while it ran.

    Autouse, so it applies to every test without any file opting in.
    """
    module = getattr(request, "module", None)
    if module is None or not hasattr(module, COUNTER):
        yield
        return

    before = _counter(module)
    yield
    after = _counter(module)

    if after > before:
        moved = after - before
        pytest.fail(
            f"{moved} check(s) failed inside {request.node.name}. "
            f"The suite counts failures instead of raising, so pytest would "
            f"otherwise record this as passed — see backend/conftest.py. "
            f"Run `python {module.__name__}.py` to see which checks failed.",
            pytrace=False,
        )
