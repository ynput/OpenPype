from openpype.hosts.maya.api import (
    lib,
    plugin
)


class CreateCamera(plugin.Creator):
    """Single baked camera"""

    name = "cameraMain"
    label = "Camera"
    family = "camera"
    icon = "video-camera"

    def __init__(self, *args, **kwargs):
        super(CreateCamera, self).__init__(*args, **kwargs)

        # get basic animation data : start / end / handles / steps
        animation_data = lib.collect_animation_data()
        for key, value in animation_data.items():
            self.data[key] = value

        # Bake to world space by default, when this is False it will also
        # include the parent hierarchy in the baked results
        self.data['bakeToWorldSpace'] = True


class CreateCameraRig(plugin.Creator):
    """Complex hierarchy with camera."""

    name = "camerarigMain"
    label = "Camera Rig"
    family = "camerarig"
    icon = "video-camera"
