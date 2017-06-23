import avalon.maya
import colorbleed.api as api


class CreateYetiFur(avalon.maya.Creator):
    """Cached yeti fur extraction"""

    name = "yetiFur"
    label = "Yeti Fur"
    family = "colorbleed.yetifur"

    def process(self):

        time_with_handles = api.OrderedDict(startFrame=True,
                                            endFrame=True,
                                            handles=True)

        api.merge()
