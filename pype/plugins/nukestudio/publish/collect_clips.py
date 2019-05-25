from pyblish import api


class CollectClips(api.ContextPlugin):
    """Collect all Track items selection."""

    order = api.CollectorOrder
    label = "Collect Clips"
    hosts = ["nukestudio"]

    def process(self, context):
        projectdata = context.data["projectData"]
        data = {}
        for item in context.data.get("selection", []):
            self.log.debug("__ item: {}".format(item))
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
                "startFrame": int(item.timelineIn()),
                "endFrame": int(item.timelineOut())
            }

        for key, value in data.items():
            family = "clip"
            context.create_instance(
                name=key,
                subset="{0}{1}".format(family, 'Default'),
                asset=value["item"].name(),
                item=value["item"],
                family=family,
                startFrame=value["startFrame"],
                endFrame=value["endFrame"],
                handles=projectdata['handles']
            )
