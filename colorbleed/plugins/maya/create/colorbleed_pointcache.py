import avalon.maya
from colorbleed.maya import lib


class CreatePointCache(avalon.maya.Creator):
    """Alembic pointcache for animated data"""

    name = "pointcache"
    label = "Point Cache"
    family = "colorbleed.pointcache"
    icon = "gears"

    def __init__(self, *args, **kwargs):
        super(CreatePointCache, self).__init__(*args, **kwargs)

        data = {"writeColorSets": False,  # Vertex colors with the geometry.
                "renderableOnly": False,  # Only renderable visible shapes
                "visibleOnly": False,  # only nodes that are visible
                "attr": "",  # Add options for custom attributes
                "attrPrefix": ""}

        # get basic animation data : start / end / handles / steps
        for key, value in lib.collect_animation_data().items():
            data[key] = value

        self.data.update(data)
