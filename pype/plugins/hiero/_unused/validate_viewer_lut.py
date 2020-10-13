from pyblish import api


class ValidateViewerLut(api.ContextPlugin):
    """Validate viewer lut in Hiero is the same as in Nuke."""

    order = api.ValidatorOrder
    label = "Viewer LUT"
    hosts = ["hiero"]
    optional = True

    def process(self, context):
        # nuke_lut = nuke.ViewerProcess.node()["current"].value()
        hiero_lut = context.data["activeProject"].lutSettingViewer()
        self.log.info("__ hiero_lut: {}".format(hiero_lut))

        msg = "Viewer LUT can only be RGB"
        assert "RGB" in hiero_lut, msg
