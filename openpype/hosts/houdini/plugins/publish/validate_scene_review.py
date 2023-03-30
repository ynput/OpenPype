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
        invalid = self.get_invalid_scene_path(instance)
        if invalid:
            raise PublishValidationError(
                "Scene path does not exist: %s" % invalid,
                title=self.label)
        invalid = self.get_invalid_resolution(instance)
        if invalid:
            raise PublishValidationError(
                "Invalid Resolution Setting",
                title=self.label)

    def get_invalid_scene_path(self, instance):
        invalid = list()
        node = hou.node(instance.data.get("instance_node"))
        scene_path_node = node.parm("scenepath").evalAsNode()
        if not scene_path_node:
            invalid.append(scene_path_node)

        return invalid

    def get_invalid_resolution(self, instance):
        invalid = list()
        node = hou.node(instance.data.get("instance_node"))
        res_width = node.parm("res1").eval()
        res_height = node.parm("res2").eval()
        if res_width == 0:
            invalid.append(res_width)
        if res_height == 0:
            invalid.append(res_height)

        return invalid
