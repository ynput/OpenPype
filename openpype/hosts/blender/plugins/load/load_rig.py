"""Load a rig asset in Blender."""

import contextlib
from pathlib import Path
from typing import Dict, List, Optional

import bpy

from openpype import lib
from openpype.pipeline import legacy_create, AVALON_CONTAINER_ID
from openpype.hosts.blender.api import plugin, get_selection
from openpype.hosts.blender.api.pipeline import AVALON_PROPERTY


class BlendRigLoader(plugin.AssetLoader):
    """Load rigs from a .blend file."""

    families = ["rig"]
    representations = ["blend"]

    label = "Link Rig"
    icon = "code-fork"
    color = "orange"
    color_tag = "COLOR_03"

    def _load_blend(self, libpath, asset_group):
        # Load collections from libpath library.
        with bpy.data.libraries.load(
            libpath, link=True, relative=False
        ) as (data_from, data_to):
            data_to.collections = data_from.collections

        # Get the right asset container from imported collections.
        container = self._get_container_from_collections(
            data_to.collections, self.families
        )
        assert container, "No asset container found"

        # Create override library for container and elements.
        override = container.override_hierarchy_create(
            bpy.context.scene, bpy.context.view_layer
        )

        # Rename all overridden objects with group_name prefix.
        for obj in set(override.all_objects):
            obj.name = f"{asset_group.name}:{obj.name}"

        # Rename overridden collections with group_name prefix.
        for child in set(override.children_recursive):
            child.name = f"{asset_group.name}:{child.name}"
            # Disable selection for modeling container.
            if (
                child.get(AVALON_PROPERTY) and
                child[AVALON_PROPERTY].get("id") == AVALON_CONTAINER_ID and
                child[AVALON_PROPERTY].get("family") == "model"
            ):
                child.hide_select = True

        # Force override object data from overridden objects and rename.
        overridden_data = set()
        for obj in set(override.all_objects):
            if obj.data and obj.data not in overridden_data:
                overridden_data.add(obj.data)
                obj.data.override_create(remap_local_usages=True)
                obj.data.name = f"{asset_group.name}:{obj.data.name}"

        # Move objects and child collections from override to asset_group.
        plugin.link_to_collection(override.objects, asset_group)
        plugin.link_to_collection(override.children, asset_group)

        # Clear and purge useless datablocks and selection.
        bpy.data.collections.remove(override)
        plugin.orphans_purge()
        plugin.deselect_all()

        return list(asset_group.all_objects)

    @staticmethod
    def _assign_action(objects, namespace):
        """Assign new action for all objects from linked rig."""

        # If rig contain only one armature.
        armatures = [obj for obj in objects if obj.type == "ARMATURE"]
        if len(armatures) == 1:
            armature = armatures[0]
            if armature.animation_data is None:
                armature.animation_data_create()
            armature.animation_data.action = bpy.data.actions.new(
                f"{namespace}_action"
            )

        # If rig contain multiple armatures, we generate actions for
        # each armature.
        elif armatures:
            for armature in armatures:
                if armature.animation_data is None:
                    armature.animation_data_create()
                armature.animation_data.action = bpy.data.actions.new(
                    f"{namespace}_{armature.name}_action"
                )

        # If rig contain no armature we generate actions for each object.
        else:
            for obj in objects:
                if obj.animation_data is None:
                    obj.animation_data_create()
                obj.animation_data.action = bpy.data.actions.new(
                    f"{namespace}_{obj.name}_action"
                )
        plugin.orphans_purge()

    @staticmethod
    def _apply_options(asset_group, options, context):
        """Apply load options fro asset_group."""

        if options.get("create_animation"):
            creator_plugin = lib.get_creator_by_name("CreateAnimation")
            if not creator_plugin:
                raise ValueError(
                    'Creator plugin "CreateAnimation" was not found.'
                )

            plugin.deselect_all()
            for obj in asset_group.all_objects:
                obj.select_set(True)

            legacy_create(
                creator_plugin,
                name=f"{asset_group.name}_animation",
                asset=context["asset"]["name"],
                options={"useSelection": False, "asset_group": asset_group},
                data={"dependencies": str(context["representation"]["_id"])}
            )

            plugin.deselect_all()

        anim_file = options.get('animation_file')
        if isinstance(anim_file, str) and Path(anim_file).is_file():

            bpy.ops.import_scene.fbx(filepath=anim_file, anim_offset=0.0)
            imported = get_selection()

            armature = None
            for obj in asset_group.all_objects:
                if obj.type == 'ARMATURE':
                    armature = obj

            if not armature:
                raise Exception(f"Armature not found for {asset_group.name}")

            for obj in imported:
                if obj.type == 'ARMATURE':
                    if not armature.animation_data:
                        armature.animation_data_create()
                    armature.animation_data.action = obj.animation_data.action

            for obj in imported:
                bpy.data.objects.remove(obj)

            plugin.orphans_purge()

        action = options.get('action')
        if isinstance(action, bpy.types.Action):
            for obj in asset_group.all_objects:
                if obj.type == 'ARMATURE':
                    if not armature.animation_data:
                        armature.animation_data_create()
                    armature.animation_data.action = action

        parent = options.get('parent')
        if isinstance(parent, bpy.types.Collection):
            plugin.link_to_collection(asset_group, parent)

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
        unique_number = plugin.get_unique_number(asset, subset)
        group_name = plugin.asset_name(asset, subset, unique_number)
        namespace = namespace or f"{asset}_{unique_number}"

        asset_group = bpy.data.collections.new(group_name)
        asset_group.color_tag = self.color_tag
        plugin.get_main_collection().children.link(asset_group)

        objects = self._load_blend(libpath, asset_group)

        self._assign_action(objects, namespace)

        if options is not None:
            self._apply_options(asset_group, options, context)

        self._update_metadata(
            asset_group, context, name, namespace, asset_name, libpath
        )

        self[:] = objects
        return objects

    def exec_update(self, container: Dict, representation: Dict):
        """Update the loaded asset"""
        self._update_process(container, representation)

        # Ensure updated rig has action.
        collection = bpy.data.collections.get(container["objectName"])
        if collection:
            self._assign_action(
                collection.all_objects, container["namespace"]
            )

    def exec_remove(self, container) -> bool:
        """Remove the existing container from Blender scene"""
        return self._remove_container(container)

    @contextlib.contextmanager
    def maintained_actions(self, asset_group):
        """Maintain actions during context."""
        asset_group_name = asset_group.name
        objects_actions = []
        armature_action = None
        # Get the armature from asset_group.
        armatures = [
            obj
            for obj in asset_group.all_objects
            if obj.type == "ARMATURE"
        ]
        # Store action from armature.
        if (
            len(armatures) == 1 and
            armatures[0].animation_data and
            armatures[0].animation_data.action
        ):
            armature_action = armatures[0].animation_data.action
        else:
            # If there is no or multiple armature or no action from armature,
            # we get actions from all objects from asset_group.
            for obj in asset_group.all_objects:
                if obj.animation_data and obj.animation_data.action:
                    objects_actions[obj.name] = obj.animation_data.action
        try:
            yield
        finally:
            # Restor action.
            asset_group = bpy.data.collections.get(asset_group_name)
            if asset_group:
                if armature_action:
                    for obj in asset_group.all_objects:
                        if obj.type == "ARMATURE":
                            if obj.animation_data is None:
                                obj.animation_data_create()
                            obj.animation_data.action = armature_action
                elif objects_actions:
                    for obj in asset_group.all_objects:
                        action = objects_actions.get(obj.name)
                        if action:
                            if obj.animation_data is None:
                                obj.animation_data_create()
                            obj.animation_data.action = action
