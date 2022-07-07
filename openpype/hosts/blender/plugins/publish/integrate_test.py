import json
import subprocess
import pyblish.api
from openpype.lib.local_settings import get_local_site_id

from openpype.modules.base import ModulesManager
from openpype.pipeline import legacy_io

from concurrent.futures import ThreadPoolExecutor as Pool

running_futures = []

# def callback(future):
#     if future.exception() is not None:
#         raise future.exception()
#     else:
#         representation, sites = paused_representations.get(future)
#         print("buya", representation, sites)
#         manager = ModulesManager()
#         sync_server_module = manager.modules_by_name["sync_server"]
#         for site in sites:
#             sync_server_module.unpause_representation(*representation, site)
        
#         # print("bouya", [f.done() for f in running_futures])
#         # if all([f.done() for f in running_futures]):
#         #     manager = ModulesManager()
#         #     sync_server_module = manager.modules_by_name["sync_server"]
#         #     sync_server_module.unpause_representation()
#         # else:
#         #     return

# paused_representations = {}


class IntegrateTest(pyblish.api.InstancePlugin):
    """Generate a JSON file for animation."""

    label = "Integrate Animation"
    order = pyblish.api.IntegratorOrder + 0.1
    optional = True
    hosts = []
    # families = ["setdress"]

    def process(self, instance):
        self.log.info("Integrate Test")

        manager = ModulesManager()
        sync_server_module = manager.modules_by_name["sync_server"]
        # sync_server_module.add_before_loop_cmd(("/Applications/Blender3.3.1.app/Contents/MacOS/Blender", ))
        # sync_server_module.add_before_loop_cmd(("sleep", "10"))
        # sync_server_module.reset_timer()
        # ("/Applications/Blender3.3.1.app/Contents/MacOS/Blender")

        # sync_server_module.pause_server()
        project_name = legacy_io.active_project()
        # global representation
        # print(instance.data.get('published_representations'))
        published_representations = instance.data.get('published_representations', {}).keys()
        # representation = project_name, instance.data.get('representations')[0]['_id'], sync_server_module.get_active_site(project_name)

        pool = Pool()
        cmds = [("/home/felix/Documents/Dev/Softs/blender-3.3.2-linux-x64/blender", ), ("sleep", 10)]
        for repre_id in published_representations:
            sites = [sync_server_module.get_active_site(project_name), sync_server_module.get_remote_site(project_name)]
            # representation = (project_name, repre_id)
            for site in sites:
                sync_server_module.pause_representation(project_name, repre_id, site)
            for c in cmds:
                # Build function to callback
                def callback(future):
                    if future.exception() is not None:
                        raise future.exception()
                    else:
                        # representation, sites = paused_representations.get(future)
                        # print("buya", representation, sites)
                        # manager = ModulesManager()
                        # sync_server_module = manager.modules_by_name["sync_server"]
                        for site in sites:
                            sync_server_module.unpause_representation(project_name, repre_id, site)
                
                # Submit call to pool
                f = pool.submit(subprocess.check_call, c, shell=True)
                f.add_done_callback(callback)
                # paused_representations[f]= (representation, sites)
                # running_futures.append(f)
        pool.shutdown(wait=False)
