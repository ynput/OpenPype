from openpype.lib import PreLaunchHook


class PrelaunchNukeAssistHook(PreLaunchHook):
    """
    Adding flag when nukeassist
    """
    app_groups = ["nukeassist"]

    def execute(self):
        self.launch_context.env["NUKEASSIST"] = "1"
