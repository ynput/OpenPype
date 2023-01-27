"""Load image in Blender."""

from pathlib import Path
from typing import Set, Tuple
import bpy

from openpype.hosts.blender.api import plugin
from openpype.hosts.blender.api.lib import get_selection
from openpype.hosts.blender.api.properties import OpenpypeContainer


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

    load_type = "LINK"

    def _load_library_datablocks(
        self,
        libpath: Path,
        container_name: str,
        container: OpenpypeContainer = None,
        **_kwargs
    ) -> Tuple[OpenpypeContainer, Set[bpy.types.ID]]:
        """OVERRIDE Load datablocks from blend file library.

        Args:
            libpath (Path): Path of library.
            container_name (str): Name of container to be loaded.
            container (OpenpypeContainer): Load into existing container.
                Defaults to None.

        Returns:
            Tuple[OpenpypeContainer, Set[bpy.types.ID]]:
                (Created scene container, Loaded datablocks)
        """
        img = bpy.data.images.load(libpath.as_posix())

        # Setup image as movie clip if inpute file extension is mov or mp4.
        if libpath.suffix in (".mov", "mp4"):
            img.source = "MOVIE"

        # Put into a container
        datablocks = [img]
        container = self._containerize_datablocks(
            container_name, datablocks, container
        )
        return container, datablocks


class ReferenceLoader(ImageLoader):
    """Load image as Reference.

    Append an bpy.types.Image in data of the current blend file and create
    empty object using the Image as display.
    """

    label = "Load Reference"
    order = 1

    def load(self, *args, **kwargs):
        """OVERRIDE"""
        container, datablocks = super().load(*args, **kwargs)
        img = datablocks[0]

        # generate empty object with image as display.
        empty_image = bpy.data.objects.new(container.name, object_data=None)
        empty_image.empty_display_type = "IMAGE"
        empty_image.empty_display_size = 10
        empty_image.empty_image_depth = "DEFAULT"
        empty_image.empty_image_side = "DOUBLE_SIDED"
        empty_image.show_empty_image_orthographic = True
        empty_image.show_empty_image_perspective = True
        empty_image.data = img

        # Setup image as movie clip if source is "MOVIE"
        # and match frame start and duration with the current scene settings.
        if img.source == "MOVIE":
            empty_image.image_user.frame_start = bpy.context.scene.frame_start
            empty_image.image_user.frame_duration = (
                bpy.context.scene.frame_end - bpy.context.scene.frame_start
            )

        bpy.context.scene.collection.objects.link(empty_image)

        return container, datablocks


class BackgroundLoader(ImageLoader):
    """Load image as Background linked to a camera.

    Append an bpy.types.Image in data of the current blend file and bind it
    to the selected camera as background image.
    """

    label = "Load Background for camera"
    order = 2

    def load(self, *args, **kwargs):
        """OVERRIDE"""
        container, datablocks = super().load(*args, **kwargs)
        img = datablocks[0]

        camera = None

        # First try, catching camera with current active object.
        if (
            bpy.context.active_object
            and bpy.context.active_object.type == "CAMERA"
        ):
            camera = bpy.context.active_object
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
                    obj
                    for obj in bpy.context.scene.objects
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

        return container, datablocks
