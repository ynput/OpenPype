import pyblish.api
import os


class CollectWorkfile(pyblish.api.ContextPlugin):
    """Collect current script for publish."""

    order = pyblish.api.CollectorOrder + 0.1
    label = "Collect Photoshop Document"
    hosts = ["photoshop"]

    def process(self, context):
        family = "workfile"
        task = os.getenv("AVALON_TASK", None)
        file_path = context.data["currentFile"]
        staging_dir = os.path.dirname(file_path)
        base_name = os.path.basename(file_path)
        subset = "main"

        # Create instance
        instance = context.create_instance(subset)
        instance.data.update({
            "subset": subset,
            "label": base_name,
            "name": base_name,
            "family": family,
            "families": ["image", "ftrack"],
            "representations": [],
            "asset": os.environ["AVALON_ASSET"]
        })

        # creating representation
        psd = {
            "name": "psd",
            "ext": "psd",
            "files": base_name,
            "stagingDir": staging_dir,
        }

        representations = [psd]

        instance.data["version_name"] = "{}_{}". \
            format(instance.data["subset"],
                   os.environ["AVALON_TASK"])

        if instance.data.get("representations"):
            instance.data["representations"].extend(representations)
        else:
            instance.data["representations"] = representations



