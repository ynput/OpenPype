import os

import pyblish.api


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

        if instance.data.get("representations"):
            instance.data["representations"].extend(representations)
        else:
            instance.data["representations"] = representations

        version_name = "{}_{}".format(instance.data["subset"],
                                      os.environ["AVALON_TASK"])

        instance.data["version_name"] = version_name

        instance.data["stagingDir"] = staging_dir
        # for rev_instance in instance.context:
        #     if rev_instance.data["family"] in ["review"]:
        #         if rev_instance.data["version_name"] == version_name:
        #             rev_instance_reps = rev_instance.data["representations"]
        #             instance.data["representations"].extend(rev_instance_reps)

        self.log.info(f"Extracted {instance} to {staging_dir}")
