from qtpy import QtCore, QtGui

# ID of context item in instance view
CONTEXT_ID = "context"
CONTEXT_LABEL = "Context"
# Not showed anywhere - used as identifier
CONTEXT_GROUP = "__ContextGroup__"

CONVERTOR_ITEM_GROUP = "Incompatible subsets"

# Allowed symbols for subset name (and variant)
# - characters, numbers, unsercore and dash
VARIANT_TOOLTIP = (
    "Variant may contain alphabetical characters (a-Z)"
    "\nnumerical characters (0-9) dot (\".\") or underscore (\"_\")."
)

INPUTS_LAYOUT_HSPACING = 4
INPUTS_LAYOUT_VSPACING = 2

# Roles for instance views
INSTANCE_ID_ROLE = QtCore.Qt.UserRole + 1
SORT_VALUE_ROLE = QtCore.Qt.UserRole + 2
IS_GROUP_ROLE = QtCore.Qt.UserRole + 3
CREATOR_IDENTIFIER_ROLE = QtCore.Qt.UserRole + 4
CREATOR_THUMBNAIL_ENABLED_ROLE = QtCore.Qt.UserRole + 5
FAMILY_ROLE = QtCore.Qt.UserRole + 6
GROUP_ROLE = QtCore.Qt.UserRole + 7
CONVERTER_IDENTIFIER_ROLE = QtCore.Qt.UserRole + 8
CREATOR_SORT_ROLE = QtCore.Qt.UserRole + 9

ResetKeySequence = QtGui.QKeySequence(
    QtCore.Qt.ControlModifier | QtCore.Qt.Key_R
)

__all__ = (
    "CONTEXT_ID",
    "CONTEXT_LABEL",

    "VARIANT_TOOLTIP",

    "INPUTS_LAYOUT_HSPACING",
    "INPUTS_LAYOUT_VSPACING",

    "INSTANCE_ID_ROLE",
    "SORT_VALUE_ROLE",
    "IS_GROUP_ROLE",
    "CREATOR_IDENTIFIER_ROLE",
    "CREATOR_THUMBNAIL_ENABLED_ROLE",
    "CREATOR_SORT_ROLE",
    "FAMILY_ROLE",
    "GROUP_ROLE",
    "CONVERTER_IDENTIFIER_ROLE",

    "ResetKeySequence",
)
