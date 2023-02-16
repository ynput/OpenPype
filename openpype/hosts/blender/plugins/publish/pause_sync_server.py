import pyblish

from openpype.modules.base import ModulesManager
from openpype.plugins.publish.integrate import IntegrateAsset


class PauseSyncServer(pyblish.api.ContextPlugin):
    label = "Pause Sync Server"
    hosts = ["blender"]
    order = IntegrateAsset.order - 0.01

    def process(self, context):
        manager = ModulesManager()
        sync_server_module = manager.modules_by_name["sync_server"]
        sync_server_module.pause_server()
        # TODO should pause only project but doesn't work because
        # _paused_projects is cached but sync server is not a singleton
