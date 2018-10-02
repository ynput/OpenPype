from collections import OrderedDict
import avalon.maya
from pype.maya import lib


class CreateLook(avalon.maya.Creator):
    """Shader connections defining shape look"""

    name = "look"
    label = "Look"
    family = "studio.look"
    icon = "paint-brush"

    def __init__(self, *args, **kwargs):
        super(CreateLook, self).__init__(*args, **kwargs)

        data = OrderedDict(**self.data)
        data["renderlayer"] = lib.get_current_renderlayer()

        self.data = data
