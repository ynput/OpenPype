import pyblish.api
from openpype.pipeline import publish
import os


class CollectFusionExpectedFrames(
    pyblish.api.InstancePlugin, publish.ColormanagedPyblishPluginMixin
):
    """Collect all frames needed to publish expected frames"""

    order = pyblish.api.CollectorOrder + 0.5
    label = "Collect Expected Frames"
    hosts = ["fusion"]
    families = ["render"]

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
