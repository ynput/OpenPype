from collections import OrderedDict

import hou

from avalon import houdini


class CreatePointCache(houdini.Creator):
    """Alembic pointcache for animated data"""

    name = "pointcache"
    label = "Point Cache"
    family = "colorbleed.pointcache"
    icon = "gears"

    def __init__(self, *args, **kwargs):
        super(CreatePointCache, self).__init__(*args, **kwargs)

        # create an ordered dict with the existing data first
        data = OrderedDict(**self.data)

        # Collect animation data for point cache exporting
        start, end = hou.playbar.timelineRange()
        data["startFrame"] = start
        data["endFrame"] = end

        self.data = data
