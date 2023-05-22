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


class ValidateFrameRange(pyblish.api.InstancePlugin,
                         OptionalPyblishPluginMixin):
    """Validates the frame ranges.

    This is an optional validator checking if the frame range on instance
    matches the frame range specified for the asset.

    It also validates render frame ranges of render layers.

    Repair action will change everything to match the asset frame range.

    This can be turned off by the artist to allow custom ranges.
    """

    label = "Validate Frame Range"
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

        frame_start = int(context.data.get("frameStart"))
        frame_end = int(context.data.get("frameEnd"))

        inst_frame_start = int(instance.data.get("frameStart"))
        inst_frame_end = int(instance.data.get("frameEnd"))

        errors = []
        if frame_start != inst_frame_start:
            errors.append(
                f"Start frame ({inst_frame_start}) on instance does not match " # noqa
                f"with the start frame ({frame_start}) set on the asset data. ")    # noqa
        if frame_end != inst_frame_end:
            errors.append(
                f"End frame ({inst_frame_end}) on instance does not match "
                f"with the end frame ({frame_start}) from the asset data. ")

        if errors:
            errors.append("You can use repair action to fix it.")
            raise PublishValidationError("\n".join(errors))

    @classmethod
    def repair(cls, instance):
        rt.rendStart = instance.context.data.get("frameStart")
        rt.rendEnd = instance.context.data.get("frameEnd")
