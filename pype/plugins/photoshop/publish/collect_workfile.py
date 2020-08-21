import os

import pyblish.api


class CollectWorkfile(pyblish.api.ContextPlugin):
    """Collect current script for publish."""

    order = pyblish.api.CollectorOrder + 0.1
    label = "Collect Photoshop Document"
    hosts = ["photoshop"]
    pair_media = True

    def process(self, context):
        family = "workfile"#"layeredimage"
        task = os.getenv("AVALON_TASK", None)
        file_path = context.data["currentFile"]
        staging_dir = os.path.dirname(file_path)
        base_name = os.path.basename(file_path)

        anatomy_data = context.data["anatomyData"]
        self.log.info("Anatomy Data: {}".format(anatomy_data))
        subset = anatomy_data.get("subset", "workfileMain")

        # Create instance
        instance = context.create_instance(subset)
        instance.data.update({
            "subset": subset,
            "label": base_name,
            "name": base_name,
            "family": family,
            "families": ["ftrack"],
            "asset": os.environ["AVALON_ASSET"],
            "stagingDir": staging_dir
        })

        # creating representation
        psd = {
            "name": "psd",
            "ext": "psd",
            "files": base_name,
            "stagingDir": staging_dir,
        }

        representations = [psd]

        instance.data["version_name"] = "{}_{}".format(subset, task)
        instance.data["stagingDir"] = staging_dir

        if instance.data.get("representations"):
            instance.data["representations"].extend(representations)
        else:
            instance.data["representations"] = representations

        # If set in plugin, pair the workfile Version in ftrack with
        # thumbnails and review media.
        if self.pair_media:
            context.data["workfile_instance"] = instance

        self.log.info(f"Extracted {instance} to {staging_dir}")
