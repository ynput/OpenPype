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
        frame = cmds.currentTime(query=True)
        instance.data["frameStart"] = frame
        instance.data["frameEnd"] = frame

        geo_sets = [
            i for i in instance[:]
            if i.lower().startswith("geometry_set")
        ]

        joint_sets = [
            i for i in instance[:]
            if i.lower().startswith("joints_set")
        ]

        instance.data["geometry"] = []
        instance.data["joints"] = []

        for geo_set in geo_sets:
            geo_content = cmds.ls(cmds.sets(geo_set, query=True), long=True)
            if geo_content:
                instance.data["geometry"] += geo_content

        for join_set in joint_sets:
            join_content = cmds.ls(cmds.sets(join_set, query=True), long=True)
            if join_content:
                instance.data["joints"] += join_content
