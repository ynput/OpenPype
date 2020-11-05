import tempfile
import avalon.io
from avalon.tvpaint import pipeline, lib


class CreateRenderPass(pipeline.TVPaintCreator):
    """Render pass is combination of one or more layers from same group.

    Requirement to create Render Pass is to have already created beauty
    instance. Beauty instance is used as base for subset name.
    """
    name = "render_pass"
    label = "Render Pass"
    family = "renderPass"
    icon = "cube"
    defaults = ["Main"]

    beauty_pass_name = "beauty"

    def process(self):
        self.log.debug("Query data from workfile.")
        instances = pipeline.list_instances()
        layers_data = lib.layers_data()

        self.log.debug("Checking selection.")
        group_ids = set()
        selected_layers = []
        for layer in layers_data:
            if layer["selected"]:
                selected_layers.append(layer)
                group_ids.add(layer["group_id"])

        if not selected_layers:
            raise AssertionError("Nothing is selected.")

        if len(group_ids) != 1:
            raise AssertionError("More than one group is in selection.")

        group_id = tuple(group_ids)[0]
        self.log.debug(f"Selected group id is \"{group_id}\".")

        beauty_instance = None
        for instance in instances:
            if (
                instance["family"] == "renderLayer"
                and instance["group_id"] == group_id
            ):
                beauty_instance = instance
                break

        if beauty_instance is None:
            raise AssertionError("Beauty pass does not exist yet.")

        family = self.data["family"]
        name = self.data["subset"]
        # Is this right way how to get name?
        name = name[len(family):]
        self.log.info(f"Extracted name from subset name \"{name}\".")

        self.data["group_id"] = group_id
        self.data["name"] = name

        layer_ids = [layer["id"] for layer in selected_layers]
        self.data["layer_ids"] = layer_ids

        beauty_subset_name = beauty_instance["subset"]
        self.log.info(
            "New subset name will be created from "
            f"beauty instance \"{beauty_subset_name}\"."
        )

        if not beauty_subset_name.endswith(self.beauty_pass_name):
            raise AssertionError(
                "BUG: Beauty subset name does not end with \"{}\"".format(
                    self.beauty_pass_name
                )
            )
        subset_name = beauty_subset_name[:-len(self.beauty_pass_name)] + name
        self.data["subset"] = subset_name
        self.log.info(f"New subset name is \"{subset_name}\".")

        existing_instance = None
        existing_instance_idx = None
        for idx, instance in enumerate(instances):
            if (
                instance["family"] == family
                and instance["group_id"] == group_id
                and instance["name"] == name
            ):
                existing_instance = instance
                existing_instance_idx = idx
                break

        if existing_instance is not None:
            self.log.info(
                f"Render pass instance for group id {group_id}"
                f" and name \"{name}\" already exists."
            )
            if existing_instance == self.data:
                self.log.info("Instance to create is same. Did nothing.")
                return
            self.log.debug("Overriding beauty instance with new data.")
            instances[existing_instance_idx] = self.data
        else:
            instances.append(self.data)

        self.write_instances(instances)
