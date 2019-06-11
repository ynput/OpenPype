from pyblish import api


class ValidateViewerLut(api.ContextPlugin):
    """Validate viewer lut in NukeStudio is the same as in Nuke."""

    order = api.ValidatorOrder
    label = "Viewer LUT"
    hosts = ["nukestudio"]
    optional = True

    def process(self, context):
        import nuke
        import hiero

        # nuke_lut = nuke.ViewerProcess.node()["current"].value()
        nukestudio_lut = context.data["activeProject"].lutSettingViewer()
        self.log.info("__ nukestudio_lut: {}".format(nukestudio_lut))

        msg = "Viewer LUT can only be RGB"
        assert "RGB" in nukestudio_lut, msg
