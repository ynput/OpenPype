"""Load an animation in Blender."""

from typing import Dict, List, Optional

import bpy

from openpype.hosts.blender.api import plugin
from openpype.hosts.blender.api.pipeline import AVALON_PROPERTY


class BlendAnimationLoader(plugin.AssetLoader):
    """Load animations from a .blend file.

    Warning:
        Loading the same asset more then once is not properly supported at the
        moment.
    """

    families = ["animation"]
    representations = ["blend"]

    label = "Link Animation"
    icon = "code-fork"
    color = "orange"
    color_tag = "COLOR_01"

    def _load_blend(self, libpath, asset_group):
        # Load actions from libpath library.
        with bpy.data.libraries.load(
            libpath, link=True, relative=False
        ) as (data_from, data_to):
            data_to.actions = data_from.actions

        assert data_to.actions, "No actions found"

        actions_by_namespace = {}
        orphans_actions = []

        # Collection action by namespace or in orphans_actions list.
        for action in data_to.actions:
            metadata = action.get(AVALON_PROPERTY)
            if metadata:
                namespaces = metadata.get("namespaces")
                if namespaces:
                    for namespace in namespaces:
                        actions_by_namespace[namespace] = action
                else:
                    orphans_actions.append(action)

        # Try to assign linked actions by collection using namespace metadata.
        for collection in bpy.data.collections:
            metadata = collection.get(AVALON_PROPERTY)
            if metadata and metadata.get("namespace") in actions_by_namespace:
                action = actions_by_namespace.get(metadata["namespace"])
                for obj in collection.all_objects:
                    if not obj.animation_data:
                        obj.animation_data_create()
                    obj.animation_data.action = action

        # Try to assign linked actions by user names.
        for action in orphans_actions:
            for user_name in action[AVALON_PROPERTY]["users"]:
                obj = bpy.data.objects.get(user_name)
                if obj:
                    if not obj.animation_data:
                        obj.animation_data_create()
                    obj.animation_data.action = action

        plugin.orphans_purge()

        return []

    def process_asset(
        self, context: dict, name: str, namespace: Optional[str] = None,
        options: Optional[Dict] = None
    ) -> Optional[List]:
        """
        Arguments:
            name: Use pre-defined name
            namespace: Use pre-defined namespace
            context: Full parenthood of representation to load
            options: Additional settings dictionary
        """
        libpath = self.fname
        asset = context["asset"]["name"]
        subset = context["subset"]["name"]

        asset_name = plugin.asset_name(asset, subset)

        asset_group = bpy.data.collections.new(asset_name)
        asset_group.color_tag = self.color_tag
        plugin.get_main_collection().children.link(asset_group)

        objects = self._load_blend(libpath, asset_group)

        self._update_metadata(
            asset_group, context, name, namespace, asset_name, libpath
        )

        self[:] = objects
        return objects

    def exec_update(self, container: Dict, representation: Dict):
        """Update the loaded asset"""
        self._update_process(container, representation)

    def exec_remove(self, container) -> bool:
        """Remove the existing container from Blender scene"""
        # Restor action from override library reference animation data.
        for obj in list(bpy.data.objects):
            if (
                obj.animation_data and
                obj.override_library and
                obj.override_library.reference and
                obj.override_library.reference.animation_data and
                obj.override_library.reference.animation_data.action
            ):
                obj.animation_data.action = (
                    obj.override_library.reference.animation_data.action
                )

        return self._remove_container(container)
