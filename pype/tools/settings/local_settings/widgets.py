from Qt import QtWidgets, QtCore
from pype.tools.settings.settings.widgets.widgets import (
    ExpandingWidget,
    SpacerWidget
)
from pype.tools.settings.settings.widgets.lib import CHILD_OFFSET


class Separator(QtWidgets.QFrame):
    def __init__(self, height=None, parent=None):
        super(Separator, self).__init__(parent)
        if height is None:
            height = 2

        splitter_item = QtWidgets.QWidget(self)
        splitter_item.setStyleSheet("background-color: #21252B;")
        splitter_item.setMinimumHeight(height)
        splitter_item.setMaximumHeight(height)

        layout = QtWidgets.QHBoxLayout(self)
        layout.setContentsMargins(5, 5, 5, 5)
        layout.addWidget(splitter_item)


class ProxyLabelWidget(QtWidgets.QWidget):
    def __init__(self, label, mouse_release_callback, parent=None):
        super(ProxyLabelWidget, self).__init__(parent)

        self.mouse_release_callback = mouse_release_callback

        layout = QtWidgets.QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)

        label_widget = QtWidgets.QLabel(label, self)
        layout.addWidget(label_widget)

        self.setAttribute(QtCore.Qt.WA_TranslucentBackground)

        self.label_widget = label_widget

    def setText(self, text):
        self.label_widget.setText(text)

    def mouseReleaseEvent(self, event):
        if self.mouse_release_callback:
            return self.mouse_release_callback(event)
        return super(ProxyLabelWidget, self).mouseReleaseEvent(event)
