# -*- coding: utf-8 -*-
import pyblish.api
from openpype.pipeline import (
    PublishValidationError,
    OptionalPyblishPluginMixin)
from openpype.pipeline.publish import RepairAction
from openpype.hosts.max.api.lib import get_current_renderer

from pymxs import runtime as rt


class ValidateViewportCamera(pyblish.api.InstancePlugin,
                             OptionalPyblishPluginMixin):
    """Validates Viewport Camera

    Check if the renderable camera in scene used as viewport
    camera for rendering
    """

    order = pyblish.api.ValidatorOrder
    families = ["maxrender"]
    hosts = ["max"]
    label = "Viewport Camera"
    optional = True
    actions = [RepairAction]

    def process(self, instance):
        if not self.is_active(instance.data):
            return
        cameras_in_scene = [c for c in rt.Objects
                            if rt.classOf(c) in rt.Camera.Classes]
        if rt.viewport.getCamera() not in cameras_in_scene:
            raise PublishValidationError(
                "Cameras in Scene not used as viewport camera"
            )

    @classmethod
    def repair(cls, instance):

        rt.viewport.setType(rt.Name("view_camera"))
        camera = rt.viewport.GetCamera()
        cls.log.info(f"Camera {camera} set as viewport camera")
        renderer_class = get_current_renderer()
        renderer = str(renderer_class).split(":")[0]
        if renderer == "Arnold":
            arv = rt.MAXToAOps.ArnoldRenderView()
            arv.setOption("Camera", str(camera))
            arv.close()
