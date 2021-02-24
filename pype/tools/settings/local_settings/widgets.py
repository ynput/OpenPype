from Qt import QtWidgets
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
