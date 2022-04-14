from collections import OrderedDict
from openpype.hosts.maya.api import (
    lib,
    plugin
)


class CreateReview(plugin.Creator):
    """Single baked camera"""

    name = "reviewDefault"
    label = "Review"
    family = "review"
    icon = "video-camera"
    keepImages = False
    isolate = False
    imagePlane = True
    transparency = [
        "preset",
        "simple",
        "object sorting",
        "weighted average",
        "depth peeling",
        "alpha cut"
    ]

    def __init__(self, *args, **kwargs):
        super(CreateReview, self).__init__(*args, **kwargs)

        # get basic animation data : start / end / handles / steps
        data = OrderedDict(**self.data)
        animation_data = lib.collect_animation_data(fps=True)
        for key, value in animation_data.items():
            data[key] = value

        data["isolate"] = self.isolate
        data["keepImages"] = self.keepImages
        data["imagePlane"] = self.imagePlane
        data["transparency"] = self.transparency

        self.data = data
