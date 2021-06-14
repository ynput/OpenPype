"""
Requires:
    none

Provides:
    instance     -> families ([])
"""
import re
import pyblish.api


class CollectFtrackFamily(pyblish.api.InstancePlugin):
    """
        Adds explicitly 'ftrack' to families to upload instance to FTrack.

        Uses selection by combination of hosts/families/tasks names (regex)
    """
    label = "Collect FTrack Family"
    order = pyblish.api.CollectorOrder + 0.4999

    hosts = ["standalonepublisher"]
    families = ["render", "image"]
    tasks = ['.*']

    def process(self, instance):
        if self.tasks:
            anatomy_data = instance.context.data["anatomyData"]
            task_name = anatomy_data["task"].lower()

            if (not any([re.search(pattern, task_name)
                         for pattern in self.tasks])):
                self.log.debug("Task not matching, skipping.")
                return

        families = instance.data.get("families")
        if families:
            instance.data["families"].append("ftrack")
        else:
            instance.data["families"] = ["ftrack"]

        self.log.debug("instance.data:: {}".format(instance.data))
