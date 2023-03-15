# -*- coding: utf-8 -*-
import pyblish.api
from openpype.pipeline import PublishValidationError
from pymxs import runtime as rt


class ValidateMaxContents(pyblish.api.InstancePlugin):
    """Validates Max contents.

    Check if MaxScene container includes any contents underneath.
    """

    order = pyblish.api.ValidatorOrder
    families = ["maxScene"]
    hosts = ["max"]
    label = "Max Scene Contents"

    def process(self, instance):
        invalid = self.get_invalid(instance)
        if invalid:
            raise PublishValidationError("No content found in the container")

    def get_invalid(self, instance):
        invalid = []
        container = rt.getNodeByName(instance.data["instance_node"])
        if not container.Children:
            invalid.append(container)

        return invalid
