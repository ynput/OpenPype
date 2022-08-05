"""Load a layout in Blender."""
from contextlib import contextmanager
from typing import Dict

import bpy

from openpype import lib
from openpype.pipeline import legacy_io, legacy_create, AVALON_INSTANCE_ID
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
    color_tag = "COLOR_02"

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
    animation_instance_mode = "global"

    def _get_rig_assets(self, asset_group):
        return [
            child
            for child in plugin.get_children_recursive(asset_group)
            if plugin.is_container(child, family="rig")
        ]

    def _get_animation_collection(self, subset):
        for collection in plugin.get_children_recursive(
            bpy.context.scene.collection
        ):
            if (
                collection.get(AVALON_PROPERTY)
                and collection[AVALON_PROPERTY]["id"] == AVALON_INSTANCE_ID
                and collection[AVALON_PROPERTY]["family"] == "animation"
                and collection[AVALON_PROPERTY]["subset"] == subset
            ):
                return collection

    def _create_animation_collection(self, name, rig_assets, dependency):
        creator_plugin = get_legacy_creator_by_name("CreateAnimation")
        if not creator_plugin:
            raise ValueError(
                'Creator plugin "CreateAnimation" was not found.'
            )

        legacy_create(
            creator_plugin,
            name=name,
            asset=legacy_io.Session.get("AVALON_ASSET"),
            options={"useSelection": False, "asset_groups": rig_assets},
            data={"dependencies": dependency}
        )

    def _make_local_actions(self, asset_group):
        """Make local for all actions from objects."""

        task = legacy_io.Session.get("AVALON_TASK")
        asset = legacy_io.Session.get("AVALON_ASSET")

        local_actions = {}

        for obj in asset_group.all_objects:
            if not obj.animation_data or not obj.animation_data.action:
                continue

            # Get local action from linked action.
            linked_action = obj.animation_data.action
            local_action = local_actions.get(linked_action)

            # Make action local if needed.
            if not local_action:
                # Get local action name with namespace from linked action.
                action_name = linked_action.name.split(":")[-1]
                local_name = f"{asset}_{task}:{action_name}"
                # Make local action, rename and upadate local_actions dict.
                if linked_action.library:
                    local_action = linked_action.make_local()
                else:
                    local_action = linked_action.copy()
                local_action.name = local_name
                local_actions[linked_action] = local_action

            # Assign local action.
            obj.animation_data.action = local_action

    def process_asset(self, *args, **kwargs) -> bpy.types.Collection:
        """Asset loading Process"""
        asset_group = super().process_asset(*args, **kwargs)

        # Create animation collection subset for loaded rig assets.
        if legacy_io.Session.get("AVALON_TASK") == "Animation":

            dependency = asset_group[AVALON_PROPERTY]["representation"]
            rig_assets = self._get_rig_assets(asset_group)

            if self.animation_instance_mode == "global":
                self._create_animation_collection(
                    "animationMain", rig_assets, dependency
                )

            elif self.animation_instance_mode == "rig":
                for rig_asset in rig_assets:
                    namespace = rig_asset[AVALON_PROPERTY].get("namespace")
                    self._create_animation_collection(
                        namespace or rig_asset.name, [rig_asset], dependency
                    )

        return asset_group

    def exec_update(self, container: Dict, representation: Dict):
        """Update the loaded asset"""
        asset_group = self._update_process(container, representation)

        # Add new loaded rig asset groups to animationMain collection.
        if legacy_io.Session.get("AVALON_TASK") == "Animation":

            dependency = asset_group[AVALON_PROPERTY]["representation"]
            rig_assets = self._get_rig_assets(asset_group)

            if self.animation_instance_mode == "global":
                animation_collection = self._get_animation_collection(
                    "animationMain"
                )
                if animation_collection:
                    plugin.link_to_collection(rig_assets, animation_collection)
                else:
                    self._create_animation_collection(
                        "animationMain", rig_assets, dependency
                    )

            elif self.animation_instance_mode == "rig":
                for rig_asset in rig_assets:
                    namespace = rig_asset[AVALON_PROPERTY].get("namespace")
                    animation_collection = self._get_animation_collection(
                        namespace or rig_asset.name
                    )
                    if animation_collection:
                        plugin.link_to_collection(
                            rig_asset, animation_collection
                        )
                    else:
                        self._create_animation_collection(
                            namespace or rig_asset.name,
                            [rig_asset],
                            dependency,
                        )

        return asset_group


class LinkLayoutLoader(LayoutLoader):
    """Link layout from a .blend file."""

    families = ["layout"]
    representations = ["blend"]

    label = "Link Layout"
    icon = "link"
    order = 0

    def _process(self, libpath, asset_group):
        self._link_blend(libpath, asset_group)
        self._make_local_actions(asset_group)


class AppendLayoutLoader(LayoutLoader):
    """Append layout from a .blend file."""

    families = ["layout"]
    representations = ["blend"]

    label = "Append Layout"
    icon = "paperclip"
    order = 2

    def _process(self, libpath, asset_group):
        self._append_blend(libpath, asset_group)
        self._make_local_actions(asset_group)
