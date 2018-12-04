import os

import nuke
import pyblish.api
from pype.nuke.lib import get_avalon_knob_data


@pyblish.api.log
class CollectNukeInstances(pyblish.api.ContextPlugin):
    """Collect all nodes with Avalon knob."""

    order = pyblish.api.CollectorOrder
    label = "Collect Instances"
    hosts = ["nuke", "nukeassist"]

    def process(self, context):
        instances = []
        # creating instances per write node
        for node in nuke.allNodes():

            try:
                if node["disable"].value():
                    continue
            except Exception:
                continue

            try:
                publish = node.knob("publish").value()
            except Exception:
                continue

            # get data from avalon knob
            avalon_knob_data = get_avalon_knob_data(node)
            if not avalon_knob_data:
                continue

            subset = avalon_knob_data.get("subset", None) or node["name"].value()

            # Create instance
            instance = context.create_instance(subset)
            instance.add(node)

            instance.data.update({
                "subset": subset,
                "asset": os.environ["AVALON_ASSET"],
                "label": node.name(),
                "name": node.name(),
                "avalonKnob": avalon_knob_data,
                "publish": publish
            })
            self.log.info("collected instance: {}".format(instance.data))
            instances.append(instance)

        context.data["instances"] = instances

        # Sort/grouped by family (preserving local index)
        context[:] = sorted(context, key=self.sort_by_family)

        self.log.debug("context: {}".format(context))

    def sort_by_family(self, instance):
        """Sort by family"""
        return instance.data.get("families", instance.data.get("family"))
