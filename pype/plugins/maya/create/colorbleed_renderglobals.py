from collections import OrderedDict

from maya import cmds

from avalon.vendor import requests
import avalon.maya
from avalon import api


class CreateRenderGlobals(avalon.maya.Creator):

    label = "Render Globals"
    family = "renderglobals"
    icon = "gears"

    def __init__(self, *args, **kwargs):
        super(CreateRenderGlobals, self).__init__(*args, **kwargs)

        # We won't be publishing this one
        self.data["id"] = "avalon.renderglobals"

        # get pools
        AVALON_DEADLINE = api.Session["AVALON_DEADLINE"]
        argument = "{}/api/pools?NamesOnly=true".format(AVALON_DEADLINE)
        response = requests.get(argument)
        if not response.ok:
            self.log.warning("No pools retrieved")
            pools = []
        else:
            pools = response.json()

        # We don't need subset or asset attributes
        self.data.pop("subset", None)
        self.data.pop("asset", None)
        self.data.pop("active", None)

        data = OrderedDict(**self.data)

        data["suspendPublishJob"] = False
        data["extendFrames"] = False
        data["overrideExistingFrame"] = True
        data["useLegacyRenderLayers"] = True
        data["priority"] = 50
        data["framesPerTask"] = 1
        data["whitelist"] = False
        data["machineList"] = ""
        data["useMayaBatch"] = True
        data["primaryPool"] = pools
        # We add a string "-" to allow the user to not set any secondary pools
        data["secondaryPool"] = ["-"] + pools

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
