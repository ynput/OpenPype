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
        frame = cmds.currentTime(query=True)
        instance.data["frameStart"] = frame
        instance.data["frameEnd"] = frame
        skeleton_sets = [
            i for i in instance
            if i.lower().endswith("skeletonanim_set")
        ]

        skeleton_mesh_sets = [
            i for i in instance
            if i.lower().endswith("skeletonmesh_set")
        ]
        if not skeleton_sets and skeleton_mesh_sets:
            self.log.debug(
                "no skeleton_set or skeleton_mesh set was found....")
            return
        instance.data["skeleton_mesh"] = []
        instance.data["skeleton_rig"] = []

        if skeleton_mesh_sets:
            instance.data["families"] += ["rig.fbx"]
            for skeleton_mesh_set in skeleton_mesh_sets:
                skeleton_mesh_content = cmds.sets(
                    skeleton_mesh_set, query=True)
                if skeleton_mesh_content:
                    instance.data["skeleton_mesh"] += skeleton_mesh_content
                    self.log.debug(
                        "Collected skeleton "
                        f"mesh Set: {skeleton_mesh_content}")

        if skeleton_sets:
            for skeleton_set in skeleton_sets:
                skeleton_content = cmds.sets(skeleton_set, query=True)
                self.log.debug(
                    "Collected animated "
                    f"skeleton data: {skeleton_content}")
                if skeleton_content:
                    instance.data["skeleton_rig"] += skeleton_content
