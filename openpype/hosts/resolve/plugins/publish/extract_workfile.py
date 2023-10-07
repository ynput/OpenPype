import os
import pyblish.api

from openpype.pipeline import publish
from openpype.hosts.resolve.api.lib import get_project_manager


class ExtractWorkfile(publish.Extractor):
    """
    Extractor export DRP workfile file representation
    """

    label = "Extract Workfile"
    order = pyblish.api.ExtractorOrder
    families = ["workfile"]
    hosts = ["resolve"]

    def process(self, instance):
        # create representation data
        if "representations" not in instance.data:
            instance.data["representations"] = []

        name = instance.data["name"]
        project = instance.context.data["activeProject"]
        staging_dir = self.staging_dir(instance)

        ext = ".drp"
        drp_file_name = name + ext
        drp_file_path = os.path.normpath(
            os.path.join(staging_dir, drp_file_name))

        # write out the drp workfile
        get_project_manager().ExportProject(
            project.GetName(), drp_file_path)

        # create drp workfile representation
        representation_drp = {
            'name': ext.lstrip("."),
            'ext': ext.lstrip("."),
            'files': drp_file_name,
            "stagingDir": staging_dir,
        }
        representations = instance.data.setdefault("representations", [])
        representations.append(representation_drp)

        # add sourcePath attribute to instance
        if not instance.data.get("sourcePath"):
            instance.data["sourcePath"] = drp_file_path

        self.log.debug(
            "Added Resolve file representation: {}".format(representation_drp)
        )
