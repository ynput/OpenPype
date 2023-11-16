from openpype.hosts.maya.api import plugin


class CreateXgen(plugin.MayaCreator):
    """Xgen"""

    identifier = "io.openpype.creators.maya.xgen"
    label = "Xgen"
    family = "xgen"
    icon = "pagelines"
