# -*- coding: utf-8 -*-
"""Plugin for validating naming conventions."""
from maya import cmds

import pyblish.api

from openpype.pipeline.publish import (
    ValidateContentsOrder,
    OptionalPyblishPluginMixin,
    PublishValidationError
)


class ValidateSkeletonTopGroupHierarchy(pyblish.api.InstancePlugin,
                                        OptionalPyblishPluginMixin):
    """Validates top group hierarchy in the SETs
    Make sure the object inside the SETs are always top
    group of the hierarchy

    """
    order = ValidateContentsOrder + 0.05
    label = "Top Group Hierarchy"
    families = ["rig"]

    def process(self, instance):
        invalid = []
        skeleton_mesh_data = instance.data(("skeleton_mesh"), [])
        if skeleton_mesh_data:
            invalid = self.get_top_hierarchy(skeleton_mesh_data)
            if invalid:
                raise PublishValidationError(
                    "The skeletonMesh_SET includes the object which "
                    f"is not at the top hierarchy: {invalid}")

    def get_top_hierarchy(self, targets):
        non_top_hierarchy_list = []
        for target in targets:
            long_names = cmds.ls(target, long=True)
            for name in long_names:
                if len(name.split["|"]) > 2:
                    non_top_hierarchy_list.append(name)
        return non_top_hierarchy_list
