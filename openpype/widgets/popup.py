import sys
import logging
import contextlib


from Qt import QtCore, QtWidgets

log = logging.getLogger(__name__)


class Popup(QtWidgets.QDialog):

    on_show = QtCore.Signal()

    def __init__(self, parent=None, *args, **kwargs):
        super(Popup, self).__init__(parent=parent, *args, **kwargs)
        self.setContentsMargins(0, 0, 0, 0)

        # Layout
        layout = QtWidgets.QHBoxLayout(self)
        layout.setContentsMargins(10, 5, 10, 10)
        message = QtWidgets.QLabel("")
        message.setStyleSheet("""
        QLabel {
            font-size: 12px;
        }
        """)
        show = QtWidgets.QPushButton("Show")
        show.setSizePolicy(QtWidgets.QSizePolicy.Maximum,
                           QtWidgets.QSizePolicy.Maximum)
        show.setStyleSheet("""QPushButton { background-color: #BB0000 }""")

        layout.addWidget(message)
        layout.addWidget(show)

        # Size
        self.resize(400, 40)
        geometry = self.calculate_window_geometry()
        self.setGeometry(geometry)

        self.widgets = {
            "message": message,
            "show": show,
        }

        # Signals
        show.clicked.connect(self._on_show_clicked)

        # Set default title
        self.setWindowTitle("Popup")

    def setMessage(self, message):
        self.widgets['message'].setText(message)

    def _on_show_clicked(self):
        """Callback for when the 'show' button is clicked.

        Raises the parent (if any)

        """

        parent = self.parent()
        self.close()

        # Trigger the signal
        self.on_show.emit()

        if parent:
            parent.raise_()

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


class Popup2(Popup):

    on_show = QtCore.Signal()

    def __init__(self, parent=None, *args, **kwargs):
        Popup.__init__(self, parent=parent, *args, **kwargs)

        layout = self.layout()

        # Add toggle
        toggle = QtWidgets.QCheckBox("Update Keys")
        layout.insertWidget(1, toggle)
        self.widgets["toggle"] = toggle

        layout.insertStretch(1, 1)

        # Update button text
        fix = self.widgets["show"]
        fix.setText("Fix")

    def calculate_window_geometry(self):
        """Respond to status changes

        On creation, align window with screen bottom right.

        """
        parent_widget = self.parent()

        desktop = QtWidgets.QApplication.desktop()
        if parent_widget:
            screen = desktop.screenNumber(parent_widget)
        else:
            screen = desktop.screenNumber(desktop.cursor().pos())
        center_point = desktop.screenGeometry(screen).center()

        frame_geo = self.frameGeometry()
        frame_geo.moveCenter(center_point)

        return frame_geo


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
