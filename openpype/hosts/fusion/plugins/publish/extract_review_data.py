import os
import pyblish.api
from openpype.pipeline.publish import (
    ColormanagedPyblishPluginMixin,
)


class FusionExtractReviewData(
    pyblish.api.InstancePlugin, ColormanagedPyblishPluginMixin
):
    """
    Extract the result of savers by starting a comp render
    This will run the local render of Fusion.
    """

    order = pyblish.api.ExtractorOrder - 0.1
    label = "Extract Review Data"
    hosts = ["fusion"]
    families = ["review"]

    def process(self, instance):
        context = instance.context

        frame_start = context.data["frameStartHandle"]
        frame_end = context.data["frameEndHandle"]
        path = instance.data["path"]
        output_dir = instance.data["outputDir"]

        basename = os.path.basename(path)
        head, ext = os.path.splitext(basename)
        files = [
            f"{head}{str(frame).zfill(4)}{ext}"
            for frame in range(frame_start, frame_end + 1)
        ]
        repre = {
            "name": ext[1:],
            "ext": ext[1:],
            "frameStart": f"%0{len(str(frame_end))}d" % frame_start,
            "files": files,
            "stagingDir": output_dir,
        }

        self.set_representation_colorspace(
            representation=repre,
            context=context,
        )

        # review representation
        if instance.data.get("review", False):
            repre["tags"] = ["review"]

        # add the repre to the instance
        if "representations" not in instance.data:
            instance.data["representations"] = []
        instance.data["representations"].append(repre)
