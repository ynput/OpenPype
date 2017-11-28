import os
import glob
import re

from maya import cmds

import pyblish.api
from avalon import api

from colorbleed.maya import lib


SETTINGS = {"renderDensity",
            "renderWidth",
            "renderLength",
            "increaseRenderBounds",
            "cbId"}


class CollectYetiCache(pyblish.api.InstancePlugin):
    """Collect all information of the Yeti caches"""

    order = pyblish.api.CollectorOrder + 0.4
    label = "Collect Yeti Cache"
    families = ["colorbleed.yetiRig", "colorbleed.yeticache"]
    hosts = ["maya"]
    tasks = ["animation", "fx"]

    def process(self, instance):

        # Collect animation data
        animation_data = lib.collect_animation_data()
        instance.data.update(animation_data)

        # We only want one frame to export if it is not animation
        if api.Session["AVALON_TASK"] not in self.tasks:
            instance.data["startFrame"] = 1
            instance.data["endFrame"] = 1

        # Collect any textures if used
        node_attrs = {}
        for node in cmds.ls(instance.data["setMembers"], type="pgYetiMaya"):
            # Get Yeti resources (textures)
            for attr in SETTINGS:
                node_attr = "%s.%s" % (node, attr)
                current = cmds.getAttr(node_attr)
                node_attrs[node_attr] = current

        instance.data["settings"] = node_attrs
