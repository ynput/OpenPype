import os

from openpype.lib import PreLaunchHook


class PreDebugHook(PreLaunchHook):
    """DEBUG hook for openrv
    """
    app_groups = ["openrv"]

    def show_env(launch_env=None):
        project_name = launch_env.env.get("AVALON_PROJECT")
        workdir = launch_env.env.get("AVALON_WORKDIR")
        print("------- project_name {}".format(project_name))
        print("------- LAUNCHDATA", launch_env.data)

        for k in launch_env.env.keys():
            print(k, launch_env.env[k])

    def execute(self):
        print("----- ---- ---- ---- ---")
        print("-------  OPENRV PREHOOK DEBUG ")
        print("RV_SUPPORT_PATH", self.launch_context.env.get("RV_SUPPORT_PATH"))
        print("HOME", self.launch_context.env.get("HOME"))
        #print("PYTHONPATH", self.launch_context.env.get("PYTHONPATH"))
        print("RV_PREFS_OVERRIDE_PATH", self.launch_context.env.get("RV_PREFS_OVERRIDE_PATH"))
        print("----- ---- ---- ---- ---")
        project_name = self.launch_context.env.get("AVALON_PROJECT")
        workdir = self.launch_context.env.get("AVALON_WORKDIR")
        if not workdir:
            self.log.warning("BUG: Workdir is not filled.")
            return
        #self.log.info("OpenPype: Setting up config files")
        #self.log.info("Workdir {}".format(workdir))
        #self.log.info("Project name {}".format(project_name))
        #print(self.data)
        # print("self.launch_context", self.launch_context.env)
        # print("self.launch_context.data", self.launch_context.data)
