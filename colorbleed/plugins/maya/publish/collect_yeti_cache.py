from maya import cmds

import pyblish.api


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
        settings = {}
        for node in cmds.ls(instance, type="pgYetiMaya"):
            settings[node] = {}
            for attr in SETTINGS:
                current = cmds.getAttr("%s.%s" % (node, attr))
                settings[node][attr] = current

        instance.data["fursettings"] = settings
