from pyblish import api
from pypeapp import config


class CollectPresets(api.ContextPlugin):
    """Collect Presets."""

    order = api.CollectorOrder
    label = "Collect Presets"

    def process(self, context):
        context.data["presets"] = config.get_presets()
        # self.log.debug(context.data["presets"])
        return
