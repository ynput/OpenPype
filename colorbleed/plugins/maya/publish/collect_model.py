from maya import cmds

import pyblish.api


class CollectModelData(pyblish.api.InstancePlugin):
    """Collect model data

    Ensures always only a single frame is extracted (current frame).

    """

    order = pyblish.api.CollectorOrder + 0.499
    label = 'Model Data'
    families = ["colorbleed.model"]

    def process(self, instance):
        # Extract only current frame (override)
        frame = cmds.currentTime(query=True)
        instance.data['startFrame'] = frame
        instance.data['endFrame'] = frame
