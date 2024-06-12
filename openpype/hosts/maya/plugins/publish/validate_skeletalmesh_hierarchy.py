# -*- coding: utf-8 -*-
import pyblish.api

from openpype.pipeline.publish import (
    ValidateContentsOrder,
    PublishXmlValidationError,
    OptionalPyblishPluginMixin
)

from maya import cmds


class ValidateSkeletalMeshHierarchy(pyblish.api.InstancePlugin,
                                    OptionalPyblishPluginMixin):
    """Validates that nodes has common root."""

    order = ValidateContentsOrder
    hosts = ["maya"]
    families = ["skeletalMesh"]
    label = "Skeletal Mesh Top Node"
    optional = False

    def process(self, instance):
        if not self.is_active(instance.data):
            return
        geo = instance.data.get("geometry")
        joints = instance.data.get("joints")

        joints_parents = cmds.ls(joints, long=True)
        geo_parents = cmds.ls(geo, long=True)

        parents_set = {
            parent.split("|")[1] for parent in (joints_parents + geo_parents)
        }

        self.log.debug(parents_set)

        if len(set(parents_set)) > 2:
            raise PublishXmlValidationError(
                self,
                "Multiple roots on geometry or joints."
            )
