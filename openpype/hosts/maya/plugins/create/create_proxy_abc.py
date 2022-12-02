from openpype.hosts.maya.api import (
    lib,
    plugin
)


class CreateProxyAlembic(plugin.Creator):
    """Proxy Alembic for animated data"""

    name = "proxyAbcMain"
    label = "Proxy Alembic"
    family = "proxyAbc"
    icon = "gears"
    write_color_sets = False
    write_face_sets = False

    def __init__(self, *args, **kwargs):
        super(CreateProxyAlembic, self).__init__(*args, **kwargs)

        # Add animation data
        self.data.update(lib.collect_animation_data())

        # Vertex colors with the geometry.
        self.data["writeColorSets"] = self.write_color_sets
        # Vertex colors with the geometry.
        self.data["writeFaceSets"] = self.write_face_sets
        # Default to exporting world-space
        self.data["worldSpace"] = True

        # remove the bbBox after publish
        self.data["removeBoundingBoxAfterPublish"] = False
        # name suffix for the bounding box
        self.data["nameSuffix"] = "_BBox"

        # Add options for custom attributes
        self.data["attr"] = ""
        self.data["attrPrefix"] = ""
