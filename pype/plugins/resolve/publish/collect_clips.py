import os
from pyblish import api
from pype.hosts import resolve
import json


class CollectClips(api.ContextPlugin):
    """Collect all Track items selection."""

    order = api.CollectorOrder + 0.01
    label = "Collect Clips"
    hosts = ["resolve"]

    def process(self, context):
        # create asset_names conversion table
        if not context.data.get("assetsShared"):
            self.log.debug("Created `assetsShared` in context")
            context.data["assetsShared"] = dict()

        projectdata = context.data["projectEntity"]["data"]
        selection = resolve.get_current_track_items(
            filter=True, selecting_color="Pink")

        for clip_data in selection:
            data = dict()

            # get basic objects form data
            project = clip_data["project"]
            sequence = clip_data["sequence"]
            clip = clip_data["clip"]

            # sequence attrs
            sq_frame_start = sequence.GetStartFrame()
            self.log.debug(f"sq_frame_start: {sq_frame_start}")

            sq_markers = sequence.GetMarkers()

            # get details of objects
            clip_item = clip["item"]
            track = clip_data["track"]

            mp = project.GetMediaPool()

            # get clip attributes
            clip_metadata = resolve.get_pype_clip_metadata(clip_item)
            clip_metadata = json.loads(clip_metadata)
            self.log.debug(f"clip_metadata: {clip_metadata}")

            compound_source_prop = clip_metadata["sourceProperties"]
            self.log.debug(f"compound_source_prop: {compound_source_prop}")

            asset_name = clip_item.GetName()
            mp_item = clip_item.GetMediaPoolItem()
            mp_prop = mp_item.GetClipProperty()
            source_first = int(compound_source_prop["Start"])
            source_last = int(compound_source_prop["End"])
            source_duration = compound_source_prop["Frames"]
            fps = float(mp_prop["FPS"])
            self.log.debug(f"source_first: {source_first}")
            self.log.debug(f"source_last: {source_last}")
            self.log.debug(f"source_duration: {source_duration}")
            self.log.debug(f"fps: {fps}")

            source_path = os.path.normpath(
                compound_source_prop["File Path"])
            source_name = compound_source_prop["File Name"]
            source_id = clip_metadata["sourceId"]
            self.log.debug(f"source_path: {source_path}")
            self.log.debug(f"source_name: {source_name}")
            self.log.debug(f"source_id: {source_id}")

            clip_left_offset = int(clip_item.GetLeftOffset())
            clip_right_offset = int(clip_item.GetRightOffset())
            self.log.debug(f"clip_left_offset: {clip_left_offset}")
            self.log.debug(f"clip_right_offset: {clip_right_offset}")

            # source in/out
            source_in = int(source_first + clip_left_offset)
            source_out = int(source_first + clip_right_offset)
            self.log.debug(f"source_in: {source_in}")
            self.log.debug(f"source_out: {source_out}")

            clip_in = int(clip_item.GetStart() - sq_frame_start)
            clip_out = int(clip_item.GetEnd() - sq_frame_start)
            clip_duration = int(clip_item.GetDuration())
            self.log.debug(f"clip_in: {clip_in}")
            self.log.debug(f"clip_out: {clip_out}")
            self.log.debug(f"clip_duration: {clip_duration}")

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
            if asset_name in str(clip_matching_with_range):
                clip_matching_with_range = False

            # rise wrong name exception if found one
            assert (not clip_matching_with_range), (
                "matching clip: {asset}"
                " timeline range ({clip_in}:{clip_out})"
                " conflicting with {clip_matching_with_range}"
                " >> rename any of clips to be the same as the other <<"
            ).format(
                **locals())

            if ("[" in source_name) and ("]" in source_name):
                is_sequence = True

            data.update({
                "name": "_".join([
                    track["name"], asset_name, source_name]),
                "item": clip_item,
                "source": mp_item,
                # "timecodeStart": str(source.timecodeStart()),
                "timelineStart": sq_frame_start,
                "sourcePath": source_path,
                "sourceFileHead": source_name,
                "isSequence": is_sequence,
                "track": track["name"],
                "trackIndex": track["index"],
                "sourceFirst": source_first,

                "sourceIn": source_in,
                "sourceOut": source_out,
                "mediaDuration": source_duration,
                "clipIn": clip_in,
                "clipOut": clip_out,
                "clipDuration": clip_duration,
                "asset": asset_name,
                "subset": "plateMain",
                "family": "clip",
                "families": [],
                "handleStart": projectdata.get("handleStart", 0),
                "handleEnd": projectdata.get("handleEnd", 0)})

            instance = context.create_instance(**data)

            self.log.info("Created instance: {}".format(instance))
            self.log.info("Created instance.data: {}".format(instance.data))

            context.data["assetsShared"][asset_name] = {
                "_clipIn": clip_in,
                "_clipOut": clip_out
            }
            self.log.info(
                "context.data[\"assetsShared\"]: {}".format(
                    context.data["assetsShared"]))
