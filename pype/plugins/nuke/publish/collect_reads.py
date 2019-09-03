import os
import re
import clique
import nuke
import pyblish.api
import logging
from avalon import io, api

log = logging.get_logger(__name__)


@pyblish.api.log
class CollectNukeReads(pyblish.api.ContextPlugin):
    """Collect all read nodes."""

    order = pyblish.api.CollectorOrder + 0.1
    label = "Collect Reads"
    hosts = ["nuke"]

    def process(self, context):
        asset_data = io.find_one({"type": "asset",
                                  "name": api.Session["AVALON_ASSET"]})
        self.log.debug("asset_data: {}".format(asset_data["data"]))
        for instance in context.data["instances"]:
            self.log.debug("checking instance: {}".format(instance))

            node = instance[0]
            if node.Class() != "Read":
                continue

            file_path = node["file"].value()
            file_name = os.path.basename(file_path)
            items = file_name.split(".")

            if len(items) < 2:
                raise ValueError

            ext = items[-1]

            # # Get frame range
            first_frame = node['first'].value()
            last_frame = node['last'].value()

            # # Easier way to sequence - Not tested
            # isSequence = True
            # if first_frame == last_frame:
            #     isSequence = False

            isSequence = False
            if len(items) > 1:
                sequence = items[-2]
                hash_regex = re.compile(r'([#*])')
                seq_regex = re.compile('[%0-9*d]')
                hash_match = re.match(hash_regex, sequence)
                seq_match = re.match(seq_regex, sequence)
                if hash_match or seq_match:
                    isSequence = True

            # get source path
            path = nuke.filename(node)
            source_dir = os.path.dirname(path)
            self.log.debug('source dir: {}'.format(source_dir))

            if isSequence:
                source_files = os.listdir(source_dir)
            else:
                source_files = file_name

            # Include start and end render frame in label
            name = node.name()
            label = "{0} ({1}-{2})".format(
                name,
                int(first_frame),
                int(last_frame)
            )

            self.log.debug("collected_frames: {}".format(label))

            if "representations" not in instance.data:
                instance.data["representations"] = []

            representation = {
                'name': ext,
                'ext': "." + ext,
                'files': source_files,
                "stagingDir": source_dir,
            }
            instance.data["representations"].append(representation)

            transfer = False
            if "publish" in node.knobs():
                transfer = node["publish"]

            instance.data['transfer'] = transfer

            self.log.debug("checking for error: {}".format(label))
            instance.data.update({
                "path": path,
                "stagingDir": source_dir,
                "ext": ext,
                "label": label,
                "frameStart": first_frame,
                "frameEnd": last_frame,
                "colorspace": node["colorspace"].value(),
                "handles": int(asset_data["data"].get("handles", 0)),
                "step": 1,
                "fps": int(nuke.root()['fps'].value())
            })

            self.log.debug("instance.data: {}".format(instance.data))

        self.log.debug("context: {}".format(context))
