import re
from Qt import QtCore


# Item identifier (unique ID - uuid4 is used)
IDENTIFIER_ROLE = QtCore.Qt.UserRole + 1
# Item has duplicated name (Asset and Task items)
DUPLICATED_ROLE = QtCore.Qt.UserRole + 2
# It is possible to move and rename items
# - that is disabled if e.g. Asset has published content
HIERARCHY_CHANGE_ABLE_ROLE = QtCore.Qt.UserRole + 3
# Item is marked for deletion
# - item will be deleted after hitting save
REMOVED_ROLE = QtCore.Qt.UserRole + 4
# Item type in string
ITEM_TYPE_ROLE = QtCore.Qt.UserRole + 5
# Item has opened editor (per column)
EDITOR_OPENED_ROLE = QtCore.Qt.UserRole + 6

# Role for project model
PROJECT_NAME_ROLE = QtCore.Qt.UserRole + 7

# Allowed symbols for any name
NAME_ALLOWED_SYMBOLS = "a-zA-Z0-9_"
NAME_REGEX = re.compile("^[" + NAME_ALLOWED_SYMBOLS + "]*$")
