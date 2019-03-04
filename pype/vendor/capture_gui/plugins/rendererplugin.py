import maya.cmds as cmds

from capture_gui.vendor.Qt import QtCore, QtWidgets
import capture_gui.lib as lib
import capture_gui.plugin


class RendererPlugin(capture_gui.plugin.Plugin):
    """Renderer plugin to control the used playblast renderer for viewport"""

    id = "Renderer"
    label = "Renderer"
    section = "config"
    order = 60

    def __init__(self, parent=None):
        super(RendererPlugin, self).__init__(parent=parent)

        layout = QtWidgets.QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        self.setLayout(layout)

        # Get active renderers for viewport
        self._renderers = self.get_renderers()

        # Create list of renderers
        self.renderers = QtWidgets.QComboBox()
        self.renderers.addItems(self._renderers.keys())

        layout.addWidget(self.renderers)

        self.apply_inputs(self.get_defaults())

        # Signals
        self.renderers.currentIndexChanged.connect(self.options_changed)

    def get_current_renderer(self):
        """Get current renderer by internal name (non-UI)

        Returns:
            str: Name of renderer.

        """
        renderer_ui = self.renderers.currentText()
        renderer = self._renderers.get(renderer_ui, None)
        if renderer is None:
            raise RuntimeError("No valid renderer: {0}".format(renderer_ui))

        return renderer

    def get_renderers(self):
        """Collect all available renderers for playblast"""
        active_editor = lib.get_active_editor()
        renderers_ui = cmds.modelEditor(active_editor,
                                        query=True,
                                        rendererListUI=True)
        renderers_id = cmds.modelEditor(active_editor,
                                        query=True,
                                        rendererList=True)

        renderers = dict(zip(renderers_ui, renderers_id))
        renderers.pop("Stub Renderer")

        return renderers

    def get_defaults(self):
        return {"rendererName": "vp2Renderer"}

    def get_inputs(self, as_preset):
        return {"rendererName": self.get_current_renderer()}

    def get_outputs(self):
        """Get the plugin outputs that matches `capture.capture` arguments

        Returns:
            dict: Plugin outputs

        """
        return {
            "viewport_options": {
                "rendererName": self.get_current_renderer()
            }
        }

    def apply_inputs(self, inputs):
        """Apply previous settings or settings from a preset

        Args:
            inputs (dict): Plugin input settings

        Returns:
            None

        """

        reverse_lookup = {value: key for key, value in self._renderers.items()}
        renderer = inputs.get("rendererName", "vp2Renderer")
        renderer_ui = reverse_lookup.get(renderer)

        if renderer_ui:
            index = self.renderers.findText(renderer_ui)
            self.renderers.setCurrentIndex(index)
        else:
            self.renderers.setCurrentIndex(1)
