import json

import pyblish.api
from avalon.tvpaint import pipeline


class CollectInstances(pyblish.api.ContextPlugin):
    label = "Collect Instances"
    order = pyblish.api.CollectorOrder - 1
    hosts = ["tvpaint"]

    def process(self, context):
        workfile_instances = context.data["workfileInstances"]

        self.log.debug("Collected ({}) instances:\n{}".format(
            len(workfile_instances),
            json.dumps(workfile_instances, indent=4)
        ))

        # TODO add validations of existing instances
        # - layer id exists
        for instance_data in workfile_instances:
            # Global instance data modifications
            # Fill families
            family = instance_data["family"]
            instance_data["families"] = [family]

            # Instance name
            subset_name = instance_data["subset"]
            name = instance_data.get("name", subset_name)
            instance_data["name"] = name

            active = instance_data.get("active", True)
            instance_data["active"] = active
            instance_data["publish"] = active

            # Different instance creation based on family
            instance = None
            if family == "review":
                instance = context.create_instance(**instance_data)
            elif family == "renderLayer":
                instance = self.create_render_layer(context, instance_data)
            elif family == "renderPass":
                instance = self.create_render_pass(context, instance_data)
            else:
                raise AssertionError(
                    "Instance with unknown family \"{}\": {}"
                )

            if instance is not None:
                self.log.debug("Created instance: {}\n{}".format(
                    instance, json.dumps(instance.data, indent=4)
                ))

    def create_render_layer(self, context, instance_data):
        layers_data = context.data["layersData"]
        group_id = instance_data["group_id"]

        name = instance_data["name"]
        instance_data["label"] = name

        group_layers = []
        for layer in layers_data:
            if layer["group_id"] == group_id and layer["visible"]:
                group_layers.append(layer)

        if not group_layers:
            # Should be handled here?
            self.log.warning(
                f"Group with id {group_id} does not contain any layers."
                f" Instance \"{name}\" not created."
            )
            return None

        instance_data["layers"] = group_layers
        return context.create_instance(**instance_data)

    def create_render_pass(self, context, instance_data):
        # Change family to `renderLayer`
        instance_data["family"] = "renderLayer"
        instance_data["families"] = [instance_data["family"]]

        layers_data = context.data["layersData"]
        layers_by_id = {
            layer["layer_id"]: layer
            for layer in layers_data
        }

        group_id = instance_data["group_id"]
        layer_ids = instance_data["layer_ids"]
        render_pass_layers = []
        for layer_id in layer_ids:
            layer = layers_by_id.get(layer_id)
            if not layer:
                self.log.warning(f"Layer with id {layer_id} was not found.")
                continue

            # Move to validator?
            if layer["group_id"] != group_id:
                self.log.warning(
                    f"Layer with id {layer_id} is in different group."
                )
                continue
            render_pass_layers.append(layer)

        if not render_pass_layers:
            name = instance_data["name"]
            self.log.warning(
                f"All layers from RenderPass \"{name}\" do not exist."
                " Instance not created."
            )
            return None

        instance_data["layers"] = render_pass_layers
        return context.create_instance(**instance_data)
