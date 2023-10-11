from openpype.lib.applications import PreLaunchHook


class PrelaunchNukeAssistHook(PreLaunchHook):
    """
    Adding flag when nukeassist
    """
    app_groups = {"nukeassist"}
    launch_types = set()

    def execute(self):
        self.launch_context.env["NUKEASSIST"] = "1"
