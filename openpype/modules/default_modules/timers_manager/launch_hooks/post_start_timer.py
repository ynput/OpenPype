from openpype.lib import PostLaunchHook


class PostStartTimerHook(PostLaunchHook):
    """Start timer with TimersManager module.

    This module requires enabled TimerManager module.
    """
    order = None

    def execute(self):
        project_name = self.data.get("project_name")
        asset_name = self.data.get("asset_name")
        task_name = self.data.get("task_name")

        missing_context_keys = set()
        if not project_name:
            missing_context_keys.add("project_name")
        if not asset_name:
            missing_context_keys.add("asset_name")
        if not task_name:
            missing_context_keys.add("task_name")

        if missing_context_keys:
            missing_keys_str = ", ".join([
                "\"{}\"".format(key) for key in missing_context_keys
            ])
            self.log.debug("Hook {} skipped. Missing data keys: {}".format(
                self.__class__.__name__, missing_keys_str
            ))
            return

        timers_manager = self.modules_manager.modules_by_name.get(
            "timers_manager"
        )
        if not timers_manager or not timers_manager.enabled:
            self.log.info((
                "Skipping starting timer because"
                " TimersManager is not available."
            ))
            return

        timers_manager.start_timer_with_webserver(
            project_name, asset_name, task_name, logger=self.log
        )
