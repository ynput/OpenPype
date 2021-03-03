from pype.hosts.maya.api import plugin


class CreateMayaAscii(plugin.Creator):
    """Raw Maya Ascii file export"""

    name = "mayaAscii"
    label = "Maya Ascii"
    family = "mayaAscii"
    icon = "file-archive-o"
    defaults = ['Main']
