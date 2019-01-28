import pyblish.api
from maya import mel


class CollectWorksceneFPS(pyblish.api.ContextPlugin):
    """Get the FPS of the work scene"""

    label = "Workscene FPS"
    order = pyblish.api.CollectorOrder
    hosts = ["maya"]

    def process(self, context):
        fps = mel.eval('currentTimeUnitToFPS()')
        self.log.info("Workscene FPS: %s" % fps)
        context.data.update({"fps": fps})
