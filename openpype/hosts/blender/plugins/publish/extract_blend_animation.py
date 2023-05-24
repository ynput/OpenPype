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

        # Deactivate preview range
        bpy.context.scene.use_preview_range = False

        # Keep animation assignations for auto reassign at loading
        actions = set()
        for datablock in instance:
            if isinstance(datablock, bpy.types.Collection):
                actions.update(
                    {
                        obj.animation_data.action
                        for obj in datablock.all_objects
                        if obj.animation_data and obj.animation_data.action
                    }
                )

            elif isinstance(datablock, bpy.types.Object):
                # Skip if object not animated
                if (
                    datablock.animation_data
                    and datablock.animation_data.action
                ):
                    actions.add(datablock.animation_data.action)

            elif isinstance(datablock, bpy.types.Action):
                actions.add(datablock)

        # TODO could be optimized with user_map
        for action in actions:
            action["users"] = [
                o.name
                for o in bpy.data.objects
                if o.animation_data and o.animation_data.action == action
            ]

        super().process(instance)
