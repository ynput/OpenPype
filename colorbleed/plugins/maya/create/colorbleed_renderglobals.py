from collections import OrderedDict

import avalon.maya


class CreateRenderGlobals(avalon.maya.Creator):

    label = "Render Globals"
    family = "colorbleed.renderglobals"
    icon = "gears"

    def __init__(self, *args, **kwargs):
        super(CreateRenderGlobals, self).__init__(*args, **kwargs)

        # We won't be publishing this one
        self.data["id"] = "avalon.renderglobals"
        data = OrderedDict(**self.data)

        data["suspendPublishJob"] = False
        data["includeDefaultRenderLayer"] = False
        data["priority"] = 50
        data["whitelist"] = False
        data["machineList"] = ""

        self.data = data
        self.options = {"useSelection": False}  # Force no content

    def process(self):
        from maya import cmds

        exists = cmds.ls("renderglobalsDefault")
        assert len(exists) <= 1, (
            "More than one renderglobal exists, this is a bug")

        if exists:
            return cmds.warning("%s already exists." % exists[0])

        super(CreateRenderGlobals, self).process()