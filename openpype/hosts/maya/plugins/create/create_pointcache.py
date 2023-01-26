from openpype.hosts.maya.api import (
    lib,
    plugin
)
from openpype.lib import (
    BoolDef,
    TextDef
)


class CreatePointCache(plugin.MayaCreator):
    """Alembic pointcache for animated data"""

    identifier = "io.openpype.creators.maya.pointcache"
    label = "Pointcache"
    family = "pointcache"
    icon = "gears"

    def get_instance_attr_defs(self):

        defs = lib.collect_animation_defs()

        defs.extend([
            BoolDef("writeColorSets",
                    label="Write vertex colors",
                    tooltip="Write vertex colors with the geometry",
                    default=False),
            BoolDef("writeFaceSets",
                    label="Write face sets",
                    tooltip="Write face sets with the geometry",
                    default=False),
            BoolDef("renderableOnly",
                    label="Renderable Only",
                    tooltip="Only export renderable visible shapes",
                    default=False),
            BoolDef("visibleOnly",
                    label="Visible Only",
                    tooltip="Only export dag objects visible during "
                            "frame range",
                    default=False),
            BoolDef("includeParentHierarchy",
                    label="Include Parent Hierarchy",
                    default=False),
            BoolDef("worldSpace",
                    label="World-Space Export",
                    default=True),
            BoolDef("refresh",
                    label="Refresh viewport during export",
                    default=False),
            TextDef("attr",
                    label="Custom Attributes",
                    default="",
                    placeholder="attr1, attr2"),
            TextDef("attrPrefix",
                    label="Custom Attributes Prefix",
                    placeholder="prefix1, prefix2")
        ])

        # TODO: Implement these on a Deadline plug-in instead?
        """
        # Default to not send to farm.
        self.data["farm"] = False
        self.data["priority"] = 50
        """

        return defs
