# backend/routes/engineering_routes.py
"""
Engineering settings — Workstream A, task A8.

Backs the /engineering screen. A plant engineer changes SAP connection details
here instead of editing `.env` on the server and restarting.

    GET  /api/engineering/settings    every setting, grouped, secrets masked
    PUT  /api/engineering/settings    persist changes
    POST /api/engineering/test-sap    try the configured connection

Everything resolves through services/runtime_config.py, which is the single
reader (database -> .env -> documented default). This module only validates and
presents.

AUTH: these routes handle credentials, so unlike the mapping routes they
require an authenticated admin.
"""

import logging

from flask import Blueprint, jsonify, request

from services import runtime_config

log = logging.getLogger("engineering")

engineering_bp = Blueprint("engineering", __name__, url_prefix="/api/engineering")


def _require_admin():
    """
    (user, None) when the caller is an admin, otherwise (None, response).

    The mapping routes are unprotected, which is its own problem — but this one
    reads and writes credentials, so it does not inherit that.
    """
    from services.auth_service import AuthService

    try:
        # Raises when the header is missing or the token does not verify.
        user = AuthService.get_current_user()
    except Exception as exc:
        log.warning("Could not identify the caller: %s", exc)
        return None, (jsonify({"error": "Sign in required"}), 401)

    roles = (user or {}).get("roles") or []
    if "admin" not in [str(role).lower() for role in roles]:
        return None, (jsonify({"error": "Administrator access required"}), 403)

    return user, None


@engineering_bp.route("/settings", methods=["GET"])
def get_settings():
    """
    Every setting with its value, where that value came from, and what it does.

    Secrets come back masked. The `source` field is the useful part: it tells an
    engineer whether a value is stored, inherited from `.env`, or just the
    built-in default — which is otherwise invisible and the usual reason a
    change "does not take".
    """
    _, denied = _require_admin()
    if denied:
        return denied

    try:
        settings = runtime_config.describe()
    except Exception as exc:
        log.exception("Could not read settings")
        return jsonify({"error": f"Could not read settings: {exc}"}), 500

    groups = []
    for entry in settings:
        group = next((g for g in groups if g["name"] == entry["group"]), None)
        if group is None:
            group = {"name": entry["group"], "settings": []}
            groups.append(group)
        group["settings"].append(entry)

    return jsonify({
        "groups": groups,
        "missing_required": runtime_config.missing_required(),
        "excluded": [
            {"name": "POSTGRES_URL",
             "reason": "The engine is built at import, before any connection "
                       "exists. You cannot read the Postgres address out of "
                       "Postgres."},
            {"name": "PORT / CORS_ALLOWED_ORIGINS",
             "reason": "Read once at startup. A control here would silently do "
                       "nothing until a restart."},
            {"name": "JWT_SECRET",
             "reason": "Saving a new value would invalidate every session "
                       "including yours, mid-save, and move a secret out of a "
                       "file with OS permissions. Rotate it on the server."},
        ],
    }), 200


@engineering_bp.route("/settings", methods=["PUT"])
def update_settings():
    """
    Persist changes. Body: {"settings": {key: value, ...}}.

    A secret sent back as its mask is treated as unchanged, so saving the form
    without retyping a password does not blank it.
    """
    _, denied = _require_admin()
    if denied:
        return denied

    payload = request.get_json(silent=True) or {}
    updates = payload.get("settings")
    if not isinstance(updates, dict) or not updates:
        return jsonify({"error": "Body must be {\"settings\": {key: value}}"}), 400

    try:
        result = runtime_config.apply(updates)
    except Exception as exc:
        log.exception("Could not save settings")
        return jsonify({"error": f"Could not save settings: {exc}"}), 500

    log.info("Engineering settings saved: %s", ", ".join(result["saved"]) or "(none)")
    return jsonify({
        **result,
        "settings": runtime_config.describe(),
        "missing_required": runtime_config.missing_required(),
    }), 200


@engineering_bp.route("/test-sap", methods=["POST"])
def test_sap():
    """
    Try the configured SAP connection and report exactly what happened.

    Uses the values in force, including anything just saved — the point is to
    check a change before an order depends on it.

    Optionally accepts an override body so a value can be tried without saving
    it first; overrides are used for this request only and never persisted.
    """
    _, denied = _require_admin()
    if denied:
        return denied

    import requests

    from database import get_mock_sap_mode

    payload = request.get_json(silent=True) or {}
    endpoint_name = payload.get("endpoint", "orders")

    base = payload.get("base_url") or runtime_config.sap_base_url()
    endpoint = runtime_config.sap_endpoint(endpoint_name)
    client = payload.get("client") or runtime_config.sap_client()
    username = payload.get("username") or runtime_config.sap_username()
    password = payload.get("password")
    if not password or password == runtime_config.MASK:
        password = runtime_config.sap_password()
    timeout = runtime_config.sap_timeout()

    url = f"{base}{endpoint}"
    mock = get_mock_sap_mode()

    result = {
        "url": url,
        "client": client,
        "mock_mode": mock,
        "timeout": timeout,
        "username": username,
    }

    if not endpoint:
        result.update(ok=False, error=f"No endpoint configured for '{endpoint_name}'")
        return jsonify(result), 400

    try:
        response = requests.get(
            url,
            params={"client": client} if client else None,
            auth=(username, password) if username else None,
            timeout=timeout,
            verify=False,
        )
        result.update(
            ok=response.status_code < 400,
            status_code=response.status_code,
            elapsed_ms=int(response.elapsed.total_seconds() * 1000),
        )
        if response.status_code >= 400:
            result["error"] = f"SAP returned HTTP {response.status_code}"
            result["body"] = response.text[:400]
    except requests.exceptions.Timeout:
        result.update(ok=False, error=f"Timed out after {timeout}s")
    except requests.exceptions.ConnectionError as exc:
        result.update(ok=False, error=f"Could not connect: {exc}")
    except Exception as exc:
        result.update(ok=False, error=f"{type(exc).__name__}: {exc}")

    if not result["ok"] and mock:
        result["hint"] = (
            "Mock SAP mode is on, so this used the mock URL. If the mock server "
            "is not running, that is the failure you are seeing rather than a "
            "problem with the production settings."
        )

    return jsonify(result), 200
