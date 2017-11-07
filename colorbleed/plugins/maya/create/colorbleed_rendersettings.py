from collections import OrderedDict

import avalon.maya
from colorbleed.maya import lib


class CreateRenderSettings(avalon.maya.Creator):

    label = "Render Settings"
    family = "colorbleed.rendersettings"
    icon = "gears"

    def __init__(self, *args, **kwargs):
        super(CreateRenderSettings, self).__init__(*args, **kwargs)

        data = OrderedDict(**self.data)

        data["publish"] = True
        data["includeDefaultRenderLayer"] = False
        data["overrideFrameRange"] = False

        # Get basic animation data : start / end / handles / steps
        for key, value in lib.collect_animation_data().items():
            data[key] = value

        self.data = data