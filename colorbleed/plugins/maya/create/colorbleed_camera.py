from collections import OrderedDict
import colorbleed.plugin
from colorbleed.maya import lib


class CreateCamera(colorbleed.plugin.Creator):
    """Single baked camera extraction"""

    name = "cameraDefault"
    label = "Camera"
    family = "colorbleed.camera"
    abbreviation = "cam"

    def __init__(self, *args, **kwargs):
        super(CreateCamera, self).__init__(*args, **kwargs)

        # get basic animation data : start / end / handles / steps
        data = OrderedDict(**self.data)
        animation_data = lib.collect_animation_data()
        for key, value in animation_data.items():
            data[key] = value

        self.data = data
