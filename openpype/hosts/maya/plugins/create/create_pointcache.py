from maya import cmds

from openpype.hosts.maya.api import (
    lib,
    plugin
)
from openpype.lib import (
    BoolDef,
    TextDef,
    NumberDef,
    EnumDef
)
from openpype.settings import get_current_project_settings#not needed if applying settings is merged.


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
                    tooltip="Write vertex colors with the geometry"),
            BoolDef("writeFaceSets",
                    label="Write face sets",
                    tooltip="Write face sets with the geometry"),
            BoolDef("renderableOnly",
                    label="Renderable Only",
                    tooltip="Only export renderable visible shapes"),
            BoolDef("visibleOnly",
                    label="Visible Only",
                    tooltip="Only export dag objects visible during "
                            "frame range"),
            BoolDef("includeParentHierarchy",
                    label="Include Parent Hierarchy",
                    tooltip="Whether to include parent hierarchy of nodes in "
                            "the publish instance"),
            BoolDef("worldSpace",
                    label="World-Space Export"),
            BoolDef("farm",
                    label="Submit to farm"),
            NumberDef("priority",
                      label="Priority for farm"),
            BoolDef("noNormals",
                    label="Include normals"),
            BoolDef("includeUserDefinedAttributes",
                    label="Include User Defined Attributes"),
            TextDef("attr",
                    label="Custom Attributes",
                    placeholder="attr1, attr2"),
            TextDef("attrPrefix",
                    label="Custom Attributes Prefix",
                    placeholder="prefix1, prefix2"),
            EnumDef("dataFormat",
                    label="Data Format",
                    items=["ogawa", "HDF"]),
            BoolDef("eulerFilter",
                    label="Apply Euler Filter"),
            BoolDef("preRoll",
                    label="Start from preroll start frame"),
            NumberDef("preRollStartFrame",
                      label="Start frame for preroll"),
            BoolDef("refresh",
                    label="Refresh viewport during export"),
            BoolDef("stripNamespaces",
                    label="Strip namespaces on export"),
            BoolDef("uvWrite",
                    label="Write UVs"),
            BoolDef("verbose",
                    label="Verbose output"),
            BoolDef("wholeFrameGeo",
                    label="Whole Frame Geo"),
            BoolDef("writeCreases",
                    label="Write Creases"),
            BoolDef("writeUVSets",
                    label="Write UV Sets"),
            BoolDef("writeVisibility",
                    label="Write Visibility")
        ])

        # Collect editable state and default values.
        settings = get_current_project_settings()
        settings = settings["maya"]["create"]["CreatePointCache"]
        editable_attributes = {}
        for key, value in settings.items():
            if not key.endswith("_editable"):
                continue

            if not value:
                continue

            attribute = key.replace("_editable", "")
            editable_attributes[attribute] = settings[attribute]

        resulting_defs = []
        for definition in defs:
            # Remove non-editable defs.
            if definition.key not in editable_attributes.keys():
                continue

            # Set default values from settings.
            definition.default = editable_attributes[definition.key]

            resulting_defs.append(definition)

        return resulting_defs

    def create(self, subset_name, instance_data, pre_create_data):

        instance = super(CreatePointCache, self).create(
            subset_name, instance_data, pre_create_data
        )
        instance_node = instance.get("instance_node")

        # For Arnold standin proxy
        proxy_set = cmds.sets(name=instance_node + "_proxy_SET", empty=True)
        cmds.sets(proxy_set, forceElement=instance_node)
