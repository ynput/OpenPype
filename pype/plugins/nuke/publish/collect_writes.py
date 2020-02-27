import os
import nuke
import pyblish.api
import pype.api as pype


@pyblish.api.log
class CollectNukeWrites(pyblish.api.InstancePlugin):
    """Collect all write nodes."""

    order = pyblish.api.CollectorOrder + 0.1
    label = "Collect Writes"
    hosts = ["nuke", "nukeassist"]
    families = ["write"]

    def process(self, instance):
        # adding 2d focused rendering
        instance.data["families"].append("render2d")

        node = None
        for x in instance:
            if x.Class() == "Write":
                node = x

        if node is None:
            return

        self.log.debug("checking instance: {}".format(instance))

        # Determine defined file type
        ext = node["file_type"].value()

        # Determine output type
        output_type = "img"
        if ext == "mov":
            output_type = "mov"

        # Get frame range
        handles = instance.context.data['handles']
        handle_start = instance.context.data["handleStart"]
        handle_end = instance.context.data["handleEnd"]
        first_frame = int(nuke.root()["first_frame"].getValue())
        last_frame = int(nuke.root()["last_frame"].getValue())

        if node["use_limit"].getValue():
            handles = 0
            first_frame = int(node["first"].getValue())
            last_frame = int(node["last"].getValue())

        # get path
        path = nuke.filename(node)
        output_dir = os.path.dirname(path)
        self.log.debug('output dir: {}'.format(output_dir))

        # # get version to instance for integration
        # instance.data['version'] = instance.context.data.get(
        #     "version", pype.get_version_from_path(nuke.root().name()))

        self.log.debug('Write Version: %s' % instance.data('version'))

        # create label
        name = node.name()
        # Include start and end render frame in label
        label = "{0} ({1}-{2})".format(
            name,
            int(first_frame),
            int(last_frame)
        )

        if 'render' in instance.data['families']:
            if "representations" not in instance.data:
                instance.data["representations"] = list()

                representation = {
                    'name': ext,
                    'ext': ext,
                    "stagingDir": output_dir,
                    "anatomy_template": "render"
                }

            try:
                collected_frames = [f for f in os.listdir(output_dir)
                                    if ext in f]
                if collected_frames:
                    representation['frameStart'] = "%0{}d".format(
                        len(str(last_frame))) % first_frame
                representation['files'] = collected_frames
                instance.data["representations"].append(representation)
            except Exception:
                instance.data["representations"].append(representation)
                self.log.debug("couldn't collect frames: {}".format(label))

        # Add version data to instance
        version_data = {
            "colorspace":  node["colorspace"].value(),
        }

        instance.data["family"] = "write"
        group_node = [x for x in instance if x.Class() == "Group"][0]
        deadlineChunkSize = 1
        if "deadlineChunkSize" in group_node.knobs():
            deadlineChunkSize = group_node["deadlineChunkSize"].value()

        deadlinePriority = 50
        if "deadlinePriority" in group_node.knobs():
            deadlinePriority = group_node["deadlinePriority"].value()

        families = [f for f in instance.data["families"] if "write" not in f]
        instance.data.update({
            "versionData": version_data,
            "path": path,
            "outputDir": output_dir,
            "ext": ext,
            "label": label,
            "handles": handles,
            "frameStart": first_frame,
            "frameEnd": last_frame,
            "outputType": output_type,
            "family": "write",
            "families": families,
            "colorspace": node["colorspace"].value(),
            "deadlineChunkSize": deadlineChunkSize,
            "deadlinePriority": deadlinePriority
        })

        self.log.debug("instance.data: {}".format(instance.data))
