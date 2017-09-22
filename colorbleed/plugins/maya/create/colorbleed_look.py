from collections import OrderedDict
import avalon.maya
from colorbleed.maya import lib


class CreateLook(avalon.maya.Creator):
    """Polygonal geometry for animation"""

    name = "look"
    label = "Look"
    family = "colorbleed.look"

    def __init__(self, *args, **kwargs):
        super(CreateLook, self).__init__(*args, **kwargs)

        data = OrderedDict(**self.data)
        data["renderlayer"] = lib.get_current_renderlayer()

        self.data = data
