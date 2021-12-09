from Qt import QtWidgets, QtGui

from .tools import (
    load_stylesheet,
    get_openpype_icon_path
)


class MessageDialog(QtWidgets.QDialog):
    """Simple message dialog with title, message and OK button."""
    def __init__(self, title, message):
        super(MessageDialog, self).__init__()

        # Set logo as icon of window
        icon_path = get_openpype_icon_path()
        pixmap_openpype_logo = QtGui.QPixmap(icon_path)
        self.setWindowIcon(QtGui.QIcon(pixmap_openpype_logo))

        # Set title
        self.setWindowTitle(title)

        # Set message
        label_widget = QtWidgets.QLabel(message, self)

        ok_btn = QtWidgets.QPushButton("OK", self)
        btns_layout = QtWidgets.QHBoxLayout()
        btns_layout.addStretch(1)
        btns_layout.addWidget(ok_btn, 0)

        layout = QtWidgets.QVBoxLayout(self)
        layout.addWidget(label_widget, 1)
        layout.addLayout(btns_layout, 0)

        ok_btn.clicked.connect(self._on_ok_clicked)

        self._label_widget = label_widget
        self._ok_btn = ok_btn

    def _on_ok_clicked(self):
        self.close()

    def showEvent(self, event):
        super(MessageDialog, self).showEvent(event)
        self.setStyleSheet(load_stylesheet())
