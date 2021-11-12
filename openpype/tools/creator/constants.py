from Qt import QtCore


FAMILY_ROLE = QtCore.Qt.UserRole + 1
ITEM_ID_ROLE = QtCore.Qt.UserRole + 2

SEPARATOR = "---"
SEPARATORS = {"---", "---separator---"}

# TODO regex should be defined by schema
SubsetAllowedSymbols = "a-zA-Z0-9_."
