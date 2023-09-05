from openpype.lib.applications import PreLaunchHook, LaunchTypes


class AddPythonUseSystemEnvArg(PreLaunchHook):
    """Add `--python-use-system-env` arg to blender launch."""

    # Append before file argument from add last workfile (at order 10)
    order = 5
    app_groups = {"blender"}
    launch_types = {LaunchTypes.local}

    def execute(self):

        arg = "--python-use-system-env"
        if arg not in self.launch_context.launch_args:
            self.log.debug(f"Adding required {arg} argument")
            self.launch_context.launch_args.append(arg)
