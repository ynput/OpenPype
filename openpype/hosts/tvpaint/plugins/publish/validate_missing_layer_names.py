import pyblish.api
from openpype.pipeline import PublishXmlValidationError


class ValidateMissingLayers(pyblish.api.InstancePlugin):
    """Validate existence of renderPass layers."""

    label = "Validate Missing Layers Names"
    order = pyblish.api.ValidatorOrder
    families = ["renderPass"]

    def process(self, instance):
        # Prepare layers
        layers_by_name = instance.context.data["layersByName"]

        # Layers ids of an instance
        layer_names = instance.data["layer_names"]

        # Check if all layers from render pass are in right group
        missing_layer_names = []
        for layer_name in layer_names:
            layers = layers_by_name.get(layer_name)
            if not layers:
                missing_layer_names.append(layer_name)

        # Everything is OK and skip exception
        if not missing_layer_names:
            return

        layers_msg = ", ".join([
            "\"{}\"".format(layer_name)
            for layer_name in missing_layer_names
        ])
        instance_label = (
            instance.data.get("label") or instance.data["name"]
        )
        description_layer_names = "<br/>".join([
            "- {}".format(layer_name)
            for layer_name in missing_layer_names
        ])

        # Raise an error
        raise PublishXmlValidationError(
            self,
            (
                "Layers were not found by name for instance \"{}\"."
                # Description what's wrong
                " Layer names marked for publishing are not available"
                " in layers list. Missing layer names: {}"
            ).format(instance.data["label"], layers_msg),
            formatting_data={
                "instance_name": instance_label,
                "layer_names": description_layer_names
            }
        )
