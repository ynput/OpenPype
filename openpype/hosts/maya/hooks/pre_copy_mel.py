from openpype.lib.applications import PreLaunchHook, LaunchTypes
from openpype.hosts.maya.lib import create_workspace_mel


class PreCopyMel(PreLaunchHook):
    """Copy workspace.mel to workdir.

    Hook `GlobalHostDataHook` must be executed before this hook.
    """
    app_groups = {"maya", "mayapy"}
    launch_types = {LaunchTypes.local}

    def execute(self):
        project_doc = self.data["project_doc"]
        workdir = self.launch_context.env.get("AVALON_WORKDIR")
        if not workdir:
            self.log.warning("BUG: Workdir is not filled.")
            return

        project_settings = self.data["project_settings"]
        create_workspace_mel(workdir, project_doc["name"], project_settings)
