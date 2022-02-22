import os

import pyblish.api


def get_comp_render_range(comp):
    """Return comp's start and end render range."""
    comp_attrs = comp.GetAttrs()
    start = comp_attrs["COMPN_RenderStart"]
    end = comp_attrs["COMPN_RenderEnd"]

    # Whenever render ranges are undefined fall back
    # to the comp's global start and end
    if start == -1000000000:
        start = comp_attrs["COMPN_GlobalEnd"]
    if end == -1000000000:
        end = comp_attrs["COMPN_GlobalStart"]

    return start, end


class CollectInstances(pyblish.api.ContextPlugin):
    """Collect Fusion saver instances

    This additionally stores the Comp start and end render range in the
    current context's data as "frameStart" and "frameEnd".

    """

    order = pyblish.api.CollectorOrder
    label = "Collect Instances"
    hosts = ["fusion"]

    def process(self, context):
        """Collect all image sequence tools"""

        from openpype.hosts.fusion.api.lib import get_frame_path

        comp = context.data["currentComp"]

        # Get all savers in the comp
        tools = comp.GetToolList(False).values()
        savers = [tool for tool in tools if tool.ID == "Saver"]

        start, end = get_comp_render_range(comp)
        context.data["frameStart"] = int(start)
        context.data["frameEnd"] = int(end)

        for tool in savers:
            path = tool["Clip"][comp.TIME_UNDEFINED]

            tool_attrs = tool.GetAttrs()
            active = not tool_attrs["TOOLB_PassThrough"]

            if not path:
                self.log.warning("Skipping saver because it "
                                 "has no path set: {}".format(tool.Name))
                continue

            filename = os.path.basename(path)
            head, padding, tail = get_frame_path(filename)
            ext = os.path.splitext(path)[1]
            assert tail == ext, ("Tail does not match %s" % ext)
            subset = head.rstrip("_. ")   # subset is head of the filename

            # Include start and end render frame in label
            label = "{subset} ({start}-{end})".format(subset=subset,
                                                      start=int(start),
                                                      end=int(end))

            instance = context.create_instance(subset)
            instance.data.update({
                "asset": os.environ["AVALON_ASSET"],  # todo: not a constant
                "subset": subset,
                "path": path,
                "outputDir": os.path.dirname(path),
                "ext": ext,  # todo: should be redundant
                "label": label,
                "frameStart": context.data["frameStart"],
                "frameEnd": context.data["frameEnd"],
                "fps": context.data["fps"],
                "families": ["render", "review", "ftrack"],
                "family": "render",
                "active": active,
                "publish": active   # backwards compatibility
            })

            instance.append(tool)

            self.log.info("Found: \"%s\" " % path)

        # Sort/grouped by family (preserving local index)
        context[:] = sorted(context, key=self.sort_by_family)

        return context

    def sort_by_family(self, instance):
        """Sort by family"""
        return instance.data.get("families", instance.data.get("family"))
