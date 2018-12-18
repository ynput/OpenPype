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
        asset_data = io.find_one({"type": "asset",
                                  "name": api.Session["AVALON_ASSET"]})
        self.log.info("asset_data: {}".format(asset_data["data"]))

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
            "publish": root.knob('publish').value(),
            "family": family,
            "representation": "nk",
            "handles": int(asset_data["data"].get("handles", 0)),
            "step": 1,
            "fps": int(root['fps'].value()),
        })
        self.log.info('Publishing script version')
        context.data["instances"].append(instance)
