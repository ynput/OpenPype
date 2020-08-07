"""
Requires:
    config_data -> colorspace.default
    config_data -> dataflow.default

Provides:
    context     -> presets
"""

from pyblish import api
from pype.api import config


class CollectPresets(api.ContextPlugin):
    """Collect Presets."""

    order = api.CollectorOrder - 0.491
    label = "Collect Presets"

    def process(self, context):
        presets = config.get_presets()
        try:
            # try if it is not in projects custom directory
            # `{PYPE_PROJECT_CONFIGS}/[PROJECT_NAME]/init.json`
            # init.json define preset names to be used
            p_init = presets["init"]
            presets["colorspace"] = presets["colorspace"][p_init["colorspace"]]
            presets["dataflow"] = presets["dataflow"][p_init["dataflow"]]
        except KeyError:
            self.log.warning("No projects custom preset available...")
            presets["colorspace"] = presets["colorspace"]["default"]
            presets["dataflow"] = presets["dataflow"]["default"]
            self.log.info(
                "Presets `colorspace` and `dataflow` loaded from `default`..."
            )

        context.data["presets"] = presets

        # self.log.info(context.data["presets"])
        return
