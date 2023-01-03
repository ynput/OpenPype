import os

from maya import cmds

import pyblish.api

from openpype.pipeline.publish import ValidateContentsOrder


class ValidatePathForPlugin(pyblish.api.InstancePlugin):
    """
    Ensure Paths in Non-Maya Nodes(from plugins
    such as Yeti, AbcExport) are correct
    """

    order = ValidateContentsOrder
    hosts = ['maya']
    families = ["workfile"]
    label = "Non-existent Paths in Non-Maya Nodes"
    optional = True

    def get_invalid(self, instance):
        invalid = list()

        # get the project setting
        validate_path = (
            instance.context.data["project_settings"]["maya"]["publish"]
        )
        file_attr = validate_path["ValidatePathForPlugin"]
        if file_attr:
            # get the nodes and file attributes
            for node, attr in file_attr.items():
                # check the related nodes
                targets = cmds.ls(type=node)
                path_attr = ".{0}".format(attr)

                if targets:
                    for target in targets:
                        # get the filepath
                        filepath = cmds.getAttr(target + path_attr)
                        if filepath and not os.path.exists(filepath):
                            invalid.append(target)

        return invalid

    def process(self, instance):
        """Process all directories Set as Filenames in Non-Maya Nodes"""
        invalid = self.get_invalid(instance)
        if invalid:
            raise RuntimeError("Non-existent Path "
                               "found: {0}".format(invalid))
