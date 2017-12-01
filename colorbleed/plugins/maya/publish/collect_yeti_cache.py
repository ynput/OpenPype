from maya import cmds

import pyblish.api

from colorbleed.maya import lib

SETTINGS = {"renderDensity",
            "renderWidth",
            "renderLength",
            "increaseRenderBounds",
            "cbId"}


class CollectYetiCache(pyblish.api.InstancePlugin):
    """Collect all information of the Yeti caches"""

    order = pyblish.api.CollectorOrder + 0.45
    label = "Collect Yeti Cache"
    families = ["colorbleed.yetiRig", "colorbleed.yeticache"]
    hosts = ["maya"]
    tasks = ["animation", "fx"]

    def process(self, instance):

        # Collect fur settings
        settings = {"nodes": []}

        # Get yeti nodes and their transforms
        yeti_shapes = cmds.ls(instance, type="pgYetiMaya")

        for shape in yeti_shapes:
            shape_data = {"transform": None,
                          "name": shape}

            # Get specific node attributes
            for attr in SETTINGS:
                current = cmds.getAttr("%s.%s" % (shape, attr))
                shape_data[attr] = current

            # Get transform data
            parent = cmds.listRelatives(shape, parent=True)[0]
            transform_data = {"name": parent,
                              "cbId": lib.get_id(parent)}

            # Store transform data
            shape_data["transform"] = transform_data

            settings["nodes"].append(shape_data)

        instance.data["fursettings"] = settings
