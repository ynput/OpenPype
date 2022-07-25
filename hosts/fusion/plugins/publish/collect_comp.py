import os

import pyblish.api

from openpype.hosts.fusion.api import get_current_comp


class CollectCurrentCompFusion(pyblish.api.ContextPlugin):
    """Collect current comp"""

    order = pyblish.api.CollectorOrder - 0.4
    label = "Collect Current Comp"
    hosts = ["fusion"]

    def process(self, context):
        """Collect all image sequence tools"""

        current_comp = get_current_comp()
        assert current_comp, "Must have active Fusion composition"
        context.data["currentComp"] = current_comp

        # Store path to current file
        filepath = current_comp.GetAttrs().get("COMPS_FileName", "")
        context.data['currentFile'] = filepath
