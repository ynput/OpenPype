import os

import pyblish.api
from avalon.tvpaint import HEADLESS


class CollectDeadlineSubmission(pyblish.api.ContextPlugin):
    label = "Collect Deadline Submission"
    order = pyblish.api.CollectorOrder
    hosts = ["tvpaint"]
    publish = False

    def process(self, context):
        if HEADLESS:
            return

        if not context:
            self.log.debug("No instances were found.")
            return

        data = {
            "label": "Deadline Submission",
            "publish": self.publish,
            "family": "deadline",
            # Needed for collect_anatomy_instance_data
            "asset": os.environ["AVALON_ASSET"],
            "subset": ""
        }
        context.create_instance("deadlineSubmission", **data)
