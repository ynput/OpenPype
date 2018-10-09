from collections import OrderedDict
import avalon.maya
from colorbleed.maya import lib


class CreateCamera(avalon.maya.Creator):
    """Single baked camera"""

    name = "cameraDefault"
    label = "Camera"
    family = "colorbleed.camera"
    icon = "video-camera"

    def __init__(self, *args, **kwargs):
        super(CreateCamera, self).__init__(*args, **kwargs)

        # get basic animation data : start / end / handles / steps
        data = OrderedDict(**self.data)
        animation_data = lib.collect_animation_data()
        for key, value in animation_data.items():
            data[key] = value

        # Bake to world space by default, when this is False it will also
        # include the parent hierarchy in the baked results
        data['bake_to_world_space'] = True

        self.data = data
