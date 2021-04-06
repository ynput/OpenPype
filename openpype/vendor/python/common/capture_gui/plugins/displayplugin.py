import maya.cmds as cmds

from capture_gui.vendor.Qt import QtCore, QtWidgets
import capture_gui.plugin
import capture_gui.colorpicker as colorpicker


# region GLOBALS

BACKGROUND_DEFAULT = [0.6309999823570251,
                      0.6309999823570251,
                      0.6309999823570251]

TOP_DEFAULT = [0.5350000262260437,
               0.6169999837875366,
               0.7020000219345093]

BOTTOM_DEFAULT = [0.052000001072883606,
                  0.052000001072883606,
                  0.052000001072883606]

COLORS = {"background": BACKGROUND_DEFAULT,
          "backgroundTop": TOP_DEFAULT,
          "backgroundBottom": BOTTOM_DEFAULT}

LABELS = {"background": "Background",
          "backgroundTop": "Top",
          "backgroundBottom": "Bottom"}
# endregion GLOBALS


class DisplayPlugin(capture_gui.plugin.Plugin):
    """Plugin to apply viewport visibilities and settings"""

    id = "Display Options"
    label = "Display Options"
    section = "config"
    order = 70

    def __init__(self, parent=None):
        super(DisplayPlugin, self).__init__(parent=parent)

        self._colors = dict()

        self._layout = QtWidgets.QVBoxLayout()
        self._layout.setContentsMargins(0, 0, 0, 0)
        self.setLayout(self._layout)

        self.override = QtWidgets.QCheckBox("Override Display Options")

        self.display_type = QtWidgets.QComboBox()
        self.display_type.addItems(["Solid", "Gradient"])

        # create color columns
        self._color_layout = QtWidgets.QHBoxLayout()
        for label, default in COLORS.items():
            self.add_color_picker(self._color_layout, label, default)

        # populate layout
        self._layout.addWidget(self.override)
        self._layout.addWidget(self.display_type)
        self._layout.addLayout(self._color_layout)

        # ensure widgets are in the correct enable state
        self.on_toggle_override()

        self.connections()

    def connections(self):
        self.override.toggled.connect(self.on_toggle_override)
        self.override.toggled.connect(self.options_changed)
        self.display_type.currentIndexChanged.connect(self.options_changed)

    def add_color_picker(self, layout, label, default):
        """Create a column with a label and a button to select a color

        Arguments:
            layout (QtWidgets.QLayout): Layout to add color picker to
            label (str): system name for the color type, e.g. : backgroundTop
            default (list): The default color values to start with

        Returns:
            colorpicker.ColorPicker: a color picker instance

        """

        column = QtWidgets.QVBoxLayout()
        label_widget = QtWidgets.QLabel(LABELS[label])

        color_picker = colorpicker.ColorPicker()
        color_picker.color = default

        column.addWidget(label_widget)
        column.addWidget(color_picker)

        column.setAlignment(label_widget, QtCore.Qt.AlignCenter)

        layout.addLayout(column)

        # connect signal
        color_picker.valueChanged.connect(self.options_changed)

        # store widget
        self._colors[label] = color_picker

        return color_picker

    def on_toggle_override(self):
        """Callback when override is toggled.

        Enable or disable the color pickers and background type widgets bases
        on the current state of the override checkbox

        Returns:
            None

        """
        state = self.override.isChecked()
        self.display_type.setEnabled(state)
        for widget in self._colors.values():
            widget.setEnabled(state)

    def display_gradient(self):
        """Return whether the background should be displayed as gradient.

        When True the colors will use the top and bottom color to define the
        gradient otherwise the background color will be used as solid color.

        Returns:
            bool: Whether background is gradient

        """
        return self.display_type.currentText() == "Gradient"

    def apply_inputs(self, settings):
        """Apply the saved inputs from the inputs configuration

        Arguments:
            settings (dict): The input settings to apply.

        """

        for label, widget in self._colors.items():
            default = COLORS.get(label, [0, 0, 0]) # fallback default to black
            value = settings.get(label, default)
            widget.color = value

        override = settings.get("override_display", False)
        self.override.setChecked(override)

    def get_inputs(self, as_preset):
        inputs = {"override_display": self.override.isChecked()}
        for label, widget in self._colors.items():
            inputs[label] = widget.color

        return inputs

    def get_outputs(self):
        """Get the plugin outputs that matches `capture.capture` arguments

        Returns:
            dict: Plugin outputs

        """

        outputs = {}
        if self.override.isChecked():
            outputs["displayGradient"] = self.display_gradient()
            for label, widget in self._colors.items():
                outputs[label] = widget.color
        else:
            # Parse active color settings
            outputs["displayGradient"] = cmds.displayPref(query=True,
                                                          displayGradient=True)
            for key in COLORS.keys():
                color = cmds.displayRGBColor(key, query=True)
                outputs[key] = color

        return {"display_options": outputs}
