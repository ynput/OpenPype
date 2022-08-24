"""Load a render scene in Blender."""

import bpy

from openpype.hosts.blender.api import plugin


class LinkRenderLoader(plugin.AssetLoader):
    """Link render scenes from a .blend file."""

    families = ["render"]
    representations = ["blend"]

    label = "Link Render"
    icon = "link"
    color = "orange"
    color_tag = "COLOR_08"
    order = 0
    no_namespace = True

    def _process(self, libpath, asset_group):
        with bpy.data.libraries.load(
            libpath, link=True, relative=False
        ) as (data_from, data_to):
            data_to.scenes = data_from.scenes

        for scene in data_to.scenes:
            scene.name = f"{asset_group.name}:{scene.name}"


class AppendRenderLoader(plugin.AssetLoader):
    """Append render scenes from a .blend file."""

    families = ["render"]
    representations = ["blend"]

    label = "Append Render"
    icon = "paperclip"
    color = "orange"
    color_tag = "COLOR_08"
    order = 1
    no_namespace = True

    def _process(self, libpath, asset_group):
        with bpy.data.libraries.load(
            libpath, link=False, relative=False
        ) as (data_from, data_to):
            data_to.scenes = data_from.scenes

        for scene in data_to.scenes:
            scene.name = f"{asset_group.name}:{scene.name}"
