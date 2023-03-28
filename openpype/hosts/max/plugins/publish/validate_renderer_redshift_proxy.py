# -*- coding: utf-8 -*-
import pyblish.api
from openpype.pipeline import PublishValidationError
from pymxs import runtime as rt
from openpype.pipeline.publish import RepairAction
from openpype.hosts.max.api.lib import get_current_renderer


class ValidateRendererRedshiftProxy(pyblish.api.InstancePlugin):
    """
    Validates Redshift as the current renderer for creating
    Redshift Proxy
    """

    order = pyblish.api.ValidatorOrder
    families = ["redshiftproxy"]
    hosts = ["max"]
    label = "Redshift Renderer"
    actions = [RepairAction]

    def process(self, instance):
        invalid = self.get_all_renderer(instance)
        if invalid:
            raise PublishValidationError("Please install Redshift for 3dsMax"
                                         " before using this!")
        invalid = self.get_current_renderer(instance)
        if invalid:
            raise PublishValidationError("Current Renderer is not Redshift")

    def get_all_renderer(self, instance):
        invalid = list()
        max_renderers_list = str(rt.RendererClass.classes)
        if "Redshift_Renderer" not in max_renderers_list:
            invalid.append(max_renderers_list)

        return invalid

    def get_current_renderer(self, instance):
        invalid = list()
        renderer_class = get_current_renderer()
        current_renderer = str(renderer_class).split(":")[0]
        if current_renderer != "Redshift_Renderer":
            invalid.append(current_renderer)

        return invalid

    @classmethod
    def repair(cls, instance):
        if "Redshift_Renderer" in str(rt.RendererClass.classes[2]()):
            rt.renderers.production = rt.RendererClass.classes[2]()
