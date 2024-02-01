import os
from openpype.lib.applications import PreLaunchHook, LaunchTypes


class LaunchWithTerminal(PreLaunchHook):
    """Mac specific pre arguments for application.

    Mac applications should be launched using "open" argument which is internal
    callbacks to open executable. We also add argument "-a" to tell it's
    application open. This is used only for executables ending with ".app". It
    is expected that these executables lead to app packages.
    """
    order = 1000

    platforms = {"darwin"}
    launch_types = {LaunchTypes.local}

    def execute(self):
        executable = str(self.launch_context.executable)
        # Skip executables not ending with ".app" or that are not folder
        if not executable.endswith(".app") or not os.path.isdir(executable):
            return

        # Check if first argument match executable path
        # - Few applications are not executed directly but through OpenPype
        #   process (Photoshop, AfterEffects, Harmony, ...). These should not
        #   use `open`.
        if self.launch_context.launch_args[0] != executable:
            return

        # Tell `open` to pass arguments if there are any
        if len(self.launch_context.launch_args) > 1:
            self.launch_context.launch_args.insert(1, "--args")
        # Prepend open arguments
        self.launch_context.launch_args.insert(0, ["open", "-na"])
