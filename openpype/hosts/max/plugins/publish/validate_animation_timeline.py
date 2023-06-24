import pyblish.api

from pymxs import runtime as rt
from openpype.pipeline.publish import (
    RepairAction,
    ValidateContentsOrder,
    PublishValidationError
)
from openpype.hosts.max.api.lib import get_frame_range, set_timeline


class ValidateAnimationTimeline(pyblish.api.InstancePlugin):
    """
    Validates Animation Timeline for Preview Animation in Max
    """

    label = "Animation Timeline for Review"
    order = ValidateContentsOrder
    families = ["review"]
    hosts = ["max"]
    actions = [RepairAction]

    def process(self, instance):
        frame_range = get_frame_range()
        frame_start_handle = frame_range["frameStart"] - int(
            frame_range["handleStart"]
        )
        frame_end_handle = frame_range["frameEnd"] + int(
            frame_range["handleEnd"]
        )
        if rt.animationRange != rt.interval(frame_start_handle,
                                            frame_end_handle):
            raise PublishValidationError("Incorrect animation timeline"
                                         "set for preview animation.. "
                                         "\nYou can use repair action to "
                                         "the correct animation timeline")

    @classmethod
    def repair(cls, instance):
        frame_range = get_frame_range()
        frame_start_handle = frame_range["frameStart"] - int(
            frame_range["handleStart"]
        )
        frame_end_handle = frame_range["frameEnd"] + int(
            frame_range["handleEnd"]
        )
        set_timeline(frame_start_handle, frame_end_handle)
