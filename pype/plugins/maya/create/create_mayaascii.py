import avalon.maya


class CreateMayaAscii(avalon.maya.Creator):
    """Raw Maya Ascii file export"""

    name = "mayaAscii"
    label = "Maya Ascii"
    family = "mayaAscii"
    icon = "file-archive-o"
    defaults = ['Main']
