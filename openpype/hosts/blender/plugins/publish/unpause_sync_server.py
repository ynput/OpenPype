from time import sleep
import pyblish

from openpype.modules.base import ModulesManager
from openpype.modules.timers_manager.plugins.publish.start_timer import (
    StartTimer,
)


class UnpauseSyncServer(pyblish.api.ContextPlugin):
    label = "Unpause Sync Server"
    hosts = ["blender"]
    order = StartTimer.order

    def process(self, context):
        manager = ModulesManager()
        sync_server_module = manager.modules_by_name["sync_server"]
        sync_server_module.unpause_server()

        # Wait for all started futures to finish
        for instance in context:
            for future in instance.data.get("representations_futures", []):
                while future.running():
                    self.log.debug(f"Waiting for {future} to finish...")
                    sleep(1)
