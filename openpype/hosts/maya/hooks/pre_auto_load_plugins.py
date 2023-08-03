from openpype.lib.applications import PreLaunchHook, LaunchTypes


class MayaPreAutoLoadPlugins(PreLaunchHook):
    """Define -noAutoloadPlugins command flag."""

    # Before AddLastWorkfileToLaunchArgs
    order = 9
    app_groups = {"maya"}
    launch_types = {LaunchTypes.local}

    def execute(self):

        # Ignore if there's no last workfile to start.
        if not self.data.get("start_last_workfile"):
            return

        maya_settings = self.data["project_settings"]["maya"]
        enabled = maya_settings["explicit_plugins_loading"]["enabled"]
        if enabled:
            # Force disable the `AddLastWorkfileToLaunchArgs`.
            self.data.pop("start_last_workfile")

            # Force post initialization so our dedicated plug-in load can run
            # prior to Maya opening a scene file.
            key = "OPENPYPE_OPEN_WORKFILE_POST_INITIALIZATION"
            self.launch_context.env[key] = "1"

            self.log.debug("Explicit plugins loading.")
            self.launch_context.launch_args.append("-noAutoloadPlugins")
