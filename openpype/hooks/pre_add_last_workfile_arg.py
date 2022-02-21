import os
from openpype.lib import PreLaunchHook


class AddLastWorkfileToLaunchArgs(PreLaunchHook):
    """Add last workfile path to launch arguments.

    This is not possible to do for all applications the same way.
    Checks 'start_last_workfile', if set to False, it will not open last
    workfile. This property is set explicitly in Launcher.
    """

    # Execute after workfile template copy
    order = 10
    app_groups = [
        "maya",
        "nuke",
        "nukex",
        "hiero",
        "nukestudio",
        "blender",
        "photoshop",
        "tvpaint",
        "afftereffects"
    ]

    def get_last_workfile(self):
        if not self.data.get("start_last_workfile"):
            self.log.info("It is set to not start last workfile on start.")
            return

        last_workfile = self.data.get("last_workfile_path")
        if not last_workfile:
            self.log.warning("Last workfile was not collected.")
            return

        if not os.path.exists(last_workfile):
            self.log.info("Current context does not have any workfile yet.")
            return

        return last_workfile

    def execute(self):

        last_workfile = self.get_last_workfile()
        if last_workfile:
            # Add path to workfile to arguments
            self.launch_context.launch_args.append(last_workfile)


class AddLastWorkfileToLaunchArgsHoudini(AddLastWorkfileToLaunchArgs):
    """Add last workfile path to launch arguments - Houdini specific"""
    app_groups = ["houdini"]

    def execute(self):

        last_workfile = self.get_last_workfile()
        if last_workfile:
            # Whenever a filepath is passed to Houdini then the startup
            # scripts 123.py and houdinicore.py won't be triggered. Thus
            # OpenPype will not initialize correctly. As such, whenever
            # we pass a workfile we first explicitly pass a startup
            # script to enforce it to run - which will load the last passed
            # argument as workfile directly.
            pype_root = os.environ["OPENPYPE_REPOS_ROOT"]
            startup_path = os.path.join(
                pype_root, "openpype", "hosts", "houdini", "startup"
            )
            startup_script = os.path.join(startup_path,
                                          "scripts",
                                          "openpype_launch.py")
            self.launch_context.launch_args.append(startup_script)

            # Add path to workfile to arguments
            self.launch_context.launch_args.append(last_workfile)
