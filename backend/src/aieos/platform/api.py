"""Interface công khai của `platform` (Architecture §3 quy tắc 1, 8; D-42)."""

from aieos.platform.config import (
    VARIABLES,
    ConfigError,
    Kind,
    Process,
    Secret,
    Settings,
    Variable,
    is_secret_name,
    load_settings,
    load_settings_or_exit,
)

__all__ = [
    "VARIABLES",
    "ConfigError",
    "Kind",
    "Process",
    "Secret",
    "Settings",
    "Variable",
    "is_secret_name",
    "load_settings",
    "load_settings_or_exit",
]
