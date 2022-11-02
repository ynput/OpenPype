"""Load image in Blender."""

import bpy

from openpype.hosts.blender.api import plugin
from openpype.hosts.blender.api.lib import get_selection


class ImageLoader(plugin.AssetLoader):
    """Load image in Blender.

    Append an bpy.types.Image in data of the current blend file.
    This Image entity allow image files and movie files.
    Images append can be found in contextual lists like image texture.
    """

    families = ["image", "render2d", "source", "plate", "render", "review"]
    representations = ["png", "jpg", "mov", "mp4"]

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

        # Setup image as movie clip if source is file extension is mov or mp4.
        if libpath.endswith((".mov", "mp4")):
            img.source = 'MOVIE'

        return img


class ReferenceLoader(ImageLoader):
    """Load image as Reference.

    Append an bpy.types.Image in data of the current blend file and create
    empty object using the Image as display.
    """

    label = "Load Reference"
    order = 1

    def process_asset(
        self, context: dict, *args, **kwargs
    ) -> bpy.types.Object:
        img = super().process_asset(context, *args, **kwargs)

        libpath = self.fname
        asset = context["asset"]["name"]
        subset = context["subset"]["name"]
        group_name = plugin.asset_name(asset, subset)

        # generate empty object with image as display.
        asset_group = bpy.data.objects.new(group_name, object_data=None)
        asset_group.empty_display_type = "IMAGE"
        asset_group.empty_display_size = 10
        asset_group.empty_image_depth = 'DEFAULT'
        asset_group.empty_image_side = 'DOUBLE_SIDED'
        asset_group.show_empty_image_orthographic = True
        asset_group.show_empty_image_perspective = True
        asset_group.data = img

        # Setup image as movie clip if source is "MOVIE"
        # and match frame start and duration with the current scene settings.
        if img.source == "MOVIE":
            asset_group.image_user.frame_start = bpy.context.scene.frame_start
            asset_group.image_user.frame_duration = (
                bpy.context.scene.frame_end - bpy.context.scene.frame_start
            )

        plugin.get_main_collection().objects.link(asset_group)

        self._update_metadata(asset_group, context, group_name, libpath)

        return asset_group


class BackgroundLoader(ImageLoader):
    """Load image as Background linked to a camera.

    Append an bpy.types.Image in data of the current blend file and bind it
    to the selected camera as background image.
    """

    label = "Load Background for camera"
    order = 2

    def process_asset(self, *args, **kwargs) -> bpy.types.Image:
        img = super().process_asset(*args, **kwargs)

        camera = None

        # First try, catching camera with current active object.
        if bpy.context.object and bpy.context.object.type == "CAMERA":
            camera = bpy.context.object
        # Second try, catching camera with current selection.
        if not camera:
            camera = next(
                (obj for obj in get_selection() if obj.type == "CAMERA"),
                None,
            )
        # Last try, catching camera with current scene objects.
        if not camera:
            camera = next(
                (
                    obj for obj in bpy.context.scene.objects
                    if obj.type == "CAMERA"
                ),
                None,
            )

        assert camera, "No camera found!"

        # Link image as background image.
        camera.data.show_background_images = True
        bkg_img = camera.data.background_images.new()
        bkg_img.image = img
        bkg_img.frame_method = "FIT"

        # Setup image as movie clip if source is "MOVIE"
        # and match frame start and duration with the current scene settings.
        if img.source == "MOVIE":
            bkg_img.image_user.frame_start = bpy.context.scene.frame_start
            bkg_img.image_user.frame_duration = (
                bpy.context.scene.frame_end - bpy.context.scene.frame_start
            )

        return img
