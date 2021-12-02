import getpass

from Qt import QtWidgets, QtCore
from openpype.lib import is_admin_password_required
from openpype.widgets import PasswordDialog
from openpype.tools.utils import PlaceholderLineEdit


class LocalGeneralWidgets(QtWidgets.QWidget):
    def __init__(self, parent):
        super(LocalGeneralWidgets, self).__init__(parent)

        self._loading_local_settings = False

        username_input = PlaceholderLineEdit(self)
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
            # Use state as `stateChanged` is connected to callbacks
            if is_admin:
                state = QtCore.Qt.Checked
            else:
                state = QtCore.Qt.Unchecked
            self.is_admin_input.setCheckState(state)

        self._loading_local_settings = False

    def _on_admin_check_change(self):
        if self._loading_local_settings:
            return

        if not self.is_admin_input.isChecked():
            return

        if not is_admin_password_required():
            return

        dialog = PasswordDialog(self, False)
        dialog.setModal(True)
        dialog.exec_()
        result = dialog.result()
        if self.is_admin_input.isChecked() != result:
            # Use state as `stateChanged` is connected to callbacks
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
