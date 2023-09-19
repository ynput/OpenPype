"""Collect camera data from the scene."""
import pyblish.api
import tde4


class CollectCameraData(pyblish.api.InstancePlugin):
    """Collect camera data from the scene."""

    order = pyblish.api.CollectorOrder
    families = ["matchmove"]
    hosts = ["equalizer"]
    label = "Collect cameras data"

    def process(self, instance):
        data = []
        camera_list = tde4.getCameraList()
        for camera in camera_list:
            camera_name = tde4.getCameraName(camera)
            enabled = tde4.getCameraEnabledFlag(camera)
            # calculation range
            c_range_start, c_range_end = tde4.getCameraCalculationRange(
                camera)
            p_range_start, p_range_end = tde4.getCameraPlaybackRange(camera)
            fov = tde4.getCameraFOV(camera)
            fps = tde4.getCameraFPS(camera)
            # focal length
            focal_length = tde4.getCameraFocalLength(camera)
            path = tde4.getCameraPath(camera)

            camera_data = {
                "camera_name": camera_name,
                "camera_id": camera,
                "enabled": enabled,
                "calculation_range": (c_range_start, c_range_end),
                "playback_range": (p_range_start, p_range_end),
                "fov": fov,
                "fps": fps,
                "focal_length": focal_length,
                "path": path
            }
            data.append(camera_data)
        instance.data["cameras"] = data
