from Qt import QtCore


ITEM_ID_ROLE = QtCore.Qt.UserRole + 1
ITEM_IS_GROUP_ROLE = QtCore.Qt.UserRole + 2
ITEM_LABEL_ROLE = QtCore.Qt.UserRole + 3
PLUGIN_SKIPPED_ROLE = QtCore.Qt.UserRole + 4
PLUGIN_ERRORED_ROLE = QtCore.Qt.UserRole + 5
INSTANCE_REMOVED_ROLE = QtCore.Qt.UserRole + 6


__all__ = (
    "ITEM_ID_ROLE",
    "ITEM_IS_GROUP_ROLE",
    "ITEM_LABEL_ROLE",
    "PLUGIN_SKIPPED_ROLE",
    "PLUGIN_ERRORED_ROLE",
    "INSTANCE_REMOVED_ROLE"
)
