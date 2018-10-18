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

        data = {"writeColorSets": False,  # Vertex colors with the geometry.
                "attr": "",  # Add options for custom attributes
                "attrPrefix": ""}

        self.data.update(data)
