import pyblish.api

from openpype.pipeline.publish import (
    OptionalPyblishPluginMixin,
    ValidateContentsOrder,
    PublishValidationError
)


class ValidateShotsContinuous(
    pyblish.api.InstancePlugin, OptionalPyblishPluginMixin
):
    """Ensure shots are continous without gaps."""

    order = ValidateContentsOrder
    label = "Shots Continuous"
    hosts = ["maya"]
    families = ["shot"]
    optional = True

    def process(self, instance):
        if not self.is_active(instance.data):
            return

        msg = "No shot is up against {} of {} at frame {}"
        time_ranges = instance.context.data["shotsTimeRanges"]

        start = instance.data["range"][0] - 1
        if start not in time_ranges:
            raise PublishValidationError(
                message=msg.format("start", instance, start),
                description=(
                    "## Publishing continous shots.\n"
                    "There are gaps between some shots."
                )
            )

        stop = instance.data["range"][1] + 1
        if stop not in time_ranges:
            raise PublishValidationError(
                message=msg.format("end", instance, stop),
                description=(
                    "## Publishing continous shots.\n"
                    "There are gaps between some shots."
                )
            )
