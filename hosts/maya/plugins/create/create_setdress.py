from openpype.hosts.maya.api import plugin


class CreateSetDress(plugin.Creator):
    """A grouped package of loaded content"""

    name = "setdressMain"
    label = "Set Dress"
    family = "setdress"
    icon = "cubes"
    defaults = ["Main", "Anim"]

    def __init__(self, *args, **kwargs):
        super(CreateSetDress, self).__init__(*args, **kwargs)

        self.data["exactSetMembersOnly"] = True
