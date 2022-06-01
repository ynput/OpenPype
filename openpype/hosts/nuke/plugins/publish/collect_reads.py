import os
import re
import nuke
import pyblish.api

from openpype.pipeline import legacy_io


@pyblish.api.log
class CollectNukeReads(pyblish.api.InstancePlugin):
    """Collect all read nodes."""

    order = pyblish.api.CollectorOrder + 0.04
    label = "Collect Source Reads"
    hosts = ["nuke", "nukeassist"]
    families = ["source"]

    def process(self, instance):
        asset_data = legacy_io.find_one({
            "type": "asset",
            "name": legacy_io.Session["AVALON_ASSET"]
        })

        self.log.debug("asset_data: {}".format(asset_data["data"]))

        self.log.debug("checking instance: {}".format(instance))

        node = instance[0]
        if node.Class() != "Read":
            return

        file_path = node["file"].value()
        file_name = os.path.basename(file_path)
        items = file_name.split(".")

        if len(items) < 2:
            raise ValueError

        ext = items[-1]

        # Get frame range
        handle_start = instance.context.data["handleStart"]
        handle_end = instance.context.data["handleEnd"]
        first_frame = node['first'].value()
        last_frame = node['last'].value()

        # colorspace
        colorspace = node["colorspace"].value()
        if "default" in colorspace:
            colorspace = colorspace.replace("default (", "").replace(")", "")

        # # Easier way to sequence - Not tested
        # isSequence = True
        # if first_frame == last_frame:
        #     isSequence = False

        isSequence = False
        if len(items) > 1:
            sequence = items[-2]
            hash_regex = re.compile(r'([#*])')
            seq_regex = re.compile(r'[%0-9*d]')
            hash_match = re.match(hash_regex, sequence)
            seq_match = re.match(seq_regex, sequence)
            if hash_match or seq_match:
                isSequence = True

        # get source path
        path = nuke.filename(node)
        source_dir = os.path.dirname(path)
        self.log.debug('source dir: {}'.format(source_dir))

        if isSequence:
            source_files = [f for f in os.listdir(source_dir)
                            if ext in f
                            if items[0] in f]
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
            'ext': ext,
            'files': source_files,
            "stagingDir": source_dir,
            "frameStart": "%0{}d".format(
                len(str(last_frame))) % first_frame
        }
        instance.data["representations"].append(representation)

        transfer = False
        if "publish" in node.knobs():
            transfer = node["publish"]

        instance.data['transfer'] = transfer

        # Add version data to instance
        version_data = {
            "handles": handle_start,
            "handleStart": handle_start,
            "handleEnd": handle_end,
            "frameStart": first_frame + handle_start,
            "frameEnd": last_frame - handle_end,
            "colorspace": colorspace,
            "families": [instance.data["family"]],
            "subset": instance.data["subset"],
            "fps": instance.context.data["fps"]
        }

        instance.data.update({
            "versionData": version_data,
            "path": path,
            "stagingDir": source_dir,
            "ext": ext,
            "label": label,
            "frameStart": first_frame,
            "frameEnd": last_frame,
            "colorspace": colorspace,
            "handles": int(asset_data["data"].get("handles", 0)),
            "step": 1,
            "fps": int(nuke.root()['fps'].value())
        })

        self.log.debug("instance.data: {}".format(instance.data))
