"""
Requires:
    context -> system_settings
    context -> openPypeModules
"""

import pyblish.api


class StartTimer(pyblish.api.ContextPlugin):
    label = "Start Timer"
    order = pyblish.api.IntegratorOrder + 1
    hosts = ["*"]

    def process(self, context):
        timers_manager = context.data["openPypeModules"]["timers_manager"]
        if not timers_manager.enabled:
            self.log.debug("TimersManager is disabled")
            return

        modules_settings = context.data["system_settings"]["modules"]
        if not modules_settings["timers_manager"]["disregard_publishing"]:
            self.log.debug("Publish is not affecting running timers.")
            return

        project_name = context.data["projectName"]
        asset_name = context.data.get("asset")
        task_name = context.data.get("task")
        if not project_name or not asset_name or not task_name:
            self.log.info((
                "Current context does not contain all"
                " required information to start a timer."
            ))
            return
        timers_manager.start_timer_with_webserver(
            project_name, asset_name, task_name, self.log
        )
