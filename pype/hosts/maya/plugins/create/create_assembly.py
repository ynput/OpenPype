import avalon.maya


class CreateAssembly(avalon.maya.Creator):
    """A grouped package of loaded content"""

    name = "assembly"
    label = "Assembly"
    family = "assembly"
    icon = "cubes"
    defaults = ['Main']
