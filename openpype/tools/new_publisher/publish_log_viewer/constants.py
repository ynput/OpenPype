from Qt import QtCore


ITEM_ID_ROLE = QtCore.Qt.UserRole + 1
ITEM_IS_GROUP_ROLE = QtCore.Qt.UserRole + 2
ITEM_LABEL_ROLE = QtCore.Qt.UserRole + 3
ITEM_ERRORED_ROLE = QtCore.Qt.UserRole + 4
PLUGIN_SKIPPED_ROLE = QtCore.Qt.UserRole + 5
PLUGIN_PASSED_ROLE = QtCore.Qt.UserRole + 6
INSTANCE_REMOVED_ROLE = QtCore.Qt.UserRole + 7


__all__ = (
    "ITEM_ID_ROLE",
    "ITEM_IS_GROUP_ROLE",
    "ITEM_LABEL_ROLE",
    "ITEM_ERRORED_ROLE",
    "PLUGIN_SKIPPED_ROLE",
    "INSTANCE_REMOVED_ROLE"
)
