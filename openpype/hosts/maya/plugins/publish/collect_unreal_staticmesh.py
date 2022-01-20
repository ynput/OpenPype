# -*- coding: utf-8 -*-
from maya import cmds
import pyblish.api


class CollectUnrealStaticMesh(pyblish.api.InstancePlugin):
    """Collect Unreal Static Mesh

    Ensures always only a single frame is extracted (current frame). This
    also sets correct FBX options for later extraction.

    """

    order = pyblish.api.CollectorOrder + 0.2
    label = "Collect Unreal Static Meshes"
    families = ["unrealStaticMesh"]

    def process(self, instance):
        # add fbx family to trigger fbx extractor
        instance.data["families"].append("fbx")
        # take the name from instance (without the `S_` prefix)
        instance.data["staticMeshCombinedName"] = instance.name[2:]

        geometry_set = [i for i in instance if i == "geometry_SET"]
        instance.data["membersToCombine"] = cmds.sets(
            geometry_set, query=True)

        collision_set = [i for i in instance if i == "collisions_SET"]
        instance.data["collisionMembers"] = cmds.sets(
            collision_set, query=True)

        # set fbx overrides on instance
        instance.data["smoothingGroups"] = True
        instance.data["smoothMesh"] = True
        instance.data["triangulate"] = True

        frame = cmds.currentTime(query=True)
        instance.data["frameStart"] = frame
        instance.data["frameEnd"] = frame
