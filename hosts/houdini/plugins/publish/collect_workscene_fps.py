import pyblish.api
import hou


class CollectWorksceneFPS(pyblish.api.ContextPlugin):
    """Get the FPS of the work scene."""

    label = "Workscene FPS"
    order = pyblish.api.CollectorOrder
    hosts = ["houdini"]

    def process(self, context):
        fps = hou.fps()
        self.log.info("Workscene FPS: %s" % fps)
        context.data.update({"fps": fps})
