import os

from services import runtime_config

# A8: SAP_CONFIG used to be a module-level dict of os.getenv() calls, evaluated
# at import, carrying the production host, username and password as its literal
# defaults. Nothing short of a restart could change it — which is why "change
# the SAP URL" was a developer task, and why the credentials shipped in the
# repository.
#
# It is now a live view over services/runtime_config (database -> .env ->
# documented default). Existing readers keep working unchanged:
# SAP_CONFIG["base_url"] still reads, it just resolves at the moment of the read
# instead of at import.


class _LiveSapConfig(dict):
    """
    Mapping view over runtime_config.

    Subclasses dict so anything doing an isinstance check, or `**SAP_CONFIG`,
    still behaves — but every lookup resolves now rather than at import.
    """

    _RESOLVERS = {
        "base_url": runtime_config.sap_base_url,
        "endpoint": lambda: runtime_config.sap_endpoint("orders"),
        "username": runtime_config.sap_username,
        "password": runtime_config.sap_password,
        "client": runtime_config.sap_client,
        "timeout": runtime_config.sap_timeout,
        "max_retries": lambda: int(os.getenv("SAP_MAX_RETRIES", "3")),
        "mock_mode": lambda: _mock_mode(),
        "fallback_mode": lambda: os.getenv("SAP_FALLBACK_MODE", "true").lower() == "true",
    }

    def __getitem__(self, key):
        resolver = self._RESOLVERS.get(key)
        if resolver is None:
            raise KeyError(key)
        return resolver()

    def get(self, key, default=None):
        try:
            return self[key]
        except KeyError:
            return default

    def keys(self):
        return self._RESOLVERS.keys()

    def __iter__(self):
        return iter(self._RESOLVERS)

    def __len__(self):
        return len(self._RESOLVERS)

    def __contains__(self, key):
        return key in self._RESOLVERS

    def items(self):
        return [(key, self[key]) for key in self._RESOLVERS]

    def values(self):
        return [self[key] for key in self._RESOLVERS]

    def __repr__(self):
        # Never print the password.
        shown = {
            key: ("********" if key == "password" else self[key])
            for key in self._RESOLVERS
        }
        return f"LiveSapConfig({shown})"


def _mock_mode() -> bool:
    """Mock mode lives in system_settings and is toggled from Admin → Demo."""
    try:
        from database import get_mock_sap_mode
        return get_mock_sap_mode()
    except Exception:
        return os.getenv("SAP_MOCK_MODE", "true").lower() == "true"


SAP_CONFIG = _LiveSapConfig()


class _LiveConfirmationEndpoints(dict):
    """The two confirmation endpoints, resolved at lookup."""

    _KEYS = {"online": "confirm_online", "offline": "confirm_offline"}

    def __getitem__(self, key):
        name = self._KEYS.get(key)
        if name is None:
            raise KeyError(key)
        return runtime_config.sap_endpoint(name)

    def get(self, key, default=None):
        try:
            return self[key]
        except KeyError:
            return default

    def keys(self):
        return self._KEYS.keys()

    def __iter__(self):
        return iter(self._KEYS)

    def __len__(self):
        return len(self._KEYS)

    def __contains__(self, key):
        return key in self._KEYS

    def items(self):
        return [(key, self[key]) for key in self._KEYS]

    def values(self):
        return [self[key] for key in self._KEYS]


SAP_CONFIRMATION_ENDPOINTS = _LiveConfirmationEndpoints()


def get_sap_url():
    return f"{runtime_config.sap_base_url()}{runtime_config.sap_endpoint('orders')}"


def get_sap_auth():
    return runtime_config.sap_auth()
