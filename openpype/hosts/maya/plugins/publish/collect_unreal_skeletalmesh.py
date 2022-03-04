# -*- coding: utf-8 -*-
from maya import cmds  # noqa
import pyblish.api
from avalon.api import Session
from openpype.api import get_project_settings


class CollectUnrealSkeletalMesh(pyblish.api.InstancePlugin):
    """Collect Unreal Skeletal Mesh."""

    order = pyblish.api.CollectorOrder + 0.2
    label = "Collect Unreal Skeletal Meshes"
    families = ["skeletalMesh"]

    def process(self, instance):
        # set fbx overrides on instance
        instance.data["smoothingGroups"] = True
        instance.data["smoothMesh"] = True
        instance.data["triangulate"] = True

        frame = cmds.currentTime(query=True)
        instance.data["frameStart"] = frame
        instance.data["frameEnd"] = frame
