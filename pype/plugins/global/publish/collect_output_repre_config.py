import os
import json
import pyblish.api
from pype import lib as pypelib


class CollectOutputRepreConfig(pyblish.api.ContextPlugin):
    """Inject the current working file into context"""

    order = pyblish.api.CollectorOrder
    label = "Collect Config for representation"
    hosts = ["shell"]

    def process(self, context):
        config_items = [
            pypelib.get_presets_path(),
            "ftrack",
            "output_representation.json"
        ]
        config_file = os.path.sep.join(config_items)
        with open(config_file) as data_file:
            config_data = json.load(data_file)

        context.data['output_repre_config'] = config_data
