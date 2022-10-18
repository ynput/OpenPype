"""Load audio in Blender."""

from pathlib import Path
from typing import Dict, Optional

import bpy

from openpype.hosts.blender.api import plugin
from openpype.hosts.blender.api.pipeline import AVALON_PROPERTY
from openpype.pipeline.load.utils import get_representation_path


class ImageLoader(plugin.AssetLoader):
    """Load image in Blender."""

    families = ["image"]
    representations = ["png", "jpg"]

    label = "Load Image"
    icon = "image"
    order = 0
    color = "orange"
    color_tag = "COLOR_02"

    def process_asset(self, context: dict, *args, **kwargs) -> bpy.types.Image:
        """Process load image in Blender"""
        libpath = self.fname
        asset = context["asset"]["name"]
        subset = context["subset"]["name"]

        img = bpy.data.images.load(libpath)
        img.name = plugin.asset_name(asset, subset)

        return img


class ReferenceLoader(ImageLoader):
    """Load image as Reference."""

    label = "Load Reference"
    icon = "image"
    order = 1

    def process_asset(self, context: dict, *args, **kwargs) -> bpy.types.Object:
        img = super().process_asset(context, *args, **kwargs)

        libpath = self.fname
        asset = context["asset"]["name"]
        subset = context["subset"]["name"]

        group_name = plugin.asset_name(asset, subset)
        asset_group = bpy.data.objects.new(group_name, object_data=None)
        
        asset_group.empty_display_type = "IMAGE"
        asset_group.empty_display_size = 10
        asset_group.empty_image_depth = 'DEFAULT'
        asset_group.empty_image_side = 'DOUBLE_SIDED'
        asset_group.show_empty_image_orthographic = True
        asset_group.show_empty_image_perspective = True
        asset_group.data = img

        plugin.get_main_collection().objects.link(asset_group)

        self._update_metadata(asset_group, context, group_name, libpath)

        return asset_group
