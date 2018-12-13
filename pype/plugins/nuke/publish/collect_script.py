from avalon import api, io
import nuke
import pyblish.api
import os
import tempfile
from avalon.nuke.lib import add_publish_knob


class CollectScript(pyblish.api.ContextPlugin):
    """Publish current script version."""

    order = pyblish.api.CollectorOrder + 0.1
    label = "Collect Script to publish"
    hosts = ['nuke']

    def process(self, context):
        asset_data = io.find_one({"type": "asset",
                                  "name": api.Session["AVALON_ASSET"]})
        self.log.debug("asset_data: {}".format(asset_data["data"]))

        root = nuke.root()
        add_publish_knob(root)

        # creating instances per write node
        file_path = root['name'].value()
        base_name = os.path.basename(file_path)
        subset = base_name.split("_v")[0]

        # Get frame range
        first_frame = int(root["first_frame"].getValue())
        last_frame = int(root["last_frame"].getValue())

        # Create instance
        instance = context.create_instance(subset)
        instance.add(root)

        # adding stage dir for faster local renderings
        staging_dir = tempfile.mkdtemp().replace("\\", "/")
        instance.data.update({"stagingDir": staging_dir})
        self.log.debug('staging_dir: {}'.format(staging_dir))

        instance.data.update({
            "subset": subset,
            "asset": os.environ["AVALON_ASSET"],
            "label": base_name,
            "name": base_name,
            "subset": subset,
            "startFrame": first_frame,
            "endFrame": last_frame,
            "publish": root.knob('publish').value(),
            "family": "script",
            "handles": int(asset_data["data"].get("handles", 0)),
            "step": 1,
            "fps": int(root['fps'].value()),
            "files": base_name
        })
        self.log.info('Publishing script version')
        context.data["instances"].append(instance)
