import nuke
import pyblish.api
import os

import pype.api as pype

from avalon.nuke import (
    get_avalon_knob_data,
    add_publish_knob
)


class CollectWorkfile(pyblish.api.ContextPlugin):
    """Publish current script version."""

    order = pyblish.api.CollectorOrder + 0.1
    label = "Collect Workfile"
    hosts = ['nuke']

    def process(self, context):
        root = nuke.root()

        knob_data = get_avalon_knob_data(root)

        add_publish_knob(root)

        family = "workfile"
        # creating instances per write node
        file_path = context.data["currentFile"]
        staging_dir = os.path.dirname(file_path)
        base_name = os.path.basename(file_path)
        subset = "{0}_{1}".format(os.getenv("AVALON_TASK", None), family)

        # get version string
        version = pype.get_version_from_path(base_name)

        # Get frame range
        first_frame = int(root["first_frame"].getValue())
        last_frame = int(root["last_frame"].getValue())

        handle_start = int(knob_data.get("handle_start", 0))
        handle_end = int(knob_data.get("handle_end", 0))

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
            "version": version,
            "startFrame": first_frame + handle_start,
            "endFrame": last_frame - handle_end,
            "resolution_width": resolution_width,
            "resolution_height": resolution_height,
            "pixel_aspect": pixel_aspect,

            # backward compatibility
            "handles": handle_start,

            "handle_start": handle_start,
            "handle_end": handle_end,
            "step": 1,
            "fps": root['fps'].value(),
        }
        context.data.update(script_data)

        # creating instance data
        instance.data.update({
            "subset": subset,
            "label": base_name,
            "name": base_name,
            "publish": root.knob('publish').value(),
            "family": family,
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
        context.data["instances"].append(instance)
