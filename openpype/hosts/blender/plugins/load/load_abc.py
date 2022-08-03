"""Load an asset in Blender from an Alembic file."""

import bpy

from openpype.hosts.blender.api import plugin


class CacheModelLoader(plugin.AssetLoader):
    """Import cache models.

    Stores the imported asset in a collection named after the asset.

    Note:
        At least for now it only supports Alembic files.
    """

    families = ["model", "pointcache"]
    representations = ["abc"]

    label = "Import Alembic"
    icon = "download"
    color = "orange"
    color_tag = "COLOR_04"
    order = 4

    def _process(self, libpath, asset_group):

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
