import os
import pyblish.api

from openpype.pipeline.publish import RepairAction
from openpype.pipeline import PublishValidationError

from openpype.hosts.fusion.api.action import SelectInvalidAction


class ValidateLocalFramesExistence(pyblish.api.InstancePlugin):
    """Checks if files for savers that's set to publish existing frames exists"""

    order = pyblish.api.ValidatorOrder
    label = "Validate Existing Frames Exists"
    families = ["render"]
    hosts = ["fusion"]
    actions = [RepairAction, SelectInvalidAction]

    @classmethod
    def get_invalid(cls, instance):
        active = instance.data.get("active", instance.data.get("publish"))
        if not active:
            return []

        if instance.data.get("render_target") == "frames":
            tool = instance[0]

            frame_start = instance.data["frameStart"]
            frame_end = instance.data["frameEnd"]
            path = instance.data["path"]
            output_dir = instance.data["outputDir"]

            basename = os.path.basename(path)
            head, ext = os.path.splitext(basename)
            files = [
                f"{head}{str(frame).zfill(4)}{ext}"
                for frame in range(frame_start, frame_end + 1)
            ]

            non_existing_frames = []

            for file in files:
                cls.log.error(file)
                if not os.path.exists(os.path.join(output_dir, file)):
                    non_existing_frames.append(file)

            if len(non_existing_frames) > 0:
                cls.log.error(
                    "Some of {}'s files does not exist".format(tool.Name)
                )
                return [tool, output_dir, non_existing_frames]

    def process(self, instance):
        invalid = self.get_invalid(instance)
        if invalid:
            raise PublishValidationError(
                "{} is set to publish existing frames but "
                "some frames are missing in the folder:\n\n{}"
                "The missing file(s) are:\n\n{}".format(
                    invalid[0].Name,
                    invalid[1],
                    "\n\n".join(invalid[2]),
                ),
                title=self.label,
            )

    @classmethod
    def repair(cls, instance):
        invalid = cls.get_invalid(instance)
        for tool in invalid:
            tool.SetInput("CreateDir", 1.0)
