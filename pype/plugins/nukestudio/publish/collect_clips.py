import os
from pyblish import api


class CollectClips(api.ContextPlugin):
    """Collect all Track items selection."""

    order = api.CollectorOrder + 0.01
    label = "Collect Clips"
    hosts = ["nukestudio"]

    def process(self, context):
        projectdata = context.data["projectData"]
        version = context.data.get("version", "001")
        instances_data = []
        for item in context.data.get("selection", []):
            self.log.debug(item)
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

            try:
                head, padding, ext = os.path.basename(source_path).split(".")
                source_first_frame = int(padding)
            except:
                source_first_frame = 0

            instances_data.append(
                {
                    "name": "{0}_{1}".format(track.name(), item.name()),
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
            )

        for data in instances_data:
            data.update(
                {
                    "asset": data["item"].name(),
                    "family": "clip",
                    "families": [],
                    "handles": projectdata["handles"],
                    "handleStart": 0,
                    "handleEnd": 0,
                    "version": version
                }
            )
            instance = context.create_instance(**data)
            self.log.debug(
                "Created instance with data: {}".format(instance.data)
            )
