import pyblish.api

from maya import cmds


class ValidateCurrentRenderLayerIsRenderable(pyblish.api.ContextPlugin):
    """Validate if current render layer has a renderable camera

    There is a bug in Redshift which occurs when the current render layer
    at file open has no renderable camera. The error raised is as follows:

    "No renderable cameras found. Aborting render"

    This error is raised even if that render layer will not be rendered.

    """

    label = "Current Render Layer Has Renderable Camera"
    order = pyblish.api.ValidatorOrder
    hosts = ["maya"]
    families = ["colorbleed.renderlayer"]

    def process(self, instance):
        layer = cmds.editRenderLayerGlobals(query=True, currentRenderLayer=True)
        cameras = cmds.ls(type="camera", long=True)
        renderable = any(c for c in cameras if cmds.getAttr(c + ".renderable"))
        assert renderable, ("Current render layer %s has no renderable camera"
                            % layer)
