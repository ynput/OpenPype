from openpype.hosts.maya.api import plugin


class CreateLayout(plugin.Creator):
    """A grouped package of loaded content"""

    name = "layoutMain"
    label = "Layout"
    family = "layout"
    icon = "cubes"
