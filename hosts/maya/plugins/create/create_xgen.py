from openpype.hosts.maya.api import plugin


class CreateXgen(plugin.Creator):
    """Xgen interactive export"""

    name = "xgen"
    label = "Xgen Interactive"
    family = "xgen"
    icon = "pagelines"
