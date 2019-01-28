import avalon.maya
from pype.maya import lib


class CreateFBX(avalon.maya.Creator):
    """FBX Export"""

    name = "fbxDefault"
    label = "FBX"
    family = "fbx"
    icon = "plug"

    def __init__(self, *args, **kwargs):
        super(CreateFBX, self).__init__(*args, **kwargs)

        # get basic animation data : start / end / handles / steps
        for key, value in lib.collect_animation_data().items():
            self.data[key] = value
