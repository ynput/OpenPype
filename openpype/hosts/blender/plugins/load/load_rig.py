"""Load a rig asset in Blender."""

from pathlib import Path
from pprint import pformat
from typing import Dict, List, Optional

import bpy

from avalon import api
from avalon.blender import lib as avalon_lib
from openpype import lib
from openpype.hosts.blender.api import plugin
from openpype.hosts.blender.api.pipeline import (
    AVALON_CONTAINERS,
    AVALON_PROPERTY,
    AVALON_CONTAINER_ID,
)


class BlendRigLoader(plugin.AssetLoader):
    """Load rigs from a .blend file."""

    families = ["rig"]
    representations = ["blend"]

    label = "Link Rig"
    icon = "code-fork"
    color = "orange"

    def _remove(self, asset_group):
        objects = list(asset_group.children)

        for obj in objects:
            if obj.type == "MESH":
                for material_slot in list(obj.material_slots):
                    if material_slot.material:
                        bpy.data.materials.remove(material_slot.material)
                bpy.data.meshes.remove(obj.data)
            elif obj.type == "ARMATURE":
                objects.extend(obj.children)
                bpy.data.armatures.remove(obj.data)
            elif obj.type == "CURVE":
                bpy.data.curves.remove(obj.data)
            elif obj.type == "EMPTY":
                objects.extend(obj.children)
                bpy.data.objects.remove(obj)

    def _process(self, libpath, asset_name):
        with bpy.data.libraries.load(libpath, link=True, relative=False) as (
            data_from,
            data_to,
        ):
            for data_from_collection in data_from.collections:
                if data_from_collection == asset_name:
                    data_to.collections.append(data_from_collection)

        scene_collection = bpy.context.scene.collection

        # Find the loaded collection and set in variable container_collection
        container_collection = None
        instances = plugin.get_instances_list()
        self.log.info("instances : %s", instances)
        for data_collection in instances:
            if data_collection.override_library is None:
                if data_collection[AVALON_PROPERTY].get("family") is not None:
                    if data_collection[AVALON_PROPERTY].get("family") == "rig":
                        container_collection = data_collection
        self.original_container_name = container_collection.name

        # Create a collection used to start the load collections at .001
        # increment_use_collection = bpy.data.collections.new(
        #     name=self.original_container_name
        # )

        # Link the container to the scene collection
        # scene_collection.children.link(increment_use_collection)
        scene_collection.children.link(container_collection)

        # Get all the collection of the container. The farest parents in first for override them first
        collections = []
        nodes = list(container_collection.children)
        collections.append(container_collection)

        for collection in nodes:
            collections.append(collection)
            nodes.extend(list(collection.children))

        # Get all the object of the container. The farest parents in first for override them first
        objects = []
        armatures = []
        non_armatures = []
        for collection in collections:
            nodes = list(collection.objects)
            objects_of_the_collection = []
            for obj in nodes:
                if obj.parent is None:
                    objects_of_the_collection.append(obj)
            # Get all objects that aren't an armature
            nodes = objects_of_the_collection
            non_armatures = []
            for obj in nodes:
                if obj.type != "ARMATURE":
                    non_armatures.append(obj)
                nodes.extend(list(obj.children))
            non_armatures.reverse()

            # Add them in objects list

            # Get all objects that are an armature
            nodes = objects_of_the_collection

            for obj in nodes:
                if obj.type == "ARMATURE":
                    armatures.append(obj)
                nodes.extend(list(obj.children))
            armatures.reverse()
            # Add them in armature list

        # Clean
        bpy.data.orphans_purge(do_local_ids=False)
        plugin.deselect_all()

        # Override the container and the objects
        for collection in collections:
            container_overrided = collection.override_create(remap_local_usages=True)
        for obj in non_armatures:
            obj.override_create(remap_local_usages=True)
        for armature in armatures:
            armature.override_create(remap_local_usages=True)
        # obj.data.override_create(remap_local_usages=True)

        # Remove the collection used to the increment
        # bpy.data.collections.remove(increment_use_collection)

        return objects

    def process_asset(
        self,
        context: dict,
        name: str,
        namespace: Optional[str] = None,
        options: Optional[Dict] = None,
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
        # asset_name = plugin.asset_name(asset, subset)
        # unique_number = plugin.get_unique_number(asset, subset)
        # group_name = plugin.asset_name(asset, subset, unique_number)
        # namespace = namespace or f"{asset}_{unique_number}"
        #
        # avalon_container = bpy.data.collections.get(AVALON_CONTAINERS)
        # if not avalon_container:
        #     avalon_container = bpy.data.collections.new(name=AVALON_CONTAINERS)
        #     bpy.context.scene.collection.children.link(avalon_container)
        #
        # asset_group = bpy.data.objects.new(group_name, object_data=None)
        # asset_group.empty_display_type = "SINGLE_ARROW"
        # avalon_container.objects.link(asset_group)
        #
        # action = None
        #
        # plugin.deselect_all()
        #
        # create_animation = False
        # anim_file = None

        # if options is not None:
        #     parent = options.get("parent")
        #     transform = options.get("transform")
        #     action = options.get("action")
        #     create_animation = options.get("create_animation")
        #     anim_file = options.get("animation_file")
        #
        #     if parent and transform:
        #         location = transform.get("translation")
        #         rotation = transform.get("rotation")
        #         scale = transform.get("scale")
        #
        #         asset_group.location = (
        #             location.get("x"),
        #             location.get("y"),
        #             location.get("z"),
        #         )
        #         asset_group.rotation_euler = (
        #             rotation.get("x"),
        #             rotation.get("y"),
        #             rotation.get("z"),
        #         )
        #         asset_group.scale = (scale.get("x"), scale.get("y"), scale.get("z"))
        #
        #         bpy.context.view_layer.objects.active = parent
        #         asset_group.select_set(True)
        #
        #         bpy.ops.object.parent_set(keep_transform=True)
        #
        #         plugin.deselect_all()

        objects = self._process(libpath, asset_name)

        # if create_animation:
        #     creator_plugin = lib.get_creator_by_name("CreateAnimation")
        #     if not creator_plugin:
        #         raise ValueError('Creator plugin "CreateAnimation" was ' "not found.")
        #
        #     asset_group.select_set(True)
        #
        #     animation_asset = options.get("animation_asset")
        #
        #     api.create(
        #         creator_plugin,
        #         name=namespace + "_animation",
        #         # name=f"{unique_number}_{subset}_animation",
        #         asset=animation_asset,
        #         options={"useSelection": False, "asset_group": asset_group},
        #         data={"dependencies": str(context["representation"]["_id"])},
        #     )
        #
        #     plugin.deselect_all()
        #
        # if anim_file:
        #     bpy.ops.import_scene.fbx(filepath=anim_file, anim_offset=0.0)
        #
        #     imported = avalon_lib.get_selection()
        #
        #     armature = [o for o in asset_group.children if o.type == "ARMATURE"][0]
        #
        #     imported_group = [o for o in imported if o.type == "EMPTY"][0]
        #
        #     for obj in imported:
        #         if obj.type == "ARMATURE":
        #             if not armature.animation_data:
        #                 armature.animation_data_create()
        #             armature.animation_data.action = obj.animation_data.action
        #
        #     self._remove(imported_group)
        #     bpy.data.objects.remove(imported_group)
        #
        # bpy.context.scene.collection.objects.link(asset_group)
        #
        # asset_group[AVALON_PROPERTY] = {
        #     "schema": "openpype:container-2.0",
        #     "id": AVALON_CONTAINER_ID,
        #     "asset": asset,
        #     "subset": subset,
        #     "name": name,
        #     "namespace": namespace or "",
        #     "loader": str(self.__class__.__name__),
        #     "representation": str(context["representation"]["_id"]),
        #     "libpath": libpath,
        #     "asset_name": asset_name,
        #     "parent": str(context["representation"]["parent"]),
        #     "family": context["representation"]["context"]["family"],
        #     "objectName": group_name,
        # }

        self[:] = objects
        return objects

    def exec_update(self, container: Dict, representation: Dict):
        """Update the loaded asset.

        This will remove all children of the asset group, load the new ones
        and add them as children of the group.
        """
        object_name = container["objectName"]
        asset_group = bpy.data.objects.get(object_name)
        libpath = Path(api.get_representation_path(representation))
        extension = libpath.suffix.lower()

        self.log.info(
            "Container: %s\nRepresentation: %s",
            pformat(container, indent=2),
            pformat(representation, indent=2),
        )

        assert asset_group, f"The asset is not loaded: {container['objectName']}"
        assert libpath, "No existing library file found for {container['objectName']}"
        assert libpath.is_file(), f"The file doesn't exist: {libpath}"
        assert extension in plugin.VALID_EXTENSIONS, f"Unsupported file: {libpath}"

        metadata = asset_group.get(AVALON_PROPERTY)
        group_libpath = metadata["libpath"]

        normalized_group_libpath = str(Path(bpy.path.abspath(group_libpath)).resolve())
        normalized_libpath = str(Path(bpy.path.abspath(str(libpath))).resolve())
        self.log.debug(
            "normalized_group_libpath:\n  %s\nnormalized_libpath:\n  %s",
            normalized_group_libpath,
            normalized_libpath,
        )
        if normalized_group_libpath == normalized_libpath:
            self.log.info("Library already loaded, not updating...")
            return

        # Check how many assets use the same library
        count = 0
        for obj in bpy.data.collections.get(AVALON_CONTAINERS).objects:
            if obj.get(AVALON_PROPERTY).get("libpath") == group_libpath:
                count += 1

        # Get the armature of the rig
        objects = asset_group.children
        armature = [obj for obj in objects if obj.type == "ARMATURE"][0]

        action = None
        if armature.animation_data and armature.animation_data.action:
            action = armature.animation_data.action

        mat = asset_group.matrix_basis.copy()

        self._remove(asset_group)

        # If it is the last object to use that library, remove it
        if count == 1:
            library = bpy.data.libraries.get(bpy.path.basename(group_libpath))
            bpy.data.libraries.remove(library)

        self._process(str(libpath), asset_group, object_name, action)

        asset_group.matrix_basis = mat

        metadata["libpath"] = str(libpath)
        metadata["representation"] = str(representation["_id"])
        metadata["parent"] = str(representation["parent"])

    def exec_remove(self, container: Dict) -> bool:
        """Remove an existing asset group from a Blender scene.

        Arguments:
            container (openpype:container-1.0): Container to remove,
                from `host.ls()`.

        Returns:
            bool: Whether the asset group was deleted.
        """
        object_name = container["objectName"]
        asset_group = bpy.data.objects.get(object_name)
        libpath = asset_group.get(AVALON_PROPERTY).get("libpath")

        # Check how many assets use the same library
        count = 0
        for obj in bpy.data.collections.get(AVALON_CONTAINERS).objects:
            if obj.get(AVALON_PROPERTY).get("libpath") == libpath:
                count += 1

        if not asset_group:
            return False

        self._remove(asset_group)

        bpy.data.objects.remove(asset_group)

        # If it is the last object to use that library, remove it
        if count == 1:
            library = bpy.data.libraries.get(bpy.path.basename(libpath))
            bpy.data.libraries.remove(library)

        return True

    def update_avalon_property(self, representation: Dict):

        container_collection = None
        instances = plugin.get_instances_list()
        for data_collection in instances:
            if (
                data_collection.override_library is None
                and data_collection.library is None
            ):
                container_collection = data_collection
        self.log.info("container name %s ", container_collection.name)

        # Set the avalon property with the representation data

        asset = str(representation["context"]["asset"])
        subset = str(representation["context"]["subset"])
        asset_name = plugin.asset_name(asset, subset)

        container_collection[AVALON_PROPERTY] = {
            "schema": "openpype:container-2.0",
            "id": AVALON_CONTAINER_ID,
            "name": asset,
            "namespace": container_collection.name,
            "loader": str(self.__class__.__name__),
            "representation": str(representation["_id"]),
            "libpath": str(representation["data"]["path"]),
            "asset_name": asset_name,
            "parent": str(representation["parent"]),
            "family": str(representation["context"]["family"]),
            "objectName": container_collection.name,
        }
