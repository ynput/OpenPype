from collections import OrderedDict

import colorbleed.plugin
from colorbleed.maya import lib


class CreateAnimation(colorbleed.plugin.Creator):
    """THe animated objects in the scene"""

    name = "animationDefault"
    label = "Animation"
    family = "colorbleed.animation"
    abbreviation = "anim"

    def __init__(self, *args, **kwargs):
        super(CreateAnimation, self).__init__(*args, **kwargs)

        # create an ordered dict with the existing data first
        data = OrderedDict(**self.data)

        # get basic animation data : start / end / handles / steps
        for key, value in lib.collect_animation_data().items():
            data[key] = value

        # Write vertex colors with the geometry.
        data["writeColorSets"] = False

        # Include only renderable visible shapes.
        # Skips locators and empty transforms
        data["renderableOnly"] = False

        # Include only nodes that are visible at least once during the
        # frame range.
        data["visibleOnly"] = False

        self.data = data
