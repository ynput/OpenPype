import os
import pyblish.api


class CollectShellWorkspace(pyblish.api.ContextPlugin):
    """Inject the current workspace into context"""

    order = pyblish.api.CollectorOrder - 0.5
    label = "Shell Workspace"

    hosts = ["shell"]

    def process(self, context):
        context.data["workspaceDir"] = os.getcwd()
