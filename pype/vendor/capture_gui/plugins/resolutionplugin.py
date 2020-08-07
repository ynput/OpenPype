import math
from functools import partial

import maya.cmds as cmds
from capture_gui.vendor.Qt import QtCore, QtWidgets

import capture_gui.lib as lib
import capture_gui.plugin


class ResolutionPlugin(capture_gui.plugin.Plugin):
    """Resolution widget.

    Allows to set scale based on set of options.

    """
    id = "Resolution"
    section = "app"
    order = 20

    resolution_changed = QtCore.Signal()

    ScaleWindow = "From Window"
    ScaleRenderSettings = "From Render Settings"
    ScaleCustom = "Custom"

    def __init__(self, parent=None):
        super(ResolutionPlugin, self).__init__(parent=parent)

        self._layout = QtWidgets.QVBoxLayout()
        self._layout.setContentsMargins(0, 0, 0, 0)
        self.setLayout(self._layout)

        # Scale
        self.mode = QtWidgets.QComboBox()
        self.mode.addItems([self.ScaleWindow,
                            self.ScaleRenderSettings,
                            self.ScaleCustom])
        self.mode.setCurrentIndex(1)  # Default: From render settings

        # Custom width/height
        self.resolution = QtWidgets.QWidget()
        self.resolution.setContentsMargins(0, 0, 0, 0)
        resolution_layout = QtWidgets.QHBoxLayout()
        resolution_layout.setContentsMargins(0, 0, 0, 0)
        resolution_layout.setSpacing(6)

        self.resolution.setLayout(resolution_layout)
        width_label = QtWidgets.QLabel("Width")
        width_label.setFixedWidth(40)
        self.width = QtWidgets.QSpinBox()
        self.width.setMinimum(0)
        self.width.setMaximum(99999)
        self.width.setValue(1920)
        heigth_label = QtWidgets.QLabel("Height")
        heigth_label.setFixedWidth(40)
        self.height = QtWidgets.QSpinBox()
        self.height.setMinimum(0)
        self.height.setMaximum(99999)
        self.height.setValue(1080)

        resolution_layout.addWidget(width_label)
        resolution_layout.addWidget(self.width)
        resolution_layout.addWidget(heigth_label)
        resolution_layout.addWidget(self.height)

        self.scale_result = QtWidgets.QLineEdit()
        self.scale_result.setReadOnly(True)

        # Percentage
        self.percent_label = QtWidgets.QLabel("Scale")
        self.percent = QtWidgets.QDoubleSpinBox()
        self.percent.setMinimum(0.01)
        self.percent.setValue(1.0)  # default value
        self.percent.setSingleStep(0.05)

        self.percent_presets = QtWidgets.QHBoxLayout()
        self.percent_presets.setSpacing(4)
        for value in [0.25, 0.5, 0.75, 1.0, 2.0]:
            btn = QtWidgets.QPushButton(str(value))
            self.percent_presets.addWidget(btn)
            btn.setFixedWidth(35)
            btn.clicked.connect(partial(self.percent.setValue, value))

        self.percent_layout = QtWidgets.QHBoxLayout()
        self.percent_layout.addWidget(self.percent_label)
        self.percent_layout.addWidget(self.percent)
        self.percent_layout.addLayout(self.percent_presets)

        # Resulting scale display
        self._layout.addWidget(self.mode)
        self._layout.addWidget(self.resolution)
        self._layout.addLayout(self.percent_layout)
        self._layout.addWidget(self.scale_result)

        # refresh states
        self.on_mode_changed()
        self.on_resolution_changed()

        # connect signals
        self.mode.currentIndexChanged.connect(self.on_mode_changed)
        self.mode.currentIndexChanged.connect(self.on_resolution_changed)
        self.percent.valueChanged.connect(self.on_resolution_changed)
        self.width.valueChanged.connect(self.on_resolution_changed)
        self.height.valueChanged.connect(self.on_resolution_changed)

        # Connect options changed
        self.mode.currentIndexChanged.connect(self.options_changed)
        self.percent.valueChanged.connect(self.options_changed)
        self.width.valueChanged.connect(self.options_changed)
        self.height.valueChanged.connect(self.options_changed)

    def on_mode_changed(self):
        """Update the width/height enabled state when mode changes"""

        if self.mode.currentText() != self.ScaleCustom:
            self.width.setEnabled(False)
            self.height.setEnabled(False)
            self.resolution.hide()
        else:
            self.width.setEnabled(True)
            self.height.setEnabled(True)
            self.resolution.show()

    def _get_output_resolution(self):

        options = self.get_outputs()
        return int(options["width"]), int(options["height"])

    def on_resolution_changed(self):
        """Update the resulting resolution label"""

        width, height = self._get_output_resolution()
        label = "Result: {0}x{1}".format(width, height)

        self.scale_result.setText(label)

        # Update label
        self.label = "Resolution ({0}x{1})".format(width, height)
        self.label_changed.emit(self.label)

    def get_outputs(self):
        """Return width x height defined by the combination of settings

        Returns:
            dict: width and height key values

        """
        mode = self.mode.currentText()
        panel = lib.get_active_editor()

        if mode == self.ScaleCustom:
            width = self.width.value()
            height = self.height.value()

        elif mode == self.ScaleRenderSettings:
            # width height from render resolution
            width = cmds.getAttr("defaultResolution.width")
            height = cmds.getAttr("defaultResolution.height")

        elif mode == self.ScaleWindow:
            # width height from active view panel size
            if not panel:
                # No panel would be passed when updating in the UI as such
                # the resulting resolution can't be previewed. But this should
                # never happen when starting the capture.
                width = 0
                height = 0
            else:
                width = cmds.control(panel, query=True, width=True)
                height = cmds.control(panel, query=True, height=True)
        else:
            raise NotImplementedError("Unsupported scale mode: "
                                      "{0}".format(mode))

        scale = [width, height]
        percentage = self.percent.value()
        scale = [math.floor(x * percentage) for x in scale]

        return {"width": scale[0], "height": scale[1]}

    def get_inputs(self, as_preset):
        return {"mode": self.mode.currentText(),
                "width": self.width.value(),
                "height": self.height.value(),
                "percent": self.percent.value()}

    def apply_inputs(self, settings):
        # get value else fall back to default values
        mode = settings.get("mode", self.ScaleRenderSettings)
        width = int(settings.get("width", 1920))
        height = int(settings.get("height", 1080))
        percent = float(settings.get("percent", 1.0))

        # set values
        self.mode.setCurrentIndex(self.mode.findText(mode))
        self.width.setValue(width)
        self.height.setValue(height)
        self.percent.setValue(percent)
