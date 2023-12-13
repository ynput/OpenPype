import pyblish.api

from pymxs import runtime as rt
from openpype.pipeline import (
    OptionalPyblishPluginMixin
)
from openpype.pipeline.publish import (
    RepairAction,
    ValidateContentsOrder,
    PublishValidationError,
    KnownPublishError
)
from openpype.hosts.max.api.lib import (
    get_frame_range,
    set_timeline,
    get_operators,
    reset_frame_range_tyFlow
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
        frame_start_handle = frame_range["frameStartHandle"]
        frame_end_handle = frame_range["frameEndHandle"]

        errors = self.get_invalid(
            instance, frame_start_handle, frame_end_handle)
        if errors:
            bullet_point_errors = "\n".join(
                "- {}".format(err) for err in errors
            )
            report = (
                "Frame range settings are incorrect.\n\n"
                f"{bullet_point_errors}\n\n"
                "You can use repair action to fix it."
            )
            raise PublishValidationError(report, title="Frame Range incorrect")

    @classmethod
    def get_invalid(cls, instance, frameStart, frameEnd):
        inst_frame_start = instance.data.get("frameStartHandle")
        inst_frame_end = instance.data.get("frameEndHandle")
        if inst_frame_start is None or inst_frame_end is None:
            raise KnownPublishError(
                "Missing frame start and frame end on "
                "instance to to validate."
            )
        invalid = []
        if frameStart != inst_frame_start:
            invalid.append(
                f"Start frame ({inst_frame_start}) on instance does not match " # noqa
                f"with the start frame ({frameStart}) set on the asset data. ")    # noqa
        if frameEnd != inst_frame_end:
            invalid.append(
                f"End frame ({inst_frame_end}) on instance does not match "
                f"with the end frame ({frameEnd}) "
                "from the asset data. ")
        return invalid

    @classmethod
    def repair(cls, instance):
        frame_range = get_frame_range()
        frame_start_handle = frame_range["frameStartHandle"]
        frame_end_handle = frame_range["frameEndHandle"]

        if instance.data["family"] == "maxrender":
            rt.rendStart = frame_start_handle
            rt.rendEnd = frame_end_handle
        else:
            set_timeline(frame_start_handle, frame_end_handle)


class ValidateTyCacheFrameRange(ValidateFrameRange):
    label = "Validate Frame Range (TyCache)"
    families = ["tycache", "tyspline"]
    optional = True

    @classmethod
    def get_invalid(cls, instance, frameStart, frameEnd):
        members = instance.data["members"]
        invalid = []
        for operators in get_operators(members):
            _, inst_frame_start, inst_frame_end, opt_name = operators
            if frameStart != inst_frame_start:
                invalid.append(
                    f"Start frame ({inst_frame_start}) on {opt_name} does not match " # noqa
                    f"with the start frame ({frameStart}) set on the asset data. ")    # noqa
            if frameEnd != inst_frame_end:
                invalid.append(
                    f"End frame ({inst_frame_end}) on {opt_name} does not match "      # noqa
                    f"with the end frame ({frameEnd}) "
                    "from the asset data. ")
            return invalid

    @classmethod
    def repair(cls, instance):
        frame_range = get_frame_range()
        frame_start_handle = frame_range["frameStartHandle"]
        frame_end_handle = frame_range["frameEndHandle"]
        reset_frame_range_tyFlow(instance.data["members"],
                                 frame_start_handle,
                                 frame_end_handle)
