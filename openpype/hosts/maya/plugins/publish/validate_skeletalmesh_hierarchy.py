# -*- coding: utf-8 -*-
import pyblish.api
import openpype.api
from openpype.pipeline import PublishXmlValidationError

from maya import cmds


class ValidateSkeletalMeshHierarchy(pyblish.api.InstancePlugin):
    """Adheres to the content of 'model' family

    - Must have one top group. (configurable)
    - Must only contain: transforms, meshes and groups

    """

    order = openpype.api.ValidateContentsOrder
    hosts = ["maya"]
    families = ["skeletalMesh"]
    label = "Skeletal Mesh Top Node"

    def process(self, instance):
        geo = instance.data.get("geometry")
        joints = instance.data.get("joints")
        # joints_parents = cmds.ls(joints, long=True)[0].split("|")[1:-1]
        # geo_parents = cmds.ls(geo, long=True)[0].split("|")[1:-1]

        joints_parents = cmds.ls(joints, long=True)
        geo_parents = cmds.ls(geo, long=True)

        parents_set = {
            parent.split("|")[1] for parent in (joints_parents + geo_parents)
        }

        if len(set(parents_set)) != 1:
            raise PublishXmlValidationError(
                self,
                "Multiple roots on geometry or joints."
            )
