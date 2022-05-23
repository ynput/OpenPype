"""Load an asset in Blender from an Alembic file."""

from typing import Dict, List, Optional

import bpy

from openpype.pipeline import legacy_io
from openpype.hosts.blender.api import plugin


class FbxModelLoader(plugin.AssetLoader):
    """Load FBX models.

    Stores the imported asset in an empty named after the asset.
    """

    families = ["model", "rig"]
    representations = ["fbx"]

    label = "Load FBX"
    icon = "code-fork"
    color = "orange"
    color_tag = "COLOR_04"

    _downstream_tasks = ("Rigging", "Modeling", "Texture", "Lookdev")

    @staticmethod
    def _rename_with_namespace(objects, namespace):
        materials = set()
        for obj in objects:
            obj.name = f"{namespace}:{obj.name}"
            if obj.data:
                obj.data.name = f"{namespace}:{obj.data.name}"

            if obj.type == 'MESH':
                for material_slot in obj.material_slots:
                    if material_slot.material:
                        materials.add(material_slot.material)

            elif obj.type == 'ARMATURE':
                anim_data = obj.animation_data
                if anim_data and anim_data.action:
                    anim_data.action.name = (
                        f"{namespace}:{anim_data.action.name}"
                    )
        for material in materials:
            material.name = f"{namespace}:{material.name}"

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

        asset_group = bpy.data.collections.new(group_name)
        plugin.get_main_collection().children.link(asset_group)

        objects = self._load_fbx(libpath, asset_group, group_name)

        if (
            legacy_io.Session.get("AVALON_ASSET") != asset or
            legacy_io.Session.get("AVALON_TASK") not in self._downstream_tasks
        ):
            self._rename_with_namespace(objects, namespace)

        self._update_metadata(
            asset_group, context, name, namespace, asset_name, libpath
        )

        self[:] = objects
        return objects

    def exec_update(self, container: Dict, representation: Dict):
        """Update the loaded asset"""
        objects = self._update_process(container, representation)

        if (
            legacy_io.Session.get("AVALON_ASSET") != container["asset_name"] or
            legacy_io.Session.get("AVALON_TASK") not in self._downstream_tasks
        ):
            self._rename_with_namespace(
                objects, container["namespace"] or container["objectName"]
            )

    def exec_remove(self, container) -> bool:
        """Remove the existing container from Blender scene"""
        return self._remove_container(container)
