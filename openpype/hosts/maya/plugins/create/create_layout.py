from openpype.hosts.maya.api import plugin


class CreateLayout(plugin.Creator):
    """A grouped package of loaded content"""

    name = "layoutMain"
    label = "Layout"
    family = "layout"
    icon = "cubes"

    def __init__(self, *args, **kwargs):
        super(CreateLayout, self).__init__(*args, **kwargs)
        # enable this when you want to
        # publish group of loaded asset
        self.data["groupLoadedAssets"] = False
