from openpype.hosts.maya.api import plugin


class CreateXgen(plugin.MayaCreator):
    """Xgen interactive export"""

    identifier = "io.openpype.creators.maya.xgen"
    label = "Xgen Interactive"
    family = "xgen"
    icon = "pagelines"
