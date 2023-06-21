from openpype.hosts.maya.api import (
    lib,
    plugin
)


class CreateAnimation(plugin.Creator):
    """Animation output for character rigs"""

    # We hide the animation creator from the UI since the creation of it
    # is automated upon loading a rig. There's an inventory action to recreate
    # it for loaded rigs if by chance someone deleted the animation instance.
    # Note: This setting is actually applied from project settings
    enabled = False

    name = "animationDefault"
    label = "Animation"
    family = "animation"
    icon = "male"
    includeUserDefinedAttributes = False
    eulerFilter = True
    noNormals = False
    preRoll = False
    renderableOnly = False
    uvWrite = True
    writeColorSets = False
    writeFaceSets = False
    wholeFrameGeo = False
    worldSpace = True
    writeVisibility = True
    writeUVSets = True
    writeCreases = False
    dataFormat = "ogawa"
    step = 1.0
    attr = ""
    attrPrefix = ""
    stripNamespaces = True
    verbose = False
    preRollStartFrame = 0
    farm = False
    priority = 50
    includeParentHierarchy = False  # Include parent groups
    refresh = False  # Default to suspend refresh.
    visibleOnly = False  # only nodes that are visible

    def __init__(self, *args, **kwargs):
        super(CreateAnimation, self).__init__(*args, **kwargs)

        # get basic animation data : start / end / handles / steps
        for key, value in lib.collect_animation_data().items():
            self.data[key] = value

        attrs = [
            "includeUserDefinedAttributes",
            "eulerFilter",
            "noNormals",
            "preRoll",
            "renderableOnly",
            "uvWrite",
            "writeColorSets",
            "writeFaceSets",
            "wholeFrameGeo",
            "worldSpace",
            "writeVisibility",
            "writeUVSets",
            "writeCreases",
            "dataFormat",
            "step",
            "attr",
            "attrPrefix",
            "stripNamespaces",
            "verbose",
            "preRollStartFrame",
            "farm",
            "priority",
            "includeParentHierarchy",
            "refresh",
            "visibleOnly"
        ]
        for attr in attrs:
            self.data[attr] = getattr(self, attr)
