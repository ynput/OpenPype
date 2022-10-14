import os

import nuke

import pyblish.api
import openpype.api as api
from openpype.pipeline import KnownPublishError


class CollectWorkfile(pyblish.api.InstancePlugin):
    """Collect current script for publish."""

    order = pyblish.api.CollectorOrder - 0.499
    label = "Collect Workfile"
    hosts = ['nuke']
    families = ["workfile"]

    def process(self, instance):  # sourcery skip: avoid-builtin-shadow
        root = nuke.root()

        current_file = os.path.normpath(nuke.root().name())

        if current_file.lower() == "root":
            raise KnownPublishError(
                "Workfile is not correct file name. \n"
                "Use workfile tool to manage the name correctly."
            )

        # creating instances per write node
        staging_dir = os.path.dirname(current_file)
        base_name = os.path.basename(current_file)

        # Get frame range
        first_frame = int(root["first_frame"].getValue())
        last_frame = int(root["last_frame"].getValue())

        handle_start = instance.data["handleStart"]
        handle_end = instance.data["handleEnd"]

        # Get format
        format = root['format'].value()
        resolution_width = format.width()
        resolution_height = format.height()
        pixel_aspect = format.pixelAspect()

        script_data = {
            "frameStart": first_frame + handle_start,
            "frameEnd": last_frame - handle_end,
            "resolutionWidth": resolution_width,
            "resolutionHeight": resolution_height,
            "pixelAspect": pixel_aspect,

            # backward compatibility handles
            "handles": handle_start,
            "handleStart": handle_start,
            "handleEnd": handle_end,
            "step": 1,
            "fps": root['fps'].value(),

            "currentFile": current_file,
            "version": int(api.get_version_from_path(current_file)),

            "host": pyblish.api.current_host(),
            "hostVersion": nuke.NUKE_VERSION_STRING
        }
        instance.context.data.update(script_data)

        # creating representation
        representation = {
            'name': 'nk',
            'ext': 'nk',
            'files': base_name,
            "stagingDir": staging_dir,
        }

        # creating instance data
        instance.data.update({
            "name": base_name,
            "representations": [representation]
        })

        # adding basic script data
        instance.data.update(script_data)

        self.log.info('Publishing script version')
