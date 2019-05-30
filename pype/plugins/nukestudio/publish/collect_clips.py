from pyblish import api


class CollectClips(api.ContextPlugin):
    """Collect all Track items selection."""

    order = api.CollectorOrder
    label = "Collect Clips"
    hosts = ["nukestudio"]

    def process(self, context):
        projectdata = context.data["projectData"]
        version = context.data.get("version", "001")
        data = {}
        for item in context.data.get("selection", []):
            # Skip audio track items
            # Try/Except is to handle items types, like EffectTrackItem
            try:
                media_type = "core.Hiero.Python.TrackItem.MediaType.kVideo"
                if str(item.mediaType()) != media_type:
                    continue
            except:
                continue

            track = item.parent()
            instance_name = "{0}_{1}".format(track.name(), item.name())
            data[instance_name] = {
                "item": item,
                "track": track.name(),
                "startFrame": int(item.timelineIn()),
                "endFrame": int(item.timelineOut())
            }

        for key, value in data.items():
            family = "clip"
            context.create_instance(
                name=key,
                asset=value["item"].name(),
                item=value["item"],
                family=family,
                families=[],
                startFrame=value["startFrame"],
                endFrame=value["endFrame"],
                handles=projectdata['handles'],
                handleStart=0,
                handleEnd=0,
                version=version,
                track=value["track"]
            )
