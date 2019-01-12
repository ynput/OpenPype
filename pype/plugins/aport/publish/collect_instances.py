import os
import json
import pyblish.api
from avalon import (
    io,
    api as avalon
)


class CollectInstancesFromJson(pyblish.api.ContextPlugin):
    """
    Collecting temp json data sent from a host context
    and path for returning json data back to hostself.

    Setting avalon session into correct context

    Args:
        context (obj): pyblish context session

    """

    label = "Collect instances from JSON"
    order = pyblish.api.CollectorOrder - 0.05

    def process(self, context):
        json_data = context.data.get("json_data", None)
        instances_data = json_data.get("instances", None)
        assert instances_data, "No `instance` data in json file"

        presets = context.data["presets"]
        rules_tasks = presets["rules_tasks"]

        instances = []
        for inst in instances_data:
            # for key, value in inst.items():
            #     self.log.debug('instance[key]: {}'.format(key))
            #
            name = asset = inst.get("name", None)
            assert name, "No `name` key in json_data.instance: {}".format(inst)

            family = inst.get("family", None)
            assert family, "No `family` key in json_data.instance: {}".format(inst)

            tags = inst.get("tags", None)
            if tags:
                tasks = [t["task"] for t in tags
                         if t.get("task")]
            else:
                tasks = rules_tasks["defaultTasks"]
            self.log.debug("tasks: `{}`".format(tasks))

            for task in tasks:
                host = rules_tasks["taskHost"][task]
                subsets = rules_tasks["taskSubsets"][task]

                for subset in subsets:
                    subset_name = "{0}_{1}".format(task, subset)
                    instance = context.create_instance(subset_name)
                    # instance.add(inst)
                    instance.data.update({
                        "subset": subset_name,
                        "task": task,
                        "host": host,
                        "asset": asset,
                        "label": "{0} - {1} > {2}".format(name, task, subset),
                        "name": subset_name,
                        "family": inst["family"],
                        "families": [subset],
                        "jsonData": inst,
                        "publish": True,
                    })
                    self.log.info("collected instance: {}".format(instance.data))
                    instances.append(instance)

        context.data["instances"] = instances

        # Sort/grouped by family (preserving local index)
        # context[:] = sorted(context, key=self.sort_by_task)

        self.log.debug("context: {}".format(context))

    def sort_by_task(self, instance):
        """Sort by family"""
        return instance.data.get("task", instance.data.get("task"))
