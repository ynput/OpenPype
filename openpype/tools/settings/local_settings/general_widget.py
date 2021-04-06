from Qt import QtWidgets


class LocalGeneralWidgets(QtWidgets.QWidget):
    def __init__(self, parent):
        super(LocalGeneralWidgets, self).__init__(parent)

        local_site_name_input = QtWidgets.QLineEdit(self)

        layout = QtWidgets.QFormLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)

        layout.addRow("Local site label", local_site_name_input)

        self.local_site_name_input = local_site_name_input

    def update_local_settings(self, value):
        site_label = ""
        if value:
            site_label = value.get("site_label", site_label)
        self.local_site_name_input.setText(site_label)

    def settings_value(self):
        # Add changed
        # If these have changed then
        output = {}
        local_site_name = self.local_site_name_input.text()
        if local_site_name:
            output["site_label"] = local_site_name
        # Do not return output yet since we don't have mechanism to save or
        #   load these data through api calls
        return output
