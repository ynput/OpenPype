from pyblish import api
import os

class CollectClipTagFrameStart(api.InstancePlugin):
    """Collect FrameStart from Tags of selected track items."""

    order = api.CollectorOrder + 0.013
    label = "Collect Frame Start"
    hosts = ["nukestudio"]
    families = ['clip']

    def process(self, instance):
        # gets tags
        tags = instance.data["tags"]

        for t in tags:
            t_metadata = dict(t["metadata"])
            t_family = t_metadata.get("tag.family", "")

            # gets only task family tags and collect labels
            if "frameStart" in t_family:
                t_value = t_metadata.get("tag.value", None)

                # backward compatibility
                t_number = t_metadata.get("tag.number", None)
                start_frame = t_number or t_value

                try:
                    start_frame = int(start_frame)
                except ValueError:
                    if "source" in t_value:
                        source_first = instance.data["sourceFirst"]
                        if source_first == 0:
                            source_first = 1
                        self.log.info("Start frame on `{0}`".format(source_first))
                        source_in = instance.data["sourceIn"]
                        self.log.info("Start frame on `{0}`".format(source_in))
                        start_frame = source_first + source_in

                instance.data["startingFrame"] = start_frame
                self.log.info("Start frame on `{0}` set to `{1}`".format(
                    instance, start_frame
                    ))
