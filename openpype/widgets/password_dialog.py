from qtpy import QtWidgets, QtCore, QtGui

from openpype import style
from openpype.resources import get_resource

from openpype.settings import get_system_settings
from openpype.settings.lib import (
    get_local_settings,
    save_local_settings
)


class PressHoverButton(QtWidgets.QPushButton):
    _mouse_pressed = False
    _mouse_hovered = False
    change_state = QtCore.Signal(bool)

    def mousePressEvent(self, event):
        self._mouse_pressed = True
        self._mouse_hovered = True
        self.change_state.emit(self._mouse_hovered)
        super(PressHoverButton, self).mousePressEvent(event)

    def mouseReleaseEvent(self, event):
        self._mouse_pressed = False
        self._mouse_hovered = False
        self.change_state.emit(self._mouse_hovered)
        super(PressHoverButton, self).mouseReleaseEvent(event)

    def mouseMoveEvent(self, event):
        mouse_pos = self.mapFromGlobal(QtGui.QCursor.pos())
        under_mouse = self.rect().contains(mouse_pos)
        if under_mouse != self._mouse_hovered:
            self._mouse_hovered = under_mouse
            self.change_state.emit(self._mouse_hovered)

        super(PressHoverButton, self).mouseMoveEvent(event)


class PasswordDialog(QtWidgets.QDialog):
    """Stupidly simple dialog to compare password from general settings."""
    finished = QtCore.Signal(bool)

    def __init__(self, parent=None, allow_remember=True):
        super(PasswordDialog, self).__init__(parent)

        self.setWindowTitle("Admin Password")
        self.resize(300, 120)

        system_settings = get_system_settings()

        self._expected_result = (
            system_settings["general"].get("admin_password")
        )
        self._final_result = None
        self._allow_remember = allow_remember

        # Password input
        password_widget = QtWidgets.QWidget(self)

        password_label = QtWidgets.QLabel("Password:", password_widget)

        password_input = QtWidgets.QLineEdit(password_widget)
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

        message_label = QtWidgets.QLabel("", self)

        # Buttons
        buttons_widget = QtWidgets.QWidget(self)

        remember_checkbox = QtWidgets.QCheckBox("Remember", buttons_widget)
        remember_checkbox.setObjectName("RememberCheckbox")
        remember_checkbox.setVisible(allow_remember)

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
        layout.addSpacing(10)
        layout.addWidget(password_widget, 0)
        layout.addWidget(message_label, 0)
        layout.addStretch(1)
        layout.addWidget(buttons_widget, 0)

        ok_btn.clicked.connect(self._on_ok_click)
        cancel_btn.clicked.connect(self._on_cancel_click)
        show_password_btn.change_state.connect(self._on_show_password)

        self.password_input = password_input
        self.remember_checkbox = remember_checkbox
        self.message_label = message_label

        self.setStyleSheet(style.load_stylesheet())

    def remember_password(self):
        if not self._allow_remember:
            return False
        return self.remember_checkbox.isChecked()

    def result(self):
        if self._final_result is None:
            return False
        return self._final_result == self._expected_result

    def keyPressEvent(self, event):
        if event.key() in (QtCore.Qt.Key_Return, QtCore.Qt.Key_Enter):
            self._on_ok_click()
            return event.accept()
        super(PasswordDialog, self).keyPressEvent(event)

    def closeEvent(self, event):
        super(PasswordDialog, self).closeEvent(event)
        self.finished.emit(self.result())

    def _on_ok_click(self):
        input_value = self.password_input.text()
        if input_value != self._expected_result:
            self.message_label.setText("Invalid password. Try it again...")
            self.password_input.setFocus()
            return

        if self.remember_password():
            local_settings = get_local_settings()
            if "general" not in local_settings:
                local_settings["general"] = {}

            local_settings["general"]["is_admin"] = True

            save_local_settings(local_settings)

        self._final_result = input_value
        self.close()

    def _on_show_password(self, show_password):
        if show_password:
            echo_mode = QtWidgets.QLineEdit.Normal
        else:
            echo_mode = QtWidgets.QLineEdit.Password
        self.password_input.setEchoMode(echo_mode)

    def _on_cancel_click(self):
        self.close()
