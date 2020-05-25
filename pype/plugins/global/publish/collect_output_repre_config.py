"""
Requires:
    config_data -> ftrack.output_representation

Provides:
    context     -> output_repre_config (str)
"""

import pyblish.api
from pype.api import config


class CollectOutputRepreConfig(pyblish.api.ContextPlugin):
    """Inject the current working file into context"""

    order = pyblish.api.CollectorOrder
    label = "Collect Config for representation"
    hosts = ["shell", "standalonepublisher"]

    def process(self, context):
        config_data = config.get_presets()["ftrack"]["output_representation"]
        context.data['output_repre_config'] = config_data
