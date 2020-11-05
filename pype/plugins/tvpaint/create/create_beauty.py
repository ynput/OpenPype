import avalon.io
from avalon.tvpaint import pipeline, lib


class CreateBeauty(pipeline.TVPaintCreator):
    name = "beauty"
    label = "Beauty"
    family = "renderLayer"
    icon = "cube"
    defaults = ["Main"]

    subset_template = "{family}{task}_{name}_{pass}"
    rename_script_template = (
        "tv_layercolor \"setcolor\""
        " {clip_id} {group_id} {r} {g} {b} \"{name}\""
    )

    def process(self):
        instances = pipeline.list_instances()
        groups_data = lib.groups_data()
        layers_data = lib.layers_data()
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

        family = self.data["family"]
        name = self.data["subset"]
        # Is this right way how to get name?
        name = name[len(family):]
        self.data["group_id"] = group_id
        self.data["name"] = name

        subset_name = self.subset_template.format(**{
            "family": self.family,
            "task": avalon.io.Session["AVALON_TASK"],
            "name": name,
            "pass": "beauty"
        })
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
            if existing_instance == self.data:
                self.log.info("Instance to create is same. Did nothing.")
                return
            instances[existing_instance_idx] = self.data
        else:
            instances.append(self.data)

        self.write_instances(instances)

        group = None
        for group_data in groups_data:
            if group_data["id"] == group_id:
                group = group_data

        if not group:
            return

        new_group_name = name.replace(" ", "_")

        rename_script = self.rename_script_template.format(
            clip_id=group["clip_id"],
            group_id=group["id"],
            r=group["red"],
            g=group["green"],
            b=group["blue"],
            name=new_group_name
        )
        lib.execute_george_through_file(rename_script)
