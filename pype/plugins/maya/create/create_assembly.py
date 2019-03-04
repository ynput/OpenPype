import avalon.maya


class CreateAssembly(avalon.maya.Creator):
    """A grouped package of loaded content"""

    name = "assembly"
    label = "Assembly"
    family = "assembly"
    icon = "boxes"
    defaults = ['Main']
