from collections import OrderedDict

import maya.cmds as cmds

import avalon.maya


class CreateRenderGlobals(avalon.maya.Creator):

    label = "Render Globals"
    family = "colorbleed.renderglobals"
    icon = "gears"

    def __init__(self, *args, **kwargs):
        super(CreateRenderGlobals, self).__init__(*args, **kwargs)

        # We won't be publishing this one
        self.data["id"] = "avalon.renderglobals"

        # We don't need subset or asset attributes
        self.data.pop("subset", None)
        self.data.pop("asset", None)
        self.data.pop("active", None)

        data = OrderedDict(**self.data)

        data["suspendPublishJob"] = False
        data["extendFrames"] = False
        data["overrideExistingFrame"] = True
        data["includeDefaultRenderLayer"] = False
        data["useLegacyRenderLayers"] = True
        data["priority"] = 50
        data["whitelist"] = False
        data["machineList"] = ""
        data["pools"] = ""

        self.data = data
        self.options = {"useSelection": False}  # Force no content

    def process(self):

        exists = cmds.ls(self.name)
        assert len(exists) <= 1, (
            "More than one renderglobal exists, this is a bug")

        if exists:
            return cmds.warning("%s already exists." % exists[0])

        super(CreateRenderGlobals, self).process()

        cmds.setAttr("{}.machineList".format(self.name), lock=True)
