# -*- coding: utf-8 -*-
"""Create Unreal Static Mesh data to be extracted as FBX."""
import openpype.api
import pyblish.api
from maya import cmds  # noqa
from uuid import uuid4


class ExtractUnrealStaticMesh(openpype.api.Extractor):
    """Extract FBX from Maya. """

    order = pyblish.api.ExtractorOrder - 0.1
    label = "Extract Unreal Static Mesh"
    families = ["unrealStaticMesh"]

    def process(self, instance):
        to_combine = instance.data.get("membersToCombine")
        static_mesh_name = instance.data.get("staticMeshCombinedName")
        self.log.info(
            "merging {} into {}".format(
                " + ".join(to_combine), static_mesh_name))
        duplicates = cmds.duplicate(to_combine, ic=True)
        cmds.polyUnite(
            *duplicates,
            n=static_mesh_name, ch=False)

        collision_duplicates = cmds.duplicate(
            instance.data.get("collisionMembers"), ic=True)
        cmds.parent(collision_duplicates, a=True, w=True)
        instance.data["collisionMembers"] = collision_duplicates

        self.log.info(
            "collision members: {}".format(instance.data["collisionMembers"]))

        if not instance.data.get("cleanNodes"):
            instance.data["cleanNodes"] = []

        instance.data["cleanNodes"].append(static_mesh_name)
        instance.data["cleanNodes"] += duplicates
        instance.data["cleanNodes"] += collision_duplicates

        instance.data["setMembers"] = [static_mesh_name]
        instance.data["setMembers"] += instance.data["collisionMembers"]
