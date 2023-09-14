# -*- coding: utf-8 -*-
from maya import cmds  # noqa
import pyblish.api


class CollectFbxAnimation(pyblish.api.InstancePlugin):
    """Collect Unreal Skeletal Mesh."""

    order = pyblish.api.CollectorOrder + 0.2
    label = "Collect Fbx Animation"
    hosts = ["maya"]
    families = ["animation"]

    def process(self, instance):
        skeleton_sets = [
            i for i in instance
            if i.lower().endswith("skeletonanim_set")
        ]
        if skeleton_sets:
            instance.data["families"].append("animation.fbx")
            for skeleton_set in skeleton_sets:
                skeleton_content = cmds.sets(skeleton_set, query=True)
                self.log.debug(
                    "Collected animated "
                    f"skeleton data: {skeleton_content}")
                if skeleton_content:
                    instance.data["animated_skeleton"] += skeleton_content
