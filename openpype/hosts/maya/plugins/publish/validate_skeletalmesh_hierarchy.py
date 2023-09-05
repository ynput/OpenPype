# -*- coding: utf-8 -*-
import pyblish.api
from maya import cmds

from openpype.pipeline.publish import (
    OptionalPyblishPluginMixin,
    PublishXmlValidationError,
    ValidateContentsOrder,
)


class ValidateSkeletalMeshHierarchy(pyblish.api.InstancePlugin,
                                    OptionalPyblishPluginMixin):
    """Validates that nodes has common root."""

    order = ValidateContentsOrder
    hosts = ["maya"]
    families = ["skeletalMesh"]
    label = "Skeletal Mesh Top Node"

    def process(self, instance):
        geo = instance.data.get("geometry")
        joints = instance.data.get("joints")

        joints_parents = cmds.ls(joints, long=True)
        geo_parents = cmds.ls(geo, long=True)

        parents_set = {
            parent.split("|")[1] for parent in (joints_parents + geo_parents)
        }

        self.log.info(parents_set)

        if len(set(parents_set)) > 2:
            raise PublishXmlValidationError(
                self,
                "Multiple roots on geometry or joints."
            )
