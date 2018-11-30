import os

import nuke
import pyblish.api
from pype.nuke.lib import get_avalon_knob_data


@pyblish.api.log
class CollectNukeInstances(pyblish.api.ContextPlugin):
    """Collect all write nodes."""

    order = pyblish.api.CollectorOrder
    label = "Collect Instances"
    hosts = ["nuke", "nukeassist"]

    def process(self, context):

        # creating instances per write node
        for node in nuke.allNodes():

            if node["disable"].value():
                continue

            # get data from avalon knob
            avalon_knob_data = get_avalon_knob_data(node)
            if not avalon_knob_data:
                continue
            subset = avalon_knob_data["subset"]

            # Create instance
            instance = context.create_instance(subset)
            instance.add(node)

            instance.data.update({
                "asset": os.environ["AVALON_ASSET"],
                "label": node.name(),
                "name": node.name(),
                "subset": subset,
                "families": [avalon_knob_data["families"]],
                "family": avalon_knob_data["family"],
                "publish": node.knob("publish").value()
            })
            self.log.info("collected instance: {}".format(instance.data))
        # Sort/grouped by family (preserving local index)
        context[:] = sorted(context, key=self.sort_by_family)

        self.log.info("context: {}".format(context))

        return context

    def sort_by_family(self, instance):
        """Sort by family"""
        return instance.data.get("families", instance.data.get("family"))
