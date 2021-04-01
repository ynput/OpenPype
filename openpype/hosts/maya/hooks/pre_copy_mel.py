from openpype.lib import PreLaunchHook
from openpype.hosts.maya.lib import copy_workspace_mel


class PreCopyMel(PreLaunchHook):
    """Copy workspace.mel to workdir.

    Hook `GlobalHostDataHook` must be executed before this hook.
    """
    app_groups = ["maya"]

    def execute(self):
        workdir = self.launch_context.env.get("AVALON_WORKDIR")
        if not workdir:
            self.log.warning("BUG: Workdir is not filled.")
            return

        copy_workspace_mel(workdir)
