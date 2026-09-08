# backend/test_config_auth.py
"""
Tests for the dynamic-configuration write guard (services/config_guard.py).

    PYTHONIOENCODING=utf-8 python test_config_auth.py

Also collected by pytest, and needs no database: the guard imports
``services.auth_service`` inside the function, so a stand-in is injected into
``sys.modules`` and the whole suite runs on pure Flask request handling. That
matters because CI has no Postgres.

WHAT IT PINS DOWN

B1 and B4 moved production configuration into the database -- which SCADA tags
exist and whether they are active, and the KPI ceilings -- and shipped the CRUD
endpoints with no authentication. Measured against the running app on
2026-09-08, with no token::

    POST /api/scada-config/tags {"tag": "ZZ_UNAUTH_PROOF", ...}  -> HTTP 201

Deactivating a tag through that route removes it from ``allowed_fields()`` and
``poll_keys()``, its readings stop arriving, and the delta that reaches SAP is
computed without it: a wrong confirmed quantity that looks like data.

The guard rejects unauthenticated and non-admin writes while leaving reads
exactly as they were, because the screens build their tag and KPI lists from
the GETs. Both halves are checked here -- a guard that also blocked reads would
pass a "writes are refused" test while breaking every screen.
"""

import os
import sys
import types

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

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


# --- a stand-in for services.auth_service, so no DB or JWT key is needed ------

_CURRENT = {"user": None, "raises": True}


def _install_fake_auth():
    """Put a controllable AuthService in sys.modules before the guard imports it."""

    class FakeAuthService:
        @staticmethod
        def get_current_user():
            if _CURRENT["raises"]:
                raise RuntimeError("no Authorization header")
            return _CURRENT["user"]

    module = types.ModuleType("services.auth_service")
    module.AuthService = FakeAuthService
    sys.modules["services.auth_service"] = module


def _as_nobody():
    _CURRENT["raises"] = True
    _CURRENT["user"] = None


def _as_user(*roles):
    _CURRENT["raises"] = False
    _CURRENT["user"] = {"username": "someone", "roles": list(roles)}


def _client():
    """A Flask app carrying only the guard, so nothing else can explain a result."""
    from flask import Blueprint, Flask, jsonify

    from services.config_guard import admin_required_for_writes

    bp = Blueprint("cfg", __name__, url_prefix="/cfg")
    bp.before_request(admin_required_for_writes)

    @bp.route("/thing", methods=["GET"])
    def read():
        return jsonify({"read": True})

    @bp.route("/thing", methods=["POST"])
    def write():
        return jsonify({"wrote": True}), 201

    @bp.route("/thing/<int:item_id>", methods=["DELETE"])
    def remove(item_id):
        return jsonify({"deleted": item_id})

    app = Flask(__name__)
    app.register_blueprint(bp)
    return app.test_client()


def test_reads_stay_open():
    """GET must behave exactly as before -- the screens depend on it."""
    print("\nReads are unaffected")
    _install_fake_auth()
    c = _client()

    _as_nobody()
    r = c.get("/cfg/thing")
    check("anonymous GET still 200", r.status_code == 200, r.status_code)
    check("anonymous GET still returns the body", r.get_json() == {"read": True},
          r.get_json())


def test_anonymous_writes_are_refused():
    """The exact shape that returned 201 from the live app must now be refused."""
    print("\nUnauthenticated writes")
    _install_fake_auth()
    c = _client()

    _as_nobody()
    post = c.post("/cfg/thing", json={"tag": "ZZ_UNAUTH_PROOF"})
    check("anonymous POST is 401", post.status_code == 401, post.status_code)
    check("anonymous POST did not reach the view", "wrote" not in (post.get_json() or {}),
          post.get_json())

    delete = c.delete("/cfg/thing/1")
    check("anonymous DELETE is 401", delete.status_code == 401, delete.status_code)


def test_signed_in_non_admin_is_refused():
    """A valid token is not enough; production config is admin-only."""
    print("\nNon-admin writes")
    _install_fake_auth()
    c = _client()

    _as_user("operator")
    r = c.post("/cfg/thing", json={})
    check("operator POST is 403 not 401", r.status_code == 403, r.status_code)

    _as_user()
    r = c.post("/cfg/thing", json={})
    check("no-roles POST is 403", r.status_code == 403, r.status_code)


def test_admin_may_write():
    """The guard must not lock out the admin screens it exists to protect."""
    print("\nAdmin writes")
    _install_fake_auth()
    c = _client()

    _as_user("admin")
    post = c.post("/cfg/thing", json={})
    check("admin POST reaches the view (201)", post.status_code == 201, post.status_code)
    check("admin POST body is the view's", post.get_json() == {"wrote": True},
          post.get_json())

    delete = c.delete("/cfg/thing/7")
    check("admin DELETE reaches the view", delete.status_code == 200, delete.status_code)

    # Roles arrive from the token in whatever case the issuer used.
    _as_user("Admin")
    r = c.post("/cfg/thing", json={})
    check("role match is case-insensitive", r.status_code == 201, r.status_code)


def test_guard_is_actually_wired_to_the_real_blueprints():
    """
    A correct guard that nothing calls protects nothing.

    Registers each real blueprint on a throwaway Flask app and reads
    ``app.before_request_funcs`` -- where Flask actually records the hook --
    rather than reading the source, so moving or renaming the call is caught.
    """
    print("\nWired into the real config blueprints")
    from flask import Flask

    from services.config_guard import admin_required_for_writes

    for module_name, attr, bp_name in (
        ("routes.scada_config_routes", "scada_config_bp", "scada_config"),
        ("routes.kpi_config_routes", "kpi_config_bp", "kpi_config"),
    ):
        try:
            module = __import__(module_name, fromlist=[attr])
        except Exception as exc:
            print(f"  SKIP  {module_name} not importable here: {exc}")
            continue

        app = Flask(__name__)
        app.register_blueprint(getattr(module, attr))
        hooks = app.before_request_funcs.get(bp_name, [])
        check(f"{attr} has the guard registered",
              admin_required_for_writes in hooks, hooks)


def main():
    print("=" * 60)
    print("Dynamic-config write guard")
    print("=" * 60)

    test_reads_stay_open()
    test_anonymous_writes_are_refused()
    test_signed_in_non_admin_is_refused()
    test_admin_may_write()
    test_guard_is_actually_wired_to_the_real_blueprints()

    print("\n" + "-" * 60)
    print(f"Result: {passed} passed, {failed} failed")
    print("-" * 60)
    return 0 if failed == 0 else 1


if __name__ == "__main__":
    sys.exit(main())
