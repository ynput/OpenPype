import avalon.maya


class CreateInstance(avalon.maya.Creator):
    """Maya instancer using cached particles"""

    name = "instanceDefault"
    label = "Instance"
    family = "colorbleed.instance"
