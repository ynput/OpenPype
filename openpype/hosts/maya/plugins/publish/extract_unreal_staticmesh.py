# -*- coding: utf-8 -*-
"""Create Unreal Static Mesh data to be extracted as FBX."""
import openpype.api
import pyblish.api
from maya import cmds  # noqa


class ExtractUnrealStaticMesh(openpype.api.Extractor):
    """Extract FBX from Maya. """

    order = pyblish.api.ExtractorOrder - 0.1
    label = "Extract Unreal Static Mesh"
    families = ["unrealStaticMesh"]

    def process(self, instance):
        to_combine = instance.data.get("membersToCombine")
        static_mesh_name = instance.data.get("staticMeshCombinedName")
        self.log.info(
            "merging {] into {}".format(
                "+ ".join(to_combine), static_mesh_name))
        cmds.polyUnite(
            *to_combine,
            n=static_mesh_name)

        if not instance.data.get("cleanNodes"):
            instance.data["cleanNodes"] = []

        instance.data["cleanNodes"].append(static_mesh_name)
