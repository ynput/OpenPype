from typing import Dict, List, Optional
from pathlib import Path

import bpy

from openpype.pipeline import (
    legacy_create,
    get_representation_path,
    AVALON_CONTAINER_ID,
)
from openpype.pipeline.create import get_legacy_creator_by_name
from openpype.hosts.blender.api import plugin
from openpype.hosts.blender.api.lib import imprint
from openpype.hosts.blender.api.pipeline import (
    AVALON_CONTAINERS,
    AVALON_PROPERTY,
)


class BlendLoader(plugin.AssetLoader):
    """Load assets from a .blend file."""

    families = ["model", "rig", "layout", "camera", "blendScene"]
    representations = ["blend"]

    label = "Append Blend"
    icon = "code-fork"
    color = "orange"

    @staticmethod
    def _get_asset_container(objects):
        empties = [obj for obj in objects if obj.type == 'EMPTY']

        for empty in empties:
            if empty.get(AVALON_PROPERTY):
                return empty

        return None

    @staticmethod
    def get_all_container_parents(asset_group):
        parent_containers = []
        parent = asset_group.parent
        while parent:
            if parent.get(AVALON_PROPERTY):
                parent_containers.append(parent)
            parent = parent.parent

        return parent_containers

    def _post_process_layout(self, container, asset, representation):
        rigs = [
            obj for obj in container.children_recursive
            if (
                obj.type == 'EMPTY' and
                obj.get(AVALON_PROPERTY) and
                obj.get(AVALON_PROPERTY).get('family') == 'rig'
            )
        ]

        for rig in rigs:
            creator_plugin = get_legacy_creator_by_name("CreateAnimation")
            legacy_create(
                creator_plugin,
                name=rig.name.split(':')[-1] + "_animation",
                asset=asset,
                options={
                    "useSelection": False,
                    "asset_group": rig
                },
                data={
                    "dependencies": representation
                }
            )

    def _process_data(self, libpath, group_name):
        # Append all the data from the .blend file
        with bpy.data.libraries.load(
            libpath, link=False, relative=False
        ) as (data_from, data_to):
            for attr in dir(data_to):
                setattr(data_to, attr, getattr(data_from, attr))

        members = []

        # Rename the object to add the asset name
        for attr in dir(data_to):
            for data in getattr(data_to, attr):
                data.name = f"{group_name}:{data.name}"
                members.append(data)

        container = self._get_asset_container(data_to.objects)
        assert container, "No asset group found"

        container.name = group_name
        container.empty_display_type = 'SINGLE_ARROW'

        # Link the collection to the scene
        bpy.context.scene.collection.objects.link(container)

        # Link all the container children to the collection
        for obj in container.children_recursive:
            bpy.context.scene.collection.objects.link(obj)

        # Remove the library from the blend file
        library = bpy.data.libraries.get(bpy.path.basename(libpath))
        bpy.data.libraries.remove(library)

        return container, members

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

        try:
            family = context["representation"]["context"]["family"]
        except ValueError:
            family = "model"

        representation = str(context["representation"]["_id"])

        asset_name = plugin.asset_name(asset, subset)
        unique_number = plugin.get_unique_number(asset, subset)
        group_name = plugin.asset_name(asset, subset, unique_number)
        namespace = namespace or f"{asset}_{unique_number}"

        avalon_container = bpy.data.collections.get(AVALON_CONTAINERS)
        if not avalon_container:
            avalon_container = bpy.data.collections.new(name=AVALON_CONTAINERS)
            bpy.context.scene.collection.children.link(avalon_container)

        container, members = self._process_data(libpath, group_name)

        if family == "layout":
            self._post_process_layout(container, asset, representation)

        avalon_container.objects.link(container)

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
            "objectName": group_name,
            "members": members,
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
        parent = asset_group.parent

        self.exec_remove(container)

        asset_group, members = self._process_data(libpath, group_name)

        avalon_container = bpy.data.collections.get(AVALON_CONTAINERS)
        avalon_container.objects.link(asset_group)

        asset_group.matrix_basis = transform
        asset_group.parent = parent

        # Restore the old data, but reset memebers, as they don't exist anymore
        # This avoids a crash, because the memory addresses of those members
        # are not valid anymore
        old_data["members"] = []
        asset_group[AVALON_PROPERTY] = old_data

        new_data = {
            "libpath": libpath,
            "representation": str(representation["_id"]),
            "parent": str(representation["parent"]),
            "members": members,
        }

        imprint(asset_group, new_data)

        # We need to update all the parent container members
        parent_containers = self.get_all_container_parents(asset_group)

        for parent_container in parent_containers:
            parent_members = parent_container[AVALON_PROPERTY]["members"]
            parent_container[AVALON_PROPERTY]["members"] = (
                parent_members + members)

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

        members = asset_group.get(AVALON_PROPERTY).get("members", [])

        # We need to update all the parent container members
        parent_containers = self.get_all_container_parents(asset_group)

        for parent in parent_containers:
            parent.get(AVALON_PROPERTY)["members"] = list(filter(
                lambda i: i not in members,
                parent.get(AVALON_PROPERTY).get("members", [])))

        for attr in attrs:
            for data in getattr(bpy.data, attr):
                if data in members:
                    # Skip the asset group
                    if data == asset_group:
                        continue
                    getattr(bpy.data, attr).remove(data)

        bpy.data.objects.remove(asset_group)
