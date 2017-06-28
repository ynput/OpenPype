from collections import OrderedDict

from maya import cmds

import avalon.maya


class CreatePointCache(avalon.maya.Creator):
    """Alembic extract"""

    name = "pointcache"
    label = "Point Cache"
    family = "colorbleed.pointcache"

    def __init__(self, *args, **kwargs):
        super(CreatePointCache, self).__init__(*args, **kwargs)

        # create an ordered dict with the existing data first
        data = OrderedDict(**self.data)

        # get scene values as defaults
        start = cmds.playbackOptions(query=True, animationStartTime=True)
        end = cmds.playbackOptions(query=True, animationEndTime=True)

        # build attributes
        data["startFrame"] = start
        data["endFrame"] = end
        data["handles"] = 1
        data["step"] = 1.0

        # Write vertex colors with the geometry.
        data["writeColorSets"] = False

        # Include only renderable visible shapes.
        # Skips locators and empty transforms
        data["renderableOnly"] = False

        # Include only nodes that are visible at least once during the
        # frame range.
        data["visibleOnly"] = False

        self.data = data
