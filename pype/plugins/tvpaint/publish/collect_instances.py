import json

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
            asset_name = instance_data["asset"]
            subset_name = instance_data["subset"]
            family = instance_data["family"]
            name = instance_data.get("name", subset_name)
            active = instance_data.get("active", True)

            instance = context.create_instance(
                name=name,
                family=family,
                families=[family],
                subset=subset_name,
                asset=asset_name,
                active=active,
                publish=active,
            )
            self.log.debug(instance)
