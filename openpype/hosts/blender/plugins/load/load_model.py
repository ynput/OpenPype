"""Load a model asset in Blender."""

import contextlib
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
from openpype.hosts.blender.api.pipeline import (
    metadata_update,
    AVALON_PROPERTY,
)


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

    _downstream_tasks = ("Rigging", "Modeling", "Texture", "Lookdev")

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
                collection_metadata.get("family") == "model"
            ):
                container = collection
                break

        assert container, "No asset container found"

        if isinstance(asset_group, bpy.types.Collection):
            # temp rename asset_group
            asset_group.name = f'{asset_group.name}.temp'
            # Create override library for container and elements.
            override = container.override_hierarchy_create(
                bpy.context.scene,
                bpy.context.view_layer,
            )
            # Relink and rename the override container using asset_group.
            plugin.get_parent_collection(override).children.unlink(override)
            parent_collection = plugin.get_parent_collection(asset_group)
            parent_collection.children.link(override)
            override.name = group_name

            # force override object data like meshes and curves.
            overridden_data = set()
            for obj in set(override.all_objects):
                if obj.data and obj.data not in overridden_data:
                    obj.data.override_create(remap_local_usages=True)
                    overridden_data.add(obj.data)

            # clear and reassign asset_group and objects variables
            bpy.data.collections.remove(asset_group)
            asset_group = override
            objects = list(override.all_objects)

        # If asset_group is an Empty, set instance collection with container.
        elif isinstance(asset_group, bpy.types.Object):
            asset_group.instance_collection = container
            asset_group.instance_type = 'COLLECTION'
            objects = list(container.all_objects)

        plugin.orphans_purge()
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

        # Get the first collection if only child or the scene root collection
        # to use it as asset group parent collection.
        parent_collection = bpy.context.scene.collection
        if len(parent_collection.children) == 1:
            parent_collection = parent_collection.children[0]

        # Create override library if current task needed it.
        if (
            legacy_io.Session.get("AVALON_TASK") in self._downstream_tasks and
            legacy_io.Session.get("AVALON_ASSET") == asset
        ):
            group_name = plugin.asset_name(asset, subset)
            asset_group = bpy.data.collections.new(group_name)
            parent_collection.children.link(asset_group)
        else:
            unique_number = plugin.get_unique_number(asset, subset)
            group_name = plugin.asset_name(asset, subset, unique_number)
            namespace = namespace or f"{asset}_{unique_number}"
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
            stack.enter_context(self.maintained_transforms(asset_group))
            stack.enter_context(self.maintained_modifiers(asset_group))
            stack.enter_context(self.maintained_constraints(asset_group))
            stack.enter_context(self.maintained_targets(asset_group))
            stack.enter_context(self.maintained_drivers(asset_group))

            plugin.remove_container(asset_group, content_only=True)

            asset_group, objects = self._process(
                str(libpath), asset_group, object_name
            )

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
