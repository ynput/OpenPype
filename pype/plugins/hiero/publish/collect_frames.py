import json

import hiero

from pyblish import api


class CollectFrames(api.ContextPlugin):
    """Collect frames from tags.

    Tag is expected to have metadata:
    {
        "family": "frame"
        "subset": "main"
    }
    """

    order = api.CollectorOrder
    label = "Collect Frames"
    hosts = ["hiero"]

    def process(self, context):
        sequence = hiero.ui.activeSequence()

        publish_frames = range(
            int(sequence.timecodeStart()),
            int(sequence.duration() + sequence.timecodeStart())
        )
        selection = hiero.selection
        if selection:
            publish_frames = []
            for track_item in selection:
                publish_frames.extend(
                    range(track_item.timelineIn(), track_item.timelineOut())
                )

        publish_frames = list(set(publish_frames))

        subset_data = {}
        for tag in sequence.tags():
            metadata = tag.metadata().dict()
            if "tag.family" not in metadata:
                continue
            if metadata["tag.family"] != "frame":
                continue

            frame = int(metadata["tag.start"])

            if frame not in publish_frames:
                continue

            subset = metadata["tag.subset"]
            try:
                subset_data[subset]["frames"].append(frame)
            except KeyError:
                subset_data[subset] = {
                    "frames": [frame], "format": metadata["tag.format"]
                }

        for subset_name, subset_data in subset_data.items():
            name = "frame" + subset_name.title()
            data = {
                "name": name,
                "label": "{} {}".format(name, subset_data["frames"]),
                "family": "image",
                "families": ["frame"],
                "asset": context.data["assetEntity"]["name"],
                "subset": subset_name,
                "format": subset_data["format"],
                "frames": subset_data["frames"]
            }
            context.create_instance(**data)
            self.log.info(
                "Created instance: {}".format(
                    json.dumps(data, sort_keys=True, indent=4)
                )
            )
