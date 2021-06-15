"""
Requires:
    none

Provides:
    instance     -> families ([])
"""
import os
import pyblish.api

from openpype.lib.plugin_tools import filter_profiles


class CollectFtrackFamily(pyblish.api.InstancePlugin):
    """
        Adds explicitly 'ftrack' to families to upload instance to FTrack.

        Uses selection by combination of hosts/families/tasks names via
        profiles resolution.

        Triggered everywhere, checks instance against configured
    """
    label = "Collect Ftrack Family"
    order = pyblish.api.CollectorOrder + 0.4999

    profiles = None

    def process(self, instance):
        if not self.profiles:
            self.log.warning("No profiles present for adding Ftrack family")
            return

        anatomy_data = instance.context.data["anatomyData"]
        task_name = instance.data("task",
                                  instance.context.data["task"])
        host_name = anatomy_data.get("app",
                                     os.environ["AVALON_APP"])
        family = instance.data["family"]

        filtering_criteria = {
            "hosts": host_name,
            "families": family,
            "tasks": task_name
        }
        profile = filter_profiles(self.profiles, filtering_criteria)

        if profile and profile["add_ftrack_family"]:
            self.log.debug("Adding ftrack family")
            families = instance.data.get("families")
            if families and "ftrack" not in families:
                instance.data["families"].append("ftrack")
            else:
                instance.data["families"] = ["ftrack"]

        self.log.debug("instance.data:: {}".format(instance.data))
