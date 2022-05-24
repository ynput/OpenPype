"""Load an asset in Blender from an Alembic file."""

from typing import Dict, List, Optional

import bpy

from openpype.pipeline import legacy_io
from openpype.hosts.blender.api import plugin
from openpype.hosts.blender.api.pipeline import (
    AVALON_PROPERTY,
    MODEL_DOWNSTREAM,
)


class CacheModelLoader(plugin.AssetLoader):
    """Load cache models.

    Stores the imported asset in a collection named after the asset.

    Note:
        At least for now it only supports Alembic files.
    """

    families = ["model", "pointcache"]
    representations = ["abc"]

    label = "Load Alembic"
    icon = "code-fork"
    color = "orange"

    @staticmethod
    def _process(libpath, asset_group):

        current_objects = set(bpy.data.objects)

        relative = bpy.context.preferences.filepaths.use_relative_paths
        bpy.ops.wm.alembic_import(
            filepath=libpath,
            relative_path=relative
        )

        objects = set(bpy.data.objects) - current_objects

        for obj in objects:
            for collection in obj.users_collection:
                collection.objects.unlink(obj)

        plugin.link_to_collection(objects, asset_group)

        plugin.orphans_purge()
        plugin.deselect_all()

        return objects

    def process_asset(self, context: dict, *args, **kwargs) -> List:
        """Asset loading Process"""
        asset_group, objects = super().process_asset(context, *args, **kwargs)

        if legacy_io.Session.get("AVALON_TASK") in MODEL_DOWNSTREAM:
            asset = context["asset"]["name"]
            subset = context["subset"]["name"]
            group_name = plugin.asset_name(asset, subset)
            asset_group.name = group_name
            asset_group[AVALON_PROPERTY]["namespace"] = asset
        else:
            namespace = asset_group[AVALON_PROPERTY]["namespace"]
            self._rename_objects_with_namespace(objects, namespace)

        return objects

    def exec_update(self, container: Dict, representation: Dict):
        """Update the loaded asset"""
        objects = self._update_process(container, representation)

        if legacy_io.Session.get("AVALON_TASK") not in MODEL_DOWNSTREAM:
            self._rename_objects_with_namespace(
                objects, container["namespace"] or container["objectName"]
            )

    def exec_remove(self, container) -> bool:
        """Remove the existing container from Blender scene"""
        return self._remove_container(container)
