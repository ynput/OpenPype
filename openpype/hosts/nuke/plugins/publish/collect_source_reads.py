import os
from pprint import pformat
import nuke
import pyblish.api
from openpype.pipeline import publish
from openpype.hosts.nuke.api import (
    get_colorspace_from_node,
    collect_expected_files_from_node,
    mark_files_for_migration
)


class CollectNukeReads(pyblish.api.InstancePlugin,
                       publish.ColormanagedPyblishPluginMixin):
    """Collect all read nodes."""

    order = pyblish.api.CollectorOrder + 0.04
    label = "Collect Source Reads"
    hosts = ["nuke", "nukeassist"]
    families = ["source"]

    def process(self, instance):
        node = instance.data["transientData"]["node"]

        self.log.debug("checking instance: {}".format(instance))

        if node.Class() != "Read":
            return

        # get node file and directory
        file_path = nuke.filename(node)
        file_name = os.path.basename(file_path)

        # Get frame range
        handle_start = instance.context.data["handleStart"]
        handle_end = instance.context.data["handleEnd"]
        first_frame = node['first'].value()
        last_frame = node['last'].value()

        # get colorspace knob value
        colorspace = get_colorspace_from_node(node)

        # get filename and padding
        _, ext = os.path.splitext(file_name)

        dir_path, source_files = collect_expected_files_from_node(node)

        staging_dir = mark_files_for_migration(
            instance, dir_path, source_files, log=self.log)

        # Include start and end render frame in label
        name = node.name()
        label = "{0} ({1}-{2})".format(
            name,
            int(first_frame),
            int(last_frame)
        )

        representation = {
            'name': ext[1:],
            'ext': ext[1:],
            'files': source_files,
            "stagingDir": staging_dir,
            "frameStart": (
                "{{:0{}d}}".format(len(str(last_frame)))
            ).format(first_frame)
        }

        # inject colorspace data
        self.set_representation_colorspace(
            representation, instance.context,
            colorspace=colorspace
        )

        # Add representation to instance
        instance.data.setdefault(
            "representations", []).append(representation)

        instance.data.update({
            "label": label,
            "path": os.path.join(staging_dir, file_name),
            "stagingDir": staging_dir,
            "ext": ext[1:],
            "handleStart": handle_start,
            "handleEnd": handle_end,
            "frameStart": first_frame + handle_start,
            "frameEnd": last_frame - handle_end,
            "colorspace": colorspace,
            "fps": instance.data["fps"]
        })

        self.log.debug("instance.data: {}".format(pformat(instance.data)))
