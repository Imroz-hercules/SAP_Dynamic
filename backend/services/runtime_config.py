# backend/services/runtime_config.py
"""
Runtime configuration — Workstream A, task A8.

The single reader for plant connection settings. Resolves, in order:

    system_settings (database)  ->  environment / .env  ->  documented default

`.env` stays as the first-boot bootstrap: a machine with an empty database still
starts, and whatever it starts with becomes the visible default on the
Engineering page.

WHY THIS EXISTS

The same SAP credentials were read from `os.getenv` in six separate places,
each with the production literals as their fallback default:

    config/sap_config.py:5-13          SAP_CONFIG, at import
    routes/kpi_routes.py:55-58, :85    at import
    routes/sap_sync.py:326-329         at import
    services/kpi_shift_auto_sync.py:32-35   at import
    services/sap_confirmation.py:29-34      per instance
    services/sap_real_client.py:16-22       fallback + per instance

Four of those read at *import* time, so nothing short of a restart could change
them — which is why "change the SAP URL" was a developer task. They now all
resolve through here, per call.

WHAT IS DELIBERATELY NOT HERE

  POSTGRES_URL   database.py builds the engine at import, before any connection
                 exists. You cannot read the Postgres address out of Postgres.
  PORT, CORS     read once at startup; a control for them would silently do
                 nothing until a restart.
  JWT_SECRET     saving a new value invalidates every session including the
                 engineer's own, mid-save, and moves a secret from a file with
                 OS permissions into a database table plus an HTTP endpoint.

  SCADA / PO poll intervals
                 APScheduler jobs are registered with literal interval
                 arguments and the scheduler object is a local inside
                 start_scheduler(), so changing a stored value does nothing
                 without reschedule_job. app_scheduler.py is Workstream B's
                 file and its intervals are B5's task; they are exposed here
                 READ-ONLY so an engineer can see the running value.
"""

from __future__ import annotations

import logging
import os
import threading
import time
from typing import Any, Dict, Optional

log = logging.getLogger("runtime_config")

CACHE_TTL_SECONDS = 15.0

_cache: Dict[str, Any] = {"values": None, "read_at": 0.0}
_lock = threading.Lock()


class Setting:
    """One configurable value, and everything the page needs to render it."""

    def __init__(self, key, env_var, default, group, label,
                 kind="string", secret=False, editable=True, help="", minimum=None):
        self.key = key
        self.env_var = env_var
        self.default = default
        self.group = group
        self.label = label
        self.kind = kind          # string | integer | float | boolean | url
        self.secret = secret      # masked on read, never returned in full
        self.editable = editable  # False -> shown for reference only
        self.help = help
        # Smallest meaningful value. A timeout of 0 is not a setting, it is a
        # broken one - every request would fail instantly. Enforced on write,
        # and ignored on read so a bad row already in the table cannot make the
        # page disagree with what the application actually uses.
        self.minimum = minimum


# The order here is the order the page renders.
SETTINGS_LIST = [
    # ---- SAP connection ----------------------------------------------------
    Setting("sap_base_url", "SAP_BASE_URL", "https://vhmioqs4ci.sap.mc3.com.sa:44300",
            "SAP connection", "Base URL", kind="url",
            help="The production SAP host. Used whenever mock mode is off."),
    Setting("sap_mock_url", "SAP_MOCK_URL", "http://localhost:6000/mock",
            "SAP connection", "Mock URL", kind="url",
            help="Where requests go while mock SAP mode is on."),
    Setting("sap_username", "SAP_USERNAME", "",
            "SAP connection", "Username"),
    Setting("sap_password", "SAP_PASSWORD", "",
            "SAP connection", "Password", secret=True),
    Setting("sap_client", "SAP_CLIENT", "250",
            "SAP connection", "Client",
            help="SAP client number. Note that the KPI shift auto-sync has "
                 "historically passed 200 instead; see the Engineering notes."),
    Setting("sap_timeout", "SAP_TIMEOUT", 30, "SAP connection", "Timeout (s)",
            kind="integer", minimum=1,
            help="Per-request timeout for every SAP call."),

    # ---- SAP endpoints -----------------------------------------------------
    Setting("sap_endpoint_orders", "SAP_ENDPOINT", "/zmi_get_orders/GETORD",
            "SAP endpoints", "Process orders"),
    Setting("sap_endpoint_confirm_online", "SAP_ENDPOINT_CONFIRM_ONLINE",
            "/zmi_conf_online/CONF", "SAP endpoints", "Confirm (online)"),
    Setting("sap_endpoint_confirm_offline", "SAP_ENDPOINT_CONFIRM_OFFLINE",
            "/zmi_conf_offlin/CONFOFF", "SAP endpoints", "Confirm (offline)"),
    Setting("sap_endpoint_kpi_milling", "SAP_ENDPOINT_KPI_MILLING",
            "/zmi_kpi_mill/MKPI", "SAP endpoints", "Milling KPI"),
    Setting("sap_endpoint_kpi_packing", "SAP_ENDPOINT_KPI_PACKING",
            "/zmi_kpi_pack/PKPI", "SAP endpoints", "Packing KPI"),
    Setting("sap_endpoint_hercules_raw", "SAP_ENDPOINT_HERCULES_RAW",
            "/zmi_raw_hercl/HERC", "SAP endpoints", "Hercules raw"),

    # ---- SQL Server --------------------------------------------------------
    Setting("mssql_enabled", "MSSQL_ENABLED", True, "SQL Server link",
            "Enabled", kind="boolean",
            help="Off on machines with no ODBC driver or SQL Server. SCADA "
                 "reads then come from the emulator."),
    Setting("mssql_url", "MSSQL_URL", "", "SQL Server link",
            "Connection URL", secret=True,
            help="Read-only SCADA link. Takes effect on the next restart — the "
                 "engine is built at import."),

    # ---- Validator ---------------------------------------------------------
    Setting("auto_validator_interval_seconds", None, 1.0, "Validator",
            "Cycle interval (s)", kind="float", minimum=0.1,
            help="How long the auto-validation worker sleeps between cycles. "
                 "Clamped to 0.1-60. Applies within about 10 seconds."),
    Setting("default_plant", None, "3130", "Validator", "Default plant",
            help="Assumed for orders that arrive from SAP without a plant. "
                 "Used to pick shift rows out of shift_master."),

    # ---- Reference only ----------------------------------------------------
    Setting("scada_poll_interval_sec", "SCADA_POLL_INTERVAL_SEC", 60,
            "Intervals (restart required)", "SCADA poll (s)",
            kind="integer", editable=False, minimum=1,
            help="Baked into the APScheduler job at startup. Changing it needs "
                 "a restart. Making it live is Workstream B's task (B5)."),
    Setting("po_pull_interval_hours", "PO_PULL_INTERVAL_HOURS", 3.0,
            "Intervals (restart required)", "SAP order pull (h)",
            kind="float", editable=False, minimum=0.1,
            help="Same — baked into the job at startup."),
]

SETTINGS: Dict[str, Setting] = {s.key: s for s in SETTINGS_LIST}

# Never accept these through the API, whatever a client sends.
FORBIDDEN_KEYS = frozenset({
    "POSTGRES_URL", "postgres_url",
    "JWT_SECRET", "jwt_secret",
    "PORT", "port",
    "CORS_ALLOWED_ORIGINS", "cors_allowed_origins",
})

MASK = "********"


# =============================================================================
# Resolution
# =============================================================================

def _coerce(setting: Setting, raw: Any) -> Any:
    """Turn a stored string into the setting's declared type."""
    if raw is None:
        return None
    if setting.kind == "boolean":
        if isinstance(raw, bool):
            return raw
        return str(raw).strip().lower() in ("1", "true", "yes", "on")
    if setting.kind == "integer":
        try:
            return int(float(raw))
        except (TypeError, ValueError):
            return None
    if setting.kind == "float":
        try:
            return float(raw)
        except (TypeError, ValueError):
            return None
    return str(raw)


def _below_minimum(setting: Setting, value: Any) -> bool:
    """True when a numeric value is below what the setting can meaningfully be."""
    if setting.minimum is None or isinstance(value, bool):
        return False
    try:
        return float(value) < float(setting.minimum)
    except (TypeError, ValueError):
        return False


def _load_from_db() -> Dict[str, Any]:
    """Every stored value, raw. One query, not one per key."""
    from models.system_settings import get_all_settings

    return get_all_settings() or {}


def _stored() -> Dict[str, Any]:
    """Cached view of the settings table."""
    now = time.time()
    with _lock:
        if _cache["values"] is not None and (now - _cache["read_at"]) < CACHE_TTL_SECONDS:
            return _cache["values"]

    try:
        values = _load_from_db()
    except Exception as exc:
        log.error("Could not read system_settings (%s) — falling back to env", exc)
        with _lock:
            return _cache["values"] or {}

    with _lock:
        _cache["values"] = values
        _cache["read_at"] = now
    return values


def invalidate() -> None:
    """Drop the cache so the next read sees a write immediately."""
    with _lock:
        _cache["values"] = None
        _cache["read_at"] = 0.0


def resolve(key: str) -> Any:
    """
    The value in force for `key`: database, else environment, else default.

    Unknown keys return None rather than raising — a caller asking for
    something that is not configurable is a bug, but not one worth taking the
    plant down for.
    """
    setting = SETTINGS.get(key)
    if setting is None:
        log.warning("resolve() called for unknown setting %r", key)
        return None

    raw = _stored().get(key)
    if raw is not None and str(raw).strip() != "":
        value = _coerce(setting, raw)
        if value is not None and not _below_minimum(setting, value):
            return value

    if setting.env_var:
        env = os.getenv(setting.env_var)
        if env is not None and env.strip() != "":
            value = _coerce(setting, env)
            if value is not None:
                return value

    return setting.default


def source_of(key: str) -> str:
    """Where the value in force came from: 'database', 'env' or 'default'."""
    setting = SETTINGS.get(key)
    if setting is None:
        return "unknown"

    raw = _stored().get(key)
    if raw is not None and str(raw).strip() != "":
        value = _coerce(setting, raw)
        # A stored value the reader will not use must not be reported as the
        # source, or the page shows one number while the app uses another.
        if value is not None and not _below_minimum(setting, value):
            return "database"
    if setting.env_var and (os.getenv(setting.env_var) or "").strip() != "":
        return "env"
    return "default"


def describe(include_secret_values: bool = False) -> list:
    """
    Every setting, with its value, source and metadata — what the page renders.

    Secrets are masked unless explicitly asked for, and the API never asks.
    """
    out = []
    for setting in SETTINGS_LIST:
        value = resolve(setting.key)
        if setting.secret and not include_secret_values:
            value = MASK if (value not in (None, "")) else ""
        out.append({
            "key": setting.key,
            "label": setting.label,
            "group": setting.group,
            "kind": setting.kind,
            "secret": setting.secret,
            "editable": setting.editable,
            "help": setting.help,
            "value": value,
            "source": source_of(setting.key),
            "env_var": setting.env_var,
        })
    return out


# =============================================================================
# Writing
# =============================================================================

def apply(updates: Dict[str, Any]) -> Dict[str, Any]:
    """
    Persist `updates` into system_settings.

    Returns {"saved": [...], "skipped": [{key, reason}, ...]}. Refuses unknown
    keys, non-editable ones, and anything on FORBIDDEN_KEYS. A secret whose
    value comes back as the mask is left alone, so a round-trip through the
    page cannot blank a password.
    """
    from models.system_settings import set_setting

    saved, skipped = [], []

    for key, value in (updates or {}).items():
        if key in FORBIDDEN_KEYS:
            skipped.append({"key": key, "reason": "not configurable at runtime"})
            continue

        setting = SETTINGS.get(key)
        if setting is None:
            skipped.append({"key": key, "reason": "unknown setting"})
            continue
        if not setting.editable:
            skipped.append({"key": key, "reason": "read-only; needs a restart"})
            continue
        if setting.secret and str(value) == MASK:
            skipped.append({"key": key, "reason": "unchanged"})
            continue

        coerced = _coerce(setting, value)
        if coerced is None:
            skipped.append({"key": key, "reason": f"not a valid {setting.kind}"})
            continue
        if _below_minimum(setting, coerced):
            skipped.append({
                "key": key,
                "reason": f"must be at least {setting.minimum}",
            })
            continue

        stored = "true" if coerced is True else "false" if coerced is False else str(coerced)
        if set_setting(key, stored, value_type=setting.kind, description=setting.help):
            saved.append(key)
        else:
            skipped.append({"key": key, "reason": "database write failed"})

    if saved:
        invalidate()
        # A5 and A1 keep their own short caches; drop those too so a change on
        # this page is not held for another TTL behind this one.
        try:
            from routes.order_validation import (
                invalidate_auto_validator_interval,
                invalidate_default_plant,
            )
            invalidate_auto_validator_interval()
            invalidate_default_plant()
        except Exception as exc:
            log.debug("Could not invalidate the validator caches: %s", exc)

    return {"saved": saved, "skipped": skipped}


# =============================================================================
# Typed accessors — what the rest of the backend calls
# =============================================================================

def sap_base_url() -> str:
    """The host in force: the mock host while mock mode is on."""
    from database import get_mock_sap_mode

    if get_mock_sap_mode():
        return str(resolve("sap_mock_url"))
    return str(resolve("sap_base_url"))


def sap_production_url() -> str:
    """The production host, regardless of mock mode."""
    return str(resolve("sap_base_url"))


def sap_mock_url() -> str:
    return str(resolve("sap_mock_url"))


def sap_username() -> str:
    return str(resolve("sap_username") or "")


def sap_password() -> str:
    return str(resolve("sap_password") or "")


def sap_auth() -> tuple:
    return sap_username(), sap_password()


def sap_client() -> str:
    return str(resolve("sap_client"))


def sap_timeout() -> int:
    return int(resolve("sap_timeout") or 30)


def sap_endpoint(name: str) -> str:
    """`orders`, `confirm_online`, `confirm_offline`, `kpi_milling`, ..."""
    return str(resolve(f"sap_endpoint_{name}") or "")


def sap_url(endpoint_name: str = "orders", client: Optional[str] = None) -> str:
    """Full URL for a named endpoint, honouring mock mode."""
    url = f"{sap_base_url()}{sap_endpoint(endpoint_name)}"
    resolved_client = client or sap_client()
    return f"{url}?client={resolved_client}" if resolved_client else url


def mssql_enabled() -> bool:
    return bool(resolve("mssql_enabled"))


def mssql_url() -> str:
    return str(resolve("mssql_url") or "")


def missing_required() -> list:
    """
    Required values that resolve to nothing.

    Used by the Engineering page and by a startup check, so a machine with no
    configuration says which variable is missing instead of silently falling
    back to a committed literal and connecting to production.
    """
    required = ("sap_base_url", "sap_username", "sap_password", "sap_client")
    return [
        key for key in required
        if str(resolve(key) or "").strip() == ""
    ]
