import os
from Qt import QtWidgets, QtGui, QtCore
from .categories import (
    CategoryState,
    SystemWidget,
    ProjectWidget
)
from .widgets import ShadowWidget
from .. import style

from openpype.api import get_system_settings


class MainWidget(QtWidgets.QWidget):
    widget_width = 1000
    widget_height = 600

    def __init__(self, user_role, parent=None):
        super(MainWidget, self).__init__(parent)

        self._user_password = ""
        self._reset_on_show = True

        self.setObjectName("MainWidget")
        self.setWindowTitle("OpenPype Settings")

        self.resize(self.widget_width, self.widget_height)

        stylesheet = style.load_stylesheet()
        self.setStyleSheet(stylesheet)
        self.setWindowIcon(QtGui.QIcon(style.app_icon_path()))

        header_tab_widget = QtWidgets.QTabWidget(parent=self)

        studio_widget = SystemWidget(user_role, header_tab_widget)
        project_widget = ProjectWidget(user_role, header_tab_widget)

        tab_widgets = [
            studio_widget,
            project_widget
        ]

        header_tab_widget.addTab(studio_widget, "System")
        header_tab_widget.addTab(project_widget, "Project")

        layout = QtWidgets.QVBoxLayout(self)
        layout.setContentsMargins(5, 5, 5, 5)
        layout.setSpacing(0)
        layout.addWidget(header_tab_widget)

        self.setLayout(layout)

        self._shadow_widget = ShadowWidget("Working...", self)
        self._shadow_widget.setVisible(False)

        for tab_widget in tab_widgets:
            tab_widget.saved.connect(self._on_tab_save)
            tab_widget.state_changed.connect(self._on_state_change)

        self.tab_widgets = tab_widgets

    def _on_tab_save(self, source_widget):
        for tab_widget in self.tab_widgets:
            tab_widget.on_saved(source_widget)

    def _on_state_change(self):
        any_working = False
        for widget in self.tab_widgets:
            if widget.state is CategoryState.Working:
                any_working = True
                break

        if (
            (any_working and self._shadow_widget.isVisible())
            or (not any_working and not self._shadow_widget.isVisible())
        ):
            return

        self._shadow_widget.setVisible(any_working)

        # Process events to apply shadow widget visibility
        app = QtWidgets.QApplication.instance()
        if app:
            app.processEvents()

    def showEvent(self, event):
        super(MainWidget, self).showEvent(event)
        if self._reset_on_show:
            self.reset()

    def _on_password_dialog(self, value):
        print(value)
        self._user_password = value
        system_settings = get_system_settings()
        password = system_settings["general"]["settings_password"]

        if not self._user_password == password:
            self.close()
        else:
            self.reset()

    def reset(self):
        system_settings = get_system_settings()
        password = system_settings["general"]["settings_password"]

        validated = self._user_password == password

        if not validated:
            self._on_state_change()

            system_settings = get_system_settings()
            password = system_settings["general"]["settings_password"]

            dialog = PasswordDialog(password, self)
            dialog.setModal(True)
            dialog.open()
            dialog.finished.connect(self._on_password_dialog)
            return

        for tab_widget in self.tab_widgets:
            tab_widget.reset()

        if self._reset_on_show:
            self._reset_on_show = False


class PasswordDialog(QtWidgets.QDialog):
    """Stupidly simple dialog to compare password from general settings."""
    finished = QtCore.Signal(str)

    def __init__(self, password, parent):
        super(PasswordDialog, self).__init__(parent)

        self.setWindowTitle("Settings Password")
        self.resize(300, 120)

        self._result = ""
        self._expected_result = password

        # Password input
        password_widget = QtWidgets.QWidget(self)

        password_label = QtWidgets.QLabel("Password:", password_widget)

        password_input = QtWidgets.QLineEdit(password_widget)
        password_input.setEchoMode(QtWidgets.QLineEdit.Password)

        current_dir = os.path.join(
            os.path.dirname(os.path.abspath(__file__))
        )
        show_password_icon_path = os.path.join(current_dir, "eye.png")
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

    def keyPressEvent(self, event):
        if event.key() in (QtCore.Qt.Key_Return, QtCore.Qt.Key_Enter):
            self._on_ok_click()
            return event.accept()
        super(PasswordDialog, self).keyPressEvent(event)

    def closeEvent(self, event):
        self.finished.emit(self._result)
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
