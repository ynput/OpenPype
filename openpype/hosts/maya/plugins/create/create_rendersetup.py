from maya import cmds
from openpype.hosts.maya.api import (
    lib,
    plugin
)


class CreateRenderSetup(plugin.Creator):
    """Create rendersetup template json data"""

    name = "rendersetup"
    label = "Render Setup Preset"
    family = "rendersetup"
    icon = "tablet"

    def __init__(self, *args, **kwargs):
        super(CreateRenderSetup, self).__init__(*args, **kwargs)

        # here we can pre-create renderSetup layers, possibly utlizing
        # settings for it.

        #  _____
        # /   __\__
        # |  /   __\__
        # |  |  /     \
        # |  |  |     |
        # \__|  |     |
        #    \__|     |
        #       \_____/

        # from pype.api import get_project_settings
        # import maya.app.renderSetup.model.renderSetup as renderSetup
        # settings = get_project_settings(get_current_project_name())
        # layer = settings['maya']['create']['renderSetup']["layer"]

        # rs = renderSetup.instance()
        # rs.createRenderLayer(layer)

        self.options = {"useSelection": False}  # Force no content

    def process(self):
        exists = cmds.ls(self.name)
        assert len(exists) <= 1, (
            "More than one renderglobal exists, this is a bug"
        )

        if exists:
            return cmds.warning("%s already exists." % exists[0])

        with lib.undo_chunk():
            instance = super(CreateRenderSetup, self).process()

        self.data["renderSetup"] = "42"
        null = cmds.sets(name="null_SET", empty=True)
        cmds.sets([null], forceElement=instance)
