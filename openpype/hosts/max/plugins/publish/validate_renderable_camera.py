# -*- coding: utf-8 -*-
import pyblish.api
from openpype.pipeline import (
    PublishValidationError,
    OptionalPyblishPluginMixin)
from openpype.pipeline.publish import RepairAction
from openpype.hosts.max.api.lib import get_current_renderer

from pymxs import runtime as rt


class ValidateRenderableCamera(pyblish.api.InstancePlugin,
                               OptionalPyblishPluginMixin):
    """Validates Renderable Camera

    Check if the renderable camera used for rendering
    """

    order = pyblish.api.ValidatorOrder
    families = ["maxrender"]
    hosts = ["max"]
    label = "Renderable Camera"
    optional = True
    actions = [RepairAction]

    def process(self, instance):
        if not self.is_active(instance.data):
            return
        if not instance.data["cameras"]:
            raise PublishValidationError(
                "No renderable Camera found in scene."
            )

    @classmethod
    def repair(cls, instance):

        rt.viewport.setType(rt.Name("view_camera"))
        camera = rt.viewport.GetCamera()
        cls.log.info(f"Camera {camera} set as renderable camera")
        renderer_class = get_current_renderer()
        renderer = str(renderer_class).split(":")[0]
        if renderer == "Arnold":
            arv = rt.MAXToAOps.ArnoldRenderView()
            arv.setOption("Camera", str(camera))
            arv.close()
        instance.data["cameras"] = [camera.name]
