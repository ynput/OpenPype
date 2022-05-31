# -*- coding: utf-8 -*-
from maya import cmds  # noqa
import pyblish.api


class CollectFbxCamera(pyblish.api.InstancePlugin):
    """Collect Camera for FBX export."""

    order = pyblish.api.CollectorOrder + 0.2
    label = "Collect Camera for FBX export"
    families = ["camera"]

    def process(self, instance):
        if not instance.data.get("families"):
            instance.data["families"] = []

        if "fbx" not in instance.data["families"]:
            instance.data["families"].append("fbx")

        instance.data["cameras"] = True
