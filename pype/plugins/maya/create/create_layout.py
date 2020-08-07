import avalon.maya


class CreateLayout(avalon.maya.Creator):
    """A grouped package of loaded content"""

    name = "layoutMain"
    label = "Layout"
    family = "layout"
    icon = "cubes"
    defaults = ["Main"]
