import os
import pyblish.api

from openpype.pipeline.publish import RepairAction
from openpype.pipeline import PublishValidationError

from openpype.hosts.fusion.api.action import SelectInvalidAction


class ValidateLocalFramesExistence(pyblish.api.InstancePlugin):
    """Checks if files for savers that's set
    to publish expected frames exists
    """

    order = pyblish.api.ValidatorOrder
    label = "Validate Expected Frames Exists"
    families = ["render"]
    hosts = ["fusion"]
    actions = [RepairAction, SelectInvalidAction]

    @classmethod
    def get_invalid(cls, instance, non_existing_frames=None):
        if non_existing_frames is None:
            non_existing_frames = []

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

            for file in files:
                if not os.path.exists(os.path.join(output_dir, file)):
                    cls.log.error(
                        f"Missing file: {os.path.join(output_dir, file)}"
                    )
                    non_existing_frames.append(file)

            if len(non_existing_frames) > 0:
                cls.log.error(f"Some of {tool.Name}'s files does not exist")
                return [tool]

    def process(self, instance):
        non_existing_frames = []
        invalid = self.get_invalid(instance, non_existing_frames)
        if invalid:
            raise PublishValidationError(
                "{} is set to publish existing frames but "
                "some frames are missing. "
                "The missing file(s) are:\n\n{}".format(
                    invalid[0].Name,
                    "\n\n".join(non_existing_frames),
                ),
                title=self.label,
            )

    @classmethod
    def repair(cls, instance):
        invalid = cls.get_invalid(instance)
        if invalid:
            tool = invalid[0]

            # Change render target to local to render locally
            tool.SetData("openpype.creator_attributes.render_target", "local")

            cls.log.info(
                f"Reload the publisher and {tool.Name} "
                "will be set to render locally"
            )
