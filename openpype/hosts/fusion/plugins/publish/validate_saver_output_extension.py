import os
import pyblish.api
from openpype.pipeline import (
    PublishValidationError,
    OptionalPyblishPluginMixin,
)
from openpype.pipeline.publish import RepairAction
from openpype.hosts.fusion.api.action import SelectInvalidAction


class ValidateSaverOutputExtension(
    pyblish.api.InstancePlugin, OptionalPyblishPluginMixin
):
    """
    Validate Saver Output Extension matches Publish menu

    This ensures that if the user tweaks the 'Output File Extension' in the publish menu,
    it is respected during the publish.
    """

    order = pyblish.api.ValidatorOrder
    label = "Validate Saver Output Extension"
    families = ["render"]
    hosts = ["fusion"]
    optional = True
    actions = [SelectInvalidAction, RepairAction]

    def process(self, instance):
        saver = instance.data["tool"]
        current_extension = get_file_extension(saver.Clip[1])
        expected_extension = instance.data["image_format"]

        if current_extension != expected_extension:
            raise PublishValidationError(
                f"Instance {saver.Name} output image format does not match the current publish selection.\n\n"
                f"Current: {current_extension}\n\n"
                f"Expected: {expected_extension}\n\n"
                "You can use the repair action to update this instance.",
                title=self.label,
            )

    @classmethod
    def repair(cls, instance):
        saver = instance.data["tool"]
        output_path = saver.Clip[1]

        root, old_extension = os.path.splitext(output_path)
        new_extension = instance.data["image_format"]

        new_output_path = f"{root}.{new_extension}"
        saver.Clip[1] = new_output_path

        saver.SetData(
            "openpype.creator_attributes.image_format",
            instance.data["image_format"],
        )


def get_file_extension(full_path):
    return os.path.splitext(full_path)[1].lstrip(".")
