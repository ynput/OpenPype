import os

from pyblish import api
import hiero
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

        projectdata = context.data["projectEntity"]["data"]
        sequence = context.data.get("activeSequence")
        selection = context.data.get("selection")

        track_effects = dict()

        # collect all trackItems as instances
        for track_index, video_track in enumerate(sequence.videoTracks()):
            items = video_track.items()
            sub_items = video_track.subTrackItems()

            for item in items:
                data = dict()
                # compare with selection or if disabled
                if item not in selection or not item.isEnabled():
                    continue

                # Skip audio track items
                # Try/Except is to handle items types, like EffectTrackItem
                try:
                    media_type = "core.Hiero.Python.TrackItem.MediaType.kVideo"
                    if str(item.mediaType()) != media_type:
                        continue
                except Exception:
                    continue

                asset = item.name()
                track = item.parent()
                source = item.source().mediaSource()
                source_path = source.firstpath()
                clip_in = int(item.timelineIn())
                clip_out = int(item.timelineOut())
                file_head = source.filenameHead()
                file_info = next((f for f in source.fileinfos()), None)
                source_first_frame = int(file_info.startFrame())
                is_sequence = False

                self.log.debug(
                    "__ assets_shared: {}".format(
                        context.data["assetsShared"]))

                # Check for clips with the same range
                # this is for testing if any vertically neighbouring
                # clips has been already processed
                clip_matching_with_range = next(
                    (k for k, v in context.data["assetsShared"].items()
                     if (v.get("_clipIn", 0) == clip_in)
                     and (v.get("_clipOut", 0) == clip_out)
                     ), False)

                # check if clip name is the same in matched
                # vertically neighbouring clip
                # if it is then it is correct and resent variable to False
                # not to be rised wrong name exception
                if asset in str(clip_matching_with_range):
                    clip_matching_with_range = False

                # rise wrong name exception if found one
                assert (not clip_matching_with_range), (
                    "matching clip: {asset}"
                    " timeline range ({clip_in}:{clip_out})"
                    " conflicting with {clip_matching_with_range}"
                    " >> rename any of clips to be the same as the other <<"
                ).format(
                    **locals())

                if not source.singleFile():
                    self.log.info("Single file")
                    is_sequence = True
                    source_path = file_info.filename()

                effects = [f for f in item.linkedItems()
                           if f.isEnabled()
                           if isinstance(f, hiero.core.EffectTrackItem)]

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

                data.update({
                    "name": "{0}_{1}".format(track.name(), item.name()),
                    "item": item,
                    "source": source,
                    "timecodeStart": str(source.timecodeStart()),
                    "timelineTimecodeStart": str(sequence.timecodeStart()),
                    "sourcePath": source_path,
                    "sourceFileHead": file_head,
                    "isSequence": is_sequence,
                    "track": track.name(),
                    "trackIndex": track_index,
                    "sourceFirst": source_first_frame,
                    "effects": effects,
                    "sourceIn": int(item.sourceIn()),
                    "sourceOut": int(item.sourceOut()),
                    "mediaDuration": int(source.duration()),
                    "clipIn": clip_in,
                    "clipOut": clip_out,
                    "clipDuration": (
                        int(item.timelineOut()) - int(
                            item.timelineIn())) + 1,
                    "asset": asset,
                    "family": "clip",
                    "families": [],
                    "handleStart": projectdata.get("handleStart", 0),
                    "handleEnd": projectdata.get("handleEnd", 0)})

                instance = context.create_instance(**data)

                self.log.info("Created instance: {}".format(instance))
                self.log.info("Created instance.data: {}".format(instance.data))
                self.log.debug(">> effects: {}".format(instance.data["effects"]))

                context.data["assetsShared"][asset] = {
                    "_clipIn": clip_in,
                    "_clipOut": clip_out
                }

            # from now we are collecting only subtrackitems on
            # track with no video items
            if len(items) > 0:
                continue

            # create list in track key
            # get all subTrackItems and add it to context
            track_effects[track_index] = list()

            # collect all subtrack items
            for sitem in sub_items:
                # unwrap from tuple >> it is always tuple with one item
                sitem = sitem[0]
                # checking if not enabled
                if not sitem.isEnabled():
                    continue

                track_effects[track_index].append(sitem)

        context.data["trackEffects"] = track_effects
        self.log.debug(">> sub_track_items: `{}`".format(track_effects))
