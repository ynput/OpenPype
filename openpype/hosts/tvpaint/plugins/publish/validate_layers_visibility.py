import pyblish.api
from openpype.pipeline import PublishXmlValidationError


# TODO @iLLiCiTiT add repair action to disable instances?
class ValidateLayersVisiblity(pyblish.api.InstancePlugin):
    """Validate existence of renderPass layers."""

    label = "Validate Layers Visibility"
    order = pyblish.api.ValidatorOrder
    families = ["review", "renderPass", "renderLayer", "renderScene"]

    def process(self, instance):
        layer_names = set()
        for layer in instance.data["layers"]:
            layer_names.add(layer["name"])
            if layer["visible"]:
                return

        instance_label = (
            instance.data.get("label") or instance.data["name"]
        )

        raise PublishXmlValidationError(
            self,
            "All layers of instance \"{}\" are not visible.".format(
                instance_label
            ),
            formatting_data={
                "instance_name": instance_label,
                "layer_names": "<br/>".join([
                    "- {}".format(layer_name)
                    for layer_name in layer_names
                ])
            }
        )
