# -*- coding: utf-8 -*-
import pyblish.api
from openpype.pipeline import PublishValidationError
import hou


class ValidateSceneReview(pyblish.api.InstancePlugin):
    """Validator Some Scene Settings before publishing the review
        1. Scene Path
        2. Resolution
    """

    order = pyblish.api.ValidatorOrder
    families = ["review"]
    hosts = ["houdini"]
    label = "Scene Setting for review"

    def process(self, instance):

        report = []
        instance_node = instance.data["transientData"]["instance_node"]

        invalid = self.get_invalid_scene_path(instance_node)
        if invalid:
            report.append(invalid)

        invalid = self.get_invalid_camera_path(instance_node)
        if invalid:
            report.append(invalid)

        invalid = self.get_invalid_resolution(instance_node)
        if invalid:
            report.extend(invalid)

        if report:
            raise PublishValidationError(
                "\n\n".join(report),
                title=self.label)

    def get_invalid_scene_path(self, rop_node):
        scene_path_parm = rop_node.parm("scenepath")
        scene_path_node = scene_path_parm.evalAsNode()
        if not scene_path_node:
            path = scene_path_parm.evalAsString()
            return "Scene path does not exist: '{}'".format(path)

    def get_invalid_camera_path(self, rop_node):
        camera_path_parm = rop_node.parm("camera")
        camera_node = camera_path_parm.evalAsNode()
        path = camera_path_parm.evalAsString()
        if not camera_node:
            return "Camera path does not exist: '{}'".format(path)
        type_name = camera_node.type().name()
        if type_name != "cam":
            return "Camera path is not a camera: '{}' (type: {})".format(
                path, type_name
            )

    def get_invalid_resolution(self, rop_node):

        # The resolution setting is only used when Override Camera Resolution
        # is enabled. So we skip validation if it is disabled.
        override = rop_node.parm("tres").eval()
        if not override:
            return

        invalid = []
        res_width = rop_node.parm("res1").eval()
        res_height = rop_node.parm("res2").eval()
        if res_width == 0:
            invalid.append("Override Resolution width is set to zero.")
        if res_height == 0:
            invalid.append("Override Resolution height is set to zero")

        return invalid
