import json

import pyblish.api
from avalon.tvpaint import pipeline


class CollectInstances(pyblish.api.ContextPlugin):
    label = "Collect Instances"
    order = pyblish.api.CollectorOrder
    hosts = ["tvpaint"]

    def process(self, context):
        workfile_instances = context.data["workfileInstances"]

        self.log.debug("Collected ({}) instances:\n{}".format(
            len(workfile_instances),
            json.dumps(workfile_instances, indent=4)
        ))

        # TODO add validations of existing instances
        # - layer id exists
        for workfile_instance in workfile_instances:
            # Fill families
            family = workfile_instance["family"]
            workfile_instance["families"] = [family]

            # Instance name
            subset_name = workfile_instance["subset"]
            name = workfile_instance.get("name", subset_name)
            workfile_instance["name"] = name

            active = workfile_instance.get("active", True)
            workfile_instance["active"] = active
            workfile_instance["publish"] = active

            instance = context.create_instance(**workfile_instance)
            self.log.debug("Created instance: {}".format(instance))
