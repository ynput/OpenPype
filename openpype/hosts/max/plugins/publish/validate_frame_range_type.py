import pyblish.api

from pymxs import runtime as rt
from openpype.pipeline.publish import (
    RepairAction,
    ValidateContentsOrder,
    PublishValidationError
)


class ValidateFrameRangeType(pyblish.api.InstancePlugin):
    """
    Validates whether the User
    specified Frame Range(Type 3) is used in render setting

    """

    label = "Validate Render Frame Range Type"
    order = ValidateContentsOrder
    families = ["maxrender"]
    hosts = ["max"]
    actions = [RepairAction]

    def process(self, instance):
        if rt.rendTimeType != 3:
            raise PublishValidationError("Incorrect type of frame range"
                                         " used in render setting."
                                         " Repair action can help to fix it.")

    @classmethod
    def repair(cls, instance):
        rt.renderTimeType = 3
        return instance
