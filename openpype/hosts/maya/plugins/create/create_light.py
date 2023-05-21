from openpype.hosts.maya.api import plugin


class CreateLight(plugin.Creator):
    """Light"""

    name = "light"
    label = "Light"
    family = "light"
    icon = "cube"
