import os

import pyblish.api


class CollectInstanceData(pyblish.api.InstancePlugin):
    """Collect Fusion saver instances

    This additionally stores the Comp start and end render range in the
    current context's data as "frameStart" and "frameEnd".

    """

    order = pyblish.api.CollectorOrder
    label = "Collect Instances Data"
    hosts = ["fusion"]

    def process(self, instance):
        """Collect all image sequence tools"""

        context = instance.context

        # Include creator attributes directly as instance data
        creator_attributes = instance.data["creator_attributes"]
        instance.data.update(creator_attributes)

        # Include start and end render frame in label
        subset = instance.data["subset"]
        start = context.data["frameStart"]
        end = context.data["frameEnd"]
        label = "{subset} ({start}-{end})".format(subset=subset,
                                                  start=int(start),
                                                  end=int(end))
        instance.data.update({
            "label": label,

            # todo: Allow custom frame range per instance
            "frameStart": context.data["frameStart"],
            "frameEnd": context.data["frameEnd"],
            "frameStartHandle": context.data["frameStartHandle"],
            "frameEndHandle": context.data["frameStartHandle"],
            "handleStart": context.data["handleStart"],
            "handleEnd": context.data["handleEnd"],
            "fps": context.data["fps"],
        })

        # Add review family if the instance is marked as 'review'
        # This could be done through a 'review' Creator attribute.
        if instance.data.get("review", False):
            self.log.info("Adding review family..")
            instance.data["families"].append("review")

        if instance.data["family"] == "render":
            # TODO: This should probably move into a collector of
            #       its own for the "render" family
            from openpype.hosts.fusion.api.lib import get_frame_path
            comp = context.data["currentComp"]

            # This is only the case for savers currently but not
            # for workfile instances. So we assume saver here.
            tool = instance.data["transientData"]["tool"]
            path = tool["Clip"][comp.TIME_UNDEFINED]

            filename = os.path.basename(path)
            head, padding, tail = get_frame_path(filename)
            ext = os.path.splitext(path)[1]
            assert tail == ext, ("Tail does not match %s" % ext)

            instance.data.update({
                "path": path,
                "outputDir": os.path.dirname(path),
                "ext": ext,  # todo: should be redundant?

                # Backwards compatibility: embed tool in instance.data
                "tool": tool
            })

            # Add tool itself as member
            instance.append(tool)
