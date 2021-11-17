from Qt import QtWidgets, QtCore

from .views import (
    TreeViewSpinner,
    DeselectableTreeView
)

ASSET_ID_ROLE = QtCore.Qt.UserRole + 1
ASSET_NAME_ROLE = QtCore.Qt.UserRole + 2
ASSET_LABEL_ROLE = QtCore.Qt.UserRole + 3
ASSET_UNDERLINE_COLORS_ROLE = QtCore.Qt.UserRole + 4


class AssetsView(TreeViewSpinner, DeselectableTreeView):
    """Item view.
    This implements a context menu.
    """

    def __init__(self, parent=None):
        super(AssetsView, self).__init__(parent)
        self.setIndentation(15)
        self.setContextMenuPolicy(QtCore.Qt.CustomContextMenu)
        self.setHeaderHidden(True)

    def mousePressEvent(self, event):
        index = self.indexAt(event.pos())
        if not index.isValid():
            modifiers = QtWidgets.QApplication.keyboardModifiers()
            if modifiers == QtCore.Qt.ShiftModifier:
                return
            elif modifiers == QtCore.Qt.ControlModifier:
                return

        super(AssetsView, self).mousePressEvent(event)

    def set_loading_state(self, loading, empty):
        if self.is_loading != loading:
            if loading:
                self.spinner.repaintNeeded.connect(
                    self.viewport().update
                )
            else:
                self.spinner.repaintNeeded.disconnect()
                self.viewport().update()

        self.is_loading = loading
        self.is_empty = empty
