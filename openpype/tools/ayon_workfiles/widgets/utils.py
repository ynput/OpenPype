from qtpy import QtWidgets, QtCore


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
