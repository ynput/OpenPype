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
    write_color_sets = False
    write_face_sets = False
    include_parent_hierarchy = False
    include_user_defined_attributes = False

    def __init__(self, *args, **kwargs):
        super(CreateAnimation, self).__init__(*args, **kwargs)

        # create an ordered dict with the existing data first

        # get basic animation data : start / end / handles / steps
        for key, value in lib.collect_animation_data().items():
            self.data[key] = value

        # Write vertex colors with the geometry.
        self.data["writeColorSets"] = self.write_color_sets
        self.data["writeFaceSets"] = self.write_face_sets

        # Include only renderable visible shapes.
        # Skips locators and empty transforms
        self.data["renderableOnly"] = False

        # Include only nodes that are visible at least once during the
        # frame range.
        self.data["visibleOnly"] = False

        # Include the groups above the out_SET content
        self.data["includeParentHierarchy"] = self.include_parent_hierarchy

        # Default to exporting world-space
        self.data["worldSpace"] = True

        # Default to not send to farm.
        self.data["farm"] = False
        self.data["priority"] = 50

        # Default to write normals.
        self.data["writeNormals"] = True

        value = self.include_user_defined_attributes
        self.data["includeUserDefinedAttributes"] = value
