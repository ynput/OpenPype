"""
Requires:
    config_data -> colorspace.default
    config_data -> dataflow.default

Provides:
    context     -> presets
"""

from pyblish import api
from pype.api import get_current_project_settings


class CollectPresets(api.ContextPlugin):
    """Collect Presets."""

    order = api.CollectorOrder - 0.491
    label = "Collect Presets"

    def process(self, context):
        project_settings = get_current_project_settings()
        context.data["presets"] = project_settings

        return
