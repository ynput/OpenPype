# -*- coding: utf-8 -*-
import pyblish.api
from openpype.pipeline import PublishValidationError
from pymxs import runtime as rt


class ValidateMaxContents(pyblish.api.InstancePlugin):
    """Validates Max contents.

    Check if MaxScene container includes any contents underneath.
    """

    order = pyblish.api.ValidatorOrder
    families = ["camera",
                "maxScene",
                "maxrender"]
    hosts = ["max"]
    label = "Max Scene Contents"

    def process(self, instance):
        container = rt.getNodeByName(instance.data["instance_node"])
        if not list(container.Children):
            raise PublishValidationError("No content found in the container")
