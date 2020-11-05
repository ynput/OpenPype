import avalon.io
from avalon.tvpaint import pipeline, lib


class CreateBeauty(pipeline.TVPaintCreator):
    """Mark layer group as one instance."""
    name = "beauty"
    label = "Beauty"
    family = "renderLayer"
    icon = "cube"
    defaults = ["Main"]

    rename_group = True

    subset_template = "{family}{task}_{name}_{pass}"
    rename_script_template = (
        "tv_layercolor \"setcolor\""
        " {clip_id} {group_id} {r} {g} {b} \"{name}\""
    )

    def process(self):
        self.log.debug("Query data from workfile.")
        instances = pipeline.list_instances()
        groups_data = lib.groups_data()
        layers_data = lib.layers_data()

        self.log.debug("Checking for selection groups.")
        group_ids = set()
        for layer in layers_data:
            if layer["selected"]:
                group_ids.add(layer["group_id"])

        if not group_ids:
            raise AssertionError("Nothing is selected.")

        if len(group_ids) > 1:
            raise AssertionError("More than one group is in selection.")

        group_id = tuple(group_ids)[0]
        if group_id == 0:
            raise AssertionError(
                "Selection is not in group. Can't mark selection as Beauty."
            )

        self.log.debug(f"Selected group id is \"{group_id}\".")
        self.data["group_id"] = group_id

        family = self.data["family"]
        # Is this right way how to get name?
        name = self.data["subset"][len(family):]
        self.log.info(f"Extracted name from subset name \"{name}\".")
        self.data["name"] = name

        subset_name = self.subset_template.format(**{
            "family": self.family,
            # Should be task name capitalized?
            "task": avalon.io.Session["AVALON_TASK"],
            "name": name,
            "pass": "beauty"
        })
        self.log.info(f"New subset name \"{subset_name}\".")
        self.data["subset"] = subset_name

        existing_instance = None
        existing_instance_idx = None
        for idx, instance in enumerate(instances):
            if (
                instance["family"] == family
                and instance["group_id"] == group_id
            ):
                existing_instance = instance
                existing_instance_idx = idx
                break

        if existing_instance is not None:
            self.log.info(
                f"Beauty instance for group id {group_id} already exists."
            )
            if existing_instance == self.data:
                self.log.info("Instance to create is same. Did nothing.")
                return
            self.log.debug("Overriding beauty instance with new data.")
            instances[existing_instance_idx] = self.data
        else:
            instances.append(self.data)

        self.write_instances(instances)

        if not self.rename_group:
            self.log.info("Group rename function is turned off. Skipping")
            return

        self.log.debug("Changing name of the group.")
        selected_group = None
        for group_data in groups_data:
            if group_data["id"] == group_id:
                selected_group = group_data

        new_group_name = name.replace(" ", "_")
        rename_script = self.rename_script_template.format(
            clip_id=selected_group["clip_id"],
            group_id=selected_group["id"],
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
