import os

import nuke

import pyblish.api
import openpype.api as pype
from openpype.hosts.nuke.api.lib import (
    add_publish_knob,
    get_avalon_knob_data
)


class CollectWorkfile(pyblish.api.ContextPlugin):
    """Collect current script for publish."""

    order = pyblish.api.CollectorOrder - 0.50
    label = "Pre-collect Workfile"
    hosts = ['nuke']

    def process(self, context):
        root = nuke.root()

        current_file = os.path.normpath(nuke.root().name())

        knob_data = get_avalon_knob_data(root)

        add_publish_knob(root)

        family = "workfile"
        task = os.getenv("AVALON_TASK", None)
        # creating instances per write node
        staging_dir = os.path.dirname(current_file)
        base_name = os.path.basename(current_file)
        subset = family + task.capitalize()

        # Get frame range
        first_frame = int(root["first_frame"].getValue())
        last_frame = int(root["last_frame"].getValue())

        handle_start = int(knob_data.get("handleStart", 0))
        handle_end = int(knob_data.get("handleEnd", 0))

        # Get format
        format = root['format'].value()
        resolution_width = format.width()
        resolution_height = format.height()
        pixel_aspect = format.pixelAspect()

        # Create instance
        instance = context.create_instance(subset)
        instance.add(root)

        script_data = {
            "asset": os.getenv("AVALON_ASSET", None),
            "frameStart": first_frame + handle_start,
            "frameEnd": last_frame - handle_end,
            "resolutionWidth": resolution_width,
            "resolutionHeight": resolution_height,
            "pixelAspect": pixel_aspect,

            # backward compatibility
            "handles": handle_start,

            "handleStart": handle_start,
            "handleEnd": handle_end,
            "step": 1,
            "fps": root['fps'].value(),

            "currentFile": current_file,
            "version": int(pype.get_version_from_path(current_file)),

            "host": pyblish.api.current_host(),
            "hostVersion": nuke.NUKE_VERSION_STRING
        }
        context.data.update(script_data)

        # creating instance data
        instance.data.update({
            "subset": subset,
            "label": base_name,
            "name": base_name,
            "publish": root.knob('publish').value(),
            "family": family,
            "families": [family],
            "representations": list()
        })

        # adding basic script data
        instance.data.update(script_data)

        # creating representation
        representation = {
            'name': 'nk',
            'ext': 'nk',
            'files': base_name,
            "stagingDir": staging_dir,
        }

        instance.data["representations"].append(representation)

        self.log.info('Publishing script version')

        # create instances in context data if not are created yet
        if not context.data.get("instances"):
            context.data["instances"] = list()

        context.data["instances"].append(instance)
