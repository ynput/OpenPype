import pyblish.api


class CollectOutputFrameRange(pyblish.api.ContextPlugin):
    """Collect frame start/end from context.

    When instances are collected context does not contain `frameStart` and
    `frameEnd` keys yet. They are collected in global plugin
    `CollectContextEntities`.
    """
    label = "Collect output frame range"
    order = pyblish.api.CollectorOrder
    hosts = ["tvpaint"]

    def process(self, context):
        for instance in context:
            frame_start = instance.data.get("frameStart")
            frame_end = instance.data.get("frameEnd")
            if frame_start is not None and frame_end is not None:
                self.log.debug(
                    "Instance {} already has set frames {}-{}".format(
                        str(instance), frame_start, frame_end
                    )
                )
                return

            frame_start = context.data.get("frameStart")
            frame_end = context.data.get("frameEnd")

            instance.data["frameStart"] = frame_start
            instance.data["frameEnd"] = frame_end

            self.log.info(
                "Set frames {}-{} on instance {} ".format(
                    frame_start, frame_end, str(instance)
                )
            )
