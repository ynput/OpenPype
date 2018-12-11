from avalon import api, io
import nuke
import pyblish.api
import os


class CollectScript(pyblish.api.ContextPlugin):
    """Publish current script version."""

    order = pyblish.api.CollectorOrder + 0.1
    label = "Collect Script to publish"
    hosts = ['nuke']

    def process(self, context):
        asset_data = io.find_one({"type": "asset",
                                  "name": api.Session["AVALON_ASSET"]})
        self.log.debug("asset_data: {}".format(asset_data["data"]))

        # creating instances per write node
        file_path = nuke.root()['name'].value()
        base_name = os.path.basename(file_path)
        subset = base_name.split("_v")[0]

        # Create instance
        instance = context.create_instance(subset)

        instance.data.update({
            "subset": subset,
            "asset": os.environ["AVALON_ASSET"],
            "label": base_name,
            "name": base_name,
            "subset": subset,
            "family": "script",
            "handles": int(asset_data["data"].get("handles", 0)),
            "step": 1,
            "fps": int(nuke.root()['fps'].value())

        })
        self.log.info('Publishing script version')
        context.data["instances"].append(instance)
