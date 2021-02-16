import pyblish.api
import os


class CollectWorkfile(pyblish.api.ContextPlugin):
    """Collect current script for publish."""

    order = pyblish.api.CollectorOrder + 0.1
    label = "Collect Workfile"
    hosts = ["photoshop"]

    def process(self, context):
        family = "workfile"
        task = os.getenv("AVALON_TASK", None)
        subset = family + task.capitalize()

        file_path = context.data["currentFile"]
        staging_dir = os.path.dirname(file_path)
        base_name = os.path.basename(file_path)

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

        # creating representation
        instance.data["representations"].append({
            "name": "psd",
            "ext": "psd",
            "files": base_name,
            "stagingDir": staging_dir,
        })
