import re


# Metadata keys for work with studio and project overrides
M_OVERRIDDEN_KEY = "__overriden_keys__"
# Metadata key for storing information about environments
M_ENVIRONMENT_KEY = "__environment_keys__"
# Metadata key for storing dynamic created labels
M_DYNAMIC_KEY_LABEL = "__dynamic_keys_labels__"

METADATA_KEYS = frozenset([
    M_OVERRIDDEN_KEY,
    M_ENVIRONMENT_KEY,
    M_DYNAMIC_KEY_LABEL
])

# Keys where studio's system overrides are stored
GLOBAL_SETTINGS_KEY = "global_settings"
SYSTEM_SETTINGS_KEY = "system_settings"
PROJECT_SETTINGS_KEY = "project_settings"
PROJECT_ANATOMY_KEY = "project_anatomy"
LOCAL_SETTING_KEY = "local_settings"

LEGACY_SETTINGS_VERSION = "legacy"

# Schema hub names
SCHEMA_KEY_SYSTEM_SETTINGS = "system_schema"
SCHEMA_KEY_PROJECT_SETTINGS = "projects_schema"

DEFAULT_PROJECT_KEY = "__default_project__"

KEY_ALLOWED_SYMBOLS = "a-zA-Z0-9-_ "
KEY_REGEX = re.compile(r"^[{}]+$".format(KEY_ALLOWED_SYMBOLS))


__all__ = (
    "M_OVERRIDDEN_KEY",
    "M_ENVIRONMENT_KEY",
    "M_DYNAMIC_KEY_LABEL",

    "METADATA_KEYS",

    "SYSTEM_SETTINGS_KEY",
    "PROJECT_SETTINGS_KEY",
    "PROJECT_ANATOMY_KEY",
    "LOCAL_SETTING_KEY",

    "SCHEMA_KEY_SYSTEM_SETTINGS",
    "SCHEMA_KEY_PROJECT_SETTINGS",

    "DEFAULT_PROJECT_KEY",

    "KEY_ALLOWED_SYMBOLS",
    "KEY_REGEX"
)
