import os

import pyblish.api
from avalon import harmony


class CollectCurrentFile(pyblish.api.ContextPlugin):
    """Inject the current working file into context"""

    order = pyblish.api.CollectorOrder - 0.5
    label = "Current File"
    hosts = ["harmony"]

    def process(self, context):
        """Inject the current working file"""
        func = """function func()
        {
            return (
                scene.currentProjectPath() + "/" +
                scene.currentVersionName() + ".xstage"
            );
        }
        func
        """

        current_file = harmony.send({"function": func})["result"]
        context.data["currentFile"] = os.path.normpath(current_file)
