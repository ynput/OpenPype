from openpype.resources import get_image_path
from openpype.tools.flickcharm import FlickCharm

from qtpy import QtWidgets, QtCore, QtGui, QtSvg


class DeselectableTreeView(QtWidgets.QTreeView):
    """A tree view that deselects on clicking on an empty area in the view"""

    def mousePressEvent(self, event):

        index = self.indexAt(event.pos())
        if not index.isValid():
            # clear the selection
            self.clearSelection()
            # clear the current index
            self.setCurrentIndex(QtCore.QModelIndex())

        QtWidgets.QTreeView.mousePressEvent(self, event)


class TreeViewSpinner(QtWidgets.QTreeView):
    size = 160

    def __init__(self, parent=None):
        super(TreeViewSpinner, self).__init__(parent=parent)

        loading_image_path = get_image_path("spinner-200.svg")

        self.spinner = QtSvg.QSvgRenderer(loading_image_path)

        self.is_loading = False
        self.is_empty = True

    def paint_loading(self, event):
        rect = event.rect()
        rect = QtCore.QRectF(rect.topLeft(), rect.bottomRight())
        rect.moveTo(
            rect.x() + rect.width() / 2 - self.size / 2,
            rect.y() + rect.height() / 2 - self.size / 2
        )
        rect.setSize(QtCore.QSizeF(self.size, self.size))
        painter = QtGui.QPainter(self.viewport())
        self.spinner.render(painter, rect)

    def paint_empty(self, event):
        painter = QtGui.QPainter(self.viewport())
        rect = event.rect()
        rect = QtCore.QRectF(rect.topLeft(), rect.bottomRight())
        qtext_opt = QtGui.QTextOption(
            QtCore.Qt.AlignHCenter | QtCore.Qt.AlignVCenter
        )
        painter.drawText(rect, "No Data", qtext_opt)

    def paintEvent(self, event):
        if self.is_loading:
            self.paint_loading(event)
        elif self.is_empty:
            self.paint_empty(event)
        else:
            super(TreeViewSpinner, self).paintEvent(event)


class TreeView(QtWidgets.QTreeView):
    """Ultimate TreeView with flick charm and double click signals.

    Tree view have deselectable mode, which allows to deselect items by
    clicking on item area without any items.

    Todos:
        Add refresh animation.
    """

    double_clicked = QtCore.Signal(QtGui.QMouseEvent)

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
        self.double_clicked.emit(event)

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
