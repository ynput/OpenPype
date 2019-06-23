from avalon import api, io
import nuke
import pyblish.api
import os
from avalon.nuke.lib import (
    add_publish_knob,
    add_avalon_tab_knob
)


class CollectScript(pyblish.api.ContextPlugin):
    """Publish current script version."""

    order = pyblish.api.CollectorOrder + 0.1
    label = "Collect Script to publish"
    hosts = ['nuke']

    def process(self, context):
        root = nuke.root()
        add_avalon_tab_knob(root)
        add_publish_knob(root)

        family = "nukescript"
        # creating instances per write node
        file_path = root['name'].value()
        base_name = os.path.basename(file_path)
        subset = "{0}_{1}".format(os.getenv("AVALON_TASK", None), family)

        # Get frame range
        first_frame = int(root["first_frame"].getValue())
        last_frame = int(root["last_frame"].getValue())

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
            "handles": context.data['handles'],
            "step": 1,
            "fps": int(root['fps'].value()),
        })
        self.log.info('Publishing script version')
        context.data["instances"].append(instance)
