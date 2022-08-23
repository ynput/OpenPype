import pyblish.api
from openpype.pipeline import PublishXmlValidationError


class ValidateLayersGroup(pyblish.api.InstancePlugin):
    """Validate layer names for publishing are unique for whole workfile."""

    label = "Validate Duplicated Layers Names"
    order = pyblish.api.ValidatorOrder
    families = ["renderPass"]

    def process(self, instance):
        # Prepare layers
        layers_by_name = instance.context.data["layersByName"]

        # Layers ids of an instance
        layer_names = instance.data["layer_names"]

        # Check if all layers from render pass are in right group
        duplicated_layer_names = []
        for layer_name in layer_names:
            layers = layers_by_name.get(layer_name)
            if len(layers) > 1:
                duplicated_layer_names.append(layer_name)

        # Everything is OK and skip exception
        if not duplicated_layer_names:
            return

        layers_msg = ", ".join([
            "\"{}\"".format(layer_name)
            for layer_name in duplicated_layer_names
        ])
        detail_lines = [
            "- {}".format(layer_name)
            for layer_name in set(duplicated_layer_names)
        ]
        raise PublishXmlValidationError(
            self,
            (
                "Layers have duplicated names for instance {}."
                # Description what's wrong
                " There are layers with same name and one of them is marked"
                " for publishing so it is not possible to know which should"
                " be published. Please look for layers with names: {}"
            ).format(instance.data["label"], layers_msg),
            formatting_data={
                "layer_names": "<br/>".join(detail_lines)
            }
        )
