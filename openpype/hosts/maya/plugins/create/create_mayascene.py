from openpype.hosts.maya.api import plugin
from openpype.lib import BoolDef


class CreateMayaScene(plugin.MayaCreator):
    """Raw Maya Scene file export"""

    identifier = "io.openpype.creators.maya.mayascene"
    name = "mayaScene"
    label = "Maya Scene"
    family = "mayaScene"
    icon = "file-archive-o"

    def get_instance_attr_defs(self):
        return [
            BoolDef(
                "preserve_references",
                label="Preserve References",
                default=True
            )
        ]
