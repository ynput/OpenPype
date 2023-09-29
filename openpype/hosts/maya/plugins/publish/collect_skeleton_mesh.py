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
        skeleton_mesh_sets = instance.data.get("skeletonMesh_SET")
        if not skeleton_mesh_sets:
            self.log.debug(
                "skeletonMesh_SET found. "
                "Skipping collecting of skeleton mesh..."
            )
            return

        # Store current frame to ensure single frame export
        frame = cmds.currentTime(query=True)
        instance.data["frameStart"] = frame
        instance.data["frameEnd"] = frame

        instance.data["skeleton_mesh"] = []

        if skeleton_mesh_sets:
            instance.data["families"] += ["rig.fbx"]
            for skeleton_mesh_set in skeleton_mesh_sets:
                skeleton_mesh_content = cmds.sets(
                    skeleton_mesh_set, query=True)
                if skeleton_mesh_content:
                    instance.data["skeleton_mesh"] += skeleton_mesh_content
                    self.log.debug(
                        "Collected skeletonmesh Set: {}".format(
                            skeleton_mesh_content
                        ))
