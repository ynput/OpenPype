from Qt import QtWidgets
from openpype.tools.experimental_tools import (
    ExperimentalTools,
    LOCAL_EXPERIMENTAL_KEY
)


__all__ = (
    "LocalExperimentalToolsWidgets",
    "LOCAL_EXPERIMENTAL_KEY"
)


class LocalExperimentalToolsWidgets(QtWidgets.QWidget):
    def __init__(self, parent):
        super(LocalExperimentalToolsWidgets, self).__init__(parent)

        self._loading_local_settings = False

        layout = QtWidgets.QFormLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)

        # Label that says there are no experimental tools available
        empty_label = QtWidgets.QLabel(self)
        empty_label.setText(
            "There are no experimental tools available..."
        )

        layout.addRow(empty_label)

        experimental_defs = ExperimentalTools(refresh=False)
        checkboxes_by_identifier = {}
        for tool in experimental_defs.tools:
            checkbox = QtWidgets.QCheckBox(self)
            label_widget = QtWidgets.QLabel(tool.label, self)
            checkbox.setToolTip(tool.tooltip)
            label_widget.setToolTip(tool.tooltip)
            layout.addRow(label_widget, checkbox)

            checkboxes_by_identifier[tool.identifier] = checkbox

        empty_label.setVisible(len(checkboxes_by_identifier) == 0)

        self._empty_label = empty_label
        self._checkboxes_by_identifier = checkboxes_by_identifier
        self._experimental_defs = experimental_defs

    def update_local_settings(self, value):
        self._loading_local_settings = True
        value = value or {}

        for identifier, checkbox in self._checkboxes_by_identifier.items():
            checked = value.get(identifier, False)
            checkbox.setChecked(checked)

        self._loading_local_settings = False

    def settings_value(self):
        # Add changed
        # If these have changed then
        output = {}
        for identifier, checkbox in self._checkboxes_by_identifier.items():
            if checkbox.isChecked():
                output[identifier] = True
        return output
