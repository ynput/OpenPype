"""Load a layout in Blender."""
import bpy

from openpype.hosts.blender.api.properties import OpenpypeContainer
from openpype.hosts.blender.api import plugin


class LayoutLoader(plugin.AssetLoader):
    """Link layout from a .blend file."""

    color = "orange"

    def _make_local_actions(self, container: OpenpypeContainer):
        """Make local for all actions from objects.

        Actions are duplicated to keep the original action from layout.

        Args:
            container (OpenpypeContainer): Loaded container
        """

        for obj in {
            d
            for d in container.datablock_refs
            if isinstance(d.datablock, bpy.types.Object)
            and d.datablock.animation_data
            and d.datablock.animation_data.action
        }:
            # Get loaded action from linked action.
            loaded_action = obj.datablock.animation_data.action
            loaded_action.use_fake_user = True

            # Get orignal action name and add suffix for reference.
            orignal_action_name = loaded_action.name
            loaded_action.name += ".ref"
            # Make local action, rename and upadate local_actions dict.
            if loaded_action.library:
                local_action = loaded_action.make_local()
            else:
                local_action = loaded_action.copy()
            local_action.name = orignal_action_name

            # Assign local action.
            obj.datablock.animation_data.action = local_action

        # Purge data
        plugin.orphans_purge()

    def load(self, *args, **kwargs):
        """Override `load` to create one animation instance by loaded rig."""
        container, datablocks = super().load(*args, **kwargs)

        # Make loaded actions local, original ones are kept for reference.
        self._make_local_actions(container)

        return container, datablocks

    def update(self, *args, **kwargs):
        """Override `update` to reassign changed objects to instances'."""
        container, datablocks = super().update(*args, **kwargs)

        # Reassign changed objects by matching the name
        for instance in bpy.context.scene.openpype_instances:
            for d_ref in instance.datablock_refs:
                matched_obj = bpy.context.scene.collection.all_objects.get(
                    d_ref.name
                )
                if matched_obj:
                    d_ref.datablock = matched_obj

        return container, datablocks


class LinkLayoutLoader(LayoutLoader):
    """Link layout from a .blend file."""

    families = ["layout"]
    representations = ["blend"]

    label = "Link Layout"
    icon = "link"
    order = 0

    load_type = "LINK"


class AppendLayoutLoader(LayoutLoader):
    """Append layout from a .blend file."""

    families = ["layout"]
    representations = ["blend"]

    label = "Append Layout"
    icon = "paperclip"
    order = 2

    load_type = "APPEND"
