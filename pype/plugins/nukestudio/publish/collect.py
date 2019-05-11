from pyblish import api

class CollectFramerate(api.ContextPlugin):
    """Collect framerate from selected sequence."""

    order = api.CollectorOrder
    label = "Collect Framerate"
    hosts = ["nukestudio"]

    def process(self, context):
        for item in context.data.get("selection", []):
            context.data["framerate"] = item.sequence().framerate().toFloat()
            return


class CollectTrackItems(api.ContextPlugin):
    """Collect all Track items selection."""

    order = api.CollectorOrder
    label = "Collect Track Items"
    hosts = ["nukestudio"]

    def process(self, context):
        import os

        data = {}
        for item in context.data.get("selection", []):
            self.log.info("__ item: {}".format(item))
            # Skip audio track items
            # Try/Except is to handle items types, like EffectTrackItem
            try:
                media_type = "core.Hiero.Python.TrackItem.MediaType.kVideo"
                if str(item.mediaType()) != media_type:
                    continue
            except:
                continue

            data[item.name()] = {
                "item": item,
                "tasks": [],
                "startFrame": item.timelineIn(),
                "endFrame": item.timelineOut()
            }

        for key, value in data.items():

            context.create_instance(
                name=key,
                subset="trackItem",
                asset=value["item"].name(),
                item=value["item"],
                family="trackItem",
                tasks=value["tasks"],
                startFrame=value["startFrame"],
                endFrame=value["endFrame"],
                handles=0
            )
