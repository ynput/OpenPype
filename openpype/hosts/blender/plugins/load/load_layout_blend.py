"""Load a layout in Blender."""
from contextlib import contextmanager

import bpy

from openpype.hosts.blender.api.properties import (
    OpenpypeContainer,
    OpenpypeInstance,
)
from openpype.pipeline import legacy_io, AVALON_INSTANCE_ID
from openpype.pipeline.create import get_legacy_creator_by_name
from openpype.hosts.blender.api import plugin
from openpype.hosts.blender.api.pipeline import AVALON_PROPERTY


class LayoutMaintainer(plugin.ContainerMaintainer):
    """Overloaded ContainerMaintainer to maintain only needed properties
    for layout container."""

    @contextmanager
    def maintained_animation_instances(self):
        """Maintain animation container content during context."""
        # Store animation instance collections content from scene collection.
        animation_instances = {
            collection.name: {
                "objects": [
                    obj.name
                    for obj in collection.objects
                    if obj in self.container_objects
                ],
                "childrens": [
                    children.name for children in collection.children
                ],
            }
            for collection in plugin.get_children_recursive(
                bpy.context.scene.collection
            )
            if (
                collection.get(AVALON_PROPERTY)
                and collection[AVALON_PROPERTY]["id"] == AVALON_INSTANCE_ID
                and collection[AVALON_PROPERTY]["family"] == "animation"
            )
        }
        try:
            yield
        finally:
            # Restor animation instance collections content.
            scene_collections = set(
                plugin.get_children_recursive(bpy.context.scene.collection)
            )

            for instance_name, content in animation_instances.items():
                # Ensure animation instance still linked to the scene.
                for collection in scene_collections:
                    if collection.name == instance_name:
                        anim_instance = collection
                        scene_collections.remove(collection)
                        break
                else:
                    continue
                # Restor content if animation_instance still valid.
                for collection in scene_collections:
                    if collection.name in content["childrens"]:
                        plugin.link_to_collection(collection, anim_instance)
                for obj in bpy.context.scene.objects:
                    if obj.name in content["objects"]:
                        plugin.link_to_collection(obj, anim_instance)


class LayoutLoader(plugin.AssetLoader):
    """Link layout from a .blend file."""

    color = "orange"

    update_maintainer = LayoutMaintainer
    maintained_parameters = [
        "parent",
        "transforms",
        "modifiers",
        "constraints",
        "targets",
        "drivers",
        "actions",
        "animation_instances",
    ]

    def _create_animation_instance(
        self, armature_object: bpy.types.Object
    ) -> OpenpypeInstance:
        """Create animation instance with given armature object as datablock.
        TODO this is a build first workfile feature, not a loader one.

        Args:
            rig_object (bpy.types.Object): Armature object.

        Raises:
            ValueError: Creator plugin 'CreateAnimation' doesn't exist

        Returns:
            OpenpypeInstance: Created instance
        """
        Creator = get_legacy_creator_by_name("CreateAnimation")
        if not Creator:
            raise ValueError('Creator plugin "CreateAnimation" was not found.')

        asset_name = legacy_io.Session.get("AVALON_ASSET")
        plugin = Creator(
            "animationMain",
            asset_name,
            {"variant": "Main"},
        )
        return plugin.process([armature_object])

    def _make_local_actions(self, container: OpenpypeContainer):
        """Make local for all actions from objects.

        Actions are duplicated to keep the original action from layout.

        Args:
            container (OpenpypeContainer): Loaded container
        """
        task = legacy_io.Session.get("AVALON_TASK")
        asset = legacy_io.Session.get("AVALON_ASSET")

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

            # Get local action name with namespace from linked action.
            # TODO uniformize name building with load rig
            action_name = loaded_action.name.split(":")[-1]
            local_name = f"{asset}_{task}:{action_name}"
            # Make local action, rename and upadate local_actions dict.
            if loaded_action.library:
                local_action = loaded_action.make_local()
            else:
                local_action = loaded_action.copy()
            local_action.name = local_name

            # Assign local action.
            obj.datablock.animation_data.action = local_action

        # Purge data
        plugin.orphans_purge()

    @plugin.exec_process
    def load(self, *args, **kwargs):
        """Override `load` to create one animation instance by loaded rig."""
        container, datablocks = super().load(*args, **kwargs)

        return container, datablocks

        # Kept for later reference in build workfile
        for d in datablocks:
            if isinstance(d, bpy.types.Object) and d.type == "ARMATURE":
                instance = self._create_animation_instance(d)
                instance.name = f"{instance.name}:{d.name}"

    @plugin.exec_process
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

    @plugin.exec_process
    def load(self, *args, **kwargs):
        """Override `load` to make loaded actions local.

        Original ones are kept for reference.
        """
        container, datablocks = super().load(*args, **kwargs)
        self._make_local_actions(container)
        return container, datablocks


class AppendLayoutLoader(LayoutLoader):
    """Append layout from a .blend file."""

    families = ["layout"]
    representations = ["blend"]

    label = "Append Layout"
    icon = "paperclip"
    order = 2

    load_type = "APPEND"

    @plugin.exec_process
    def load(self, *args, **kwargs):
        """Override `load` to make loaded actions local.

        Original ones are kept for reference.
        """
        container, datablocks = super().load(*args, **kwargs)
        self._make_local_actions(container)
        return container, datablocks
