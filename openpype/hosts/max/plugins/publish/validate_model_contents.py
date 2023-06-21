# -*- coding: utf-8 -*-
import pyblish.api
from pymxs import runtime as rt

from openpype.pipeline import PublishValidationError


class ValidateModelContent(pyblish.api.InstancePlugin):
    """Validates Model instance contents.

    A model instance may only hold either geometry-related
    object(excluding Shapes) or editable meshes.
    """

    order = pyblish.api.ValidatorOrder
    families = ["model"]
    hosts = ["max"]
    label = "Model Contents"

    def process(self, instance):
        if invalid := self.get_invalid(instance):  # noqa
            raise PublishValidationError(("Model instance must only include"
                                          "Geometry and Editable Mesh. "
                                          f"Invalid types on: {invalid}"))

    def get_invalid(self, instance):
        """
        Get invalid nodes if the instance is not camera
        """
        invalid = []
        container = instance.data["instance_node"]
        self.log.info(f"Validating model content for {container}")

        selection_list = instance.data["members"]
        for sel in selection_list:
            if rt.ClassOf(sel) in rt.Camera.classes:
                invalid.append(sel)
            if rt.ClassOf(sel) in rt.Light.classes:
                invalid.append(sel)
            if rt.ClassOf(sel) in rt.Shape.classes:
                invalid.append(sel)

        return invalid
