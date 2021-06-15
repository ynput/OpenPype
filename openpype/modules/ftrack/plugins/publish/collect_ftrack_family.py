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
        if self.profiles:
            anatomy_data = instance.context.data["anatomyData"]
            task_name = anatomy_data.get("task",
                                         os.environ["AVALON_TASK"])
            host_name = anatomy_data.get("app",
                                         os.environ["AVALON_APP"])
            family = instance.data["family"]

            filtering_criteria = {
                "hosts": host_name,
                "families": family,
                "tasks": task_name
            }
            profile = filter_profiles(self.profiles, filtering_criteria)

            if profile:
                families = instance.data.get("families")
                if profile["add_ftrack_family"]:
                    self.log.debug("Adding ftrack family")
                    if families and "ftrack" not in families:
                        instance.data["families"].append("ftrack")
                    else:
                        instance.data["families"] = ["ftrack"]
                else:
                    self.log.debug("Removing ftrack family if present")
                    if families and "ftrack" in families:
                        instance.data["families"].pop("ftrack")

        self.log.debug("instance.data:: {}".format(instance.data))
