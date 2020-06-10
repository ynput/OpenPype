from .vendor.Qt import QtCore, QtWidgets
from . import model
from .constants import Roles


class ArtistView(QtWidgets.QListView):
    # An item is requesting to be toggled, with optional forced-state
    toggled = QtCore.Signal(QtCore.QModelIndex, object)
    show_perspective = QtCore.Signal(QtCore.QModelIndex)

    def __init__(self, parent=None):
        super(ArtistView, self).__init__(parent)

        self.horizontalScrollBar().hide()
        self.viewport().setAttribute(QtCore.Qt.WA_Hover, True)
        self.setContextMenuPolicy(QtCore.Qt.CustomContextMenu)
        self.setSelectionMode(QtWidgets.QAbstractItemView.ExtendedSelection)
        self.setResizeMode(QtWidgets.QListView.Adjust)
        self.setVerticalScrollMode(QtWidgets.QListView.ScrollPerPixel)

    def event(self, event):
        if not event.type() == QtCore.QEvent.KeyPress:
            return super(ArtistView, self).event(event)

        elif event.key() == QtCore.Qt.Key_Space:
            for index in self.selectionModel().selectedIndexes():
                self.toggled.emit(index, None)

            return True

        elif event.key() == QtCore.Qt.Key_Backspace:
            for index in self.selectionModel().selectedIndexes():
                self.toggled.emit(index, False)

            return True

        elif event.key() == QtCore.Qt.Key_Return:
            for index in self.selectionModel().selectedIndexes():
                self.toggled.emit(index, True)

            return True

        return super(ArtistView, self).event(event)

    def focusOutEvent(self, event):
        self.selectionModel().clear()

    def mouseReleaseEvent(self, event):
        if event.button() == QtCore.Qt.LeftButton:
            indexes = self.selectionModel().selectedIndexes()
            if len(indexes) <= 1 and event.pos().x() < 20:
                for index in indexes:
                    self.toggled.emit(index, None)
            if len(indexes) == 1 and event.pos().x() > self.width() - 40:
                for index in indexes:
                    self.show_perspective.emit(index)

        return super(ArtistView, self).mouseReleaseEvent(event)


class OverviewView(QtWidgets.QTreeView):
    # An item is requesting to be toggled, with optional forced-state
    toggled = QtCore.Signal(QtCore.QModelIndex, object)
    show_perspective = QtCore.Signal(QtCore.QModelIndex)

    def __init__(self, parent=None):
        super(OverviewView, self).__init__(parent)

        self.horizontalScrollBar().hide()
        self.viewport().setAttribute(QtCore.Qt.WA_Hover, True)
        self.setContextMenuPolicy(QtCore.Qt.CustomContextMenu)
        self.setSelectionMode(QtWidgets.QAbstractItemView.ExtendedSelection)
        self.setItemsExpandable(True)
        self.setVerticalScrollMode(QtWidgets.QTreeView.ScrollPerPixel)
        self.setHeaderHidden(True)
        self.setRootIsDecorated(False)
        self.setIndentation(0)

        self.clicked.connect(self.item_expand)

    def event(self, event):
        if not event.type() == QtCore.QEvent.KeyPress:
            return super(OverviewView, self).event(event)

        elif event.key() == QtCore.Qt.Key_Space:
            for index in self.selectionModel().selectedIndexes():
                self.toggled.emit(index, None)

            return True

        elif event.key() == QtCore.Qt.Key_Backspace:
            for index in self.selectionModel().selectedIndexes():
                self.toggled.emit(index, False)

            return True

        elif event.key() == QtCore.Qt.Key_Return:
            for index in self.selectionModel().selectedIndexes():
                self.toggled.emit(index, True)

            return True

        return super(OverviewView, self).event(event)

    def focusOutEvent(self, event):
        self.selectionModel().clear()

    def item_expand(self, index):
        if index.data(Roles.TypeRole) == model.GroupType:
            if self.isExpanded(index):
                self.collapse(index)
            else:
                self.expand(index)

    def mouseReleaseEvent(self, event):
        if event.button() == QtCore.Qt.LeftButton:
            indexes = self.selectionModel().selectedIndexes()
            if len(indexes) == 1:
                index = indexes[0]
                # If instance or Plugin
                if index.data(Roles.TypeRole) in (
                    model.InstanceType, model.PluginType
                ):
                    if event.pos().x() < 20:
                        self.toggled.emit(index, None)
                    elif event.pos().x() > self.width() - 20:
                        self.show_perspective.emit(index)

            # Deselect all group labels
            for index in indexes:
                if index.data(Roles.TypeRole) == model.GroupType:
                    self.selectionModel().select(
                        index, QtCore.QItemSelectionModel.Deselect
                    )

        return super(OverviewView, self).mouseReleaseEvent(event)


class TerminalView(QtWidgets.QTreeView):
    # An item is requesting to be toggled, with optional forced-state
    def __init__(self, parent=None):
        super(TerminalView, self).__init__(parent)
        self.setSelectionBehavior(QtWidgets.QAbstractItemView.SelectRows)
        self.setSelectionMode(QtWidgets.QAbstractItemView.ExtendedSelection)
        self.setAutoScroll(False)
        self.setHeaderHidden(True)
        self.setIndentation(0)
        self.setVerticalScrollMode(QtWidgets.QTreeView.ScrollPerPixel)
        self.verticalScrollBar().setSingleStep(10)
        self.setRootIsDecorated(False)

        self.clicked.connect(self.item_expand)

    def event(self, event):
        if not event.type() == QtCore.QEvent.KeyPress:
            return super(TerminalView, self).event(event)

        elif event.key() == QtCore.Qt.Key_Space:
            for index in self.selectionModel().selectedIndexes():
                if self.isExpanded(index):
                    self.collapse(index)
                else:
                    self.expand(index)

        elif event.key() == QtCore.Qt.Key_Backspace:
            for index in self.selectionModel().selectedIndexes():
                self.collapse(index)

        elif event.key() == QtCore.Qt.Key_Return:
            for index in self.selectionModel().selectedIndexes():
                self.expand(index)

        return super(TerminalView, self).event(event)

    def focusOutEvent(self, event):
        self.selectionModel().clear()

    def item_expand(self, index):
        if index.data(Roles.TypeRole) == model.TerminalLabelType:
            if self.isExpanded(index):
                self.collapse(index)
            else:
                self.expand(index)
                self.model().layoutChanged.emit()
            self.updateGeometry()

    def rowsInserted(self, parent, start, end):
        """Automatically scroll to bottom on each new item added."""
        super(TerminalView, self).rowsInserted(parent, start, end)
        self.updateGeometry()
        self.scrollToBottom()

    def resizeEvent(self, event):
        super(self.__class__, self).resizeEvent(event)
        self.model().layoutChanged.emit()

    def sizeHint(self):
        size = super(TerminalView, self).sizeHint()
        height = (
            self.contentsMargins().top()
            + self.contentsMargins().bottom()
        )
        for idx_i in range(self.model().rowCount()):
            index = self.model().index(idx_i, 0)
            height += self.rowHeight(index)
            if self.isExpanded(index):
                for idx_j in range(index.model().rowCount(index)):
                    child_index = index.child(idx_j, 0)
                    height += self.rowHeight(child_index)

        size.setHeight(height)
        return size
