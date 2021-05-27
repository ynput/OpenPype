from pype.hosts.maya import plugin


class CreateLayout(plugin.Creator):
    """A grouped package of loaded content"""

    name = "layoutMain"
    label = "Layout"
    family = "layout"
    icon = "cubes"
    defaults = ["Main"]
