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
from openpype.hosts.max.api.lib import get_frame_range, set_timeline


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
    families = ["camera", "maxrender",
                "pointcache", "pointcloud",
                "review", "redshiftproxy"]
    hosts = ["max"]
    optional = True
    actions = [RepairAction]

    def process(self, instance):
        if not self.is_active(instance.data):
            self.log.debug("Skipping Validate Frame Range...")
            return

        frame_range = get_frame_range(
            asset_doc=instance.data["assetEntity"])

        inst_frame_start = instance.data.get("frameStart")
        inst_frame_end = instance.data.get("frameEnd")
        frame_start_handle = frame_range["frameStart"] - int(
            frame_range["handleStart"]
        )
        frame_end_handle = frame_range["frameEnd"] + int(
            frame_range["handleEnd"]
        )
        errors = []
        if frame_start_handle != inst_frame_start:
            errors.append(
                f"Start frame ({inst_frame_start}) on instance does not match " # noqa
                f"with the start frame ({frame_start_handle}) set on the asset data. ")    # noqa
        if frame_end_handle != inst_frame_end:
            errors.append(
                f"End frame ({inst_frame_end}) on instance does not match "
                f"with the end frame ({frame_end_handle}) "
                "from the asset data. ")

        if errors:
            errors.append("You can use repair action to fix it.")
            report = "Frame range settings are incorrect.\n\n"
            for error in errors:
                report += "- {}\n\n".format(error)
            raise PublishValidationError(report, title="Frame Range incorrect")

    @classmethod
    def repair(cls, instance):
        frame_range = get_frame_range()
        frame_start_handle = frame_range["frameStart"] - int(
            frame_range["handleStart"]
        )
        frame_end_handle = frame_range["frameEnd"] + int(
            frame_range["handleEnd"]
        )
        if instance.data["family"] == "maxrender":
            rt.rendStart = frame_start_handle
            rt.rendEnd = frame_end_handle
        else:
            set_timeline(frame_start_handle, frame_end_handle)
