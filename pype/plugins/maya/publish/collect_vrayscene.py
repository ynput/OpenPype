# -*- coding: utf-8 -*-
"""Collect Vray Scene and prepare it for extraction and publishing."""
import os
from maya import cmds

import pyblish.api


class CollectVrayScene(pyblish.api.InstancePlugin):
    """Collect Vray Scene.

    If export on farm is checked, job is created to export it.
    """

    order = pyblish.api.CollectorOrder + 0.2
    label = "Collect Model Data"
    families = ["vrayscene"]

    def process(self, instance):
        """Collector entry point."""
        if instance.data.get("exportOnFarm"):
            filepath = instance.context.data["currentFile"].replace("\\", "/")
            workspace = instance.context.data["workspaceDir"]
            scene, _ = os.path.splitext(filepath)
            instance.data["families"].append("renderlayer")
            instance.data["renderer"] = "vrayExport"
            instance.data["review"] = False
            instance.data["source"] = filepath
            instance.data["VRayExportFile"] = os.path.join(
                workspace, "vrscene", scene, "{}.vrscene".format(scene))
            instance.data["expectedFiles"] = ""
