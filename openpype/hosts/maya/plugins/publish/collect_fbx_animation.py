# -*- coding: utf-8 -*-
from maya import cmds  # noqa
import pyblish.api


class CollectFbxAnimation(pyblish.api.InstancePlugin):
    """Collect Unreal Skeletal Mesh."""

    order = pyblish.api.CollectorOrder + 0.2
    label = "Collect Fbx Animation"
    families = ["rig"]

    def process(self, instance):
        frame = cmds.currentTime(query=True)
        instance.data["frameStart"] = frame
        instance.data["frameEnd"] = frame

        skeleton_sets = [
            i for i in instance[:]
            if i.lower().endswith("skeletonanim_set")
        ]
        if skeleton_sets:
            instance.data["families"].append("rig.fbx")
            for skeleton_set in skeleton_sets:
                skeleton_content = cmds.ls(
                    cmds.sets(skeleton_set, query=True), long=True)
                if skeleton_content:
                    instance.data["animated_skeleton"] += skeleton_content
