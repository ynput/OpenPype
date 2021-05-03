import os
from Qt import QtWidgets, QtCore, QtGui

from openpype.api import get_system_settings
from .resources import get_resource


class PasswordDialog(QtWidgets.QDialog):
    """Stupidly simple dialog to compare password from general settings."""
    finished = QtCore.Signal(bool)

    def __init__(self, parent):
        super(PasswordDialog, self).__init__(parent)

        self.setWindowTitle("Settings Password")
        self.resize(300, 120)

        system_settings = get_system_settings()

        self._expected_result = (
            system_settings["general"].get("admin_password")
        )
        self._result = ""

        # Password input
        password_widget = QtWidgets.QWidget(self)

        password_label = QtWidgets.QLabel("Password:", password_widget)

        password_input = QtWidgets.QLineEdit(password_widget)
        password_input.setEchoMode(QtWidgets.QLineEdit.Password)

        current_dir = os.path.join(
            os.path.dirname(os.path.abspath(__file__))
        )
        show_password_icon_path = get_resource("images", "eye.png")
        show_password_icon = QtGui.QIcon(show_password_icon_path)
        show_password_btn = QtWidgets.QPushButton(password_widget)
        show_password_btn.setIcon(show_password_icon)
        show_password_btn.setStyleSheet((
            "border: none;padding:0.1em;"
        ))

        password_layout = QtWidgets.QHBoxLayout(password_widget)
        password_layout.setContentsMargins(0, 0, 0, 0)
        password_layout.addWidget(password_label)
        password_layout.addWidget(password_input)
        password_layout.addWidget(show_password_btn)

        message_label = QtWidgets.QLabel("", self)

        # Buttons
        buttons_widget = QtWidgets.QWidget(self)

        ok_btn = QtWidgets.QPushButton("Ok", buttons_widget)
        cancel_btn = QtWidgets.QPushButton("Cancel", buttons_widget)

        buttons_layout = QtWidgets.QHBoxLayout(buttons_widget)
        buttons_layout.setContentsMargins(0, 0, 0, 0)
        buttons_layout.addStretch(1)
        buttons_layout.addWidget(ok_btn)
        buttons_layout.addWidget(cancel_btn)

        # Main layout
        layout = QtWidgets.QVBoxLayout(self)
        layout.addSpacing(10)
        layout.addWidget(password_widget, 0)
        layout.addWidget(message_label, 0)
        layout.addStretch(1)
        layout.addWidget(buttons_widget, 0)

        password_input.textChanged.connect(self._on_text_change)
        ok_btn.clicked.connect(self._on_ok_click)
        cancel_btn.clicked.connect(self._on_cancel_click)
        show_password_btn.clicked.connect(self._on_show_password)

        self.password_input = password_input
        self.message_label = message_label

    def result(self):
        if not self._expected_result:
            return True
        return self._result == self._expected_result

    def keyPressEvent(self, event):
        if event.key() in (QtCore.Qt.Key_Return, QtCore.Qt.Key_Enter):
            self._on_ok_click()
            return event.accept()
        super(PasswordDialog, self).keyPressEvent(event)

    def showEvent(self, event):
        super(PasswordDialog, self).showEvent(event)
        if self.result():
            self.close()

    def closeEvent(self, event):
        self.finished.emit(self.result())
        super(PasswordDialog, self).closeEvent(event)

    def _on_text_change(self, text):
        self._result = text

    def _on_ok_click(self):
        if self._result == self._expected_result:
            self.close()
        self.message_label.setText("Invalid password. Try it again...")

    def _on_show_password(self):
        if self.password_input.echoMode() == QtWidgets.QLineEdit.Password:
            echo_mode = QtWidgets.QLineEdit.Normal
        else:
            echo_mode = QtWidgets.QLineEdit.Password
        self.password_input.setEchoMode(echo_mode)

    def _on_cancel_click(self):
        self._result = ""
        self.close()
