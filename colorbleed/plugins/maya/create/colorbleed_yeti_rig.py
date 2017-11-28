import avalon.maya


class CreateYetiRig(avalon.maya.Creator):
    """Output for procedural plugin nodes ( Yeti / XGen / etc)"""

    name = "yetiDefault"
    label = "Procedural"
    family = "colorbleed.yetirig"
    icon = "usb"

    def __init__(self, *args, **kwargs):
        super(CreateYetiRig, self).__init__(*args, **kwargs)

        self.data["preroll"] = 0
