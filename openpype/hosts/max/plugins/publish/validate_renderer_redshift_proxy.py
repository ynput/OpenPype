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
        invalid = self.get_redshift_renderer(instance)
        if invalid:
            raise PublishValidationError("Please install Redshift for 3dsMax"
                                         " before using the Redshift proxy instance")   # noqa
        invalid = self.get_current_renderer(instance)
        if invalid:
            raise PublishValidationError("The Redshift proxy extraction"
                                         "discontinued since the current renderer is not Redshift")  # noqa

    def get_redshift_renderer(self, instance):
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
        for Renderer in rt.RendererClass.classes:
            renderer = Renderer()
            if "Redshift_Renderer" in str(renderer):
                rt.renderers.production = renderer
                break
