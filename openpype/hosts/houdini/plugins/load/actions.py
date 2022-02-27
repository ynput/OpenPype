"""A module containing generic loader actions that will display in the Loader.

"""

from avalon import api
from openpype.lib import get_frame_info


class SetFrameRangeLoader(api.Loader):
    """Set Houdini frame range"""

    families = [
        "animation",
        "camera",
        "pointcache",
        "vdbcache",
        "usd",
    ]
    representations = ["abc", "vdb", "usd"]

    label = "Set frame range"
    order = 11
    icon = "clock-o"
    color = "white"

    def load(self, context, name, namespace, data):

        import hou

        version = context["version"]
        version_data = version.get("data", {})

        frame_start = version_data.get("frameStart", None)
        frame_end = version_data.get("frameEnd", None)

        if frame_start is None or frame_end is None:
            print(
                "Skipping setting frame range because start or "
                "end frame data is missing.."
            )
            return

        handle_start = version_data.get("handleStart")
        handle_end = version_data.get("handleEnd")
        frame_info = get_frame_info(
            frame_start, frame_end, handle_start, handle_end
        )

        hou.playbar.setFrameRange(
            frame_info.frame_start, frame_info.frame_end
        )
        hou.playbar.setPlaybackRange(
            frame_info.frame_start, frame_info.frame_end
        )


class SetFrameRangeWithHandlesLoader(api.Loader):
    """Set Maya frame range including pre- and post-handles"""

    families = [
        "animation",
        "camera",
        "pointcache",
        "vdbcache",
        "usd",
    ]
    representations = ["abc", "vdb", "usd"]

    label = "Set frame range (with handles)"
    order = 12
    icon = "clock-o"
    color = "white"

    def load(self, context, name, namespace, data):

        import hou

        version = context["version"]
        version_data = version.get("data", {})

        frame_start = version_data.get("frameStart", None)
        frame_end = version_data.get("frameEnd", None)

        if frame_start is None or frame_end is None:
            print(
                "Skipping setting frame range because start or "
                "end frame data is missing.."
            )
            return

        handle_start = version_data.get("handleStart")
        handle_end = version_data.get("handleEnd")
        frame_info = get_frame_info(
            frame_start, frame_end, handle_start, handle_end
        )

        hou.playbar.setFrameRange(
            frame_info.handle_frame_start, frame_info.handle_frame_end
        )
        hou.playbar.setPlaybackRange(
            frame_info.handle_frame_start, frame_info.handle_frame_end
        )
