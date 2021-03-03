from avalon.tvpaint import pipeline, lib
from pype.hosts.tvpaint.api import plugin


class CreateRenderPass(plugin.Creator):
    """Render pass is combination of one or more layers from same group.

    Requirement to create Render Pass is to have already created beauty
    instance. Beauty instance is used as base for subset name.
    """
    name = "render_pass"
    label = "RenderPass"
    family = "renderPass"
    icon = "cube"
    defaults = ["Main"]

    subset_template = "{family}_{render_layer}_{pass}"

    def process(self):
        self.log.debug("Query data from workfile.")
        instances = pipeline.list_instances()
        layers_data = lib.layers_data()

        self.log.debug("Checking selection.")
        # Get all selected layers and their group ids
        group_ids = set()
        selected_layers = []
        for layer in layers_data:
            if layer["selected"]:
                selected_layers.append(layer)
                group_ids.add(layer["group_id"])

        # Raise if nothing is selected
        if not selected_layers:
            raise AssertionError("Nothing is selected.")

        # Raise if layers from multiple groups are selected
        if len(group_ids) != 1:
            raise AssertionError("More than one group is in selection.")

        group_id = tuple(group_ids)[0]
        self.log.debug(f"Selected group id is \"{group_id}\".")

        # Find beauty instance for selected layers
        beauty_instance = None
        for instance in instances:
            if (
                instance["family"] == "renderLayer"
                and instance["group_id"] == group_id
            ):
                beauty_instance = instance
                break

        # Beauty is required for this creator so raise if was not found
        if beauty_instance is None:
            raise AssertionError("Beauty pass does not exist yet.")

        render_layer = beauty_instance["name"]

        # Extract entered name
        family = self.data["family"]
        name = self.data["subset"]
        # Is this right way how to get name?
        name = name[len(family):]
        self.log.info(f"Extracted name from subset name \"{name}\".")

        self.data["group_id"] = group_id
        self.data["pass"] = name
        self.data["render_layer"] = render_layer

        # Collect selected layer ids to be stored into instance
        layer_names = [layer["name"] for layer in selected_layers]
        self.data["layer_names"] = layer_names

        # Replace `beauty` in beauty's subset name with entered name
        subset_name = self.subset_template.format(**{
            "family": family,
            "render_layer": render_layer,
            "pass": name
        })
        self.data["subset"] = subset_name
        self.log.info(f"New subset name is \"{subset_name}\".")

        # Check if same instance already exists
        existing_instance = None
        existing_instance_idx = None
        for idx, instance in enumerate(instances):
            if (
                instance["family"] == family
                and instance["group_id"] == group_id
                and instance["pass"] == name
            ):
                existing_instance = instance
                existing_instance_idx = idx
                break

        if existing_instance is not None:
            self.log.info(
                f"Render pass instance for group id {group_id}"
                f" and name \"{name}\" already exists, overriding."
            )
            instances[existing_instance_idx] = self.data
        else:
            instances.append(self.data)

        self.write_instances(instances)
