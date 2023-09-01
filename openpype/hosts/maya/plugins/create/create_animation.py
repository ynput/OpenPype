from openpype.hosts.maya.api import (
    lib,
    plugin
)
from openpype.lib import (
    BoolDef,
    TextDef
)


class CreateAnimation(plugin.MayaHiddenCreator):
    """Animation output for character rigs

    We hide the animation creator from the UI since the creation of it is
    automated upon loading a rig. There's an inventory action to recreate it
    for loaded rigs if by chance someone deleted the animation instance.
    """
    identifier = "io.openpype.creators.maya.animation"
    name = "animationDefault"
    label = "Animation"
    family = "animation"
    icon = "male"

    write_color_sets = False
    write_face_sets = False
    include_parent_hierarchy = False
    include_user_defined_attributes = False

    def get_instance_attr_defs(self):

        defs = lib.collect_animation_defs()

        defs.extend([
            BoolDef("writeColorSets",
                    label="Write vertex colors",
                    tooltip="Write vertex colors with the geometry",
                    default=self.write_color_sets),
            BoolDef("writeFaceSets",
                    label="Write face sets",
                    tooltip="Write face sets with the geometry",
                    default=self.write_face_sets),
            BoolDef("writeNormals",
                    label="Write normals",
                    tooltip="Write normals with the deforming geometry",
                    default=True),
            BoolDef("renderableOnly",
                    label="Renderable Only",
                    tooltip="Only export renderable visible shapes",
                    default=False),
            BoolDef("visibleOnly",
                    label="Visible Only",
                    tooltip="Only export dag objects visible during "
                            "frame range",
                    default=False),
            BoolDef("includeParentHierarchy",
                    label="Include Parent Hierarchy",
                    tooltip="Whether to include parent hierarchy of nodes in "
                            "the publish instance",
                    default=self.include_parent_hierarchy),
            BoolDef("worldSpace",
                    label="World-Space Export",
                    default=True),
            BoolDef("includeUserDefinedAttributes",
                    label="Include User Defined Attributes",
                    default=self.include_user_defined_attributes),
            TextDef("attr",
                    label="Custom Attributes",
                    default="",
                    placeholder="attr1, attr2"),
            TextDef("attrPrefix",
                    label="Custom Attributes Prefix",
                    placeholder="prefix1, prefix2")
        ])

        # TODO: Implement these on a Deadline plug-in instead?
        """
        # Default to not send to farm.
        self.data["farm"] = False
        self.data["priority"] = 50
        """

        return defs

    def apply_settings(self, project_settings):
        super(CreateAnimation, self).apply_settings(project_settings)
        # Hardcoding creator to be enabled due to existing settings would
        # disable the creator causing the creator plugin to not be
        # discoverable.
        self.enabled = True
