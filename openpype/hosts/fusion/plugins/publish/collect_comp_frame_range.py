import pyblish.api


def get_comp_render_range(comp):
    """Return comp's start-end render range and global start-end range."""
    comp_attrs = comp.GetAttrs()
    start = comp_attrs["COMPN_RenderStart"]
    end = comp_attrs["COMPN_RenderEnd"]
    global_start = comp_attrs["COMPN_GlobalStart"]
    global_end = comp_attrs["COMPN_GlobalEnd"]

    frame_data = comp.GetData("openpype_instance")
    handle_start = frame_data.get("handleStart", 0)
    handle_end = frame_data.get("handleEnd", 0)
    frame_start = frame_data.get("frameStart", 0)
    frame_end = frame_data.get("frameEnd", 0)

    # Whenever render ranges are undefined fall back
    # to the comp's global start and end
    if start == -1000000000:
        start = frame_start
    if end == -1000000000:
        end = frame_end

    return start, end, global_start, global_end, handle_start, handle_end


class CollectFusionCompFrameRanges(pyblish.api.ContextPlugin):
    """Collect current comp"""

    # We run this after CollectorOrder - 0.1 otherwise it gets
    # overridden by global plug-in `CollectContextEntities`
    order = pyblish.api.CollectorOrder - 0.05
    label = "Collect Comp Frame Ranges"
    hosts = ["fusion"]

    def process(self, context):
        """Collect all image sequence tools"""

        comp = context.data["currentComp"]

        # Store comp render ranges
        (
            start, end,
            global_start,
            global_end,
            handle_start,
            handle_end
        ) = get_comp_render_range(comp)

        data = {}
        data["frameStart"] = int(start)
        data["frameEnd"] = int(end)
        data["frameStartHandle"] = int(global_start)
        data["frameEndHandle"] = int(global_end)
        data["handleStart"] = int(handle_start)
        data["handleEnd"] = int(handle_end)

        self.log.debug("_ data: {}".format(data))

        context.data.update(data)
