"""A module containing generic loader actions that will display in the Loader.

"""

from avalon import api


class SetFrameRangeLoader(api.Loader):
    """Specific loader of Alembic for the avalon.animation family"""

    families = ["colorbleed.animation",
                "colorbleed.camera",
                "colorbleed.pointcache"]
    representations = ["abc"]

    label = "Set frame range"
    order = 11
    icon = "clock-o"
    color = "white"

    def load(self, context, name, namespace, data):

        import maya.cmds as cmds

        version = context['version']
        version_data = version.get("data", {})

        start = version_data.get("startFrame", None)
        end = version_data.get("endFrame", None)

        if start is None or end is None:
            print("Skipping setting frame range because start or "
                  "end frame data is missing..")
            return

        cmds.playbackOptions(minTime=start,
                             maxTime=end,
                             animationStartTime=start,
                             animationEndTime=end)


class SetFrameRangeWithHandlesLoader(api.Loader):
    """Specific loader of Alembic for the avalon.animation family"""

    families = ["colorbleed.animation",
                "colorbleed.camera",
                "colorbleed.pointcache"]
    representations = ["abc"]

    label = "Set frame range (with handles)"
    order = 12
    icon = "clock-o"
    color = "white"

    def load(self, context, name, namespace, data):

        import maya.cmds as cmds

        version = context['version']
        version_data = version.get("data", {})

        start = version_data.get("startFrame", None)
        end = version_data.get("endFrame", None)

        if start is None or end is None:
            print("Skipping setting frame range because start or "
                  "end frame data is missing..")
            return

        # Include handles
        handles = version_data.get("handles", 0)
        start -= handles
        end += handles

        cmds.playbackOptions(minTime=start,
                             maxTime=end,
                             animationStartTime=start,
                             animationEndTime=end)
