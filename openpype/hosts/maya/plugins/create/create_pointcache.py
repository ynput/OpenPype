from openpype.hosts.maya.api import (
    lib,
    plugin
)


class CreatePointCache(plugin.Creator):
    """Alembic pointcache for animated data"""

    name = "pointcache"
    label = "Point Cache"
    family = "pointcache"
    icon = "gears"
    write_color_sets = False

    def __init__(self, *args, **kwargs):
        super(CreatePointCache, self).__init__(*args, **kwargs)

        # Add animation data
        self.data.update(lib.collect_animation_data())

        # Vertex colors with the geometry.
        self.data["writeColorSets"] = self.write_color_sets
        self.data["writeFaceSets"] = False  # Vertex colors with the geometry.
        self.data["renderableOnly"] = False  # Only renderable visible shapes
        self.data["visibleOnly"] = False     # only nodes that are visible
        self.data["includeParentHierarchy"] = False  # Include parent groups
        self.data["worldSpace"] = True       # Default to exporting world-space

        # Add options for custom attributes
        self.data["attr"] = ""
        self.data["attrPrefix"] = ""

        # Default to not send to farm.
        self.data["farm"] = False
        self.data["priority"] = 50
