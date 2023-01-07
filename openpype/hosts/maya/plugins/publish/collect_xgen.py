from maya import cmds

import pyblish.api
from openpype.hosts.maya.api.lib import get_attribute_input


class CollectXgen(pyblish.api.InstancePlugin):
    """Collect Xgen"""

    order = pyblish.api.CollectorOrder + 0.499999
    label = "Collect Xgen"
    families = ["xgen"]

    def process(self, instance):
        data = {
            "xgmPalettes": cmds.ls(instance, type="xgmPalette", long=True),
            "xgmDescriptions": cmds.ls(
                instance, type="xgmDescription", long=True
            ),
            "xgmSubdPatches": cmds.ls(instance, type="xgmSubdPatch", long=True)
        }
        data["xgenNodes"] = (
            data["xgmPalettes"] +
            data["xgmDescriptions"] +
            data["xgmSubdPatches"]
        )

        if data["xgmPalettes"]:
            data["xgmPalette"] = data["xgmPalettes"][0]

        data["xgenConnections"] = {}
        for node in data["xgmSubdPatches"]:
            data["xgenConnections"][node] = {}
            for attr in ["transform", "geometry"]:
                input = get_attribute_input("{}.{}".format(node, attr))
                data["xgenConnections"][node][attr] = input

        self.log.info(data)
        instance.data.update(data)
