import os

from maya import cmds

import pyblish.api

from openpype.hosts.maya.api.lib import pairwise
from openpype.hosts.maya.api.action import SelectInvalidAction
from openpype.pipeline.publish import (
    ValidateContentsOrder,
    PublishValidationError,
    OptionalPyblishPluginMixin
)


class ValidatePluginPathAttributes(pyblish.api.InstancePlugin,
                                   OptionalPyblishPluginMixin):
    """
    Validate plug-in path attributes point to existing file paths.
    """

    order = ValidateContentsOrder
    hosts = ['maya']
    families = ["workfile"]
    label = "Plug-in Path Attributes"
    actions = [SelectInvalidAction]
    optional = False

    # Attributes are defined in project settings
    attribute = []

    @classmethod
    def get_invalid(cls, instance):
        invalid = list()

        file_attrs = cls.attribute
        if not file_attrs:
            return invalid

        # Consider only valid node types to avoid "Unknown object type" warning
        all_node_types = set(cmds.allNodeTypes())
        node_types = [
            key for key in file_attrs.keys()
            if key in all_node_types
        ]

        for node, node_type in pairwise(cmds.ls(type=node_types,
                                                showType=True)):
            # get the filepath
            file_attr = "{}.{}".format(node, file_attrs[node_type])
            filepath = cmds.getAttr(file_attr)

            if filepath and not os.path.exists(filepath):
                cls.log.error("{} '{}' uses non-existing filepath: {}"
                              .format(node_type, node, filepath))
                invalid.append(node)

        return invalid

    def process(self, instance):
        """Process all directories Set as Filenames in Non-Maya Nodes"""
        if not self.is_active(instance.data):
            return
        invalid = self.get_invalid(instance)
        if invalid:
            raise PublishValidationError(
                title="Plug-in Path Attributes",
                message="Non-existent filepath found on nodes: {}".format(
                    ", ".join(invalid)
                ),
                description=(
                    "## Plug-in nodes use invalid filepaths\n"
                    "The workfile contains nodes from plug-ins that use "
                    "filepaths which do not exist.\n\n"
                    "Please make sure their filepaths are correct and the "
                    "files exist on disk."
                )
            )
