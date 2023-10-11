from openpype.hosts.maya.api import plugin
from openpype.lib import BoolDef


class CreateLayout(plugin.MayaCreator):
    """A grouped package of loaded content"""

    identifier = "io.openpype.creators.maya.layout"
    label = "Layout"
    family = "layout"
    icon = "cubes"

    def get_instance_attr_defs(self):

        return [
            BoolDef("groupLoadedAssets",
                    label="Group Loaded Assets",
                    tooltip="Enable this when you want to publish group of "
                            "loaded asset",
                    default=False)
        ]
