import getpass

from Qt import QtWidgets, QtCore
from openpype.tools.settings import (
    is_password_required,
    PasswordDialog
)


class LocalGeneralWidgets(QtWidgets.QWidget):
    def __init__(self, parent):
        super(LocalGeneralWidgets, self).__init__(parent)

        self._loading_local_settings = False

        username_input = QtWidgets.QLineEdit(self)
        username_input.setPlaceholderText(getpass.getuser())

        is_admin_input = QtWidgets.QCheckBox(self)

        layout = QtWidgets.QFormLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)

        layout.addRow("OpenPype Username", username_input)
        layout.addRow("Admin permissions", is_admin_input)

        is_admin_input.stateChanged.connect(self._on_admin_check_change)

        self.username_input = username_input
        self.is_admin_input = is_admin_input

    def update_local_settings(self, value):
        self._loading_local_settings = True

        username = ""
        is_admin = False
        if value:
            username = value.get("username", username)
            is_admin = value.get("is_admin", is_admin)

        self.username_input.setText(username)

        if self.is_admin_input.isChecked() != is_admin:
            self.is_admin_input.setChecked(is_admin)

        self._loading_local_settings = False

    def _on_admin_check_change(self):
        if self._loading_local_settings:
            return

        if not self.is_admin_input.isChecked():
            return

        if not is_password_required():
            return

        dialog = PasswordDialog(self)
        dialog.setModal(True)
        dialog.exec_()
        result = dialog.result()
        if self.is_admin_input.isChecked() != result:
            if result:
                state = QtCore.Qt.Checked
            else:
                state = QtCore.Qt.Unchecked
            self.is_admin_input.setCheckState(state)

    def settings_value(self):
        # Add changed
        # If these have changed then
        output = {}
        username = self.username_input.text()
        if username:
            output["username"] = username

        is_admin = self.is_admin_input.isChecked()
        if is_admin:
            output["is_admin"] = is_admin
        return output
