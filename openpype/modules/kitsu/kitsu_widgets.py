from Qt import QtWidgets, QtCore, QtGui

from openpype import style
from openpype.modules.kitsu.utils.credentials import (
    clear_credentials,
    load_credentials,
    save_credentials,
    set_credentials_envs,
    validate_credentials,
)
from openpype.resources import get_resource
from openpype.settings.lib import (
    get_system_settings,
)

from openpype.widgets.password_dialog import PressHoverButton


class KitsuPasswordDialog(QtWidgets.QDialog):
    """Kitsu login dialog."""

    finished = QtCore.Signal(bool)

    def __init__(self, parent=None):
        super(KitsuPasswordDialog, self).__init__(parent)

        self.setWindowTitle("Kitsu Credentials")
        self.resize(300, 120)

        system_settings = get_system_settings()
        user_login, user_pwd = load_credentials()
        remembered = bool(user_login or user_pwd)

        self._final_result = None
        self._connectable = bool(
            system_settings["modules"].get("kitsu", {}).get("server")
        )

        # Server label
        server_message = (
            system_settings["modules"]["kitsu"]["server"]
            if self._connectable
            else "no server url set in Studio Settings..."
        )
        server_label = QtWidgets.QLabel(
            f"Server: {server_message}",
            self,
        )

        # Login input
        login_widget = QtWidgets.QWidget(self)

        login_label = QtWidgets.QLabel("Login:", login_widget)

        login_input = QtWidgets.QLineEdit(
            login_widget,
            text=user_login if remembered else None,
        )
        login_input.setPlaceholderText("Your Kitsu account login...")

        login_layout = QtWidgets.QHBoxLayout(login_widget)
        login_layout.setContentsMargins(0, 0, 0, 0)
        login_layout.addWidget(login_label)
        login_layout.addWidget(login_input)

        # Password input
        password_widget = QtWidgets.QWidget(self)

        password_label = QtWidgets.QLabel("Password:", password_widget)

        password_input = QtWidgets.QLineEdit(
            password_widget,
            text=user_pwd if remembered else None,
        )
        password_input.setPlaceholderText("Your password...")
        password_input.setEchoMode(QtWidgets.QLineEdit.Password)

        show_password_icon_path = get_resource("icons", "eye.png")
        show_password_icon = QtGui.QIcon(show_password_icon_path)
        show_password_btn = PressHoverButton(password_widget)
        show_password_btn.setObjectName("PasswordBtn")
        show_password_btn.setIcon(show_password_icon)
        show_password_btn.setFocusPolicy(QtCore.Qt.ClickFocus)

        password_layout = QtWidgets.QHBoxLayout(password_widget)
        password_layout.setContentsMargins(0, 0, 0, 0)
        password_layout.addWidget(password_label)
        password_layout.addWidget(password_input)
        password_layout.addWidget(show_password_btn)

        # Message label
        message_label = QtWidgets.QLabel("", self)

        # Buttons
        buttons_widget = QtWidgets.QWidget(self)

        remember_checkbox = QtWidgets.QCheckBox("Remember", buttons_widget)
        remember_checkbox.setObjectName("RememberCheckbox")
        remember_checkbox.setChecked(remembered)

        ok_btn = QtWidgets.QPushButton("Ok", buttons_widget)
        cancel_btn = QtWidgets.QPushButton("Cancel", buttons_widget)

        buttons_layout = QtWidgets.QHBoxLayout(buttons_widget)
        buttons_layout.setContentsMargins(0, 0, 0, 0)
        buttons_layout.addWidget(remember_checkbox)
        buttons_layout.addStretch(1)
        buttons_layout.addWidget(ok_btn)
        buttons_layout.addWidget(cancel_btn)

        # Main layout
        layout = QtWidgets.QVBoxLayout(self)
        layout.addSpacing(5)
        layout.addWidget(server_label, 0)
        layout.addSpacing(5)
        layout.addWidget(login_widget, 0)
        layout.addWidget(password_widget, 0)
        layout.addWidget(message_label, 0)
        layout.addStretch(1)
        layout.addWidget(buttons_widget, 0)

        ok_btn.clicked.connect(self._on_ok_click)
        cancel_btn.clicked.connect(self._on_cancel_click)
        show_password_btn.change_state.connect(self._on_show_password)

        self.login_input = login_input
        self.password_input = password_input
        self.remember_checkbox = remember_checkbox
        self.message_label = message_label

        self.setStyleSheet(style.load_stylesheet())

    def result(self):
        return self._final_result

    def keyPressEvent(self, event):
        if event.key() in (QtCore.Qt.Key_Return, QtCore.Qt.Key_Enter):
            self._on_ok_click()
            return event.accept()
        super(KitsuPasswordDialog, self).keyPressEvent(event)

    def closeEvent(self, event):
        super(KitsuPasswordDialog, self).closeEvent(event)
        self.finished.emit(self.result())

    def _on_ok_click(self):
        # Check if is connectable
        if not self._connectable:
            self.message_label.setText(
                "Please set server url in Studio Settings!"
            )
            return

        # Collect values
        login_value = self.login_input.text()
        pwd_value = self.password_input.text()
        remember = self.remember_checkbox.isChecked()

        # Authenticate
        if validate_credentials(login_value, pwd_value):
            set_credentials_envs(login_value, pwd_value)
        else:
            self.message_label.setText("Authentication failed...")
            return

        # Remember password cases
        if remember:
            save_credentials(login_value, pwd_value)
        else:
            # Clear local settings
            clear_credentials()

            # Clear input fields
            self.login_input.clear()
            self.password_input.clear()

        self._final_result = True
        self.close()

    def _on_show_password(self, show_password):
        if show_password:
            echo_mode = QtWidgets.QLineEdit.Normal
        else:
            echo_mode = QtWidgets.QLineEdit.Password
        self.password_input.setEchoMode(echo_mode)

    def _on_cancel_click(self):
        self.close()
