# -*- coding: utf-8 -*-
"""Validate custom frame range of the instances.

Check if the glob

"""

import pyblish.api

from pymxs import runtime as rt
from openpype.pipeline import (
    OptionalPyblishPluginMixin
)
from openpype.pipeline.publish import (
    RepairAction,
    ValidateContentsOrder,
    PublishValidationError
)


class ValidateCustomFrameRange(pyblish.api.InstancePlugin,
                               OptionalPyblishPluginMixin):


    label = "Validate Custom Frame Range"
    order = ValidateContentsOrder
    families = ["maxrender"]
    hosts = ["max"]
    optional = True
    actions = [RepairAction]

    def process(self, instance):
        if not self.is_active(instance.data):
            self.log.info("Skipping validation...")
            return
        context = instance.context

        attr_data = self.get_attr_values_from_data(instance.data)
        if not attr_data.get("use_custom_range"):
            self.log.info("No custom frame range set, skipping...")
            return

        # render globals
        frame_start = int(rt.rendStart)
        frame_end = int(rt.rendEnd)

        inst_frame_start = int(instance.data.get("frameStart"))
        inst_frame_end = int(instance.data.get("frameEnd"))

        errors = []
        if frame_start != inst_frame_start:
            errors.append(
                f"Start frame ({inst_frame_start}) on instance does not match " # noqa
                f"with the start frame ({frame_start}) in Render Settings. ")    # noqa
        if frame_end != inst_frame_end:
            errors.append(
                f"End frame ({inst_frame_end}) on instance does not match "
                f"with the end frame ({frame_start}) in Render Settings. ")

        if errors:
            errors.append("You can use repair action to fix it.")
            raise PublishValidationError("\n".join(errors))

    @classmethod
    def repair(cls, instance):
        rt.rendStart = instance.context.data.get("frameStart")
        rt.rendEnd = instance.context.data.get("frameEnd")
