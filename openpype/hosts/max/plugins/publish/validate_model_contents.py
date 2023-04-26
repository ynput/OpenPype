# -*- coding: utf-8 -*-
import pyblish.api
from openpype.pipeline import PublishValidationError
from pymxs import runtime as rt


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
        invalid = self.get_invalid(instance)
        if invalid:
            raise PublishValidationError("Model instance must only include"
                                         "Geometry and Editable Mesh")

    def get_invalid(self, instance):
        """
        Get invalid nodes if the instance is not camera
        """
        invalid = list()
        container = instance.data["instance_node"]
        self.log.info("Validating look content for "
                      "{}".format(container))

        con = rt.getNodeByName(container)
        selection_list = list(con.Children) or rt.getCurrentSelection()
        for sel in selection_list:
            if rt.classOf(sel) in rt.Camera.classes:
                invalid.append(sel)
            if rt.classOf(sel) in rt.Light.classes:
                invalid.append(sel)
            if rt.classOf(sel) in rt.Shape.classes:
                invalid.append(sel)

        return invalid
