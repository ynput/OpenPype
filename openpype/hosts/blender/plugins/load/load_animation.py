"""Load an animation in Blender."""

from typing import Dict, Optional

import bpy

from openpype.hosts.blender.api import plugin


class AnimationLoader(plugin.AssetLoader):
    """Load animations from a .blend file."""

    color = "orange"

    bl_types = frozenset({bpy.types.Action})

    def load(
        self,
        context: dict,
        name: Optional[str] = None,
        namespace: Optional[str] = None,
        options: Optional[Dict] = None,
    ) -> Optional[bpy.types.Collection]:
        container, datablocks = super().load(context, name, namespace, options)

        # Try to assign linked actions by parsing their name
        for action in datablocks:
            # armature_name = action.get("armature", "")
            users = action.get("users", {})
            for user_name in users:
                obj = bpy.context.scene.objects.get(user_name)
                if obj:
                    # Ensure animation data
                    if not obj.animation_data:
                        obj.animation_data_create()

                    # Assign action
                    obj.original_action = obj.animation_data.action
                    obj.animation_data.action = action
                else:
                    self.log.debug(
                        f"Cannot match armature by name '{user_name}' "
                        f"for action: {action.name}"
                    )
                    continue

        return container, datablocks

    def remove(self, container: Dict) -> bool:
        """Override `remove` to restore original actions to objects."""
        # Restore original actions
        scene_container = self._get_scene_container(container)
        for d_ref in scene_container.datablock_refs:
            for obj in bpy.context.scene.collection.all_objects:
                if (
                    obj.type == "ARMATURE"
                    and obj.animation_data
                    and obj.animation_data.action == d_ref.datablock
                ):
                    obj.animation_data.action = obj.original_action

        return super().remove(container)


class LinkAnimationLoader(AnimationLoader):
    """Link animations from a .blend file."""

    families = ["animation"]
    representations = ["blend"]

    label = "Link Animation"
    icon = "link"
    order = 0

    load_type = "LINK"


class AppendAnimationLoader(AnimationLoader):
    """Append animations from a .blend file."""

    families = ["animation"]
    representations = ["blend"]

    label = "Append Animation"
    icon = "paperclip"
    order = 1

    load_type = "APPEND"
