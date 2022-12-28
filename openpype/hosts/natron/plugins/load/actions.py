"""A module containing generic loader actions that will display in the Loader.

"""

from openpype.pipeline import load


class NatronSetFrameRangeLoader(load.LoaderPlugin):
    """Set frame range excluding pre- and post-handles"""

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

        from openpype.hosts.natron.api import get_app

        version = context['version']
        version_data = version.get("data", {})

        start = version_data.get("frameStart", None)
        end = version_data.get("frameEnd", None)

        if start is None or end is None:
            print("Skipping setting frame range because start or "
                  "end frame data is missing..")
            return

        app = get_app()
        app.getProjectParam('frameRange').set(int(start), int(end))


class NatronSetFrameRangeWithHandlesLoader(load.LoaderPlugin):
    """Set frame range including pre- and post-handles"""

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

        from openpype.hosts.natron.api import get_app

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

        app = get_app()
        app.getProjectParam('frameRange').set(int(start), int(end))
