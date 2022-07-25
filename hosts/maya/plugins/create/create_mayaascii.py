from openpype.hosts.maya.api import plugin


class CreateMayaScene(plugin.Creator):
    """Raw Maya Scene file export"""

    name = "mayaScene"
    label = "Maya Scene"
    family = "mayaScene"
    icon = "file-archive-o"
