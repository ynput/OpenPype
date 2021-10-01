import os
import json

import pyblish


class CollectJsonData(pyblish.api.ContextPlugin):
    label = "Collect Json Data"
    order = pyblish.api.CollectorOrder - 0.5
    hosts = ["tvpaint"]

    def process(self, context):
        if os.environ.get("PYPE_TVPAINT_JSON"):
            with open(os.environ["PYPE_TVPAINT_JSON"]) as f:
                context.data.update(json.load(f))
