"""A module containing generic loader actions that will display in the Loader.

"""

from avalon import api


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

        start = version_data.get("startFrame", None)
        end = version_data.get("endFrame", None)

        if start is None or end is None:
            print(
                "Skipping setting frame range because start or "
                "end frame data is missing.."
            )
            return

        hou.playbar.setFrameRange(start, end)
        hou.playbar.setPlaybackRange(start, end)


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

        start = version_data.get("startFrame", None)
        end = version_data.get("endFrame", None)

        if start is None or end is None:
            print(
                "Skipping setting frame range because start or "
                "end frame data is missing.."
            )
            return

        # Include handles
        handles = version_data.get("handles", 0)
        start -= handles
        end += handles

        hou.playbar.setFrameRange(start, end)
        hou.playbar.setPlaybackRange(start, end)
