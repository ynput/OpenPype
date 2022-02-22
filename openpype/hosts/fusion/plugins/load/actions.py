"""A module containing generic loader actions that will display in the Loader.

"""

from avalon import api


class FusionSetFrameRangeLoader(api.Loader):
    """Specific loader of Alembic for the avalon.animation family"""

    families = ["animation",
                "camera",
                "imagesequence",
                "yeticache",
                "pointcache",
                "render"]
    representations = ["*"]

    label = "Set frame range"
    order = 11
    icon = "clock-o"
    color = "white"

    def load(self, context, name, namespace, data):

        from openpype.hosts.fusion.api import lib

        version = context['version']
        version_data = version.get("data", {})

        start = version_data.get("frameStart", None)
        end = version_data.get("frameEnd", None)

        if start is None or end is None:
            print("Skipping setting frame range because start or "
                  "end frame data is missing..")
            return

        lib.update_frame_range(start, end)


class FusionSetFrameRangeWithHandlesLoader(api.Loader):
    """Specific loader of Alembic for the avalon.animation family"""

    families = ["animation",
                "camera",
                "imagesequence",
                "yeticache",
                "pointcache",
                "render"]
    representations = ["*"]

    label = "Set frame range (with handles)"
    order = 12
    icon = "clock-o"
    color = "white"

    def load(self, context, name, namespace, data):

        from openpype.hosts.fusion.api import lib

        version = context['version']
        version_data = version.get("data", {})

        start = version_data.get("frameStart", None)
        end = version_data.get("frameEnd", None)

        if start is None or end is None:
            print("Skipping setting frame range because start or "
                  "end frame data is missing..")
            return

        # Include handles
        handles = version_data.get("handles", 0)
        start -= handles
        end += handles

        lib.update_frame_range(start, end)
