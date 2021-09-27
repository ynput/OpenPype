"""
Requires:
    none

Provides:
    instance     -> families ([])
"""
import pyblish.api
import avalon.api

from openpype.lib.plugin_tools import filter_profiles


class CollectFtrackFamily(pyblish.api.InstancePlugin):
    """
        Adds explicitly 'ftrack' to families to upload instance to FTrack.

        Uses selection by combination of hosts/families/tasks names via
        profiles resolution.

        Triggered everywhere, checks instance against configured.

        Checks advanced filtering which works on 'families' not on main
        'family', as some variants dynamically resolves addition of ftrack
        based on 'families' (editorial drives it by presence of 'review')
    """
    label = "Collect Ftrack Family"
    order = pyblish.api.CollectorOrder + 0.4998

    profiles = None

    def process(self, instance):
        if not self.profiles:
            self.log.warning("No profiles present for adding Ftrack family")
            return

        task_name = instance.data.get("task",
                                      avalon.api.Session["AVALON_TASK"])
        host_name = avalon.api.Session["AVALON_APP"]
        family = instance.data["family"]

        filtering_criteria = {
            "hosts": host_name,
            "families": family,
            "tasks": task_name
        }
        profile = filter_profiles(self.profiles, filtering_criteria,
                                  logger=self.log)

        if profile:
            families = instance.data.get("families")
            add_ftrack_family = profile["add_ftrack_family"]

            additional_filters = profile.get("advanced_filtering")
            if additional_filters:
                add_ftrack_family = self._get_add_ftrack_f_from_addit_filters(
                    additional_filters,
                    families,
                    add_ftrack_family
                )

            if add_ftrack_family:
                self.log.debug("Adding ftrack family for '{}'".
                               format(instance.data.get("family")))

                if families:
                    if "ftrack" not in families:
                        instance.data["families"].append("ftrack")
                else:
                    instance.data["families"] = ["ftrack"]

    def _get_add_ftrack_f_from_addit_filters(self,
                                             additional_filters,
                                             families,
                                             add_ftrack_family):
        """
            Compares additional filters - working on instance's families.

            Triggered for more detailed filtering when main family matches,
            but content of 'families' actually matter.
            (For example 'review' in 'families' should result in adding to
            Ftrack)

            Args:
                additional_filters (dict) - from Setting
                families (list) - subfamilies
                add_ftrack_family (bool) - add ftrack to families if True
        """
        override_filter = None
        override_filter_value = -1
        for additional_filter in additional_filters:
            filter_families = set(additional_filter["families"])
            valid = filter_families <= set(families)  # issubset
            if not valid:
                continue

            value = len(filter_families)
            if value > override_filter_value:
                override_filter = additional_filter
                override_filter_value = value

        if override_filter:
            add_ftrack_family = override_filter["add_ftrack_family"]

        return add_ftrack_family
