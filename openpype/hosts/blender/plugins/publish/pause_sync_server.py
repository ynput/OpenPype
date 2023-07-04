import pyblish

from openpype.plugins.publish.integrate import IntegrateAsset


class PauseSyncServer(pyblish.api.ContextPlugin):
    label = "Pause Sync Server"
    hosts = ["blender"]
    order = IntegrateAsset.order - 0.01

    def process(self, context):
        project_name = context.data["projectEntity"]["name"]
        sync_server_module = context.data["openPypeModules"]["sync_server"]
        sync_server_module.pause_project(project_name)
