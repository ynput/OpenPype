from capture_gui.vendor.Qt import QtCore, QtWidgets
import capture_gui.plugin


class PanZoomPlugin(capture_gui.plugin.Plugin):
    """Pan/Zoom widget.

    Allows to toggle whether you want to playblast with the camera's pan/zoom
    state or disable it during the playblast. When "Use pan/zoom from camera"
    is *not* checked it will force disable pan/zoom.

    """
    id = "PanZoom"
    label = "Pan/Zoom"
    section = "config"
    order = 110

    def __init__(self, parent=None):
        super(PanZoomPlugin, self).__init__(parent=parent)

        self._layout = QtWidgets.QHBoxLayout()
        self._layout.setContentsMargins(5, 0, 5, 0)
        self.setLayout(self._layout)

        self.pan_zoom = QtWidgets.QCheckBox("Use pan/zoom from camera")
        self.pan_zoom.setChecked(True)

        self._layout.addWidget(self.pan_zoom)

        self.pan_zoom.stateChanged.connect(self.options_changed)

    def get_outputs(self):

        if not self.pan_zoom.isChecked():
            return {"camera_options": {
                "panZoomEnabled": 1,
                "horizontalPan": 0.0,
                "verticalPan": 0.0,
                "zoom": 1.0}
            }
        else:
            return {}

    def apply_inputs(self, settings):
        self.pan_zoom.setChecked(settings.get("pan_zoom", True))

    def get_inputs(self, as_preset):
        return {"pan_zoom": self.pan_zoom.isChecked()}
