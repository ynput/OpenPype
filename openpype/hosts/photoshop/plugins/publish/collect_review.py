import os

import pyblish.api


class CollectReview(pyblish.api.ContextPlugin):
    """Gather the active document as review instance."""

    label = "Review"
    order = pyblish.api.CollectorOrder
    hosts = ["photoshop"]

    def process(self, context):
        family = "review"

        families_whitelist = os.getenv("PYBLISH_FAMILY_WHITELIST")
        if families_whitelist:
            families_whitelist = families_whitelist.split(',')
        if families_whitelist:
            if family not in families_whitelist:
                self.log.info("Skipped instance with not whitelisted "
                              "family: {}".format(family))
                return

        task = os.getenv("AVALON_TASK", None)
        subset = family + task.capitalize()

        file_path = context.data["currentFile"]
        base_name = os.path.basename(file_path)

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
