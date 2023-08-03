from openpype.lib.applications import PreLaunchHook, LaunchTypes


class SetPath(PreLaunchHook):
    """Set current dir to workdir.

    Hook `GlobalHostDataHook` must be executed before this hook.
    """
    app_groups = ["houdini"]
    launch_types = {LaunchTypes.local}

    def execute(self):
        workdir = self.launch_context.env.get("AVALON_WORKDIR", "")
        if not workdir:
            self.log.warning("BUG: Workdir is not filled.")
            return

        self.launch_context.kwargs["cwd"] = workdir
