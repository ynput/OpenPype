import os

import nuke
import pyblish.api
from avalon import io, api
from pype.nuke.lib import get_avalon_knob_data


@pyblish.api.log
class CollectNukeInstances(pyblish.api.ContextPlugin):
    """Collect all nodes with Avalon knob."""

    order = pyblish.api.CollectorOrder + 0.01
    label = "Collect Instances"
    hosts = ["nuke", "nukeassist"]

    def process(self, context):
        asset_data = io.find_one({"type": "asset",
                                  "name": api.Session["AVALON_ASSET"]})

        # add handles into context
        context.data['handles'] = context.data['handles']

        self.log.debug("asset_data: {}".format(asset_data["data"]))
        instances = []
        # creating instances per write node
        for node in nuke.allNodes():

            try:
                if node["disable"].value():
                    continue
            except Exception:
                continue

            # get data from avalon knob
            avalon_knob_data = get_avalon_knob_data(node)
            if not avalon_knob_data:
                continue

            if avalon_knob_data["id"] != "pyblish.avalon.instance":
                continue

            subset = avalon_knob_data.get(
                "subset", None) or node["name"].value()

            # Create instance
            instance = context.create_instance(subset)
            instance.add(node)

            family = avalon_knob_data["families"]
            if node["render"].value():
                self.log.info("flagged for render")
                family = "render.local"
                # dealing with local/farm rendering
                if node["render_farm"].value():
                    self.log.info("adding render farm family")
                    family = "render.farm"
                    instance.data['transfer'] = False

            instance.data.update({
                "subset": subset,
                "asset": os.environ["AVALON_ASSET"],
                "label": node.name(),
                "name": node.name(),
                "subset": subset,
                "family": avalon_knob_data["family"],
                "families": [family],
                "avalonKnob": avalon_knob_data,
                "publish": node.knob('publish').value(),
                "step": 1,
                "fps": int(nuke.root()['fps'].value())

            })

            self.log.info("collected instance: {}".format(instance.data))
            instances.append(instance)

        context.data["instances"] = instances

        self.log.debug("context: {}".format(context))
