import os
import tempfile
import nuke
import pyblish.api
import logging


log = logging.getLogger(__name__)


@pyblish.api.log
class CollectNukeWrites(pyblish.api.ContextPlugin):
    """Collect all write nodes."""

    order = pyblish.api.CollectorOrder + 0.1
    label = "Collect Writes"
    hosts = ["nuke", "nukeassist"]

    def process(self, context):
        for instance in context.data["instances"]:

            if not instance.data["publish"]:
                continue

            self.log.debug("checking instance: {}".format(instance))
            node = instance[0]

            if node.Class() != "Write":
                continue

            # Determine defined file type
            ext = node["file_type"].value()

            # Determine output type
            output_type = "img"
            if ext == "mov":
                output_type = "mov"

            # Get frame range
            first_frame = int(nuke.root()["first_frame"].getValue())
            last_frame = int(nuke.root()["last_frame"].getValue())

            if node["use_limit"].getValue():
                first_frame = int(node["first"].getValue())
                last_frame = int(node["last"].getValue())

            # get path
            path = nuke.filename(node)
            output_dir = os.path.dirname(path)
            self.log.debug('output dir: {}'.format(output_dir))

            # create label
            name = node.name()
            # Include start and end render frame in label
            label = "{0} ({1}-{2})".format(
                name,
                int(first_frame),
                int(last_frame)
            )

            # preredered frames
            # collect frames by try
            # collect families in next file
            if "files" not in instance.data:
                instance.data["files"] = list()

            try:
                collected_frames = os.listdir(output_dir)
                self.log.debug("collected_frames: {}".format(label))

                instance.data["files"].append(collected_frames)
            except Exception:
                pass

            # adding stage dir for faster local renderings
            staging_dir = tempfile.mkdtemp().replace("\\", "/")
            instance.data.update({"stagingDir": staging_dir})
            self.log.debug('staging_dir: {}'.format(staging_dir))

            instance.data.update({
                "path": path,
                "outputDir": output_dir,
                "ext": ext,
                "label": label,
                "startFrame": first_frame,
                "endFrame": last_frame,
                "outputType": output_type,
                "colorspace": node["colorspace"].value(),
            })

            self.log.debug("instance.data: {}".format(instance.data))

        self.log.debug("context: {}".format(context))
