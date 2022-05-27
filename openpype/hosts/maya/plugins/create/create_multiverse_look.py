from openpype.hosts.maya.api import plugin, lib


class CreateMultiverseLook(plugin.Creator):
    """Create Multiverse Look"""

    name = "mvLook"
    label = "Multiverse Look"
    family = "mvLook"
    icon = "cubes"

    def __init__(self, *args, **kwargs):
        super(CreateMultiverseLook, self).__init__(*args, **kwargs)
        self.data["fileFormat"] = ["usda", "usd"]
        self.data["expectMipMap"] = True
