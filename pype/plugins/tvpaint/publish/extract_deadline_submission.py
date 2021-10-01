import json
import os
import tempfile

import pyblish.api
from avalon.tvpaint import HEADLESS


class ExtractDeadlineSubmission(pyblish.api.ContextPlugin):
    label = "Extract Deadline Submission"
    order = pyblish.api.ExtractorOrder
    hosts = ["tvpaint"]
    families = ["deadline"]

    def process(self, context):
        # Skip extract if in headless mode.
        if HEADLESS:
            return

        # Adding "deadline" family to all active instances to skip
        # integration, except workfile.
        workfile_instance = None
        for instance in context:
            families = instance.data.get(
                "families", [instance.data["family"]]
            )
            if "workfile" in families:
                workfile_instance = instance
                continue

            if "deadline" not in families:
                instance.data["families"].append("deadline")

        # Remove instances from workfileInstances that are not marked as
        # publishable.
        publish_state_by_uuid = {}
        for instance in context:
            uuid = instance.data.get("uuid")
            if not uuid:
                continue

            publish_state_by_uuid[uuid] = instance.data["publish"]

        publishable_instances = []
        for instance in context.data["jsonData"]["workfileInstances"]:
            if publish_state_by_uuid[instance["uuid"]]:
                publishable_instances.append(instance)
        context.data["jsonData"]["workfileInstances"] = publishable_instances

        # Extract data for deadline submission.
        name = os.path.splitext(workfile_instance.data["name"])[0]
        basename = "pype_" + name + ".json"
        path = os.path.join(tempfile.gettempdir(), basename)
        with open(path, "w") as f:
            json.dump(
                context.data["jsonData"], f, sort_keys=True, indent=4
            )
        self.log.info(
            "Extracted submission data to \"{}\":\n{}".format(
                path, context.data["jsonData"]
            )
        )

        workfile_instance.data["representations"].append(
            {
                "name": "json",
                "ext": "json",
                "files": basename,
                "stagingDir": tempfile.gettempdir()
            }
        )
