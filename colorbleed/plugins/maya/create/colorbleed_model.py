from collections import OrderedDict

import avalon.maya


class CreateModel(avalon.maya.Creator):
    """Polygonal static geometry"""

    name = "modelDefault"
    label = "Model"
    family = "colorbleed.model"
    icon = "cube"

    def __init__(self, *args, **kwargs):
        super(CreateModel, self).__init__(*args, **kwargs)

        # create an ordered dict with the existing data first
        data = OrderedDict(**self.data)

        # Write vertex colors with the geometry.
        data["writeColorSets"] = False

        self.data = data
