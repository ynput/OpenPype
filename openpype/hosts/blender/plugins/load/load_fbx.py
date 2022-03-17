"""Load an asset in Blender from an Alembic file."""

from pathlib import Path
from pprint import pformat
from typing import Dict, List, Optional

import bpy

from openpype.pipeline import get_representation_path
from openpype.hosts.blender.api import plugin, lib
from openpype.hosts.blender.api.pipeline import (
    AVALON_CONTAINERS,
    AVALON_PROPERTY,
    AVALON_CONTAINER_ID
)


class FbxModelLoader(plugin.AssetLoader):
    """Load FBX models.

    Stores the imported asset in an empty named after the asset.
    """

    families = ["model", "rig"]
    representations = ["fbx"]

    label = "Load FBX"
    icon = "code-fork"
    color = "orange"

    def _remove(self, asset_group):
        objects = list(asset_group.children)

        for obj in objects:
            if obj.type == 'MESH':
                for material_slot in list(obj.material_slots):
                    if material_slot.material:
                        bpy.data.materials.remove(material_slot.material)
                bpy.data.meshes.remove(obj.data)
            elif obj.type == 'ARMATURE':
                objects.extend(obj.children)
                bpy.data.armatures.remove(obj.data)
            elif obj.type == 'CURVE':
                bpy.data.curves.remove(obj.data)
            elif obj.type == 'EMPTY':
                objects.extend(obj.children)
                bpy.data.objects.remove(obj)

    def _process(self, libpath, asset_group, group_name, action):
        plugin.deselect_all()

        collection = bpy.context.view_layer.active_layer_collection.collection

        bpy.ops.import_scene.fbx(filepath=libpath)

        parent = bpy.context.scene.collection

        imported = lib.get_selection()

        empties = [obj for obj in imported if obj.type == 'EMPTY']

        container = None

        for empty in empties:
            if not empty.parent:
                container = empty
                break

        assert container, "No asset group found"

        # Children must be linked before parents,
        # otherwise the hierarchy will break
        objects = []
        nodes = list(container.children)

        for obj in nodes:
            obj.parent = asset_group

        bpy.data.objects.remove(container)

        for obj in nodes:
            objects.append(obj)
            nodes.extend(list(obj.children))

        objects.reverse()

        for obj in objects:
            parent.objects.link(obj)
            collection.objects.unlink(obj)

        for obj in objects:
            name = obj.name
            obj.name = f"{group_name}:{name}"
            if obj.type != 'EMPTY':
                name_data = obj.data.name
                obj.data.name = f"{group_name}:{name_data}"

            if obj.type == 'MESH':
                for material_slot in obj.material_slots:
                    name_mat = material_slot.material.name
                    material_slot.material.name = f"{group_name}:{name_mat}"
            elif obj.type == 'ARMATURE':
                anim_data = obj.animation_data
                if action is not None:
                    anim_data.action = action
                elif anim_data.action is not None:
                    name_action = anim_data.action.name
                    anim_data.action.name = f"{group_name}:{name_action}"

            if not obj.get(AVALON_PROPERTY):
                obj[AVALON_PROPERTY] = dict()

            avalon_info = obj[AVALON_PROPERTY]
            avalon_info.update({"container_name": group_name})

        plugin.deselect_all()

        return objects

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

        avalon_container = bpy.data.collections.get(AVALON_CONTAINERS)
        if not avalon_container:
            avalon_container = bpy.data.collections.new(name=AVALON_CONTAINERS)
            bpy.context.scene.collection.children.link(avalon_container)

        asset_group = bpy.data.objects.new(group_name, object_data=None)
        avalon_container.objects.link(asset_group)

        objects = self._process(libpath, asset_group, group_name, None)

        objects = []
        nodes = list(asset_group.children)

        for obj in nodes:
            objects.append(obj)
            nodes.extend(list(obj.children))

        bpy.context.scene.collection.objects.link(asset_group)

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

        # Get the armature of the rig
        objects = asset_group.children
        armatures = [obj for obj in objects if obj.type == 'ARMATURE']
        action = None

        if armatures:
            armature = armatures[0]

            if armature.animation_data and armature.animation_data.action:
                action = armature.animation_data.action

        mat = asset_group.matrix_basis.copy()
        self._remove(asset_group)

        self._process(str(libpath), asset_group, object_name, action)

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
