import avalon.maya


class CreateYetiRig(avalon.maya.Creator):
    """Output for procedural plugin nodes ( Yeti / XGen / etc)"""

    name = "yetiDefault"
    label = "Yeti Cache"
    family = "colorbleed.yeticache"
    icon = "pagelines"

    def __init__(self, *args, **kwargs):
        super(CreateYetiRig, self).__init__(*args, **kwargs)

        self.data["peroll"] = 0
