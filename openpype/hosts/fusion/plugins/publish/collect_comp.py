import pyblish.api

from openpype.hosts.fusion.api import get_current_comp


def get_comp_render_range(comp):
    """Return comp's start-end render range and global start-end range."""
    comp_attrs = comp.GetAttrs()
    start = comp_attrs["COMPN_RenderStart"]
    end = comp_attrs["COMPN_RenderEnd"]
    global_start = comp_attrs["COMPN_GlobalStart"]
    global_end = comp_attrs["COMPN_GlobalEnd"]

    # Whenever render ranges are undefined fall back
    # to the comp's global start and end
    if start == -1000000000:
        start = global_start
    if end == -1000000000:
        end = global_end

    return start, end, global_start, global_end


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

        # Store comp render ranges
        start, end, global_start, global_end = get_comp_render_range(comp)
        context.data["frameStart"] = int(start)
        context.data["frameEnd"] = int(end)
        context.data["frameStartHandle"] = int(global_start)
        context.data["frameEndHandle"] = int(global_end)
