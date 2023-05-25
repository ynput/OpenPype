import pyblish.api

from avalon.tvpaint import lib, HEADLESS


class CollectLayerBehaviors(pyblish.api.ContextPlugin):

    order = pyblish.api.CollectorOrder
    label = "Collect Layer Behaviours"
    hosts = ["tvpaint"]

    def process(self, context):
        # Skip extract if in headless mode.
        if HEADLESS:
            return

        # Map layers by position
        layers_by_position = {}
        layer_ids = []
        for layer in context.data["layersData"]:
            position = layer["position"]
            layers_by_position[position] = layer

            layer_ids.append(layer["layer_id"])

        # Sort layer positions in reverse order
        sorted_positions = list(reversed(sorted(layers_by_position.keys())))
        if not sorted_positions:
            return [], None

        behavior_by_layer_id = lib.get_layers_pre_post_behavior(layer_ids)
        context.data["behavior_by_layer_id"] = behavior_by_layer_id
        context.data["jsonData"]["behavior_by_layer_id"] = behavior_by_layer_id
