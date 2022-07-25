import json

from maya import cmds

import pyblish.api


class CollectFileDependencies(pyblish.api.ContextPlugin):
    """Gather all files referenced in this scene."""

    label = "Collect File Dependencies"
    order = pyblish.api.CollectorOrder - 0.49
    hosts = ["maya"]

    def process(self, context):
        dependencies = []
        for node in cmds.ls(type="file"):
            path = cmds.getAttr("{}.{}".format(node, "fileTextureName"))
            if path not in dependencies:
                dependencies.append(path)

        for node in cmds.ls(type="AlembicNode"):
            path = cmds.getAttr("{}.{}".format(node, "abc_File"))
            if path not in dependencies:
                dependencies.append(path)

        context.data["fileDependencies"] = dependencies
        self.log.debug(json.dumps(dependencies, indent=4))
