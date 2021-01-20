import enum


# Metadata keys for work with studio and project overrides
M_OVERRIDEN_KEY = "__overriden_keys__"
# Metadata key for storing information about environments
M_ENVIRONMENT_KEY = "__environment_keys__"
# Metadata key for storing dynamic created labels
M_DYNAMIC_KEY_LABEL = "__dynamic_keys_labels__"
# NOTE key popping not implemented yet
M_POP_KEY = "__pop_key__"

METADATA_KEYS = (
    M_OVERRIDEN_KEY,
    M_ENVIRONMENT_KEY,
    M_DYNAMIC_KEY_LABEL,
    M_POP_KEY
)

# File where studio's system overrides are stored
SYSTEM_SETTINGS_KEY = "system_settings"
PROJECT_SETTINGS_KEY = "project_settings"
PROJECT_ANATOMY_KEY = "project_anatomy"

WRAPPER_TYPES = ["form", "collapsible-wrap"]

__all__ = (
    "M_OVERRIDEN_KEY",
    "M_ENVIRONMENT_KEY",
    "M_DYNAMIC_KEY_LABEL",
    "M_POP_KEY",

    "METADATA_KEYS",

    "SYSTEM_SETTINGS_KEY",
    "PROJECT_SETTINGS_KEY",
    "PROJECT_ANATOMY_KEY"
)


class OverrideState(enum.Enum):
    DEFAULTS = object()
    STUDIO = object()
    PROJECT = object()
