from Qt import QtWidgets


class LocalGeneralWidgets(QtWidgets.QWidget):
    def __init__(self, parent):
        super(LocalGeneralWidgets, self).__init__(parent)

        username_input = QtWidgets.QLineEdit(self)

        layout = QtWidgets.QFormLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)

        layout.addRow("OpenPype Username", username_input)

        self.username_input = username_input

    def update_local_settings(self, value):
        username = ""
        if value:
            username = value.get("username", username)
        self.username_input.setText(username)

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
