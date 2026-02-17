"""MARIS v2 Configuration - Environment-based configuration for all components.

DEPRECATED: Use maris.settings instead.
This module maintains backward compatibility by wrapping maris.settings.
"""

from maris.settings import settings, MARISSettings as MARISConfig


def get_config() -> MARISConfig:
    """Return the singleton settings instance."""
    return settings

