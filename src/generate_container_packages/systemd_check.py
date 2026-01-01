"""Systemd check injection for container apps.

This module injects an environment variable check into docker-compose.yml
that prevents direct `docker compose up` usage. The check requires
HALOS_SYSTEMD_STARTED=1 which is only set by the systemd unit.
"""

import copy
from typing import Any

# Error message shown when someone tries to run docker compose directly
SYSTEMD_ERROR_MESSAGE = (
    "Container must be started via systemctl, not docker compose directly"
)

# Environment variable name set by systemd
SYSTEMD_CHECK_VAR = "HALOS_SYSTEMD_STARTED"

# The check uses bash's required variable syntax: ${VAR:?error}
SYSTEMD_CHECK_VALUE = f"${{{SYSTEMD_CHECK_VAR}:?{SYSTEMD_ERROR_MESSAGE}}}"


def inject_systemd_check(compose: dict[str, Any]) -> dict[str, Any]:
    """Inject systemd check into docker-compose services.

    Adds a hidden environment variable to the first service that requires
    HALOS_SYSTEMD_STARTED to be set. If someone runs `docker compose up`
    directly without going through systemd, they'll get a clear error message.

    Args:
        compose: Original docker-compose dictionary

    Returns:
        Modified docker-compose dictionary with systemd check added
    """
    # Deep copy to avoid modifying original
    compose = copy.deepcopy(compose)

    services = compose.get("services", {})
    if not services:
        return compose

    # Add check to the first service only (one check is enough)
    first_service_name = next(iter(services))
    service_config = services[first_service_name]

    if not isinstance(service_config, dict):
        return compose

    # Get or create environment section
    env = service_config.get("environment", [])

    # The check variable - uses a name starting with underscore to indicate internal use
    check_entry = f"_HALOS_SYSTEMD_CHECK={SYSTEMD_CHECK_VALUE}"

    if isinstance(env, list):
        # List format: ["VAR=value", ...]
        # Check if already present
        if not any(e.startswith("_HALOS_SYSTEMD_CHECK=") for e in env):
            env.append(check_entry)
        service_config["environment"] = env
    elif isinstance(env, dict):
        # Dict format: {VAR: value, ...}
        if "_HALOS_SYSTEMD_CHECK" not in env:
            env["_HALOS_SYSTEMD_CHECK"] = SYSTEMD_CHECK_VALUE
        service_config["environment"] = env
    else:
        # No environment - create list
        service_config["environment"] = [check_entry]

    return compose
