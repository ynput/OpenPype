# -*- coding: utf-8 -*-
from maya import cmds  # noqa
import pyblish.api


class CollectSkeletonMesh(pyblish.api.InstancePlugin):
    """Collect Static Rig Data for FBX Extractor."""

    order = pyblish.api.CollectorOrder + 0.2
    label = "Collect Skeleton Mesh"
    hosts = ["maya"]
    families = ["rig"]

    def process(self, instance):
        skeleton_mesh_set = instance.data["rig_sets"].get(
            "skeletonMesh_SET")
        if not skeleton_mesh_set:
            self.log.debug(
                "No skeletonMesh_SET found. "
                "Skipping collecting of skeleton mesh..."
            )
            return

        # Store current frame to ensure single frame export
        frame = cmds.currentTime(query=True)
        instance.data["frameStart"] = frame
        instance.data["frameEnd"] = frame

        instance.data["skeleton_mesh"] = []

        skeleton_mesh_content = cmds.sets(
            skeleton_mesh_set, query=True) or []
        if not skeleton_mesh_content:
            self.log.debug(
                "No object nodes in skeletonMesh_SET. "
                "Skipping collecting of skeleton mesh..."
            )
            return
        instance.data["families"] += ["rig.fbx"]
        instance.data["skeleton_mesh"] = skeleton_mesh_content
        self.log.debug(
            "Collected skeletonMesh_SET members: {}".format(
                skeleton_mesh_content
            ))
