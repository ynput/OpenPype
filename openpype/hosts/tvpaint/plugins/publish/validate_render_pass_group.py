import collections
import pyblish.api
from openpype.pipeline import PublishXmlValidationError


class ValidateLayersGroup(pyblish.api.InstancePlugin):
    """Validate group ids of renderPass layers.

    Validates that all layers are in same group as they were during creation.
    """

    label = "Validate Layers Group"
    order = pyblish.api.ValidatorOrder + 0.1
    families = ["renderPass"]

    def process(self, instance):
        # Prepare layers
        layers_data = instance.context.data["layersData"]
        layers_by_name = {
            layer["name"]: layer
            for layer in layers_data
        }

        # Expected group id for instance layers
        group_id = instance.data["group_id"]
        # Layers ids of an instance
        layer_names = instance.data["layer_names"]
        # Check if all layers from render pass are in right group
        invalid_layers_by_group_id = collections.defaultdict(list)
        invalid_layer_names = set()
        for layer_name in layer_names:
            layer = layers_by_name.get(layer_name)
            _group_id = layer["group_id"]
            if _group_id != group_id:
                invalid_layers_by_group_id[_group_id].append(layer)
                invalid_layer_names.add(layer_name)

        # Everything is OK and skip exception
        if not invalid_layers_by_group_id:
            return

        # Exception message preparations
        groups_data = instance.context.data["groupsData"]
        groups_by_id = {
            group["group_id"]: group
            for group in groups_data
        }
        correct_group = groups_by_id[group_id]

        per_group_msgs = []
        for _group_id, layers in invalid_layers_by_group_id.items():
            _group = groups_by_id[_group_id]
            layers_msgs = []
            for layer in layers:
                layers_msgs.append(
                    "\"{}\" (id: {})".format(layer["name"], layer["layer_id"])
                )
            per_group_msgs.append(
                "Group \"{}\" (id: {}) < {} >".format(
                    _group["name"],
                    _group["group_id"],
                    ", ".join(layers_msgs)
                )
            )

        # Raise an error
        raise PublishXmlValidationError(
            self,
            (
                # Short message
                "Layers in wrong group."
                # Description what's wrong
                " Layers from render pass \"{}\" must be in group {} (id: {})."
                # Detailed message
                " Layers in wrong group: {}"
            ).format(
                instance.data["label"],
                correct_group["name"],
                correct_group["group_id"],
                " | ".join(per_group_msgs)
            ),
            formatting_data={
                "instance_name": (
                    instance.data.get("label") or instance.data["name"]
                ),
                "expected_group": correct_group["name"],
                "layer_names": ", ".join(invalid_layer_names)

            }
        )
