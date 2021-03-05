import pyblish.api


class ValidateLayersVisiblity(pyblish.api.InstancePlugin):
    """Validate existence of renderPass layers."""

    label = "Validate Layers Visibility"
    order = pyblish.api.ValidatorOrder
    families = ["review", "renderPass", "renderLayer"]

    def process(self, instance):
        for layer in instance.data["layers"]:
            if layer["visible"]:
                return

        raise AssertionError("All layers of instance are not visible.")
