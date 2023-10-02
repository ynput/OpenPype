from openpype.lib.applications import PreLaunchHook, LaunchTypes


class AddPythonUseSystemEnvArg(PreLaunchHook):
    """Add `--python-use-system-env` arg to blender launch."""

    # Append before file argument from add last workfile (at order 10)
    order = 5
    app_groups = {"blender"}
    launch_types = {LaunchTypes.local}

    def execute(self):

        add_var = self.get_application_setting("add_python_use_system_env",
                                               default=True)
        if not add_var:
            return

        arg = "--python-use-system-env"
        if arg not in self.launch_context.launch_args:
            self.log.debug(f"Adding required {arg} argument")
            self.launch_context.launch_args.append(arg)
        else:
            self.log.debug(f"Required {arg} argument already provided before "
                           f"this prelaunch hook.")

    def get_application_setting(self, key, default=None):
        app = self.launch_context.application
        group_name = app.group.name
        app_name = app.name
        return (
            self.data["system_settings"]["applications"][group_name]
                     ["variants"][app_name].get(key, default)
        )
