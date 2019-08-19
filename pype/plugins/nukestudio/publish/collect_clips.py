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
        sequence = context.data.get("activeSequence")
        instances_data = []

        # get all subTrackItems and add it to context
        effects_on_tracks = []
        sub_track_items = []

        # looop trough all tracks and search for subtreacks
        for track_index, video_track in enumerate(sequence.videoTracks()):
            sub_items = video_track.subTrackItems()
            if not sub_items:
                continue
            for si in sub_items:
                selected_track = [(indx, vt) for indx, vt in enumerate(sequence.videoTracks())
                                  if vt.name() in si[0].parentTrack().name()]

                # if filtered track index is the same as \
                # actual track there is match
                if (selected_track[0][0] == track_index):
                    sub_track_items += si
                    if (track_index not in effects_on_tracks):
                        effects_on_tracks.append(track_index)

        # add it to context
        context.data["subTrackUsedTracks"] = effects_on_tracks
        context.data["subTrackItems"] = sub_track_items

        for item in context.data.get("selection", []):
            # Skip audio track items
            # Try/Except is to handle items types, like EffectTrackItem
            try:
                media_type = "core.Hiero.Python.TrackItem.MediaType.kVideo"
                if str(item.mediaType()) != media_type:
                    continue
            except Exception:
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
            except Exception:
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
                    "clipIn": int(item.timelineIn()),
                    "clipOut": int(item.timelineOut())
                }
            )

        for data in instances_data:
            data.update(
                {
                    "asset": data["item"].name(),
                    "family": "clip",
                    "families": [],
                    "handles": 0,
                    "handleStart": projectdata.get("handles", 0),
                    "handleEnd": projectdata.get("handles", 0),
                    "version": int(version)
                }
            )
            instance = context.create_instance(**data)
            self.log.debug(
                "Created instance with data: {}".format(instance.data)
            )
            context.data["assetsShared"][data["asset"]] = dict()
