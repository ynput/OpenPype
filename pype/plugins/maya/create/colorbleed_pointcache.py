from collections import OrderedDict

import avalon.maya
from pype.maya import lib


class CreatePointCache(avalon.maya.Creator):
    """Alembic pointcache for animated data"""

    name = "pointcache"
    label = "Point Cache"
    family = "studio.pointcache"
    icon = "gears"

    def __init__(self, *args, **kwargs):
        super(CreatePointCache, self).__init__(*args, **kwargs)

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