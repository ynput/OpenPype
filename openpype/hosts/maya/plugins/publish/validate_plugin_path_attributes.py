import os

from maya import cmds

import pyblish.api

from openpype.pipeline.publish import (
    ValidateContentsOrder,
    PublishValidationError
)


class ValidatePluginPathAttributes(pyblish.api.InstancePlugin):
    """
    Validate plug-in path attributes point to existing file paths.
    """

    order = ValidateContentsOrder
    hosts = ['maya']
    families = ["workfile"]
    label = "Plug-in Path Attributes"

    def get_invalid(self, instance):
        invalid = list()

        # get the project setting
        validate_path = (
            instance.context.data["project_settings"]["maya"]["publish"]
        )
        file_attr = validate_path["ValidatePluginPathAttributes"]["attribute"]
        if not file_attr:
            return invalid

        # get the nodes and file attributes
        for node, attr in file_attr.items():
            # check the related nodes
            targets = cmds.ls(type=node)

            for target in targets:
                # get the filepath
                file_attr = "{}.{}".format(target, attr)
                filepath = cmds.getAttr(file_attr)

                if filepath and not os.path.exists(filepath):
                    self.log.error("File {0} not exists".format(filepath))  # noqa
                    invalid.append(target)

        return invalid

    def process(self, instance):
        """Process all directories Set as Filenames in Non-Maya Nodes"""
        invalid = self.get_invalid(instance)
        if invalid:
            raise PublishValidationError("Non-existent Path "
                               "found: {0}".format(invalid))
