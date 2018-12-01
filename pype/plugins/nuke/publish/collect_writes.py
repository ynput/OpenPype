import os

import nuke
import pyblish.api
import clique
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
            # Include start and end render frame in label
            name = node.name()

            label = "{0} ({1}-{2})".format(
                name,
                int(first_frame),
                int(last_frame)
            )

            self.log.debug("checking for error: {}".format(label))

            files = []
            # preredered frames
            if not node["render"].value():
                # dealing with local/farm rendering
                if node["render_farm"].value():
                    families = "{}.farm".format(instance.data["families"][0])
                else:
                    families = "{}.local".format(instance.data["families"][0])
            else:
                families = 'prerendered.frames'
                files = [f for f in os.listdir(output_dir)]

            self.log.debug("checking for error: {}".format(label))
            instance.data.update({
                "path": path,
                "outputDir": output_dir,
                "ext": ext,  # todo: should be redundant
                "label": label,
                "families": [families],
                "files": files,
                "firstFrame": first_frame,
                "lastFrame": last_frame,
                "outputType": output_type
            })

            self.log.debug("instance.data: {}".format(instance.data))

        self.log.debug("context: {}".format(context))

    def sort_by_family(self, instance):
        """Sort by family"""
        return instance.data.get("families", instance.data.get("family"))
