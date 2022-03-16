from openpype.pipeline import CreatorError
from openpype.lib import prepare_template_data
from openpype.hosts.tvpaint.api import (
    plugin,
    pipeline,
    lib,
    CommunicationWrapper
)


class CreateRenderlayer(plugin.Creator):
    """Mark layer group as one instance."""
    name = "render_layer"
    label = "RenderLayer"
    family = "renderLayer"
    icon = "cube"
    defaults = ["Main"]

    rename_group = True
    render_pass = "beauty"

    rename_script_template = (
        "tv_layercolor \"setcolor\""
        " {clip_id} {group_id} {r} {g} {b} \"{name}\""
    )

    dynamic_subset_keys = ["render_pass", "render_layer", "group"]

    @classmethod
    def get_dynamic_data(
        cls, variant, task_name, asset_id, project_name, host_name
    ):
        dynamic_data = super(CreateRenderlayer, cls).get_dynamic_data(
            variant, task_name, asset_id, project_name, host_name
        )
        # Use render pass name from creator's plugin
        dynamic_data["render_pass"] = cls.render_pass
        # Add variant to render layer
        dynamic_data["render_layer"] = variant
        # Change family for subset name fill
        dynamic_data["family"] = "render"

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
            layers_data = lib.get_layers_data()

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
        layers_data = lib.get_layers_data()

        self.log.debug("Checking for selection groups.")
        # Collect group ids from selection
        group_ids = set()
        for layer in layers_data:
            if layer["selected"]:
                group_ids.add(layer["group_id"])

        # Raise if there is no selection
        if not group_ids:
            raise CreatorError("Nothing is selected.")

        # This creator should run only on one group
        if len(group_ids) > 1:
            raise CreatorError("More than one group is in selection.")

        group_id = tuple(group_ids)[0]
        # If group id is `0` it is `default` group which is invalid
        if group_id == 0:
            raise CreatorError(
                "Selection is not in group. Can't mark selection as Beauty."
            )

        self.log.debug(f"Selected group id is \"{group_id}\".")
        self.data["group_id"] = group_id

        group_data = lib.get_groups_data()
        group_name = None
        for group in group_data:
            if group["group_id"] == group_id:
                group_name = group["name"]
                break

        if group_name is None:
            raise AssertionError(
                "Couldn't find group by id \"{}\"".format(group_id)
            )

        subset_name_fill_data = {
            "group": group_name
        }

        family = self.family = self.data["family"]

        # Fill dynamic key 'group'
        subset_name = self.data["subset"].format(
            **prepare_template_data(subset_name_fill_data)
        )
        self.data["subset"] = subset_name

        # Check for instances of same group
        existing_instance = None
        existing_instance_idx = None
        # Check if subset name is not already taken
        same_subset_instance = None
        same_subset_instance_idx = None
        for idx, instance in enumerate(instances):
            if instance["family"] == family:
                if instance["group_id"] == group_id:
                    existing_instance = instance
                    existing_instance_idx = idx
                elif instance["subset"] == subset_name:
                    same_subset_instance = instance
                    same_subset_instance_idx = idx

            if (
                same_subset_instance_idx is not None
                and existing_instance_idx is not None
            ):
                break

        if same_subset_instance_idx is not None:
            if self._ask_user_subset_override(same_subset_instance):
                instances.pop(same_subset_instance_idx)
            else:
                return

        if existing_instance is not None:
            self.log.info(
                f"Beauty instance for group id {group_id} already exists"
                ", overriding"
            )
            instances[existing_instance_idx] = self.data
        else:
            instances.append(self.data)

        self.write_instances(instances)

        if not self.rename_group:
            self.log.info("Group rename function is turned off. Skipping")
            return

        self.log.debug("Querying groups data from workfile.")
        groups_data = lib.get_groups_data()

        self.log.debug("Changing name of the group.")
        selected_group = None
        for group_data in groups_data:
            if group_data["group_id"] == group_id:
                selected_group = group_data

        # Rename TVPaint group (keep color same)
        # - groups can't contain spaces
        new_group_name = self.data["variant"].replace(" ", "_")
        rename_script = self.rename_script_template.format(
            clip_id=selected_group["clip_id"],
            group_id=selected_group["group_id"],
            r=selected_group["red"],
            g=selected_group["green"],
            b=selected_group["blue"],
            name=new_group_name
        )
        lib.execute_george_through_file(rename_script)

        self.log.info(
            f"Name of group with index {group_id}"
            f" was changed to \"{new_group_name}\"."
        )

    def _ask_user_subset_override(self, instance):
        from Qt import QtCore
        from Qt.QtWidgets import QMessageBox

        title = "Subset \"{}\" already exist".format(instance["subset"])
        text = (
            "Instance with subset name \"{}\" already exists."
            "\n\nDo you want to override existing?"
        ).format(instance["subset"])

        dialog = QMessageBox()
        dialog.setWindowFlags(
            dialog.windowFlags()
            | QtCore.Qt.WindowStaysOnTopHint
        )
        dialog.setWindowTitle(title)
        dialog.setText(text)
        dialog.setStandardButtons(QMessageBox.Yes | QMessageBox.No)
        dialog.setDefaultButton(QMessageBox.Yes)
        dialog.exec_()
        if dialog.result() == QMessageBox.Yes:
            return True
        return False
