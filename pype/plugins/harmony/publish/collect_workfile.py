import pyblish.api
import os


class CollectWorkfile(pyblish.api.ContextPlugin):
    """Collect current script for publish."""

    order = pyblish.api.CollectorOrder + 0.1
    label = "Collect Workfile"
    hosts = ["harmony"]

    def process(self, context):
        family = "workfile"
        task = os.getenv("AVALON_TASK", None)
        sanitized_task_name = task[0].upper() + task[1:]
        subset = "{}{}".format(family, sanitized_task_name)
        base_name = os.path.basename(context.data["currentFile"])

        # Create instance
        instance = context.create_instance(subset)
        instance.data.update({
            "subset": subset,
            "label": base_name,
            "name": base_name,
            "family": family,
            "families": [],
            "representations": [],
            "asset": os.environ["AVALON_ASSET"]
        })
