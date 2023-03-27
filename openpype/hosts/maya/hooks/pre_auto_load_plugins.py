from openpype.lib import PreLaunchHook


class PreAutoLoadPlugins(PreLaunchHook):
    """Define -noAutoloadPlugins command flag."""

    # Execute before workfile argument.
    order = 0
    app_groups = ["maya"]

    def execute(self):
        maya_settings = self.data["project_settings"]["maya"]
        if maya_settings["explicit_plugins_loading"]["enabled"]:
            self.log.debug("Explicit plugins loading.")
            self.launch_context.launch_args.append("-noAutoloadPlugins")
