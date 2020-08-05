import os
import opentimelineio as otio
import tempfile
import pyblish.api
from pype import lib as plib


class CollectClipInstances(pyblish.api.InstancePlugin):
    """Collect Clips instances from editorial's OTIO sequence"""

    order = pyblish.api.CollectorOrder + 0.01
    label = "Collect Clips"
    hosts = ["standalonepublisher"]
    families = ["editorial"]

    # presets
    subsets = {
        "referenceMain": {
            "family": "review",
            "families": ["review", "ftrack"],
            "ftrackFamily": "review",
            "extension": ".mp4"
        },
        "audioMain": {
            "family": "audio",
            "families": ["ftrack"],
            "ftrackFamily": "audio",
            "extension": ".wav"
        },
        "shotMain": {
            "family": "shot",
            "families": []
        }
    }
    start_frame_offset = None  # if 900000 for edl default then -900000
    custom_start_frame = None

    def process(self, instance):

        staging_dir = os.path.normpath(
            tempfile.mkdtemp(prefix="pyblish_tmp_")
        )
        # get context
        context = instance.context

        # create asset_names conversion table
        if not context.data.get("assetsShared"):
            self.log.debug("Created `assetsShared` in context")
            context.data["assetsShared"] = dict()

        # get timeline otio data
        timeline = instance.data["otio_timeline"]
        fps = plib.get_asset()["data"]["fps"]

        tracks = timeline.each_child(
            descended_from_type=otio.schema.track.Track
        )
        self.log.debug(f"__ tracks: `{tracks}`")

        # get data from avalon
        asset_entity = instance.context.data["assetEntity"]
        asset_data = asset_entity["data"]
        asset_name = asset_entity["name"]
        self.log.debug(f"__ asset_entity: `{asset_entity}`")

        # Timeline data.
        handle_start = int(asset_data["handleStart"])
        handle_end = int(asset_data["handleEnd"])

        instances = []
        for track in tracks:
            self.log.debug(f"__ track: `{track}`")
            try:
                track_start_frame = (
                    abs(track.source_range.start_time.value)
                )
            except AttributeError:
                track_start_frame = 0

            self.log.debug(f"__ track: `{track}`")

            for clip in track.each_child():
                # skip all generators like black ampty
                if isinstance(
                    clip.media_reference,
                        otio.schema.GeneratorReference):
                    continue

                # Transitions are ignored, because Clips have the full frame
                # range.
                if isinstance(clip, otio.schema.transition.Transition):
                    continue

                if clip.name is None:
                    continue

                # basic unique asset name
                clip_name = os.path.splitext(clip.name)[0].lower()
                name = f"{asset_name.split('_')[0]}_{clip_name}"

                # frame ranges data
                clip_in = clip.range_in_parent().start_time.value
                clip_out = clip.range_in_parent().end_time_inclusive().value
                clip_duration = clip.duration().value

                source_in = clip.trimmed_range().start_time.value
                source_out = source_in + clip_duration
                source_in_h = source_in - handle_start
                source_out_h = source_out + handle_end

                clip_in_h = clip_in - handle_start
                clip_out_h = clip_out + handle_end

                # define starting frame for future shot
                frame_start = self.custom_start_frame or clip_in

                # add offset in case there is any
                if self.start_frame_offset:
                    frame_start += self.start_frame_offset

                frame_end = frame_start + clip_duration

                # create shared new instance data
                instance_data = {
                    "stagingDir": staging_dir,

                    # shared attributes
                    "asset": name,
                    "assetShareName": name,
                    "editorialVideoPath": instance.data[
                        "editorialVideoPath"],
                    "item": clip,

                    # parent time properities
                    "trackStartFrame": track_start_frame,
                    "handleStart": handle_start,
                    "handleEnd": handle_end,
                    "fps": fps,

                    # media source
                    "sourceIn": source_in,
                    "sourceOut": source_out,
                    "sourceInH": source_in_h,
                    "sourceOutH": source_out_h,

                    # timeline
                    "clipIn": clip_in,
                    "clipOut": clip_out,
                    "clipDuration": clip_duration,
                    "clipInH": clip_in_h,
                    "clipOutH": clip_out_h,
                    "clipDurationH": clip_duration + handle_start + handle_end,

                    # task
                    "frameStart": frame_start,
                    "frameEnd": frame_end,
                    "frameStartH": frame_start - handle_start,
                    "frameEndH": frame_end + handle_end
                }

                # adding subsets to context as instances
                for subset, properities in self.subsets.items():
                    # adding Review-able instance
                    subset_instance_data = instance_data.copy()
                    subset_instance_data.update(properities)
                    subset_instance_data.update({
                        # unique attributes
                        "name": f"{subset}_{name}",
                        "label": f"{subset} {name} ({clip_in}-{clip_out})",
                        "subset": subset
                    })
                    instances.append(instance.context.create_instance(
                        **subset_instance_data))
                    self.log.debug(instance_data)

                context.data["assetsShared"][name] = {
                    "_clipIn": clip_in,
                    "_clipOut": clip_out
                }
