import os
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
            source = item.source().mediaSource()
            source_path = source.firstpath()
            instance_name = "{0}_{1}".format(track.name(), item.name())

            try:
                head, padding, ext = os.path.basename(source_path).split('.')
                source_first_frame = int(padding)
            except:
                source_first_frame = 0

            data[instance_name] = {
                "item": item,
                "source": source,
                "sourcePath": source_path,
                "track": track.name(),
                "sourceFirst": source_first_frame,
                "sourceIn": int(item.sourceIn()),
                "sourceOut": int(item.sourceOut()),
                "startFrame": int(item.timelineIn()),
                "endFrame": int(item.timelineOut())
            }

        for key, value in data.items():
            family = "clip"
            context.create_instance(
                name=key,
                asset=value["item"].name(),
                item=value["item"],
                source=value["source"],
                sourcePath=value["sourcePath"],
                family=family,
                families=[],
                sourceFirst=value["sourceFirst"],
                sourceIn=value["sourceIn"],
                sourceOut=value["sourceOut"],
                startFrame=value["startFrame"],
                endFrame=value["endFrame"],
                handles=projectdata['handles'],
                handleStart=0,
                handleEnd=0,
                version=version,
                track=value["track"]
            )
