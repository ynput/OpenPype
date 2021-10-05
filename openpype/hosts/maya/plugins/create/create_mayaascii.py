from openpype.hosts.maya.api import plugin


class CreateMayaScene(plugin.Creator):
    """Raw Maya Ascii file export"""

    name = "mayaScene"
    label = "Maya Scene"
    family = "mayaScene"
    icon = "file-archive-o"
    defaults = ['Main']
