"""Create a camera asset."""

from itertools import chain
from typing import List, Union
import bpy

from openpype.hosts.blender.api import plugin
from openpype.hosts.blender.api.properties import OpenpypeInstance
from openpype.hosts.blender.api.utils import get_all_outliner_children

def _get_camera_from_datablocks(datablocks: List[bpy.types.ID])->Union[bpy.types.Object, None]:
    """Get first camera found in given datablocks list.

    Args:
        datablocks (List[bpy.types.ID]):
            List of datablocks to get camera from

    Returns:
        Union[bpy.types.Object, None]: Found camera if any.
    """
    outliner_children = set(
        chain.from_iterable(
            get_all_outliner_children(d) for d in datablocks
        )
    )
    return next(
        (
            c
            for c in outliner_children | set(datablocks)
            if isinstance(c, bpy.types.Object) and c.type == "CAMERA"
        ),
        None,
    )

class CreateCamera(plugin.Creator):
    """Single baked camera"""

    name = "cameraMain"
    label = "Camera"
    family = "camera"
    icon = "video-camera"

    def process(
        self, datablocks: List[bpy.types.ID] = None, **kwargs
    ) -> OpenpypeInstance:
        # Create instance object
        asset = self.data["asset"]
        subset = self.data["subset"]
        instance_name = plugin.build_op_basename(asset, subset)

        # Rename existing camera or create one
        datablocks = datablocks or []
        camera = _get_camera_from_datablocks(datablocks)
        if camera:
            camera.name = instance_name
            camera.data.name = instance_name
        else:
            camera = bpy.data.cameras.new(instance_name)
            camera_obj = bpy.data.objects.new(instance_name, camera)
            datablocks.append(camera_obj)

        # Create Instance
        return super().process(datablocks, **kwargs)
