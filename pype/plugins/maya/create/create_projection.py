import avalon.maya

from pype.hosts.maya import lib


class CreateProjection(avalon.maya.Creator):
    """Geometry with projected texture."""

    name = "projection"
    label = "Projection"
    family = "projection"
    icon = "video-camera"
    defaults = ["Main"]

    def __init__(self, *args, **kwargs):
        super(CreateProjection, self).__init__(*args, **kwargs)

        self.data["renderlayer"] = lib.get_current_renderlayer()
        self.data.update(lib.collect_animation_data())

        self.data["writeColorSets"] = False  # Vertex colors with the geometry.
        self.data["renderableOnly"] = False  # Only renderable visible shapes
        self.data["visibleOnly"] = False     # only nodes that are visible
        self.data["includeParentHierarchy"] = False  # Include parent groups
        self.data["worldSpace"] = True       # Default to exporting world-space

        # Add options for custom attributes
        self.data["attr"] = ""
        self.data["attrPrefix"] = ""

        # Bake to world space by default, when this is False it will also
        # include the parent hierarchy in the baked results
        self.data["bakeToWorldSpace"] = True
