from collections import OrderedDict
import avalon.maya
from colorbleed.maya import lib


class CreateYetiFur(avalon.maya.Creator):
    """Cached yeti fur extraction"""

    name = "yetiFur"
    label = "Yeti Fur"
    family = "colorbleed.yetifur"

    def __init__(self, *args, **kwargs):
        super(CreateYetiFur, self).__init__(*args, **kwargs)

        # get scene values as defaults
        data = OrderedDict(**self.data)
        animation_data = lib.collect_animation_data()
        for key, value in animation_data.items():
            data[key] = value

        self.data = data
