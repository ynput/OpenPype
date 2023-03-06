"""
Requires:
    anatomy


Provides:
    instance     -> stagingDir (folder path)
                 -> stagingDir_persistent (bool)
"""
import copy

import pyblish.api

from openpype.lib import filter_profiles


class CollectTransientStaging(pyblish.api.InstancePlugin):
    """
        Looks through profiles if stagingDir should be persistent.

    Transient staging dir could be useful in specific use cases where is
    desirable to have temporary renders is specific, persistent folders.

    It is studio responsibility to clean up obsolete folders with data.
    """
    label = "Collect Transient Staging Dir"
    order = pyblish.api.CollectorOrder + 0.4990

    template_key = "transient"

    # configurable in Settings
    transient_staging_profiles = None

    def process(self, instance):
        if not self.transient_staging_profiles:
            self.log.debug("No profiles present for transient staging")
            return

        transient_staging = False
        family = instance.data["family"]
        subset_name = instance.data["subset"]
        host_name = instance.context.data["hostName"]
        project_name = instance.context.data["projectName"]

        anatomy_data = copy.deepcopy(instance.data["anatomyData"])
        task = anatomy_data.get("task", {})

        filtering_criteria = {
            "hosts": host_name,
            "families": family,
            "task_names": task.get("name"),
            "task_types": task.get("type"),
            "subsets": subset_name
        }
        profile = filter_profiles(self.transient_staging_profiles,
                                  filtering_criteria,
                                  logger=self.log)

        if profile:
            transient_staging = profile["transient_staging"]

            if transient_staging:
                anatomy = instance.context.data["anatomy"]
                is_config = self._is_valid_configuration(anatomy,
                                                         self.template_key,
                                                         project_name)
                if not is_config:
                    return

                anatomy_filled = anatomy.format(anatomy_data)
                staging_dir = anatomy_filled[self.template_key]["folder"]

                instance.data["stagingDir"] = staging_dir
                instance.data["stagingDir_persistent"] = True

        result_str = "Adding"
        if not transient_staging:
            result_str = "Not adding"
        self.log.info("{} transient staging dir for instance with '{}'".format(
            result_str, family
        ))

    def _is_valid_configuration(self, anatomy, template_key, project_name):
        is_valid = True
        if self.template_key not in anatomy.templates:
            self.log.warning((
                 "!!! Anatomy of project \"{}\" does not have set"
                 " \"{}\" template key!"
             ).format(project_name, template_key))
            is_valid = False

        self.log.info("template::{}".format(anatomy.templates))
        if is_valid and "folder" not in anatomy.templates["others"][template_key]:  # noqa
            self.log.warning((
                 "!!! There is not set \"path\" template in \"{}\" anatomy"
                 " for project \"{}\"."
             ).format(template_key, project_name))
            is_valid = False

        return is_valid
