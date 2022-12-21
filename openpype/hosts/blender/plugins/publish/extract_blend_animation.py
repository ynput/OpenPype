import bpy

from openpype.hosts.blender.plugins.publish.extract_blend import ExtractBlend


class ExtractBlendAnimation(ExtractBlend):
    """Extract animation as blend file."""

    label = "Extract Anim Blend"
    hosts = ["blender"]
    families = ["animation"]
    optional = True

    def process(self, instance):
        """Override `process` to keep users of action.

        Users are reassigned when loading animation.
        """

        # Perform extraction
        self.log.info("Performing extraction...")

        # Keep animation assignations for auto reassign at loading
        for datablock in instance:
            if isinstance(datablock, bpy.types.Object):
                action = datablock.animation_data.action
            else:
                action = datablock
            action["users"] = [
                o.name
                for o in bpy.data.objects
                if o.animation_data and o.animation_data.action == action
            ]

        super().process(instance)
