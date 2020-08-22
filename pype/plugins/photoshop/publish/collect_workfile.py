import os
import pyblish.api

from pype.api import Anatomy

class CollectWorkfile(pyblish.api.ContextPlugin):
    """Collect current script for publish."""

    order = pyblish.api.CollectorOrder + 0.1
    label = "Collect Workfile"
    hosts = ["photoshop"]

    def process(self, context):
        family = "layeredimage"
        task = os.getenv("AVALON_TASK", None)
        sanitized_task_name = task[0].upper() + task[1:]
        # subset = "{}{}".format(family, sanitized_task_name)

        file_path = context.data["currentFile"]
        #@TODO: This is horrible... but will work
        # Attempt to get subset from workfile name
        subset = "layeredimageMain"

        staging_dir = os.path.dirname(file_path)
        base_name = os.path.basename(file_path)

        # Create instance
        instance = context.create_instance(subset)
        instance.data.update({
            "subset": subset,
            "label": base_name,
            "name": base_name,
            "family": family,
            "families": ["ftrack"],
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

        instance.data["version_name"] = "{}_{}".format(subset,task)

        self.log.info(f"Extracted {instance} to {staging_dir}")