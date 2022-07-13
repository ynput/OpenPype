"""Produces instance.data["subsetGroup"] data used during integration.

Requires:
    dict -> context["anatomyData"] *(pyblish.api.CollectorOrder + 0.49)

Provides:
    instance -> subsetGroup (str)

"""
import pyblish.api

from openpype.lib.profiles_filtering import filter_profiles
from openpype.lib import (
    prepare_template_data,
    StringTemplate,
    TemplateUnsolved
)


class CollectSubsetGroup(pyblish.api.InstancePlugin):
    """Collect Subset Group for publish."""

    # Run after CollectAnatomyInstanceData
    order = pyblish.api.CollectorOrder + 0.495
    label = "Collect Subset Group"

    # Attributes set by settings
    subset_grouping_profiles = None

    def process(self, instance):
        """Look into subset group profiles set by settings.

        Attribute 'subset_grouping_profiles' is defined by OpenPype settings.
        """

        # Skip if 'subset_grouping_profiles' is empty
        if not self.subset_grouping_profiles:
            return

        # Skip if there is no matching profile
        filter_criteria = self.get_profile_filter_criteria(instance)
        profile = filter_profiles(self.subset_grouping_profiles,
                                  filter_criteria,
                                  logger=self.log)
        if not profile:
            return

        if instance.data.get("subsetGroup"):
            # If subsetGroup is already set then allow that value to remain
            self.log.debug("Skipping collect subset group due to existing "
                           "value: {}".format(instance.data["subsetGroup"]))
            return

        template = profile["template"]

        fill_pairs = prepare_template_data({
            "family": filter_criteria["families"],
            "task": filter_criteria["tasks"],
            "host": filter_criteria["hosts"],
            "subset": instance.data["subset"],
            "renderlayer": instance.data.get("renderlayer")
        })

        filled_template = None
        try:
            filled_template = StringTemplate.format_strict_template(
                template, fill_pairs
            )
        except (KeyError, TemplateUnsolved):
            keys = fill_pairs.keys()
            msg = "Subset grouping failed. " \
                  "Only {} are expected in Settings".format(','.join(keys))
            self.log.warning(msg)

        if filled_template:
            instance.data["subsetGroup"] = filled_template

    def get_profile_filter_criteria(self, instance):
        """Return filter criteria for `filter_profiles`"""
        # TODO: This logic is used in much more plug-ins in one way or another
        #       Maybe better suited for lib?
        # Anatomy data is pre-filled by Collectors
        anatomy_data = instance.data["anatomyData"]

        # Task can be optional in anatomy data
        task = anatomy_data.get("task", {})

        # Return filter criteria
        return {
            "families": anatomy_data["family"],
            "tasks": task.get("name"),
            "hosts": anatomy_data["app"],
            "task_types": task.get("type")
        }
