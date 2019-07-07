import os

from pyblish import api

import nuke


class CollectClips(api.ContextPlugin):
    """Collect all Track items selection."""

    order = api.CollectorOrder + 0.01
    label = "Collect Clips"
    hosts = ["nukestudio"]

    def process(self, context):
        # create asset_names conversion table
        if not context.data.get("assetsShared"):
            self.log.debug("Created `assetsShared` in context")
            context.data["assetsShared"] = dict()

        projectdata = context.data["projectData"]
        version = context.data.get("version", "001")
        instances_data = []
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

            # If source is *.nk its a comp effect and we need to fetch the
            # write node output. This should be improved by parsing the script
            # rather than opening it.
            if source_path.endswith(".nk"):
                nuke.scriptOpen(source_path)
                # There should noly be one.
                write_node = nuke.allNodes(filter="Write")[0]
                path = nuke.filename(write_node)

                if "%" in path:
                    # Get start frame from Nuke script and use the item source
                    # in/out, because you can have multiple shots covered with
                    # one nuke script.
                    start_frame = int(nuke.root()["first_frame"].getValue())
                    if write_node["use_limit"].getValue():
                        start_frame = int(write_node["first"].getValue())

                    path = path % (start_frame + item.sourceIn())

                source_path = path
                self.log.debug(
                    "Fetched source path \"{}\" from \"{}\" in "
                    "\"{}\".".format(
                        source_path, write_node.name(), source.firstpath()
                    )
                )

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
                    "handles": projectdata.get("handles", 0),
                    "handleStart": 0,
                    "handleEnd": 0,
                    "version": version
                }
            )
            instance = context.create_instance(**data)
            self.log.debug(
                "Created instance with data: {}".format(instance.data)
            )
            context.data["assetsShared"][data["asset"]] = dict()
