import sys
import contextlib


from avalon.vendor.Qt import QtCore, QtWidgets


class Popup(QtWidgets.QDialog):
    """A Popup that moves itself to bottom right of screen on show event.

    The UI contains a message label and a red highlighted button to "show"
    or perform another custom action from this pop-up.

    """

    on_clicked = QtCore.Signal()

    def __init__(self, parent=None, *args, **kwargs):
        super(Popup, self).__init__(parent=parent, *args, **kwargs)
        self.setContentsMargins(0, 0, 0, 0)

        # Layout
        layout = QtWidgets.QHBoxLayout(self)
        layout.setContentsMargins(10, 5, 10, 10)

        # Increase spacing slightly for readability
        layout.setSpacing(10)

        message = QtWidgets.QLabel("")
        message.setStyleSheet("""
        QLabel {
            font-size: 12px;
        }
        """)
        button = QtWidgets.QPushButton("Show")
        button.setSizePolicy(QtWidgets.QSizePolicy.Maximum,
                           QtWidgets.QSizePolicy.Maximum)
        button.setStyleSheet("""QPushButton { background-color: #BB0000 }""")

        layout.addWidget(message)
        layout.addWidget(button)

        # Default size
        self.resize(400, 40)

        self.widgets = {
            "message": message,
            "button": button,
        }

        # Signals
        button.clicked.connect(self._on_clicked)

        # Set default title
        self.setWindowTitle("Popup")

    def setMessage(self, message):
        self.widgets['message'].setText(message)

    def setButtonText(self, text):
        self.widgets["button"].setText(text)

    def _on_clicked(self):
        """Callback for when the 'show' button is clicked.

        Raises the parent (if any)

        """

        parent = self.parent()
        self.close()

        # Trigger the signal
        self.on_clicked.emit()

        if parent:
            parent.raise_()

    def showEvent(self, event):

        # Position popup based on contents on show event
        geo = self.calculate_window_geometry()
        self.setGeometry(geo)

        return super(Popup, self).showEvent(event)

    def calculate_window_geometry(self):
        """Respond to status changes

        On creation, align window with screen bottom right.

        """

        window = self

        width = window.width()
        width = max(width, window.minimumWidth())

        height = window.height()
        height = max(height, window.sizeHint().height())

        desktop_geometry = QtWidgets.QDesktopWidget().availableGeometry()
        screen_geometry = window.geometry()

        screen_width = screen_geometry.width()
        screen_height = screen_geometry.height()

        # Calculate width and height of system tray
        systray_width = screen_geometry.width() - desktop_geometry.width()
        systray_height = screen_geometry.height() - desktop_geometry.height()

        padding = 10

        x = screen_width - width
        y = screen_height - height

        x -= systray_width + padding
        y -= systray_height + padding

        return QtCore.QRect(x, y, width, height)


class PopupUpdateKeys(Popup):
    """Popup with Update Keys checkbox (intended for Maya)"""

    on_clicked_state = QtCore.Signal(bool)

    def __init__(self, parent=None, *args, **kwargs):
        Popup.__init__(self, parent=parent, *args, **kwargs)

        layout = self.layout()

        # Insert toggle for Update keys
        toggle = QtWidgets.QCheckBox("Update Keys")
        layout.insertWidget(1, toggle)
        self.widgets["toggle"] = toggle

        self.on_clicked.connect(self.emit_click_with_state)

        layout.insertStretch(1, 1)

    def emit_click_with_state(self):
        """Emit the on_clicked_state signal with the toggled state"""
        checked = self.widgets["toggle"].isChecked()
        self.on_clicked_state.emit(checked)


@contextlib.contextmanager
def application():
    app = QtWidgets.QApplication(sys.argv)
    yield
    app.exec_()


if __name__ == "__main__":
    with application():
        dialog = Popup()
        dialog.setMessage("There are outdated containers in your Maya scene.")
        dialog.show()
