from qtpy import QtCore


DEFAULT_PROJECT_LABEL = "< Default >"
PROJECT_NAME_ROLE = QtCore.Qt.UserRole + 1
PROJECT_IS_ACTIVE_ROLE = QtCore.Qt.UserRole + 2
PROJECT_IS_SELECTED_ROLE = QtCore.Qt.UserRole + 3
PROJECT_VERSION_ROLE = QtCore.Qt.UserRole + 4

# Save/Extract keys
SETTINGS_PATH_KEY = "__settings_path__"
ROOT_KEY = "__root_key__"
VALUE_KEY = "__value__"
SAVE_TIME_KEY = "__extracted__"
PROJECT_NAME_KEY = "__project_name__"

__all__ = (
    "DEFAULT_PROJECT_LABEL",

    "PROJECT_NAME_ROLE",
    "PROJECT_IS_ACTIVE_ROLE",
    "PROJECT_IS_SELECTED_ROLE",
    "PROJECT_VERSION_ROLE",

    "SETTINGS_PATH_KEY",
    "ROOT_KEY",
    "VALUE_KEY",
    "SAVE_TIME_KEY",
    "PROJECT_NAME_KEY",
)
