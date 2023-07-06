from maya import cmds

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
    settings_attrs = [
        "step",
        "writeColorSets",
        "writeFaceSets",
        "renderableOnly",
        "visibleOnly",
        "includeParentHierarchy",
        "worldSpace",
        "farm",
        "priority",
        "writeNormals",
        "includeUserDefinedAttributes",
        "attr",
        "attrPrefix",
        "dataFormat",
        "eulerFilter",
        "noNormals",
        "preRoll",
        "preRollStartFrame",
        "refresh",
        "stripNamespaces",
        "uvWrite",
        "verbose",
        "wholeFrameGeo",
        "writeCreases",
        "writeUVSets",
        "writeVisibility"
    ]

    def __init__(self, *args, **kwargs):
        super(CreateAnimation, self).__init__(*args, **kwargs)

        # get basic animation data : start / end / handles / steps
        for key, value in lib.collect_animation_data().items():
            self.data[key] = value

        # Setting value from settings.
        for attr in self.settings_attrs:
            if not hasattr(self, attr):
                continue

            self.data[attr] = getattr(self, attr)

    def post_imprint(self, objset):
        for attr in self.settings_attrs:
            editable = attr + "_editable"

            if not hasattr(self, editable):
                continue

            if getattr(self, editable):
                continue

            self.log.debug(
                "Locking \"{}\" because its disabled in settings".format(attr)
            )
            cmds.setAttr(
                objset + "." + attr, channelBox=False, lock=True
            )
