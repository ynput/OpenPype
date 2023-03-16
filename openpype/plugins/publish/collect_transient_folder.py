"""
Requires:
    anatomy


Provides:
    instance.data     -> stagingDir (folder path)
                      -> stagingDir_persistent (bool)
"""
import copy
import os.path

import pyblish.api

from openpype.pipeline.publish.lib import get_transient_dir_info


class CollectTransientFolder(pyblish.api.InstancePlugin):
    """Looks through profiles if stagingDir should be persistent and in special
    location.

    Transient staging dir could be useful in specific use cases where is
    desirable to have temporary renders in specific, persistent folders, could
    be on disks optimized for speed for example.

    It is studio responsibility to clean up obsolete folders with data.

    Location of the folder is configured in `project_anatomy/templates/others`.
    ('transient' key is expected, with 'folder' key)

    Which family/task type/subset is applicable is configured in:
    `project_settings/global/publish/CollectTransientFolder`

    """
    label = "Collect Transient Staging Dir"
    order = pyblish.api.CollectorOrder + 0.4990

    template_key = "transient"

    def process(self, instance):
        family = instance.data["family"]
        subset_name = instance.data["subset"]
        host_name = instance.context.data["hostName"]
        project_name = instance.context.data["projectName"]

        anatomy = instance.context.data["anatomy"]
        anatomy_data = copy.deepcopy(instance.data["anatomyData"])
        task = anatomy_data.get("task", {})

        transient_tml, is_persistent = get_transient_dir_info(project_name,
                                                              host_name,
                                                              family,
                                                              task.get("name"),
                                                              task.get("type"),
                                                              subset_name,
                                                              anatomy,
                                                              log=self.log)
        result_str = "Not adding"
        if transient_tml:
            anatomy_data["root"] = anatomy.roots
            scene_name = instance.context.data.get("currentFile")
            if scene_name:
                anatomy_data["scene_name"] = os.path.basename(scene_name)
            transient_dir = transient_tml.format(**anatomy_data)
            instance.data["stagingDir"] = transient_dir

            instance.data["stagingDir_persistent"] = is_persistent
            result_str = "Adding '{}' as".format(transient_dir)

        self.log.info("{} transient staging dir for instance with '{}'".format(
            result_str, family
        ))
