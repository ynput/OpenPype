"""Load a rig asset in Blender."""

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
from openpype.hosts.blender.api.pipeline import (
    metadata_update,
    AVALON_PROPERTY,
)


class BlendRigLoader(plugin.AssetLoader):
    """Load rigs from a .blend file."""

    families = ["rig"]
    representations = ["blend"]

    label = "Link Rig"
    icon = "code-fork"
    color = "orange"

    @staticmethod
    def _process(libpath, group_name):
        # Get the first collection if only child or the scene root collection
        # to use it as asset group parent collection.
        parent_collection = bpy.context.scene.collection
        if len(parent_collection.children) == 1:
            parent_collection = parent_collection.children[0]

        # Load collections from libpath library
        with bpy.data.libraries.load(
            libpath, link=True, relative=False
        ) as (data_from, data_to):
            data_to.collections = data_from.collections

        container = None

        # get valid container from loaded collections
        for collection in data_to.collections:
            collection_metadata = collection.get(AVALON_PROPERTY)
            if (
                collection_metadata and
                collection_metadata.get("family") == "rig"
            ):
                container = collection
                break

        assert container, "No asset container found"

        # Create override library for container and elements.
        override = container.override_hierarchy_create(
            bpy.context.scene,
            bpy.context.view_layer,
        )

        # Rename all objects from override container with group_name.
        for obj in set(override.all_objects):
            obj.name = f"{group_name}:{obj.name}"

        # Force override collection from override container and rename.
        for child in set(override.children_recursive):
            # child = child.override_create(remap_local_usages=True)
            child.name = f"{group_name}:{child.name}"

        # force override object data from overridden objects and rename.
        overridden_data = set()
        for obj in set(override.all_objects):
            if obj.data and obj.data not in overridden_data:
                overridden_data.add(obj.data)
                obj.data.override_create(remap_local_usages=True)
                obj.data.name = f"{group_name}:{obj.data.name}"

        # Relink and rename the override container.
        bpy.context.scene.collection.children.unlink(override)
        parent_collection.children.link(override)
        override.name = group_name

        plugin.orphans_purge()
        plugin.deselect_all()

        return override, list(override.all_objects)

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

        asset_group, objects = self._process(libpath, group_name)

        # update avalon metadata
        asset_group[AVALON_PROPERTY] = {
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
            "objectName": group_name
        }

        self[:] = objects
        return objects

    def exec_update(self, container: Dict, representation: Dict):
        """Update the loaded asset.

        This will remove all objects of the current collection, load the new
        ones and add them to the collection.
        If the objects of the collection are used in another collection they
        will not be removed, only unlinked. Normally this should not be the
        case though.
        """
        object_name = container["objectName"]
        asset_group = bpy.data.objects.get(object_name)
        libpath = Path(get_representation_path(representation))
        extension = libpath.suffix.lower()

        if not asset_group:
            asset_group = bpy.data.collections.get(object_name)

        self.log.info(
            "Container: %s\nRepresentation: %s",
            pformat(container, indent=2),
            pformat(representation, indent=2),
        )

        assert asset_group, (
            f"The asset is not loaded: {container['objectName']}"
        )
        assert libpath, (
            f"No existing library file found for {container['objectName']}"
        )
        assert libpath.is_file(), (
            f"The file doesn't exist: {libpath}"
        )
        assert extension in plugin.VALID_EXTENSIONS, (
            f"Unsupported file: {libpath}"
        )

        metadata = asset_group.get(AVALON_PROPERTY).to_dict()
        group_libpath = metadata["libpath"]

        normalized_group_libpath = (
            str(Path(bpy.path.abspath(group_libpath)).resolve())
        )
        normalized_libpath = (
            str(Path(bpy.path.abspath(str(libpath))).resolve())
        )
        self.log.debug(
            "normalized_group_libpath:\n  %s\nnormalized_libpath:\n  %s",
            normalized_group_libpath,
            normalized_libpath,
        )
        if normalized_group_libpath == normalized_libpath:
            self.log.info("Library already loaded, not updating...")
            return

        with contextlib.ExitStack() as stack:
            stack.enter_context(self.maintained_parent(asset_group))
            stack.enter_context(self.maintained_modifiers(asset_group))
            stack.enter_context(self.maintained_constraints(asset_group))
            stack.enter_context(self.maintained_transforms(asset_group))
            stack.enter_context(self.maintained_targets(asset_group))
            stack.enter_context(self.maintained_action(asset_group))

            plugin.remove_container(asset_group)

            asset_group, objects = self._process(str(libpath), object_name)

        # update override library operations from asset objects
        for obj in objects:
            if obj.override_library:
                obj.override_library.operations_update()

        # clear orphan datablocks and libraries
        plugin.orphans_purge()

        # update metadata
        metadata.update({
            "libpath": str(libpath),
            "representation": str(representation["_id"]),
            "parent": str(representation["parent"]),
        })
        metadata_update(asset_group, metadata)

    def exec_remove(self, container) -> bool:
        """Remove the existing container from Blender scene"""
        return self._remove_container(container)

    @contextlib.contextmanager
    def maintained_action(self, asset_group):
        """Maintain action during context."""
        asset_group_name = asset_group.name
        # Get the armature from asset_group.
        armature = None
        for obj in asset_group.all_objects:
            if obj.type == "ARMATURE":
                armature = obj
                break
        # Store action from armature.
        action = None
        if (
            armature and
            armature.animation_data and
            armature.animation_data.action
        ):
            action = armature.animation_data.action
        try:
            yield
        finally:
            # Restor action.
            asset_group = bpy.data.collections.get(asset_group_name)
            if asset_group and action:
                for obj in asset_group.all_objects:
                    if obj.animation_data is None:
                        obj.animation_data_create()
                    obj.animation_data.action = action
