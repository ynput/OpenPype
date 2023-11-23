"""Load an asset in Blender from an Alembic file."""

from pathlib import Path
from pprint import pformat
from typing import Dict, List, Optional

import bpy

from openpype.pipeline import (
    get_representation_path,
    AVALON_CONTAINER_ID,
)

from openpype.hosts.blender.api.pipeline import (
    AVALON_CONTAINERS,
    AVALON_PROPERTY,
)
from openpype.hosts.blender.api import plugin, lib


class CacheModelLoader(plugin.AssetLoader):
    """Load cache models.

    Stores the imported asset in a collection named after the asset.

    Note:
        At least for now it only supports Alembic files.
    """
    families = ["model", "pointcache", "animation"]
    representations = ["abc"]

    label = "Load Alembic"
    icon = "code-fork"
    color = "orange"

    def _remove(self, asset_group):
        objects = list(asset_group.children)
        empties = []

        for obj in objects:
            if obj.type == 'MESH':
                for material_slot in list(obj.material_slots):
                    bpy.data.materials.remove(material_slot.material)
                bpy.data.meshes.remove(obj.data)
            elif obj.type == 'EMPTY':
                objects.extend(obj.children)
                empties.append(obj)

        for empty in empties:
            bpy.data.objects.remove(empty)

    def _process(self, libpath, asset_group, group_name):
        plugin.deselect_all()

        relative = bpy.context.preferences.filepaths.use_relative_paths
        bpy.ops.wm.alembic_import(
            filepath=libpath,
            relative_path=relative
        )

        imported = lib.get_selection()

        # Use first EMPTY without parent as container
        container = next(
            (obj for obj in imported
             if obj.type == "EMPTY" and not obj.parent),
            None
        )

        objects = []
        if container:
            nodes = list(container.children)

            for obj in nodes:
                obj.parent = asset_group

            bpy.data.objects.remove(container)

            objects.extend(nodes)
            for obj in nodes:
                objects.extend(obj.children_recursive)
        else:
            for obj in imported:
                obj.parent = asset_group
            objects = imported

        for obj in objects:
            # Unlink the object from all collections
            collections = obj.users_collection
            for collection in collections:
                collection.objects.unlink(obj)
            name = obj.name
            obj.name = f"{group_name}:{name}"
            if obj.type != 'EMPTY':
                name_data = obj.data.name
                obj.data.name = f"{group_name}:{name_data}"

                for material_slot in obj.material_slots:
                    name_mat = material_slot.material.name
                    material_slot.material.name = f"{group_name}:{name_mat}"

            if not obj.get(AVALON_PROPERTY):
                obj[AVALON_PROPERTY] = {}

            avalon_info = obj[AVALON_PROPERTY]
            avalon_info.update({"container_name": group_name})

        plugin.deselect_all()

        return objects

    def _link_objects(self, objects, collection, containers, asset_group):
        # Link the imported objects to any collection where the asset group is
        # linked to, except the AVALON_CONTAINERS collection
        group_collections = [
            collection
            for collection in asset_group.users_collection
            if collection != containers]

        for obj in objects:
            for collection in group_collections:
                collection.objects.link(obj)

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

        libpath = self.filepath_from_context(context)
        asset = context["asset"]["name"]
        subset = context["subset"]["name"]

        asset_name = plugin.prepare_scene_name(asset, subset)
        unique_number = plugin.get_unique_number(asset, subset)
        group_name = plugin.prepare_scene_name(asset, subset, unique_number)
        namespace = namespace or f"{asset}_{unique_number}"

        containers = bpy.data.collections.get(AVALON_CONTAINERS)
        if not containers:
            containers = bpy.data.collections.new(name=AVALON_CONTAINERS)
            bpy.context.scene.collection.children.link(containers)

        asset_group = bpy.data.objects.new(group_name, object_data=None)
        asset_group.empty_display_type = 'SINGLE_ARROW'
        containers.objects.link(asset_group)

        objects = self._process(libpath, asset_group, group_name)

        # Link the asset group to the active collection
        collection = bpy.context.view_layer.active_layer_collection.collection
        collection.objects.link(asset_group)

        self._link_objects(objects, asset_group, containers, asset_group)

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

        Warning:
            No nested collections are supported at the moment!
        """
        object_name = container["objectName"]
        asset_group = bpy.data.objects.get(object_name)
        libpath = Path(get_representation_path(representation))
        extension = libpath.suffix.lower()

        self.log.info(
            "Container: %s\nRepresentation: %s",
            pformat(container, indent=2),
            pformat(representation, indent=2),
        )

        assert asset_group, (
            f"The asset is not loaded: {container['objectName']}"
        )
        assert libpath, (
            "No existing library file found for {container['objectName']}"
        )
        assert libpath.is_file(), (
            f"The file doesn't exist: {libpath}"
        )
        assert extension in plugin.VALID_EXTENSIONS, (
            f"Unsupported file: {libpath}"
        )

        metadata = asset_group.get(AVALON_PROPERTY)
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

        mat = asset_group.matrix_basis.copy()
        self._remove(asset_group)

        objects = self._process(str(libpath), asset_group, object_name)

        containers = bpy.data.collections.get(AVALON_CONTAINERS)
        self._link_objects(objects, asset_group, containers, asset_group)

        asset_group.matrix_basis = mat

        metadata["libpath"] = str(libpath)
        metadata["representation"] = str(representation["_id"])

    def exec_remove(self, container: Dict) -> bool:
        """Remove an existing container from a Blender scene.

        Arguments:
            container (openpype:container-1.0): Container to remove,
                from `host.ls()`.

        Returns:
            bool: Whether the container was deleted.

        Warning:
            No nested collections are supported at the moment!
        """
        object_name = container["objectName"]
        asset_group = bpy.data.objects.get(object_name)

        if not asset_group:
            return False

        self._remove(asset_group)

        bpy.data.objects.remove(asset_group)

        return True
