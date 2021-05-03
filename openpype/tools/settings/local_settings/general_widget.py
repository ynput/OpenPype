import getpass

from Qt import QtWidgets


class LocalGeneralWidgets(QtWidgets.QWidget):
    def __init__(self, parent):
        super(LocalGeneralWidgets, self).__init__(parent)

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
        username = ""
        is_admin = False
        if value:
            username = value.get("username", username)
            is_admin = value.get("is_admin", is_admin)

        self.username_input.setText(username)

        if self.is_admin_input.isChecked() != is_admin:
            self.is_admin_input.setChecked(is_admin)

    def _on_admin_check_change(self):
        self.is_admin_input.setChecked(False)

    def settings_value(self):
        # Add changed
        # If these have changed then
        output = {}
        username = self.username_input.text()
        if username:
            output["username"] = username
        # Do not return output yet since we don't have mechanism to save or
        #   load these data through api calls
        return output
