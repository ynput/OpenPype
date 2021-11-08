from Qt import QtCore

# roles for use in model's data function
# separated into its own file because Python 2 hosts (lib contains attrs)
ProviderRole = QtCore.Qt.UserRole + 12
ProgressRole = QtCore.Qt.UserRole + 14
DateRole = QtCore.Qt.UserRole + 16
FailedRole = QtCore.Qt.UserRole + 18
HeaderNameRole = QtCore.Qt.UserRole + 20
FullItemRole = QtCore.Qt.UserRole + 22
EditIconRole = QtCore.Qt.UserRole + 24
