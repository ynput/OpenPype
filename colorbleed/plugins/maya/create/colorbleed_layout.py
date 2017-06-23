import avalon.maya
from colorbleed.maya import lib


class CreateLayout(avalon.maya.Creator):
    """The layout of a episode / sequence / shot """

    name = "layoutDefault"
    label = "Layout"
    family = "colorbleed.layout"

    def __init__(self, *args, **kwargs):
        super(CreateLayout, self).__init__(*args, **kwargs)

        # create an ordered dict with the existing data first
        data = lib.OrderedDict(**self.data)

        # get basic animation data : start / end / handles / steps
        for key, value in lib.collect_animation_data().items():
            data[key] = value

        # Write vertex colors with the geometry.
        data["writeColorSets"] = False

        # Write GPU cache as placeholder cube in stead of full data
        data["placeholder"] = False

        # Include only renderable visible shapes.
        # Skips locators and empty transforms
        data["renderableOnly"] = False

        # Include only nodes that are visible at least once during the
        # frame range.
        data["visibleOnly"] = False

        self.data = data
