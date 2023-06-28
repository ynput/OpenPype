import os

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

        # Collect all files under palette root as resources.
        import xgenm

        data_path = xgenm.getAttr(
            "xgDataPath", data["xgmPalette"].replace("|", "")
        ).split(os.pathsep)[0]
        data_path = data_path.replace(
            "${PROJECT}",
            xgenm.getAttr("xgProjectPath", data["xgmPalette"].replace("|", ""))
        )
        transfers = []

        # Since we are duplicating this palette when extracting we predict that
        # the name will be the basename without namespaces.
        predicted_palette_name = data["xgmPalette"].split(":")[-1]
        predicted_palette_name = predicted_palette_name.replace("|", "")

        for root, _, files in os.walk(data_path):
            for file in files:
                source = os.path.join(root, file).replace("\\", "/")
                destination = os.path.join(
                    instance.data["resourcesDir"],
                    "collections",
                    predicted_palette_name,
                    source.replace(data_path, "")[1:]
                )
                transfers.append((source, destination.replace("\\", "/")))

        data["transfers"] = transfers

        self.log.info(data)
        instance.data.update(data)
