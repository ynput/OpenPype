from openpype.hosts.maya.api import plugin


class CreateAssembly(plugin.Creator):
    """A grouped package of loaded content"""

    name = "assembly"
    label = "Assembly"
    family = "assembly"
    icon = "cubes"
