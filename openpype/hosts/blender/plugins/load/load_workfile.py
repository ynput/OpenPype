"""Load a workfile in Blender."""

import bpy

from openpype.hosts.blender.api import plugin


class LinkWorkfileLoader(plugin.AssetLoader):
    """Link Workfile from a .blend file."""

    families = ["workfile"]
    representations = ["blend"]

    label = "Link Workfile"
    icon = "link"
    color = "orange"
    color_tag = "COLOR_06"
    order = 0

    def _process(self, libpath, asset_group):
        with bpy.data.libraries.load(
            libpath, link=True, relative=False
        ) as (data_from, data_to):
            data_to.scenes = data_from.scenes

        scene = data_to.scenes[0]

        # Move objects and child from scene collections to asset_group.
        plugin.link_to_collection(scene.collection.objects, asset_group)
        plugin.link_to_collection(scene.collection.children, asset_group)

        for scene in data_to.scenes:
            bpy.data.scenes.remove(scene)


class AppendWorkfileLoader(plugin.AssetLoader):
    """Append Workfile from a .blend file."""

    families = ["workfile"]
    representations = ["blend"]

    label = "Append Workfile"
    icon = "paperclip"
    color = "orange"
    color_tag = "COLOR_06"
    order = 1

    def _process(self, libpath, asset_group):
        with bpy.data.libraries.load(
            libpath, link=False, relative=False
        ) as (data_from, data_to):
            data_to.scenes = data_from.scenes

        scene = data_to.scenes[0]

        # Move objects and child from scene collections to asset_group.
        plugin.link_to_collection(scene.collection.objects, asset_group)
        plugin.link_to_collection(scene.collection.children, asset_group)

        for scene in data_to.scenes:
            bpy.data.scenes.remove(scene)
