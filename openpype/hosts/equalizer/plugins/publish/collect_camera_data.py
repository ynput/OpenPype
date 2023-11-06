"""Collect camera data from the scene."""
import pyblish.api
import tde4


class CollectCameraData(pyblish.api.InstancePlugin):
    """Collect camera data from the scene."""

    order = pyblish.api.CollectorOrder
    families = ["matchmove"]
    hosts = ["equalizer"]
    label = "Collect camera data"

    def process(self, instance: pyblish.api.Instance):
        # handle camera selection.
        # possible values are:
        #   - __current__ - current camera
        #   - __ref__ - reference cameras
        #   - __seq__ - sequence cameras
        #   - __all__ - all cameras
        #   - camera_id - specific camera

        try:
            camera_sel = instance.data["creator_attributes"]["camera_selection"]  # noqa: E501
        except KeyError:
            self.log.warning("No camera defined")
            return

        if camera_sel == "__all__":
            cameras = tde4.getCameraList()
        elif camera_sel == "__current__":
            cameras = [tde4.getCurrentCamera()]
        elif camera_sel in ["__ref__", "__seq__"]:
            cameras = [
                c for c in tde4.getCameraList()
                if tde4.getCameraType(c) == "REF_FRAME"
            ]
        else:
            if camera_sel not in tde4.getCameraList():
                self.log.warning("Invalid camera found")
                return
            cameras = [camera_sel]

        data = []

        for camera in cameras:
            camera_name = tde4.getCameraName(camera)
            enabled = tde4.getCameraEnabledFlag(camera)
            # calculation range
            c_range_start, c_range_end = tde4.getCameraCalculationRange(
                camera)
            p_range_start, p_range_end = tde4.getCameraPlaybackRange(camera)
            fov = tde4.getCameraFOV(camera)
            fps = tde4.getCameraFPS(camera)
            # focal length is time based, so lets skip it for now
            # focal_length = tde4.getCameraFocalLength(camera, frame)
            path = tde4.getCameraPath(camera)

            camera_data = {
                "name": camera_name,
                "id": camera,
                "enabled": enabled,
                "calculation_range": (c_range_start, c_range_end),
                "playback_range": (p_range_start, p_range_end),
                "fov": fov,
                "fps": fps,
                # "focal_length": focal_length,
                "path": path
            }
            data.append(camera_data)
        instance.data["cameras"] = data
