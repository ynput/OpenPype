from collections import OrderedDict

import avalon.maya


class CreateVRayScene(avalon.maya.Creator):

    label = "VRay Scene"
    family = "colorbleed.vrayscene"
    # icon = "blocks"

    def __init__(self, *args, **kwargs):
        super(CreateVRayScene, self).__init__(*args, **kwargs)

        # We won't be publishing this one
        self.data["id"] = "avalon.vrayscene"

        # We don't need subset or asset attributes
        self.data.pop("subset", None)
        self.data.pop("asset", None)
        self.data.pop("active", None)

        data = OrderedDict(**self.data)

        data["camera"] = "persp"
        data["pools"] = ""

        self.data = data

        self.options = {"useSelection": False}  # Force no content
