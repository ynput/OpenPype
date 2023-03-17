"""
Requires:
    none

Provides:
    instance     -> families ([])
"""
import pyblish.api

from openpype.lib import filter_profiles


class CollectFtrackFamily(pyblish.api.InstancePlugin):
    """Adds explicitly 'ftrack' to families to upload instance to FTrack.

    Uses selection by combination of hosts/families/tasks names via
    profiles resolution.

    Triggered everywhere, checks instance against configured.

    Checks advanced filtering which works on 'families' not on main
    'family', as some variants dynamically resolves addition of ftrack
    based on 'families' (editorial drives it by presence of 'review')
    """

    label = "Collect Ftrack Family"
    order = pyblish.api.CollectorOrder + 0.4990

    profiles = None

    def process(self, instance):
        if not self.profiles:
            self.log.warning("No profiles present for adding Ftrack family")
            return

        host_name = instance.context.data["hostName"]
        family = instance.data["family"]
        task_name = instance.data.get("task")

        filtering_criteria = {
            "hosts": host_name,
            "families": family,
            "tasks": task_name
        }
        profile = filter_profiles(
            self.profiles,
            filtering_criteria,
            logger=self.log
        )

        add_ftrack_family = False
        families = instance.data.setdefault("families", [])

        if profile:
            add_ftrack_family = profile["add_ftrack_family"]
            additional_filters = profile.get("advanced_filtering")
            if additional_filters:
                families_set = set(families) | {family}
                self.log.info(
                    "'{}' families used for additional filtering".format(
                        families_set))
                add_ftrack_family = self._get_add_ftrack_f_from_addit_filters(
                    additional_filters,
                    families_set,
                    add_ftrack_family
                )

        result_str = "Not adding"
        if add_ftrack_family:
            result_str = "Adding"
            if "ftrack" not in families:
                families.append("ftrack")

        self.log.info("{} 'ftrack' family for instance with '{}'".format(
            result_str, family
        ))

    def _get_add_ftrack_f_from_addit_filters(
        self, additional_filters, families, add_ftrack_family
    ):
        """Compares additional filters - working on instance's families.

        Triggered for more detailed filtering when main family matches,
        but content of 'families' actually matter.
        (For example 'review' in 'families' should result in adding to
        Ftrack)

        Args:
            additional_filters (dict) - from Setting
            families (set[str]) - subfamilies
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
