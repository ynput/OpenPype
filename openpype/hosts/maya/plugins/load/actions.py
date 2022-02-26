"""A module containing generic loader actions that will display in the Loader.

"""

from avalon import api
from openpype.hosts.maya.api.lib import (
    maintained_selection,
    unique_namespace
)


class SetFrameRangeLoader(api.Loader):
    """Specific loader of Alembic for the avalon.animation family"""

    families = ["animation",
                "camera",
                "pointcache"]
    representations = ["abc"]

    label = "Set frame range"
    order = 11
    icon = "clock-o"
    color = "white"

    def load(self, context, name, namespace, data):

        import maya.cmds as cmds

        version = context['version']
        version_data = version.get("data", {})

        start = version_data.get("frameStart", None)
        end = version_data.get("frameEnd", None)

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

    families = ["animation",
                "camera",
                "pointcache"]
    representations = ["abc"]

    label = "Set frame range (with handles)"
    order = 12
    icon = "clock-o"
    color = "white"

    def load(self, context, name, namespace, data):

        import maya.cmds as cmds

        version = context['version']
        version_data = version.get("data", {})

        start = version_data.get("frameStart", None)
        end = version_data.get("frameEnd", None)

        if start is None or end is None:
            print("Skipping setting frame range because start or "
                  "end frame data is missing..")
            return

        # Include handles
        start -= version_data.get("handleStart", 0)
        end += version_data.get("handleEnd", 0)

        cmds.playbackOptions(minTime=start,
                             maxTime=end,
                             animationStartTime=start,
                             animationEndTime=end)


class ImportMayaLoader(api.Loader):
    """Import action for Maya (unmanaged)

    Warning:
        The loaded content will be unmanaged and is *not* visible in the
        scene inventory. It's purely intended to merge content into your scene
        so you could also use it as a new base.

    """
    representations = ["ma", "mb"]
    families = ["*"]

    label = "Import"
    order = 10
    icon = "arrow-circle-down"
    color = "#775555"

    def load(self, context, name=None, namespace=None, data=None):
        import maya.cmds as cmds

        choice = self.display_warning()
        if choice is False:
            return

        asset = context['asset']

        namespace = namespace or unique_namespace(
            asset["name"] + "_",
            prefix="_" if asset["name"][0].isdigit() else "",
            suffix="_",
        )

        with maintained_selection():
            cmds.file(self.fname,
                      i=True,
                      preserveReferences=True,
                      namespace=namespace,
                      returnNewNodes=True,
                      groupReference=True,
                      groupName="{}:{}".format(namespace, name))

        # We do not containerize imported content, it remains unmanaged
        return

    def display_warning(self):
        """Show warning to ensure the user can't import models by accident

        Returns:
            bool

        """

        from Qt import QtWidgets

        accept = QtWidgets.QMessageBox.Ok
        buttons = accept | QtWidgets.QMessageBox.Cancel

        message = "Are you sure you want import this"
        state = QtWidgets.QMessageBox.warning(None,
                                              "Are you sure?",
                                              message,
                                              buttons=buttons,
                                              defaultButton=accept)

        return state == accept
