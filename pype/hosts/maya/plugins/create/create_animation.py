import avalon.maya
from pype.hosts.maya import lib


class CreateAnimation(avalon.maya.Creator):
    """Animation output for character rigs"""

    name = "animationDefault"
    label = "Animation"
    family = "animation"
    icon = "male"
    defaults = ['Main']

    def __init__(self, *args, **kwargs):
        super(CreateAnimation, self).__init__(*args, **kwargs)

        # create an ordered dict with the existing data first

        # get basic animation data : start / end / handles / steps
        for key, value in lib.collect_animation_data().items():
            self.data[key] = value

        # Write vertex colors with the geometry.
        self.data["writeColorSets"] = False

        # Include only renderable visible shapes.
        # Skips locators and empty transforms
        self.data["renderableOnly"] = False

        # Include only nodes that are visible at least once during the
        # frame range.
        self.data["visibleOnly"] = False

        # Include the groups above the out_SET content
        self.data["includeParentHierarchy"] = False  # Include parent groups

        # Default to exporting world-space
        self.data["worldSpace"] = True
