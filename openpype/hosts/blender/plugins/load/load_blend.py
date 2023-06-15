from typing import Dict, List, Optional

import bpy

from openpype.pipeline import (
    AVALON_CONTAINER_ID,
)
from openpype.hosts.blender.api import plugin
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

        container[AVALON_PROPERTY] = {
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

        objects = [
            obj for obj in bpy.data.objects
            if f"{group_name}:" in obj.name
        ]

        self[:] = objects
        return objects

    def exec_update(self, container: Dict, representation: Dict):
        """
        Update the loaded asset.
        """
        raise NotImplementedError()

    def exec_remove(self, container: Dict) -> bool:
        """
        Remove an existing container from a Blender scene.
        """
        raise NotImplementedError()
