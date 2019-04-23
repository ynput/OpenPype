import os
import nuke
import pyblish.api
import pype.api as pype



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

            node = instance[0]

            if node.Class() != "Write":
                continue

            self.log.debug("checking instance: {}".format(instance))

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

            # get version
            version = pype.get_version_from_path(path)
            instance.data['version'] = version
            self.log.debug('Write Version: %s' % instance.data('version'))

            # create label
            name = node.name()
            # Include start and end render frame in label
            label = "{0} ({1}-{2})".format(
                name,
                int(first_frame),
                int(last_frame)
            )

            if "files" not in instance.data:
                instance.data["files"] = list()
            try:
                collected_frames = os.listdir(output_dir)
                self.log.debug("collected_frames: {}".format(label))
                instance.data["files"].append(collected_frames)

            except Exception:
                self.log.debug("couldn't collect frames: {}".format(label))

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
