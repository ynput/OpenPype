from maya import cmds

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
    write_color_sets = False
    write_face_sets = False
    include_user_defined_attributes = False

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
                    tooltip="Whether to include parent hierarchy of nodes in "
                            "the publish instance",
                    default=False),
            BoolDef("worldSpace",
                    label="World-Space Export",
                    default=True),
            BoolDef("refresh",
                    label="Refresh viewport during export",
                    default=False),
            BoolDef("includeUserDefinedAttributes",
                    label="Include User Defined Attributes",
                    default=self.include_user_defined_attributes),
            TextDef("attr",
                    label="Custom Attributes",
                    default="",
                    placeholder="attr1, attr2"),
            TextDef("attrPrefix",
                    label="Custom Attributes Prefix",
                    default="",
                    placeholder="prefix1, prefix2")
        ])

        # TODO: Implement these on a Deadline plug-in instead?
        """
        # Default to not send to farm.
        self.data["farm"] = False
        self.data["priority"] = 50
        """

        return defs

    def create(self, subset_name, instance_data, pre_create_data):

        instance = super(CreatePointCache, self).create(
            subset_name, instance_data, pre_create_data
        )
        instance_node = instance.get("instance_node")

        # For Arnold standin proxy
        proxy_set = cmds.sets(name=instance_node + "_proxy_SET", empty=True)
        cmds.sets(proxy_set, forceElement=instance_node)
