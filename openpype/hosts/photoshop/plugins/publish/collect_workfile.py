import os
import pyblish.api

from openpype.pipeline.create import get_subset_name


class CollectWorkfile(pyblish.api.ContextPlugin):
    """Collect current script for publish."""

    order = pyblish.api.CollectorOrder + 0.1
    label = "Collect Workfile"
    hosts = ["photoshop"]

    default_variant = "Main"

    def process(self, context):
        for instance in context:
            if instance.data["family"] == "workfile":
                file_path = context.data["currentFile"]
                _, ext = os.path.splitext(file_path)
                staging_dir = os.path.dirname(file_path)
                base_name = os.path.basename(file_path)

                # creating representation
                _, ext = os.path.splitext(file_path)
                instance.data["representations"].append({
                    "name": ext[1:],
                    "ext": ext[1:],
                    "files": base_name,
                    "stagingDir": staging_dir,
                })
                return
