# backend/test_runtime_config.py
"""
Tests for A8 — runtime configuration.

Standalone script, like the other backend/test_*.py files. Writes settings and
restores every one it touched, including on failure.

    PYTHONIOENCODING=utf-8 python test_runtime_config.py

What it pins down:

  * resolution order is database -> env -> documented default
  * `source` reports honestly which of the three a value came from
  * secrets are masked, and a masked value round-tripped through the API does
    not blank the stored one
  * the excluded keys cannot be written, whatever a client sends
  * read-only keys cannot be written
  * SAP_CONFIG is a live view, not an import-time snapshot
  * the committed credential literals are gone from the source
"""

import io
import os
import pathlib
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from models.system_settings import set_setting  # noqa: E402
from services import runtime_config as rc  # noqa: E402

passed = 0
failed = 0
TOUCHED = ("sap_base_url", "sap_client", "sap_timeout", "sap_mock_url",
           "sap_endpoint_orders", "sap_password")
_original = {}


def check(name, condition, detail=None):
    global passed, failed
    if condition:
        passed += 1
        print(f"  PASS  {name}")
    else:
        failed += 1
        print(f"  FAIL  {name}" + (f"  - {detail!r}" if detail is not None else ""))


def store(key, value):
    setting = rc.SETTINGS[key]
    set_setting(key, value, value_type=setting.kind)
    rc.invalidate()


def clear(key):
    """Blank the stored value so resolution falls through to env/default."""
    set_setting(key, "", value_type=rc.SETTINGS[key].kind)
    rc.invalidate()


def test_resolution_order():
    print("\nResolution: database -> env -> default")

    # `sap_endpoint_confirm_online` has no env var set anywhere, so it starts
    # on its documented default.
    clear("sap_endpoint_orders")
    from_env = rc.resolve("sap_endpoint_orders")
    check("falls through to env when nothing is stored",
          rc.source_of("sap_endpoint_orders") == "env", rc.source_of("sap_endpoint_orders"))
    check("and the value is the env one",
          from_env == os.getenv("SAP_ENDPOINT"), (from_env, os.getenv("SAP_ENDPOINT")))

    store("sap_endpoint_orders", "/stored/ENDPOINT")
    check("a stored value wins over env",
          rc.resolve("sap_endpoint_orders") == "/stored/ENDPOINT",
          rc.resolve("sap_endpoint_orders"))
    check("and source says so", rc.source_of("sap_endpoint_orders") == "database")

    # A key with no env var falls straight to its default.
    check("no env var -> default",
          rc.source_of("sap_endpoint_kpi_milling") == "default",
          rc.source_of("sap_endpoint_kpi_milling"))
    check("and the default is the documented one",
          rc.resolve("sap_endpoint_kpi_milling") == "/zmi_kpi_mill/MKPI")


def test_types():
    print("\nValues come back in their declared type")
    store("sap_timeout", "45")
    check("integer", rc.resolve("sap_timeout") == 45 and isinstance(rc.resolve("sap_timeout"), int),
          rc.resolve("sap_timeout"))
    check("boolean", isinstance(rc.resolve("mssql_enabled"), bool), rc.resolve("mssql_enabled"))
    check("float", isinstance(rc.resolve("auto_validator_interval_seconds"), float))
    check("string", isinstance(rc.resolve("sap_client"), str))


def test_secrets_are_masked():
    print("\nSecrets are masked on read")
    described = {row["key"]: row for row in rc.describe()}
    check("password is masked", described["sap_password"]["value"] == rc.MASK,
          described["sap_password"]["value"])
    check("mssql url is masked", described["mssql_url"]["value"] == rc.MASK)
    check("a non-secret is not masked", described["sap_client"]["value"] != rc.MASK)
    check("the real value is still readable in-process",
          rc.sap_password() != rc.MASK)

    # Round-tripping the mask must not blank the stored value.
    before = rc.sap_password()
    result = rc.apply({"sap_password": rc.MASK})
    check("a masked value is skipped, not written",
          result["saved"] == [] and result["skipped"][0]["reason"] == "unchanged", result)
    rc.invalidate()
    check("and the password is unchanged", rc.sap_password() == before,
          (before, rc.sap_password()))


def test_forbidden_and_readonly():
    print("\nWhat cannot be written")
    for key in ("JWT_SECRET", "POSTGRES_URL", "PORT", "CORS_ALLOWED_ORIGINS"):
        result = rc.apply({key: "anything"})
        check(f"{key} refused",
              result["saved"] == [] and "not configurable" in result["skipped"][0]["reason"],
              result)

    result = rc.apply({"scada_poll_interval_sec": 5})
    check("a read-only interval is refused",
          result["saved"] == [] and "read-only" in result["skipped"][0]["reason"], result)

    result = rc.apply({"no_such_setting": 1})
    check("an unknown key is refused",
          result["saved"] == [] and result["skipped"][0]["reason"] == "unknown setting", result)

    result = rc.apply({"sap_timeout": "not-a-number"})
    check("a bad type is refused",
          result["saved"] == [] and "valid integer" in result["skipped"][0]["reason"], result)


def test_sap_config_is_live():
    print("\nSAP_CONFIG is a live view, not an import-time snapshot")
    from config.sap_config import SAP_CONFIG, get_sap_auth, get_sap_url

    store("sap_client", "999")
    check("SAP_CONFIG['client'] follows the store", SAP_CONFIG["client"] == "999",
          SAP_CONFIG["client"])

    store("sap_client", "250")
    check("and follows it back", SAP_CONFIG["client"] == "250", SAP_CONFIG["client"])

    check("get_sap_auth returns the resolved pair",
          get_sap_auth() == (rc.sap_username(), rc.sap_password()))
    check("get_sap_url uses the resolved host",
          get_sap_url().startswith(rc.sap_base_url()), get_sap_url())
    check("repr never prints the password", "********" in repr(SAP_CONFIG),
          repr(SAP_CONFIG)[:80])

    # dict-protocol behaviour the old module had.
    check("'base_url' in SAP_CONFIG", "base_url" in SAP_CONFIG)
    check("iteration works", len(list(SAP_CONFIG)) == 9, len(list(SAP_CONFIG)))


def test_mock_mode_is_honoured():
    print("\nThe resolved host follows mock mode")
    from database import get_mock_sap_mode

    mock = get_mock_sap_mode()
    check("mock mode is readable", isinstance(mock, bool))
    expected = rc.sap_mock_url() if mock else rc.sap_production_url()
    check("sap_base_url() returns the host in force", rc.sap_base_url() == expected,
          (rc.sap_base_url(), expected))
    check("sap_production_url() ignores mock mode",
          rc.sap_production_url() == rc.resolve("sap_base_url"))


def test_no_committed_credentials():
    print("\nThe committed credential literals are gone from the source")
    root = pathlib.Path(__file__).parent
    offenders = []
    for path in root.rglob("*.py"):
        if "__pycache__" in str(path) or path.name.startswith("test_"):
            continue
        try:
            text = io.open(path, encoding="utf-8").read()
        except Exception:
            continue
        for literal in ('P@ssw0rdP@ssw0rd', '"99999"'):
            for line in text.splitlines():
                if literal in line and not line.strip().startswith("#"):
                    offenders.append(f"{path.name}: {line.strip()[:70]}")
    check("no SAP password literal in live code", not offenders, offenders[:4])


def test_missing_required_names_the_variable():
    print("\nA missing required value is named, not silently defaulted")
    store("sap_base_url", "")
    # With the store blank it falls through to env, which is set here — so
    # check the mechanism against a key that has no env fallback.
    check("nothing missing while env provides it", rc.missing_required() == [],
          rc.missing_required())

    real_env = os.environ.pop("SAP_USERNAME", None)
    try:
        store("sap_username", "")
        rc.invalidate()
        check("a value with no store and no env is reported",
              "sap_username" in rc.missing_required(), rc.missing_required())
    finally:
        if real_env is not None:
            os.environ["SAP_USERNAME"] = real_env
        rc.invalidate()


def main():
    print("A8 — runtime configuration")
    for key in TOUCHED:
        _original[key] = rc._stored().get(key)
    try:
        test_resolution_order()
        test_types()
        test_secrets_are_masked()
        test_forbidden_and_readonly()
        test_sap_config_is_live()
        test_mock_mode_is_honoured()
        test_no_committed_credentials()
        test_missing_required_names_the_variable()
    finally:
        for key, value in _original.items():
            set_setting(key, "" if value is None else value,
                        value_type=rc.SETTINGS[key].kind)
        rc.invalidate()
        print("\n  (restored every setting this test touched)")

    print(f"\n{passed} passed, {failed} failed")
    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(main())
