from capture_gui.vendor.Qt import QtCore, QtWidgets

import capture_gui.lib as lib
import capture_gui.plugin


class CodecPlugin(capture_gui.plugin.Plugin):
    """Codec widget.

    Allows to set format, compression and quality.

    """
    id = "Codec"
    label = "Codec"
    section = "config"
    order = 50

    def __init__(self, parent=None):
        super(CodecPlugin, self).__init__(parent=parent)

        self._layout = QtWidgets.QHBoxLayout()
        self._layout.setContentsMargins(0, 0, 0, 0)
        self.setLayout(self._layout)

        self.format = QtWidgets.QComboBox()
        self.compression = QtWidgets.QComboBox()
        self.quality = QtWidgets.QSpinBox()
        self.quality.setMinimum(0)
        self.quality.setMaximum(100)
        self.quality.setValue(100)
        self.quality.setToolTip("Compression quality percentage")

        self._layout.addWidget(self.format)
        self._layout.addWidget(self.compression)
        self._layout.addWidget(self.quality)

        self.format.currentIndexChanged.connect(self.on_format_changed)

        self.refresh()

        # Default to format 'qt'
        index = self.format.findText("qt")
        if index != -1:
            self.format.setCurrentIndex(index)

            # Default to compression 'H.264'
            index = self.compression.findText("H.264")
            if index != -1:
                self.compression.setCurrentIndex(index)

        self.connections()

    def connections(self):
        self.compression.currentIndexChanged.connect(self.options_changed)
        self.format.currentIndexChanged.connect(self.options_changed)
        self.quality.valueChanged.connect(self.options_changed)

    def refresh(self):
        formats = sorted(lib.list_formats())
        self.format.clear()
        self.format.addItems(formats)

    def on_format_changed(self):
        """Refresh the available compressions."""

        format = self.format.currentText()
        compressions = lib.list_compressions(format)
        self.compression.clear()
        self.compression.addItems(compressions)

    def get_outputs(self):
        """Get the plugin outputs that matches `capture.capture` arguments

        Returns:
            dict: Plugin outputs

        """

        return {"format": self.format.currentText(),
                "compression": self.compression.currentText(),
                "quality": self.quality.value()}

    def get_inputs(self, as_preset):
        # a bit redundant but it will work when iterating over widgets
        # so we don't have to write an exception
        return self.get_outputs()

    def apply_inputs(self, settings):
        codec_format = settings.get("format", 0)
        compr = settings.get("compression", 4)
        quality = settings.get("quality", 100)

        self.format.setCurrentIndex(self.format.findText(codec_format))
        self.compression.setCurrentIndex(self.compression.findText(compr))
        self.quality.setValue(int(quality))
