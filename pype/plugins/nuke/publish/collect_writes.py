import os

import nuke
import pyblish.api
import logging
from avalon import io, api

log = logging.getLogger(__name__)


@pyblish.api.log
class CollectNukeWrites(pyblish.api.ContextPlugin):
    """Collect all write nodes."""

    order = pyblish.api.CollectorOrder + 0.1
    label = "Collect Writes"
    hosts = ["nuke", "nukeassist"]

    def process(self, context):
        asset_data = io.find_one({"type": "asset",
                                  "name": api.Session["AVALON_ASSET"]})
        self.log.debug("asset_data: {}".format(asset_data["data"]))
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
            self.log.debug('output dir: {}'.format(output_dir))
            # Include start and end render frame in label
            name = node.name()

            label = "{0} ({1}-{2})".format(
                name,
                int(first_frame),
                int(last_frame)
            )

            # preredered frames
            if not node["render"].value():
                families = "prerendered.frames"
                collected_frames = os.listdir(output_dir)
                self.log.debug("collected_frames: {}".format(label))
                if "files" not in instance.data:
                    instance.data["files"] = list()
                instance.data["files"].append(collected_frames)
                instance.data['transfer'] = False
            else:
                # dealing with local/farm rendering
                if node["render_farm"].value():
                    families = "{}.farm".format(instance.data["avalonKnob"]["families"][0])
                else:
                    families = "{}.local".format(instance.data["avalonKnob"]["families"])

            self.log.debug("checking for error: {}".format(label))
            instance.data.update({
                "path": path,
                "outputDir": output_dir,
                "ext": ext,
                "label": label,
                "families": [families, 'ftrack'],
                "startFrame": first_frame,
                "endFrame": last_frame,
                "outputType": output_type,
                "stagingDir": output_dir,
                "colorspace": node["colorspace"].value(),
                "handles": int(asset_data["data"].get("handles", 0)),
                "step": 1,
                "fps": int(nuke.root()['fps'].value())
            })

            self.log.debug("instance.data: {}".format(instance.data))

        self.log.debug("context: {}".format(context))

    def sort_by_family(self, instance):
        """Sort by family"""
        return instance.data.get("families", instance.data.get("family"))
