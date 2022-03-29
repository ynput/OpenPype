import os
import pyblish.api

from openpype.lib import get_subset_name


class CollectWorkfile(pyblish.api.ContextPlugin):
    """Collect current script for publish."""

    order = pyblish.api.CollectorOrder + 0.1
    label = "Collect Workfile"
    hosts = ["photoshop"]

    def process(self, context):
        existing_instance = None
        for instance in context:
            if instance.data["family"] == "workfile":
                self.log.debug("Workfile instance found, won't create new")
                existing_instance = instance
                break

        family = "workfile"
        task = os.getenv("AVALON_TASK", None)
        subset = get_subset_name(
            family,
            "",
            task,
            context.data["assetEntity"]["_id"],
            host_name="photoshop"
        )

        file_path = context.data["currentFile"]
        staging_dir = os.path.dirname(file_path)
        base_name = os.path.basename(file_path)

        # Create instance
        if existing_instance is None:
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
        else:
            instance = existing_instance

        # creating representation
        _, ext = os.path.splitext(file_path)
        instance.data["representations"].append({
            "name": ext[1:],
            "ext": ext[1:],
            "files": base_name,
            "stagingDir": staging_dir,
        })
