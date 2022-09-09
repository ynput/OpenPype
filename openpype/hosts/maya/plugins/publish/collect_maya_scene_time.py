from maya import cmds

import pyblish.api


class CollectMayaSceneTime(pyblish.api.InstancePlugin):
    """Collect Maya Scene playback range

    This allows to reproduce the playback range for the content to be loaded.
    It does *not* limit the extracted data to only data inside that time range.

    """

    order = pyblish.api.CollectorOrder + 0.2
    label = 'Collect Maya Scene Time'
    families = ["mayaScene"]

    def process(self, instance):
        instance.data.update({
            "frameStart": cmds.playbackOptions(query=True, minTime=True),
            "frameEnd": cmds.playbackOptions(query=True, maxTime=True),
            "frameStartHandle": cmds.playbackOptions(query=True,
                                                     animationStartTime=True),
            "frameEndHandle": cmds.playbackOptions(query=True,
                                                   animationEndTime=True)
        })
