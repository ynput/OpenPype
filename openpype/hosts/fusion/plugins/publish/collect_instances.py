import os

import pyblish.api


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


class CollectInstances(pyblish.api.ContextPlugin):
    """Collect Fusion saver instances

    This additionally stores the Comp start and end render range in the
    current context's data as "frameStart" and "frameEnd".

    """

    order = pyblish.api.CollectorOrder
    label = "Collect Instances Data"
    hosts = ["fusion"]

    def process(self, context):
        """Collect all image sequence tools"""

        from openpype.hosts.fusion.api.lib import get_frame_path

        comp = context.data["currentComp"]
        start, end, global_start, global_end = get_comp_render_range(comp)
        context.data["frameStart"] = int(start)
        context.data["frameEnd"] = int(end)
        context.data["frameStartHandle"] = int(global_start)
        context.data["frameEndHandle"] = int(global_end)

        for instance in context:

            tool = instance.data["transientData"]["tool"]

            path = tool["Clip"][comp.TIME_UNDEFINED]
            filename = os.path.basename(path)
            head, padding, tail = get_frame_path(filename)
            ext = os.path.splitext(path)[1]
            assert tail == ext, ("Tail does not match %s" % ext)

            # Include start and end render frame in label
            subset = instance.data["subset"]
            label = "{subset} ({start}-{end})".format(subset=subset,
                                                      start=int(start),
                                                      end=int(end))
            instance.data.update({
                "path": path,
                "outputDir": os.path.dirname(path),
                "ext": ext,  # todo: should be redundant?
                "label": label,
                # todo: Allow custom frame range per instance
                "frameStart": context.data["frameStart"],
                "frameEnd": context.data["frameEnd"],
                "frameStartHandle": context.data["frameStartHandle"],
                "frameEndHandle": context.data["frameStartHandle"],
                "fps": context.data["fps"],
                "families": ["render", "review"],
                "family": "render",

                # Backwards compatibility: embed tool in instance.data
                "tool": tool
            })

            # Add tool itself as member
            instance.append(tool)

            self.log.info("Found: \"%s\" " % path)
