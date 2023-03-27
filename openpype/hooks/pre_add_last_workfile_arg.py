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
        "3dsmax",
        "maya",
        "nuke",
        "nukex",
        "hiero",
        "houdini",
        "nukestudio",
        "fusion",
        "blender",
        "photoshop",
        "tvpaint",
        "aftereffects"
    ]

    def execute(self):
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

        # Determine whether to open workfile post initialization.
        if self.host_name == "maya":
            maya_settings = self.data["project_settings"]["maya"]

            if maya_settings["explicit_plugins_loading"]["enabled"]:
                self.log.debug("Explicit plugins loading.")
                self.launch_context.launch_args.append("-noAutoloadPlugins")

            keys = [
                "open_workfile_post_initialization", "explicit_plugins_loading"
            ]
            values = [maya_settings[k] for k in keys]
            if any(values):
                self.log.debug("Opening workfile post initialization.")
                key = "OPENPYPE_OPEN_WORKFILE_POST_INITIALIZATION"
                self.data["env"][key] = "1"
                return

        # Add path to workfile to arguments
        self.launch_context.launch_args.append(last_workfile)
