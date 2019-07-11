import nuke
import pyblish.api
import os

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
        file_path = root['name'].value()
        base_name = os.path.basename(file_path)
        subset = "{0}_{1}".format(os.getenv("AVALON_TASK", None), family)

        # Get frame range
        first_frame = int(root["first_frame"].getValue())
        last_frame = int(root["last_frame"].getValue())

        handle_start = int(knob_data["handle_start"])
        handle_end = int(knob_data["handle_end"])

        # Get format
        format = root['format'].value()
        resolution_width = format.width()
        resolution_height = format.height()
        pixel_aspect = format.pixelAspect()

        # Create instance
        instance = context.create_instance(subset)
        instance.add(root)

        instance.data.update({
            "subset": subset,
            "asset": os.getenv("AVALON_ASSET", None),
            "label": base_name,
            "name": base_name,
            "startFrame": first_frame,
            "endFrame": last_frame,
            "resolution_width": resolution_width,
            "resolution_height": resolution_height,
            "pixel_aspect": pixel_aspect,
            "publish": root.knob('publish').value(),
            "family": family,
            "representation": "nk",
            "handle_start": handle_start,
            "handle_end": handle_end,
            "step": 1,
            "fps": int(root['fps'].value()),
        })
        self.log.info('Publishing script version')
        context.data["instances"].append(instance)
