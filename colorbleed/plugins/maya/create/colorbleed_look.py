import avalon.maya
from colorbleed.maya import lib


class CreateLook(avalon.maya.Creator):
    """Polygonal geometry for animation"""

    name = "lookDefault"
    label = "Look Dev"
    family = "colorbleed.lookdev"

    def __init__(self, *args, **kwargs):
        super(CreateLook, self).__init__(*args, **kwargs)

        data = lib.OrderedDict(**self.data)
        data["renderlayer"] = lib.get_current_renderlayer()

        self.data = data
