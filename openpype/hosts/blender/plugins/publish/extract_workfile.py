from pathlib import Path
from typing import Set

import pyblish
import bpy
from openpype.hosts.blender.plugins.publish import extract_blend

from openpype.hosts.blender.api import get_compress_setting


class ExtractWorkfile(extract_blend.ExtractBlend):
    """Extract the scene as workfile blend file."""

    label = "Extract workfile"
    hosts = ["blender"]
    families = ["workfile"]
    
    # Run first
    order = pyblish.api.ExtractorOrder - 0.1

    def _write_data(self, filepath: Path, *args):
        """Override to save mainfile with all data.

        Args:
            filepath (Path): Path to save mainfile to.
        """
        bpy.ops.wm.save_as_mainfile(
            filepath=filepath.as_posix(),
            compress=get_compress_setting(),
            relative_remap=False,
            copy=True,
        )

    def _get_used_images(self, *args) -> Set[bpy.types.Image]:
        """Override to return all images.

        Returns:
            Set[bpy.types.Image]: All images in blend file
        """
        return bpy.data.images
