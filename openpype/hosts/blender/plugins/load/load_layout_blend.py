"""Load a layout in Blender."""

import contextlib
from pathlib import Path
from pprint import pformat
from typing import Dict, List, Optional

import bpy

from openpype.pipeline import (
    get_representation_path,
    AVALON_CONTAINER_ID,
)
from openpype.hosts.blender.api import plugin
from openpype.hosts.blender.api.pipeline import metadata_update


class BlendLayoutLoader(plugin.AssetLoader):
    """Load layout from a .blend file."""

    families = ["layout"]
    representations = ["blend"]

    label = "Link Layout"
    icon = "code-fork"
    color = "orange"

    def _process(self, libpath, asset_group):
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

        # Move objects and child collections from override to asset_group.
        plugin.link_to_collection(override.objects, asset_group)
        plugin.link_to_collection(override.children, asset_group)

        # Make all actions local.
        for action in bpy.data.actions:
            action.make_local()

        # Clear and purge useless datablocks and selection.
        bpy.data.collections.remove(container)
        plugin.orphans_purge()
        plugin.deselect_all()

        return list(asset_group.all_objects)

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
        asset_group.color_tag = "COLOR_02"
        plugin.get_main_collection().children.link(asset_group)

        objects = self._process(libpath, asset_group)

        metadata_update(
            asset_group,
            {
                "schema": "openpype:container-2.0",
                "id": AVALON_CONTAINER_ID,
                "name": name,
                "namespace": namespace or '',
                "loader": str(self.__class__.__name__),
                "representation": str(context["representation"]["_id"]),
                "libpath": libpath,
                "asset_name": asset_name,
                "parent": str(context["representation"]["parent"]),
                "family": context["representation"]["context"]["family"],
                "objectName": asset_name
            }
        )

        self[:] = objects
        return objects

    def update(self, container: Dict, representation: Dict):
        """Update the loaded asset.

        This will remove all objects of the current collection, load the new
        ones and add them to the collection.
        If the objects of the collection are used in another collection they
        will not be removed, only unlinked. Normally this should not be the
        case though.

        Warning:
            No nested collections are supported at the moment!
        """
        object_name = container["objectName"]
        asset_group = bpy.data.collections.get(object_name)
        libpath = Path(get_representation_path(representation))

        self.log.info(
            "Container: %s\nRepresentation: %s",
            pformat(container, indent=2),
            pformat(representation, indent=2),
        )

        if self._is_updated(asset_group, object_name, libpath):
            self.log.info("Asset already up to date, not updating...")
            return

        with contextlib.ExitStack() as stack:
            stack.enter_context(self.maintained_parent(asset_group))
            stack.enter_context(self.maintained_modifiers(asset_group))
            stack.enter_context(self.maintained_constraints(asset_group))
            stack.enter_context(self.maintained_transforms(asset_group))
            stack.enter_context(self.maintained_targets(asset_group))
            stack.enter_context(self.maintained_action(asset_group))

            plugin.remove_container(asset_group)
            objects = self._process(str(libpath), asset_group, object_name)

        # update override library operations from asset objects
        for obj in objects:
            if obj.override_library:
                obj.override_library.operations_update()

        # clear orphan datablocks and libraries
        plugin.orphans_purge()
        plugin.deselect_all()

        # update metadata
        metadata_update(
            asset_group,
            {
                "libpath": str(libpath),
                "representation": str(representation["_id"]),
                "parent": str(representation["parent"]),
            }
        )

    def exec_remove(self, container) -> bool:
        """Remove the existing container from Blender scene"""
        return self._remove_container(container)

    @contextlib.contextmanager
    def maintained_action(self, asset_group):
        """Maintain action during context."""
        asset_group_name = asset_group.name
        # Get the armatures from asset_group.
        armatures = [
            obj
            for obj in asset_group.all_objects
            if obj.type == "ARMATURE"
        ]
        actions = {}
        # Store actions from armatures.
        for armature in armatures:
            if armature.animation_data and armature.animation_data.action:
                actions[armature.name] = armature.animation_data.action
                armature.animation_data.action.use_fake_user = True
        try:
            yield
        finally:
            # Restor actions.
            asset_group = bpy.data.collections.get(asset_group_name)
            if asset_group and actions:
                for obj in asset_group.all_objects:
                    action = actions.get(obj.name)
                    if action:
                        if obj.animation_data is None:
                            obj.animation_data_create()
                        obj.animation_data.action = action
            for action in actions.values():
                action.use_fake_user = False
