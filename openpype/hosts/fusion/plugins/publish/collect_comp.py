import pyblish.api

from openpype.hosts.fusion.api import get_current_comp


class CollectCurrentCompFusion(pyblish.api.ContextPlugin):
    """Collect current comp"""

    order = pyblish.api.CollectorOrder - 0.4
    label = "Collect Current Comp"
    hosts = ["fusion"]

    def process(self, context):
        """Collect all image sequence tools"""

        comp = get_current_comp()
        assert comp, "Must have active Fusion composition"
        context.data["currentComp"] = comp

        # Store path to current file
        filepath = comp.GetAttrs().get("COMPS_FileName", "")
        context.data['currentFile'] = filepath
