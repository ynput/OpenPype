import re
from Qt import QtCore


IDENTIFIER_ROLE = QtCore.Qt.UserRole + 1
DUPLICATED_ROLE = QtCore.Qt.UserRole + 2
HIERARCHY_CHANGE_ABLE_ROLE = QtCore.Qt.UserRole + 3
REMOVED_ROLE = QtCore.Qt.UserRole + 4

NAME_ALLOWED_SYMBOLS = "a-zA-Z0-9_"
NAME_REGEX = re.compile("^[" + NAME_ALLOWED_SYMBOLS + "]*$")
