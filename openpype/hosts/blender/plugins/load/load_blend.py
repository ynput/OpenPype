from typing import Dict, List, Optional
from pathlib import Path

import bpy

from openpype.pipeline import (
    get_representation_path,
    AVALON_CONTAINER_ID,
)
from openpype.hosts.blender.api import plugin
from openpype.hosts.blender.api.lib import imprint
from openpype.hosts.blender.api.pipeline import (
    AVALON_CONTAINERS,
    AVALON_PROPERTY,
)


class BlendLoader(plugin.AssetLoader):
    """Load assets from a .blend file."""

    families = ["model", "rig"]
    representations = ["blend"]

    label = "Load Blend"
    icon = "code-fork"
    color = "orange"

    @staticmethod
    def _get_asset_container(objects):
        empties = [obj for obj in objects if obj.type == 'EMPTY']

        for empty in empties:
            if empty.get(AVALON_PROPERTY):
                return empty

        return None

    def _process_data(self, libpath, group_name):
        # Append all the data from the .blend file
        with bpy.data.libraries.load(
            libpath, link=False, relative=False
        ) as (data_from, data_to):
            for attr in dir(data_to):
                setattr(data_to, attr, getattr(data_from, attr))

        # Rename the object to add the asset name
        for attr in dir(data_to):
            for data in getattr(data_to, attr):
                data.name = f"{group_name}:{data.name}"

        container = self._get_asset_container(data_to.objects)
        assert container, "No asset group found"

        container.name = group_name
        container.empty_display_type = 'SINGLE_ARROW'

        # Link the collection to the scene
        bpy.context.scene.collection.objects.link(container)

        # Link all the container children to the collection
        for obj in container.children_recursive:
            bpy.context.scene.collection.objects.link(obj)

        return container

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

        container = self._process_data(libpath, group_name)

        avalon_container.objects.link(container)

        # Remove the library from the blend file
        library = bpy.data.libraries.get(bpy.path.basename(libpath))
        bpy.data.libraries.remove(library)

        data = {
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

        container[AVALON_PROPERTY] = data

        objects = [
            obj for obj in bpy.data.objects
            if obj.name.startswith(f"{group_name}:")
        ]

        self[:] = objects
        return objects

    def exec_update(self, container: Dict, representation: Dict):
        """
        Update the loaded asset.
        """
        group_name = container["objectName"]
        asset_group = bpy.data.objects.get(group_name)
        libpath = Path(get_representation_path(representation)).as_posix()

        assert asset_group, (
            f"The asset is not loaded: {container['objectName']}"
        )

        transform = asset_group.matrix_basis.copy()
        old_data = dict(asset_group.get(AVALON_PROPERTY))

        self.exec_remove(container)

        asset_group = self._process_data(libpath, group_name)

        avalon_container = bpy.data.collections.get(AVALON_CONTAINERS)
        avalon_container.objects.link(asset_group)

        # Remove the library from the blend file
        library = bpy.data.libraries.get(bpy.path.basename(libpath))
        bpy.data.libraries.remove(library)

        asset_group.matrix_basis = transform

        asset_group[AVALON_PROPERTY] = old_data

        new_data = {
            "libpath": libpath,
            "representation": str(representation["_id"]),
            "parent": str(representation["parent"]),
        }

        imprint(asset_group, new_data)

    def exec_remove(self, container: Dict) -> bool:
        """
        Remove an existing container from a Blender scene.
        """
        group_name = container["objectName"]
        asset_group = bpy.data.objects.get(group_name)

        attrs = [
            attr for attr in dir(bpy.data)
            if isinstance(
                getattr(bpy.data, attr),
                bpy.types.bpy_prop_collection
            )
        ]

        for attr in attrs:
            for data in getattr(bpy.data, attr):
                if data.name.startswith(f"{group_name}:"):
                    getattr(bpy.data, attr).remove(data)

        bpy.data.objects.remove(asset_group)
