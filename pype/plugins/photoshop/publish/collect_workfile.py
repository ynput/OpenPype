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
        subset = base_name.split("_")[2]
        if subset == task:
            subset = "Main"

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
        psd = {
            "name": "psd",
            "ext": "psd",
            "files": base_name,
            "stagingDir": staging_dir,
        }

        representations = [psd]

        image_context_instance = instance.context.data.get("image_instance")
        if image_context_instance:
            if image_context_instance.data.get("representations"):
                image_context_instance.data["representations"].extend(
                    representations)
            else:
                image_context_instance.data["representations"] = \
                    representations
            # Required for extract_review plugin (L222 onwards).
            image_context_instance.data["frameStart"] = 1
            image_context_instance.data["frameEnd"] = 1
            image_context_instance.data["fps"] = 24
            instance.data["families"].append("paired_media")
            self.log.info(f"Extracted {instance} to {staging_dir}")

        else:

            if instance.data.get("representations"):
                instance.data["representations"].extend(representations)
            else:
                instance.data["representations"] = representations



