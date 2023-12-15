import os

import pyblish.api
from openpype.pipeline import PublishValidationError
from openpype.pipeline.publish import RepairAction
from openpype.hosts.fusion.api.action import SelectInvalidAction


class ValidateSaverOutputExtension(pyblish.api.InstancePlugin):
    """
    Temp docstring
    """

    order = pyblish.api.ValidatorOrder
    label = "Validate Saver Output Extension"
    families = ["render"]
    hosts = ["fusion"]
    actions = [SelectInvalidAction, RepairAction]

    @classmethod
    def get_invalid(cls, instance):
        saver = instance.data["tool"]
        output_path = saver.Clip[1]
        current_ext = get_file_extension(output_path)
        ext = instance.data["image_format"]
        if not current_ext == ext:
            return (saver, current_ext, ext)

    def process(self, instance):
        saver = instance.data["tool"]
        current_ext = get_file_extension(saver.Clip[1])
        expected_ext = instance.data["image_format"]

        if not current_ext == expected_ext:
            raise PublishValidationError(
                f"Instance {saver.Name} output image format does not match the current publish selection.\n\n"
                f"Current: {current_ext}\n\n"
                f"Expected: {expected_ext}\n\n"
                "You can use the repair action to update this instance.",
                title=self.label,
            )

    @classmethod
    def repair(cls, instance):
        saver = instance.data["tool"]
        output_path = saver.Clip[1]
        ext = get_file_extension(output_path)
        output_path = output_path.replace(
            f".{ext}", f".{instance.data['image_format']}"
        )
        saver.SetData(
            "openpype.creator_attributes.image_format",
            instance.data["image_format"],
        )
        saver.Clip[1] = output_path


def get_file_extension(full_path):
    return os.path.splitext(full_path)[1].replace(".", "")
