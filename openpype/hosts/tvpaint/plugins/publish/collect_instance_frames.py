import pyblish.api


class CollectOutputFrameRange(pyblish.api.InstancePlugin):
    """Collect frame start/end from context.

    When instances are collected context does not contain `frameStart` and
    `frameEnd` keys yet. They are collected in global plugin
    `CollectContextEntities`.
    """

    label = "Collect output frame range"
    order = pyblish.api.CollectorOrder + 0.4999
    hosts = ["tvpaint"]
    families = ["review", "render"]

    def process(self, instance):
        asset_doc = instance.data.get("assetEntity")
        if not asset_doc:
            return

        context = instance.context

        frame_start = asset_doc["data"]["frameStart"]
        fps = asset_doc["data"]["fps"]
        frame_end = frame_start + (
            context.data["sceneMarkOut"] - context.data["sceneMarkIn"]
        )
        instance.data["fps"] = fps
        instance.data["frameStart"] = frame_start
        instance.data["frameEnd"] = frame_end
        self.log.info(
            "Set frames {}-{} on instance {} ".format(
                frame_start, frame_end, instance.data["subset"]
            )
        )
