from openpype.pipeline import CreatorError
from openpype.lib import prepare_template_data
from openpype.hosts.tvpaint.api import (
    plugin,
    pipeline,
    lib,
    CommunicationWrapper
)


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

    dynamic_subset_keys = [
        "renderpass", "renderlayer", "render_pass", "render_layer"
    ]

    @classmethod
    def get_dynamic_data(
        cls, variant, task_name, asset_id, project_name, host_name
    ):
        dynamic_data = super(CreateRenderPass, cls).get_dynamic_data(
            variant, task_name, asset_id, project_name, host_name
        )
        dynamic_data["renderpass"] = variant
        dynamic_data["family"] = "render"

        # TODO remove - Backwards compatibility for old subset name templates
        # - added 2022/04/28
        dynamic_data["render_pass"] = dynamic_data["renderpass"]

        return dynamic_data

    @classmethod
    def get_default_variant(cls):
        """Default value for variant in Creator tool.

        Method checks if TVPaint implementation is running and tries to find
        selected layers from TVPaint. If only one is selected it's name is
        returned.

        Returns:
            str: Default variant name for Creator tool.
        """
        # Validate that communication is initialized
        if CommunicationWrapper.communicator:
            # Get currently selected layers
            layers_data = lib.layers_data()

            selected_layers = [
                layer
                for layer in layers_data
                if layer["selected"]
            ]
            # Return layer name if only one is selected
            if len(selected_layers) == 1:
                return selected_layers[0]["name"]

        # Use defaults
        if cls.defaults:
            return cls.defaults[0]
        return None

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
            raise CreatorError("Nothing is selected.")

        # Raise if layers from multiple groups are selected
        if len(group_ids) != 1:
            raise CreatorError("More than one group is in selection.")

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
            raise CreatorError("Beauty pass does not exist yet.")

        subset_name = self.data["subset"]

        subset_name_fill_data = {}

        # Backwards compatibility
        # - beauty may be created with older creator where variant was not
        #   stored
        if "variant" not in beauty_instance:
            render_layer = beauty_instance["name"]
        else:
            render_layer = beauty_instance["variant"]

        subset_name_fill_data["renderlayer"] = render_layer
        subset_name_fill_data["render_layer"] = render_layer

        # Format dynamic keys in subset name
        new_subset_name = subset_name.format(
            **prepare_template_data(subset_name_fill_data)
        )
        self.data["subset"] = new_subset_name
        self.log.info(f"New subset name is \"{new_subset_name}\".")

        family = self.data["family"]
        variant = self.data["variant"]

        self.data["group_id"] = group_id
        self.data["pass"] = variant
        self.data["renderlayer"] = render_layer

        # Collect selected layer ids to be stored into instance
        layer_names = [layer["name"] for layer in selected_layers]
        self.data["layer_names"] = layer_names

        # Check if same instance already exists
        existing_instance = None
        existing_instance_idx = None
        for idx, instance in enumerate(instances):
            if (
                instance["family"] == family
                and instance["group_id"] == group_id
                and instance["pass"] == variant
            ):
                existing_instance = instance
                existing_instance_idx = idx
                break

        if existing_instance is not None:
            self.log.info(
                f"Render pass instance for group id {group_id}"
                f" and name \"{variant}\" already exists, overriding."
            )
            instances[existing_instance_idx] = self.data
        else:
            instances.append(self.data)

        self.write_instances(instances)
