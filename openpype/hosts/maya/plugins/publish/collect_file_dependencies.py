import os
import json

from maya import cmds

import pyblish.api


class CollectFileDependencies(pyblish.api.ContextPlugin):
    """Gather all files referenced in this scene."""

    label = "Collect File Dependencies"
    order = pyblish.api.CollectorOrder - 0.49
    hosts = ["maya"]
    families = ["renderlayer"]

    @classmethod
    def apply_settings(cls, project_settings, system_settings):
        # Disable plug-in if not used for deadline submission anyway
        settings = project_settings["deadline"]["publish"]["MayaSubmitDeadline"]  # noqa
        cls.enabled = settings.get("asset_dependencies", True)

    def process(self, context):
        dependencies = set()
        for node in cmds.ls(type="file"):
            path = cmds.getAttr("{}.{}".format(node, "fileTextureName"))
            if path not in dependencies:
                dependencies.add(path)

        for node in cmds.ls(type="AlembicNode"):
            path = cmds.getAttr("{}.{}".format(node, "abc_File"))
            if path not in dependencies:
                dependencies.add(path)

        dependencies = list(dependencies)
        context.data["fileDependencies"] = dependencies

        if os.environ.get("OPENPYPE_DEBUG") == "1":
            self.log.debug(json.dumps(dependencies, indent=4))
