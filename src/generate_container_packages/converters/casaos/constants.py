"""Shared constants for CasaOS converter.

Constants used across converter components to avoid duplication
and reduce coupling between modules.
"""

from pathlib import Path

# Default values for metadata enrichment
# These are used when CasaOS apps lack required HaLOS metadata fields
DEFAULT_VERSION = "1.0.0"
DEFAULT_MAINTAINER_DOMAIN = "auto-converted@casaos.io"
DEFAULT_LICENSE = "Unknown"
DEFAULT_ARCHITECTURE = "all"
REQUIRED_ROLE_TAG = "role::container-app"


def get_default_mappings_dir() -> Path:
    """Get the default mappings directory path.

    Returns:
        Path to the default CasaOS mappings directory

    Example:
        >>> mappings_dir = get_default_mappings_dir()
        >>> assert (mappings_dir / "categories.yaml").exists()
    """
    # Navigate from this file's location to the mappings directory
    # Structure: src/generate_container_packages/converters/casaos/constants.py
    #         -> mappings/casaos/
    return Path(__file__).parent.parent.parent.parent.parent / "mappings" / "casaos"
