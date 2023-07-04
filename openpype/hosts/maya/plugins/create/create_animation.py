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
    writeNormals = True  # Multiverse specific attribute.

    def __init__(self, *args, **kwargs):
        super(CreateAnimation, self).__init__(*args, **kwargs)

        # get basic animation data : start / end / handles / steps
        for key, value in lib.collect_animation_data().items():
            self.data[key] = value

        attrs = [
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
        for attr in attrs:
            value = getattr(self, attr)
            if isinstance(value, dict):
                if not value["enabled"]:
                    self.log.debug(
                        "Skipping \"{}\" because its disabled in "
                        "settings".format(attr)
                    )
                    continue
                value = value["value"]

            # Setting value from settings.
            self.data[attr] = value
