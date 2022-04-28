"""Load a model asset in Blender."""

from pathlib import Path
from pprint import pformat
from typing import Dict, List, Optional

import bpy

from openpype.pipeline import (
    legacy_io,
    get_representation_path,
    AVALON_CONTAINER_ID,
)
from openpype.hosts.blender.api import plugin
from openpype.hosts.blender.api.pipeline import AVALON_PROPERTY


class BlendModelLoader(plugin.AssetLoader):
    """Load models from a .blend file.

    Because they come from a .blend file we can simply link the collection that
    contains the model. There is no further need to 'containerise' it.
    """

    families = ["model"]
    representations = ["blend"]

    label = "Link Model"
    icon = "code-fork"
    color = "orange"

    @staticmethod
    def _remove(asset_group):
        # remove all objects in asset_group
        objects = list(asset_group.all_objects)
        for obj in objects:
            objects.extend(obj.children)
            if obj.type == 'MESH':
                for material_slot in list(obj.material_slots):
                    bpy.data.materials.remove(material_slot.material)
                bpy.data.meshes.remove(obj.data)
            else:
                bpy.data.objects.remove(obj)
        # remove all collections in asset_group
        childrens = list(asset_group.children)
        for child in childrens:
            childrens.extend(child.children)
            bpy.data.collections.remove(child)

    @staticmethod
    def _process(libpath, asset_group, group_name):
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
                collection_metadata.get("family") == "model" and
                collection_metadata.get("asset") == group_name.split("_")[0]
            ):
                container = collection
                break

        assert container, "No asset container found"

        objects = list(container.all_objects)

        for obj in objects:
            local_obj = plugin.prepare_data(obj, group_name)
            if local_obj.type != 'EMPTY':
                plugin.prepare_data(local_obj.data, group_name)

                for material_slot in local_obj.material_slots:
                    if material_slot.material:
                        plugin.prepare_data(material_slot.material, group_name)

            if not local_obj.get(AVALON_PROPERTY):
                local_obj[AVALON_PROPERTY] = dict()

            avalon_info = local_obj[AVALON_PROPERTY]
            avalon_info.update({"container_name": group_name})

        if isinstance(asset_group, bpy.types.Collection):
            # Create override libraries for container and elements.
            overridden = container.override_create(remap_local_usages=True)
            for child in container.children_recursive:
                child.override_create(remap_local_usages=True)
            for obj in container.all_objects:
                obj.override_create(remap_local_usages=True)
            # Link and rename overridden container using asset_group.
            parent_collection = plugin.get_parent_collection(asset_group)
            parent_collection.children.link(overridden)
            asset_group.name = f'{asset_group.name}.removed'
            overridden.name = group_name
            # clear and reassign asset_group
            bpy.data.collections.remove(asset_group)
            asset_group = overridden

        # If asset_group is an Empty, set instance collection with container.
        elif isinstance(asset_group, bpy.types.Object):
            asset_group.instance_collection = container
            asset_group.instance_type = 'COLLECTION'

        bpy.data.orphans_purge(do_local_ids=False)

        plugin.deselect_all()

        return asset_group, objects

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

        # Get the first collection if only child or the scene root collection
        # to use it as asset group parent collection.
        parent_collection = bpy.context.scene.collection
        if len(parent_collection.children) == 1:
            parent_collection = parent_collection.children[0]

        # Create override library if current task needed it.
        if legacy_io.Session["AVALON_TASK"] in (
            "Rigging", "Modeling", "Texture", "Lookdev"
        ):
            asset_group = bpy.data.collections.new(group_name)
            parent_collection.children.link(asset_group)
        else:
            asset_group = bpy.data.objects.new(group_name, object_data=None)
            asset_group.empty_display_type = 'SINGLE_ARROW'
            parent_collection.objects.link(asset_group)

            plugin.deselect_all()

            if options is not None:
                parent = options.get('parent')
                transform = options.get('transform')

                if parent and transform:
                    location = transform.get('translation')
                    rotation = transform.get('rotation')
                    scale = transform.get('scale')

                    asset_group.location = (
                        location.get('x'),
                        location.get('y'),
                        location.get('z')
                    )
                    asset_group.rotation_euler = (
                        rotation.get('x'),
                        rotation.get('y'),
                        rotation.get('z')
                    )
                    asset_group.scale = (
                        scale.get('x'),
                        scale.get('y'),
                        scale.get('z')
                    )

                    bpy.context.view_layer.objects.active = parent
                    asset_group.select_set(True)

                    bpy.ops.object.parent_set(keep_transform=True)

                    plugin.deselect_all()

        asset_group, objects = self._process(libpath, asset_group, group_name)

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

        # Check how many assets use the same library
        count = 0
        assets = [o for o in bpy.data.objects if o.get(AVALON_PROPERTY)]
        assets += [c for c in bpy.data.collections if c.get(AVALON_PROPERTY)]
        for asset in assets:
            if asset.get(AVALON_PROPERTY).get('libpath') == libpath:
                count += 1

        matrix_basis = None

        if isinstance(asset_group, bpy.types.Collection):
            self._remove(asset_group)

        elif isinstance(asset_group, bpy.types.Object):
            matrix_basis = asset_group.matrix_basis.copy()

        # If it is the last object to use that library, remove it
        if count == 1:
            library = bpy.data.libraries.get(bpy.path.basename(group_libpath))
            if library:
                bpy.data.libraries.remove(library)

        asset_group, _ = self._process(str(libpath), asset_group, object_name)

        if matrix_basis and isinstance(asset_group, bpy.types.Object):
            asset_group.matrix_basis = matrix_basis

        metadata = asset_group.get(AVALON_PROPERTY)
        metadata["libpath"] = str(libpath)
        metadata["representation"] = str(representation["_id"])
        metadata["parent"] = str(representation["parent"])

    def exec_remove(self, container: Dict) -> bool:
        """Remove an existing container from a Blender scene.

        Arguments:
            container (openpype:container-1.0): Container to remove,
                from `host.ls()`.

        Returns:
            bool: Whether the container was deleted.
        """
        object_name = container["objectName"]
        asset_group = bpy.data.objects.get(object_name)

        if not asset_group:
            asset_group = bpy.data.collections.get(object_name)

        if not asset_group:
            return False

        # Check how many assets use the same library
        libpath = asset_group.get(AVALON_PROPERTY).get('libpath')
        count = 0
        assets = [o for o in bpy.data.objects if o.get(AVALON_PROPERTY)]
        assets += [c for c in bpy.data.collections if c.get(AVALON_PROPERTY)]
        for asset in assets:
            if asset.get(AVALON_PROPERTY).get('libpath') == libpath:
                count += 1

        if isinstance(asset_group, bpy.types.Collection):
            self._remove(asset_group)
            bpy.data.collections.remove(asset_group)
        else:
            bpy.data.objects.remove(asset_group)

        # If it is the last object to use that library, remove it
        if count == 1:
            library = bpy.data.libraries.get(bpy.path.basename(libpath))
            bpy.data.libraries.remove(library)

        return True
