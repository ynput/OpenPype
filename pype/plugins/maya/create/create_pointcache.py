import avalon.maya
from pype.hosts.maya import lib


class CreatePointCache(avalon.maya.Creator):
    """Alembic pointcache for animated data"""

    name = "pointcache"
    label = "Point Cache"
    family = "pointcache"
    icon = "gears"
    defaults = ['Main']

    def __init__(self, *args, **kwargs):
        super(CreatePointCache, self).__init__(*args, **kwargs)

        # Add animation data
        self.data.update(lib.collect_animation_data())

        self.data["writeColorSets"] = False  # Vertex colors with the geometry.
        self.data["renderableOnly"] = False  # Only renderable visible shapes
        self.data["visibleOnly"] = False     # only nodes that are visible
        self.data["includeParentHierarchy"] = False  # Include parent groups
        self.data["worldSpace"] = True       # Default to exporting world-space

        # Add options for custom attributes
        self.data["attr"] = ""
        self.data["attrPrefix"] = ""
