from Qt import QtCore


CONTEXT_ID = "context"

SUBSET_NAME_ALLOWED_SYMBOLS = "a-zA-Z0-9_\."
VARIANT_TOOLTIP = (
    "Variant may contain alphabetical characters (a-Z)"
    "\nnumerical characters (0-9) dot (\".\") or underscore (\"_\")."
)
INSTANCE_ID_ROLE = QtCore.Qt.UserRole + 1
SORT_VALUE_ROLE = QtCore.Qt.UserRole + 2


__all__ = (
    "CONTEXT_ID",

    "SUBSET_NAME_ALLOWED_SYMBOLS",
    "VARIANT_TOOLTIP",

    "INSTANCE_ID_ROLE",
    "SORT_VALUE_ROLE"
)
