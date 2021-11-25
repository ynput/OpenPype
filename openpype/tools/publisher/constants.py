from Qt import QtCore

# ID of context item in instance view
CONTEXT_ID = "context"
CONTEXT_LABEL = "Options"

# Allowed symbols for subset name (and variant)
# - characters, numbers, unsercore and dash
VARIANT_TOOLTIP = (
    "Variant may contain alphabetical characters (a-Z)"
    "\nnumerical characters (0-9) dot (\".\") or underscore (\"_\")."
)

# Roles for instance views
INSTANCE_ID_ROLE = QtCore.Qt.UserRole + 1
SORT_VALUE_ROLE = QtCore.Qt.UserRole + 2
IS_GROUP_ROLE = QtCore.Qt.UserRole + 3
CREATOR_IDENTIFIER_ROLE = QtCore.Qt.UserRole + 4
FAMILY_ROLE = QtCore.Qt.UserRole + 5


__all__ = (
    "CONTEXT_ID",

    "VARIANT_TOOLTIP",

    "INSTANCE_ID_ROLE",
    "SORT_VALUE_ROLE",
    "IS_GROUP_ROLE",
    "CREATOR_IDENTIFIER_ROLE",
    "FAMILY_ROLE"
)
