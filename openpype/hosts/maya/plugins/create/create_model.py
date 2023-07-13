from openpype.hosts.maya.api import plugin
from openpype.lib import (
    BoolDef,
    TextDef
)


class CreateModel(plugin.MayaCreator):
    """Polygonal static geometry"""

    identifier = "io.openpype.creators.maya.model"
    label = "Model"
    family = "model"
    icon = "cube"
    defaults = ["Main", "Proxy", "_MD", "_HD", "_LD"]

    write_color_sets = False
    write_face_sets = False

    def get_instance_attr_defs(self):

        return [
            BoolDef("writeColorSets",
                    label="Write vertex colors",
                    tooltip="Write vertex colors with the geometry",
                    default=self.write_color_sets),
            BoolDef("writeFaceSets",
                    label="Write face sets",
                    tooltip="Write face sets with the geometry",
                    default=self.write_face_sets),
            BoolDef("includeParentHierarchy",
                    label="Include Parent Hierarchy",
                    tooltip="Whether to include parent hierarchy of nodes in "
                            "the publish instance",
                    default=False),
            TextDef("attr",
                    label="Custom Attributes",
                    default="",
                    placeholder="attr1, attr2"),
            TextDef("attrPrefix",
                    label="Custom Attributes Prefix",
                    placeholder="prefix1, prefix2")
        ]
