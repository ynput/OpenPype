import pyblish.api
import avalon.io
from avalon.tvpaint import pipeline


class CollectInstances(pyblish.api.ContextPlugin):
    label = "Collect Instances"
    order = pyblish.api.CollectorOrder
    hosts = ["tvpaint"]

    def process(self, context):
        self.log.info("Collecting instance data from workfile")
        instances_data = pipeline.list_instances()
        self.log.debug("Collected ({}) instances: {}".format(
            len(instances_data), instances_data
        ))

        # TODO add validations of existing instances
        # - layer id exists
        for instance_data in instances_data:
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

            instance = context.create_instance(**instance_data)
            self.log.debug("Created instance: {}".format(instance))
