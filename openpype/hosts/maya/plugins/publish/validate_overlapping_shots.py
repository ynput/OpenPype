import pyblish.api

from openpype.pipeline.publish import (
    OptionalPyblishPluginMixin,
    ValidateContentsOrder,
    PublishValidationError
)


class ValidateOverlappingShots(
    pyblish.api.InstancePlugin, OptionalPyblishPluginMixin
):
    """Ensure shots are not overlapping."""

    order = ValidateContentsOrder
    label = "Overlapping shots"
    hosts = ["maya"]
    families = ["shot"]
    optional = True

    def process(self, instance):
        if not self.is_active(instance.data):
            return

        for inst in instance.context:
            families = inst.data["families"] + [inst.data["family"]]
            if "shot" not in families:
                continue

            if instance == inst:
                continue

            msg = "{} ({}-{}) {} frame is within {} ({}-{})"
            if (inst.data["range"][0] <
               instance.data["range"][0] <
               inst.data["range"][1]):
                raise PublishValidationError(
                    message=(
                        msg.format(
                            instance,
                            instance.data["range"][0],
                            instance.data["range"][1],
                            "start",
                            inst,
                            inst.data["range"][0],
                            inst.data["range"][1]
                        )
                    ),
                    description=(
                        "## Publishing overlapping shots.\n"
                        "There are shots that have ranges within other shots."
                        " In most cases this is not desirable. If required, "
                        "this validation can be turned off on the instance."
                    )
                )

            if (inst.data["range"][0] <
               instance.data["range"][1] <
               inst.data["range"][1]):
                raise PublishValidationError(
                    message=(
                        msg.format(
                            instance,
                            instance.data["range"][0],
                            instance.data["range"][1],
                            "stop",
                            inst,
                            inst.data["range"][0],
                            inst.data["range"][1]
                        )
                    ),
                    description=(
                        "## Publishing overlapping shots.\n"
                        "There are shots that have ranges within other shots."
                        " In most cases this is not desirable. If required, "
                        "this validation can be turned off on the instance."
                    )
                )
