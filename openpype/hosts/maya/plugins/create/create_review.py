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
    Width = 0
    Height = 0
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
        data = OrderedDict(**self.data)

        # get basic animation data : start / end / handles / steps
        for key, value in lib.get_frame_range().items():
            data[key] = value

        data["fps"] = lib.collect_animation_data(fps=True)["fps"]
        data["review_width"] = self.Width
        data["review_height"] = self.Height
        data["isolate"] = self.isolate
        data["keepImages"] = self.keepImages
        data["imagePlane"] = self.imagePlane
        data["transparency"] = self.transparency

        self.data = data
