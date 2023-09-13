# -*- coding: utf-8 -*-
import sys
import pyblish.api
import six

from openpype.pipeline import PublishValidationError


class ValidateCopOutputNode(pyblish.api.InstancePlugin):
    """Validate the instance COP Output Node.

    This will ensure:
        - The COP Path is set.
        - The COP Path refers to an existing object.
        - The COP Path node is a COP node.

    """

    order = pyblish.api.ValidatorOrder
    families = ["imagesequence"]
    hosts = ["houdini"]
    label = "Validate COP Output Node"

    def process(self, instance):

        invalid = self.get_invalid(instance)
        if invalid:
            raise PublishValidationError(
                ("Output node(s) `{}` are incorrect. "
                 "See plug-in log for details.").format(invalid),
                title=self.label
            )

    @classmethod
    def get_invalid(cls, instance):

        import hou

        try:
            output_node = instance.data["output_node"]
        except KeyError:
            six.reraise(
                PublishValidationError,
                PublishValidationError(
                    "Can't determine COP output node.",
                    title=cls.__name__),
                sys.exc_info()[2]
            )

        if output_node is None:
            node = instance.data["transientData"]["instance_node"]
            cls.log.error(
                "COP Output node in '%s' does not exist. "
                "Ensure a valid COP output path is set." % node.path()
            )

            return [node.path()]

        # Output node must be a Sop node.
        if not isinstance(output_node, hou.CopNode):
            cls.log.error(
                "Output node %s is not a COP node. "
                "COP Path must point to a COP node, "
                "instead found category type: %s"
                % (output_node.path(), output_node.type().category().name())
            )
            return [output_node.path()]

        # For the sake of completeness also assert the category type
        # is Cop2 to avoid potential edge case scenarios even though
        # the isinstance check above should be stricter than this category
        if output_node.type().category().name() != "Cop2":
            raise PublishValidationError(
                ("Output node %s is not of category Cop2. "
                 "This is a bug...").format(output_node.path()),
                title=cls.label)
