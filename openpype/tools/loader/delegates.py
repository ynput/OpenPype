from qtpy import QtWidgets, QtGui, QtCore


class LoadedInSceneDelegate(QtWidgets.QStyledItemDelegate):
    """Delegate for Loaded in Scene state columns.

    Shows "yes" or "no" for True or False values
    Colorizes green or dark grey based on True or False values

    """

    def __init__(self, *args, **kwargs):
        super(LoadedInSceneDelegate, self).__init__(*args, **kwargs)
        self._colors = {
            True: QtGui.QColor(80, 170, 80),
            False: QtGui.QColor(90, 90, 90)
        }

    def displayText(self, value, locale):
        return "yes" if value else "no"

    def initStyleOption(self, option, index):
        super(LoadedInSceneDelegate, self).initStyleOption(option, index)

        # Colorize based on value
        value = index.data(QtCore.Qt.DisplayRole)
        color = self._colors[bool(value)]
        option.palette.setBrush(QtGui.QPalette.Text, color)
