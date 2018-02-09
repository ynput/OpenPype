import os
import re

import pyblish.api

from avalon.vendor import clique


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
    """Collect Fusion saver instances"""

    order = pyblish.api.CollectorOrder
    label = "Collect Instances"
    hosts = ["fusion"]

    def process(self, context):
        """Collect all image sequence tools"""

        comp = context.data["currentComp"]

        # Get all savers in the comp
        tools = comp.GetToolList(False).values()
        savers = [tool for tool in tools if tool.ID == "Saver"]

        start, end = get_comp_render_range(comp)
        for tool in savers:
            path = tool["Clip"][comp.TIME_UNDEFINED]
            if not path:
                self.log.warning("Skipping saver because it "
                                 "has no path set: {}".format(tool.Name))
                continue

            fname = os.path.basename(path)
            # we don't use the padding
            basename, ext = os.path.splitext(fname)
            chars = [char for char in basename if
                     not char.isdigit() and char != "."]

            subset = "".join(chars)

            # Include start and end render frame in label
            label = "{subset} ({start}-{end})".format(subset=subset,
                                                      start=int(start),
                                                      end=int(end))

            instance = context.create_instance(subset)
            instance.data.update({
                "asset": os.environ["AVALON_ASSET"],  # todo: not a constant
                "subset": subset,
                "path": path,
                "ext": ext,  # todo: should be redundant
                "label": label,
                "families": ["colorbleed.imagesequence"],
                "family": "colorbleed.imagesequence",
            })

            instance.append(tool)  # For future use, store the tool

            self.log.info("Found: \"%s\" " % path)

        # Sort/grouped by family (preserving local index)
        context[:] = sorted(context, key=self.sort_by_family)

        return context

    def sort_by_family(self, instance):
        """Sort by family"""
        return instance.data.get("families", instance.data.get("family"))
