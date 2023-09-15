from qtpy import QtWidgets, QtCore
from openpype.tools.flickcharm import FlickCharm


class TreeView(QtWidgets.QTreeView):
    """Ultimate TreeView with flick charm and double click signals.

    Tree view have deselectable mode, which allows to deselect items by
    clicking on item area without any items.

    Todos:
        Add to tools utils.
    """

    double_clicked_left = QtCore.Signal()
    double_clicked_right = QtCore.Signal()

    def __init__(self, *args, **kwargs):
        super(TreeView, self).__init__(*args, **kwargs)
        self._deselectable = False

        self._flick_charm_activated = False
        self._flick_charm = FlickCharm(parent=self)
        self._before_flick_scroll_mode = None

    def is_deselectable(self):
        return self._deselectable

    def set_deselectable(self, deselectable):
        self._deselectable = deselectable

    deselectable = property(is_deselectable, set_deselectable)

    def mousePressEvent(self, event):
        if self._deselectable:
            index = self.indexAt(event.pos())
            if not index.isValid():
                # clear the selection
                self.clearSelection()
                # clear the current index
                self.setCurrentIndex(QtCore.QModelIndex())
        super(TreeView, self).mousePressEvent(event)

    def mouseDoubleClickEvent(self, event):
        if event.button() == QtCore.Qt.LeftButton:
            self.double_clicked_left.emit()

        elif event.button() == QtCore.Qt.RightButton:
            self.double_clicked_right.emit()

        return super(TreeView, self).mouseDoubleClickEvent(event)

    def activate_flick_charm(self):
        if self._flick_charm_activated:
            return
        self._flick_charm_activated = True
        self._before_flick_scroll_mode = self.verticalScrollMode()
        self._flick_charm.activateOn(self)
        self.setVerticalScrollMode(QtWidgets.QAbstractItemView.ScrollPerPixel)

    def deactivate_flick_charm(self):
        if not self._flick_charm_activated:
            return
        self._flick_charm_activated = False
        self._flick_charm.deactivateFrom(self)
        if self._before_flick_scroll_mode is not None:
            self.setVerticalScrollMode(self._before_flick_scroll_mode)


class BaseOverlayFrame(QtWidgets.QFrame):
    """Base frame for overlay widgets.

    Has implemented automated resize and event filtering.
    """

    def __init__(self, parent):
        super(BaseOverlayFrame, self).__init__(parent)
        self.setObjectName("OverlayFrame")

        self._parent = parent

    def setVisible(self, visible):
        super(BaseOverlayFrame, self).setVisible(visible)
        if visible:
            self._parent.installEventFilter(self)
            self.resize(self._parent.size())
        else:
            self._parent.removeEventFilter(self)

    def eventFilter(self, obj, event):
        if event.type() == QtCore.QEvent.Resize:
            self.resize(obj.size())

        return super(BaseOverlayFrame, self).eventFilter(obj, event)
