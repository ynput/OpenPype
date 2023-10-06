# -*- coding: utf-8 -*-
import pyblish.api
from openpype.pipeline import PublishValidationError
from openpype.hosts.houdini.api.action import SelectInvalidAction

import hou


class ValidateFrameRange(pyblish.api.InstancePlugin):
    """Validate Frame Range.

    Due to the usage of start and end handles,
    then Frame Range must be >= (start handle + end handle)
    which results that frameEnd be smaller than frameStart
    """

    order = pyblish.api.ValidatorOrder - 0.1
    hosts = ["houdini"]
    label = "Validate Frame Range"
    actions = [SelectInvalidAction]

    def process(self, instance):

        invalid = self.get_invalid(instance)
        if invalid:
            nodes = [n.path() for n in invalid]
            raise PublishValidationError(
                "Invalid Frame Range on: {0}".format(nodes),
                title="Invalid Frame Range"
            )

    @classmethod
    def get_invalid(cls, instance):

        if not instance.data.get("instance_node"):
            return

        rop_node = hou.node(instance.data["instance_node"])
        if instance.data["frameStart"] > instance.data["frameEnd"]:
            cls.log.error(
                "Wrong frame range, please consider handle start and end.\n"
                "frameEnd should at least be {}.\n"
                "Use \"End frame hotfix\" action to do that."
                .format(
                    instance.data["handleEnd"] +
                    instance.data["handleStart"] +
                    instance.data["frameStartHandle"]
                )
            )
            return [rop_node]
