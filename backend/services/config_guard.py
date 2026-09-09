# backend/services/config_guard.py
"""
Admin guard for the dynamic-configuration write endpoints.

WHY THIS EXISTS

The static-to-dynamic migration moved the numbers that drive production out of
the source and into the database: which SCADA tags exist and whether they are
active (``scada_tags``, B1), and the KPI ceilings and nameplate (``kpi_config``,
B4). That is the point of the migration -- but it also means those tables are
now the production math, and B1/B4 shipped their CRUD endpoints with no
authentication at all.

Measured on 2026-09-08 against the running app, with no token of any kind::

    POST /api/scada-config/tags   {"tag": "ZZ_UNAUTH_PROOF", ...}   -> HTTP 201
    GET  /api/scada-config/tags                                     -> the tag is there
    DELETE /api/scada-config/tags/71                                -> HTTP 200

So anyone who could reach the backend could add a tag, deactivate a real one,
or change a KPI ceiling. Deactivating a tag is the dangerous one: it drops out
of ``allowed_fields()`` and ``poll_keys()``, its readings stop arriving, and the
delta that reaches SAP is computed without it -- a wrong confirmed quantity that
looks like data. That is the same failure the rest of this migration exists to
remove, reachable over HTTP.

``routes/engineering_routes.py`` already had this guard because it reads and
writes credentials, and its docstring recorded that the neighbouring routes did
not inherit it. This module is that guard, factored out.

WHAT IT DOES AND DOES NOT COVER

Writes only. GET stays open, exactly as before, because the screens read these
endpoints to build their tag and KPI lists and several are reachable before a
token exists; restricting reads would change what operators see, which is a
different decision and not one to make silently. ``Frontend/client/src/lib/api.ts``
already attaches the bearer token in ``getJSON`` -- added by A6 in anticipation
of precisely this change -- so the admin screens keep working unchanged.

The mapping routes (``palletizer_mapping``, ``milling_version_mappings``) are
still unprotected. They are a larger surface with their own callers and are
recorded as outstanding rather than changed here.
"""

import logging

from flask import jsonify, request

log = logging.getLogger(__name__)

SAFE_METHODS = frozenset({"GET", "HEAD", "OPTIONS"})


def admin_required_for_writes():
    """
    ``None`` when the request may proceed, otherwise a 401/403 response.

    Written for ``Blueprint.before_request``: returning ``None`` lets Flask
    carry on to the view, and returning a response short-circuits it.
    """
    if request.method in SAFE_METHODS:
        return None

    from services.auth_service import AuthService

    try:
        # Raises when the header is missing or the token does not verify.
        user = AuthService.get_current_user()
    except Exception as exc:
        log.warning(
            "Rejected unauthenticated %s %s: %s", request.method, request.path, exc
        )
        return jsonify({"error": "Sign in required"}), 401

    roles = [str(role).lower() for role in ((user or {}).get("roles") or [])]
    if "admin" not in roles:
        log.warning(
            "Rejected non-admin %s %s (roles=%s)", request.method, request.path, roles
        )
        return jsonify({"error": "Administrator access required"}), 403

    return None
