import os

import pythoncom

import pyblish.api


class CollectReview(pyblish.api.ContextPlugin):
    """Gather the active document as review instance."""

    label = "Review Media"
    order = pyblish.api.CollectorOrder
    hosts = ["photoshop"]
    reviewable_families = ["image", "workfile"]
    def process(self, context):
        # Necessary call when running in a different thread which pyblish-qml
        # can be.
        pythoncom.CoInitialize()

        family = "review"
        task = os.getenv("AVALON_TASK", None)
        sanitized_task_name = task[0].upper() + task[1:]
        subset = "{}{}".format(family, sanitized_task_name)

        file_path = context.data["currentFile"]
        base_name = os.path.basename(file_path)

        for reviewable_instance in context:
            if reviewable_instance.data["family"] in self.reviewable_families:
                self.label = ("Review Media ({})"
                              .format(reviewable_instance.data["name"]))
                instance = context.create_instance(subset)
                instance.data.update({
                    "subset": reviewable_instance.data["subset"],
                    "label": "Review Media",
                    "name": reviewable_instance.data["name"],
                    "family": family,
                    "families": ["paired_media"],
                    "representations": [],
                    "asset": os.environ["AVALON_ASSET"]
                })
