from collections import OrderedDict

import avalon.maya
from maya import cmds


class CreateAnimation(avalon.maya.Creator):
    """THe animated objects in the scene"""

    name = "animationDefault"
    label = "Animation"
    family = "colorbleed.animation"

    def __init__(self, *args, **kwargs):
        super(CreateAnimation, self).__init__(*args, **kwargs)

        # get scene values as defaults
        start = cmds.playbackOptions(query=True, animationStartTime=True)
        end = cmds.playbackOptions(query=True, animationEndTime=True)

        # build attributes
        attributes = OrderedDict()
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
