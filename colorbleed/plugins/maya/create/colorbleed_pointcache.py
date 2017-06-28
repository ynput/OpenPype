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
        attributes["startFrame"] = start
        attributes["endFrame"] = end
        attributes["handles"] = 1
        attributes["step"] = 1.0

        # Write vertex colors with the geometry.
        attributes["writeColorSets"] = False

        # Include only renderable visible shapes.
        # Skips locators and empty transforms
        attributes["renderableOnly"] = False

        # Include only nodes that are visible at least once during the
        # frame range.
        attributes["visibleOnly"] = False

        self.data = attributes