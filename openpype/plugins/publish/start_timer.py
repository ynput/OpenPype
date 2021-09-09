import pyblish.api

from openpype.api import get_system_settings
from openpype.lib import change_timer_to_current_context


class StartTimer(pyblish.api.ContextPlugin):
    label = "Start Timer"
    order = pyblish.api.IntegratorOrder + 1
    hosts = ["*"]

    def process(self, context):
        modules_settings = get_system_settings()["modules"]
        if modules_settings["timers_manager"]["disregard_publishing"]:
            change_timer_to_current_context()
