import colorbleed.plugin


class CreateInstance(colorbleed.plugin.Creator):
    """Maya instancer using cached particles"""

    name = "instanceDefault"
    label = "Instance"
    family = "colorbleed.instance"
    abbreviation = "inst"
