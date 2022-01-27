import os
import opentimelineio as otio
import pyblish.api
from openpype import lib as plib
from copy import deepcopy

class CollectInstances(pyblish.api.InstancePlugin):
    """Collect instances from editorial's OTIO sequence"""

    order = pyblish.api.CollectorOrder + 0.01
    label = "Collect Editorial Instances"
    hosts = ["standalonepublisher"]
    families = ["editorial"]

    # presets
    subsets = {
        "referenceMain": {
            "family": "review",
            "families": ["clip"],
            "extensions": ["mp4"]
        },
        "audioMain": {
            "family": "audio",
            "families": ["clip"],
            "extensions": ["wav"],
        }
    }
    timeline_frame_start = 900000  # starndard edl default (10:00:00:00)
    timeline_frame_offset = None
    custom_start_frame = None

    def process(self, instance):
        # get context
        context = instance.context

        instance_data_filter = [
            "editorialSourceRoot",
            "editorialSourcePath"
        ]

        # attribute for checking duplicity during creation
        if not context.data.get("assetNameCheck"):
            context.data["assetNameCheck"] = list()

        # create asset_names conversion table
        if not context.data.get("assetsShared"):
            context.data["assetsShared"] = dict()

        # get timeline otio data
        timeline = instance.data["otio_timeline"]
        fps = plib.get_asset()["data"]["fps"]

        tracks = timeline.each_child(
            descended_from_type=otio.schema.Track
        )

        # get data from avalon
        asset_entity = instance.context.data["assetEntity"]
        asset_data = asset_entity["data"]
        asset_name = asset_entity["name"]

        # Timeline data.
        handle_start = int(asset_data["handleStart"])
        handle_end = int(asset_data["handleEnd"])

        for track in tracks:
            self.log.debug(f"track.name: {track.name}")
            try:
                track_start_frame = (
                    abs(track.source_range.start_time.value)
                )
                self.log.debug(f"track_start_frame: {track_start_frame}")
                track_start_frame -= self.timeline_frame_start
            except AttributeError:
                track_start_frame = 0

            self.log.debug(f"track_start_frame: {track_start_frame}")

            for clip in track.each_child():
                if clip.name is None:
                    continue

                if isinstance(clip, otio.schema.Gap):
                    continue

                # skip all generators like black empty
                if isinstance(
                    clip.media_reference,
                        otio.schema.GeneratorReference):
                    continue

                # Transitions are ignored, because Clips have the full frame
                # range.
                if isinstance(clip, otio.schema.Transition):
                    continue

                # basic unique asset name
                clip_name = os.path.splitext(clip.name)[0].lower()
                name = f"{asset_name.split('_')[0]}_{clip_name}"

                if name not in context.data["assetNameCheck"]:
                    context.data["assetNameCheck"].append(name)
                else:
                    self.log.warning(f"duplicate shot name: {name}")

                # frame ranges data
                clip_in = clip.range_in_parent().start_time.value
                clip_in += track_start_frame
                clip_out = clip.range_in_parent().end_time_inclusive().value
                clip_out += track_start_frame
                self.log.info(f"clip_in: {clip_in} | clip_out: {clip_out}")

                # add offset in case there is any
                if self.timeline_frame_offset:
                    clip_in += self.timeline_frame_offset
                    clip_out += self.timeline_frame_offset

                clip_duration = clip.duration().value
                self.log.info(f"clip duration: {clip_duration}")

                source_in = clip.trimmed_range().start_time.value
                source_out = source_in + clip_duration
                source_in_h = source_in - handle_start
                source_out_h = source_out + handle_end

                clip_in_h = clip_in - handle_start
                clip_out_h = clip_out + handle_end

                # define starting frame for future shot
                if self.custom_start_frame is not None:
                    frame_start = self.custom_start_frame
                else:
                    frame_start = clip_in

                frame_end = frame_start + (clip_duration - 1)

                # create shared new instance data
                instance_data = {
                    # shared attributes
                    "asset": name,
                    "assetShareName": name,
                    "item": clip,
                    "clipName": clip_name,

                    # parent time properties
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

                for data_key in instance_data_filter:
                    instance_data.update({
                        data_key: instance.data.get(data_key)})

                # adding subsets to context as instances
                self.subsets.update({
                    "shotMain": {
                        "family": "shot",
                        "families": []
                    }
                })
                for subset, properties in self.subsets.items():
                    version = properties.get("version")
                    if version == 0:
                        properties.pop("version")

                    # adding Review-able instance
                    subset_instance_data = deepcopy(instance_data)
                    subset_instance_data.update(deepcopy(properties))
                    subset_instance_data.update({
                        # unique attributes
                        "name": f"{name}_{subset}",
                        "label": f"{name} {subset} ({clip_in}-{clip_out})",
                        "subset": subset
                    })
                    # create new instance
                    _instance = instance.context.create_instance(
                        **subset_instance_data)
                    self.log.debug(
                        f"Instance: `{_instance}` | "
                        f"families: `{subset_instance_data['families']}`")

                context.data["assetsShared"][name] = {
                    "_clipIn": clip_in,
                    "_clipOut": clip_out
                }

                self.log.debug("Instance: `{}` | families: `{}`")
