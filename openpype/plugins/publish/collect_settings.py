from pyblish import api
from openpype.settings import (
    get_current_project_settings,
    get_system_settings,
)


class CollectSettings(api.ContextPlugin):
    """Collect Settings and store in the context."""

    order = api.CollectorOrder - 0.491
    label = "Collect Settings"

    def process(self, context):
        context.data["project_settings"] = get_current_project_settings()
        context.data["system_settings"] = get_system_settings()
