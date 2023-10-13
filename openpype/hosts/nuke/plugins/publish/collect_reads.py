import os
import nuke
import pyblish.api

from openpype.hosts.nuke.api.lib import get_node_path


class CollectNukeReads(pyblish.api.InstancePlugin):
    """Collect all read nodes."""

    order = pyblish.api.CollectorOrder + 0.04
    label = "Collect Source Reads"
    hosts = ["nuke", "nukeassist"]
    families = ["source"]

    def process(self, instance):
        self.log.debug("checking instance: {}".format(instance))

        node = instance.data["transientData"]["node"]
        if node.Class() != "Read":
            return

        file_path = nuke.filename(node)
        file_name = os.path.basename(file_path)

        # Get frame range
        handle_start = instance.context.data["handleStart"]
        handle_end = instance.context.data["handleEnd"]
        first_frame = node['first'].value()
        last_frame = node['last'].value()

        # colorspace
        colorspace = node["colorspace"].value()
        if "default" in colorspace:
            colorspace = colorspace.replace("default (", "").replace(")", "")

        isSequence = False
        filename, padding, ext = get_node_path(file_name, strict=True)
        if padding:
            isSequence = True

        # get source path
        source_dir = os.path.dirname(file_path)
        self.log.debug('source dir: {}'.format(source_dir))

        if isSequence:
            source_files = [
                f_ for f_ in os.listdir(source_dir)
                if ext in f_
                if filename in f_
            ]
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
            'name': ext[1:],
            'ext': ext[1:],
            'files': source_files,
            "stagingDir": source_dir,
            "frameStart": "%0{}d".format(
                len(str(last_frame))) % first_frame
        }
        instance.data["representations"].append(representation)

        transfer = node["publish"] if "publish" in node.knobs() else False
        instance.data['transfer'] = transfer

        # Add version data to instance
        version_data = {
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
            "path": file_path,
            "stagingDir": source_dir,
            "ext": ext[1:],
            "label": label,
            "frameStart": first_frame,
            "frameEnd": last_frame,
            "colorspace": colorspace,
            "handleStart": handle_start,
            "handleEnd": handle_end,
            "step": 1,
            "fps": int(nuke.root()['fps'].value())
        })

        self.log.debug("instance.data: {}".format(instance.data))
