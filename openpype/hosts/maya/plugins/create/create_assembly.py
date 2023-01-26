from openpype.hosts.maya.api import plugin


class CreateAssembly(plugin.MayaCreator):
    """A grouped package of loaded content"""

    identifier = "io.openpype.creators.maya.assembly"
    label = "Assembly"
    family = "assembly"
    icon = "cubes"
