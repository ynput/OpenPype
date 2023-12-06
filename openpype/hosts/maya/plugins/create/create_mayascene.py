from openpype.hosts.maya.api import plugin


class CreateMayaScene(plugin.MayaCreator):
    """Raw Maya Scene file export"""

    identifier = "io.openpype.creators.maya.mayascene"
    name = "mayaScene"
    label = "Maya Scene"
    family = "mayaScene"
    icon = "file-archive-o"
