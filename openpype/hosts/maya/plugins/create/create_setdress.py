from openpype.hosts.maya.api import plugin
from openpype.lib import BoolDef


class CreateSetDress(plugin.MayaCreator):
    """A grouped package of loaded content"""

    identifier = "io.openpype.creators.maya.setdress"
    label = "Set Dress"
    family = "setdress"
    icon = "cubes"
    defaults = ["Main", "Anim"]

    def get_instance_attr_defs(self):
        return [
            BoolDef("exactSetMembersOnly",
                    label="Exact Set Members Only",
                    default=True)
        ]
