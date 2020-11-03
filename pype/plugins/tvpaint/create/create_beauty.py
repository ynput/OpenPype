import avalon.io
from avalon.tvpaint import pipeline, CommunicationWrapper


class CreateBeauty(pipeline.TVPaintCreator):
    """Arnold Archive"""

    name = "beauty"
    label = "Beauty"
    family = "renderLayer"
    icon = "cube"
    defaults = ["Main"]

    subset_template = "{family}{task}_{name}_{pass}"

    def process(self):
        instances = pipeline.list_instances()
        layers_data = CommunicationWrapper.layers_data()
        group_ids = set()
        for layer in layers_data:
            if layer["selected"]:
                group_ids.add(layer["group_id"])

        if not group_ids:
            raise AssertionError("Nothing is selected.")

        if len(group_ids) > 1:
            raise AssertionError("More than one group is in selection.")

        group_id = tuple(group_ids)[0]

        existing_instance = None
        existing_instance_idx = None
        for idx, instance in enumerate(instances):
            if (
                instance["family"] == self.family
                and instance["group_id"] == group_id
            ):
                existing_instance = instance
                existing_instance_idx = idx
                break

        self.data["group_id"] = group_id

        name = self.data["subset"]
        self.data["name"] = name

        subset_name = self.subset_template.format(**{
            "family": self.family,
            "task": avalon.io.Session["AVALON_TASK"],
            "name": name,
            "pass": "beauty"
        })
        self.data["subset"] = subset_name

        if existing_instance is not None:
            if existing_instance == self.data:
                self.log.info("Instance to create is same. Did nothing.")
                return
            instances[existing_instance_idx] = self.data
        else:
            instances.append(self.data)

        self.write_instances(instances)
