# -*- coding: utf-8 -*-
import pyblish.api
from openpype.pipeline import PublishValidationError


class ValidateIntermediateDirectoriesChecked(pyblish.api.InstancePlugin):
    """Validate Create Intermediate Directories is enabled on ROP node."""

    order = pyblish.api.ValidatorOrder
    families = ["pointcache", "camera", "vdbcache"]
    hosts = ["houdini"]
    label = "Create Intermediate Directories Checked"

    def process(self, instance):

        invalid = self.get_invalid(instance)
        if invalid:
            raise PublishValidationError(
                ("Found ROP node with Create Intermediate "
                 "Directories turned off: {}".format(invalid)),
                title=self.label)

    @classmethod
    def get_invalid(cls, instance):

        result = []

        for node in instance[:]:
            if node.parm("mkpath").eval() != 1:
                cls.log.error("Invalid settings found on `%s`" % node.path())
                result.append(node.path())

        return result
