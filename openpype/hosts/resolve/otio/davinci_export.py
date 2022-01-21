""" compatibility OpenTimelineIO 0.12.0 and older
"""

import os
import re
import sys
import json
import opentimelineio as otio
from . import utils
import clique

self = sys.modules[__name__]
self.track_types = {
    "video": otio.schema.TrackKind.Video,
    "audio": otio.schema.TrackKind.Audio
}
self.project_fps = None


def create_otio_rational_time(frame, fps):
    return otio.opentime.RationalTime(
        float(frame),
        float(fps)
    )


def create_otio_time_range(start_frame, frame_duration, fps):
    return otio.opentime.TimeRange(
        start_time=create_otio_rational_time(start_frame, fps),
        duration=create_otio_rational_time(frame_duration, fps)
    )


def create_otio_reference(media_pool_item):
    metadata = _get_metadata_media_pool_item(media_pool_item)
    print("media pool item: {}".format(media_pool_item.GetName()))

    _mp_clip_property = media_pool_item.GetClipProperty

    path = _mp_clip_property("File Path")
    reformat_path = utils.get_reformated_path(path, padded=True)
    padding = utils.get_padding_from_path(path)

    if padding:
        metadata.update({
            "isSequence": True,
            "padding": padding
        })

    # get clip property regarding to type
    fps = float(_mp_clip_property("FPS"))
    if _mp_clip_property("Type") == "Video":
        frame_start = int(_mp_clip_property("Start"))
        frame_duration = int(_mp_clip_property("Frames"))
    else:
        audio_duration = str(_mp_clip_property("Duration"))
        frame_start = 0
        frame_duration = int(utils.timecode_to_frames(
            audio_duration, float(fps)))

    otio_ex_ref_item = None

    if padding:
        # if it is file sequence try to create `ImageSequenceReference`
        # the OTIO might not be compatible so return nothing and do it old way
        try:
            dirname, filename = os.path.split(path)
            collection = clique.parse(filename, '{head}[{ranges}]{tail}')
            padding_num = len(re.findall("(\\d+)(?=-)", filename).pop())
            otio_ex_ref_item = otio.schema.ImageSequenceReference(
                target_url_base=dirname + os.sep,
                name_prefix=collection.format("{head}"),
                name_suffix=collection.format("{tail}"),
                start_frame=frame_start,
                frame_zero_padding=padding_num,
                rate=fps,
                available_range=create_otio_time_range(
                    frame_start,
                    frame_duration,
                    fps
                )
            )
        except AttributeError:
            pass

    if not otio_ex_ref_item:
        # in case old OTIO or video file create `ExternalReference`
        otio_ex_ref_item = otio.schema.ExternalReference(
            target_url=reformat_path,
            available_range=create_otio_time_range(
                frame_start,
                frame_duration,
                fps
            )
        )

    # add metadata to otio item
    add_otio_metadata(otio_ex_ref_item, media_pool_item, **metadata)

    return otio_ex_ref_item


def create_otio_markers(track_item, fps):
    track_item_markers = track_item.GetMarkers()
    markers = []
    for marker_frame in track_item_markers:
        note = track_item_markers[marker_frame]["note"]
        if "{" in note and "}" in note:
            metadata = json.loads(note)
        else:
            metadata = {"note": note}
        markers.append(
            otio.schema.Marker(
                name=track_item_markers[marker_frame]["name"],
                marked_range=create_otio_time_range(
                    marker_frame,
                    track_item_markers[marker_frame]["duration"],
                    fps
                ),
                color=track_item_markers[marker_frame]["color"].upper(),
                metadata=metadata
            )
        )
    return markers


def create_otio_clip(track_item):
    media_pool_item = track_item.GetMediaPoolItem()
    _mp_clip_property = media_pool_item.GetClipProperty

    if not self.project_fps:
        fps = float(_mp_clip_property("FPS"))
    else:
        fps = self.project_fps

    name = track_item.GetName()

    media_reference = create_otio_reference(media_pool_item)
    source_range = create_otio_time_range(
        int(track_item.GetLeftOffset()),
        int(track_item.GetDuration()),
        fps
    )

    if _mp_clip_property("Type") == "Audio":
        return_clips = list()
        audio_chanels = _mp_clip_property("Audio Ch")
        for channel in range(0, int(audio_chanels)):
            clip = otio.schema.Clip(
                name=f"{name}_{channel}",
                source_range=source_range,
                media_reference=media_reference
            )
            for marker in create_otio_markers(track_item, fps):
                clip.markers.append(marker)
            return_clips.append(clip)
        return return_clips
    else:
        clip = otio.schema.Clip(
            name=name,
            source_range=source_range,
            media_reference=media_reference
        )
        for marker in create_otio_markers(track_item, fps):
            clip.markers.append(marker)

        return clip


def create_otio_gap(gap_start, clip_start, tl_start_frame, fps):
    return otio.schema.Gap(
        source_range=create_otio_time_range(
            gap_start,
            (clip_start - tl_start_frame) - gap_start,
            fps
        )
    )


def _create_otio_timeline(project, timeline, fps):
    metadata = _get_timeline_metadata(project, timeline)
    start_time = create_otio_rational_time(
        timeline.GetStartFrame(), fps)
    otio_timeline = otio.schema.Timeline(
        name=timeline.GetName(),
        global_start_time=start_time,
        metadata=metadata
    )
    return otio_timeline


def _get_timeline_metadata(project, timeline):
    media_pool = project.GetMediaPool()
    root_folder = media_pool.GetRootFolder()
    ls_folder = root_folder.GetClipList()
    timeline = project.GetCurrentTimeline()
    timeline_name = timeline.GetName()
    for tl in ls_folder:
        if tl.GetName() not in timeline_name:
            continue
        return _get_metadata_media_pool_item(tl)


def _get_metadata_media_pool_item(media_pool_item):
    data = dict()
    data.update({k: v for k, v in media_pool_item.GetMetadata().items()})
    property = media_pool_item.GetClipProperty() or {}
    for name, value in property.items():
        if "Resolution" in name and "" != value:
            width, height = value.split("x")
            data.update({
                "width": int(width),
                "height": int(height)
            })
        if "PAR" in name and "" != value:
            try:
                data.update({"pixelAspect": float(value)})
            except ValueError:
                if "Square" in value:
                    data.update({"pixelAspect": float(1)})
                else:
                    data.update({"pixelAspect": float(1)})

    return data


def create_otio_track(track_type, track_name):
    return otio.schema.Track(
        name=track_name,
        kind=self.track_types[track_type]
    )


def add_otio_gap(clip_start, otio_track, track_item, timeline):
    # if gap between track start and clip start
    if clip_start > otio_track.available_range().duration.value:
        # create gap and add it to track
        otio_track.append(
            create_otio_gap(
                otio_track.available_range().duration.value,
                track_item.GetStart(),
                timeline.GetStartFrame(),
                self.project_fps
            )
        )


def add_otio_metadata(otio_item, media_pool_item, **kwargs):
    mp_metadata = media_pool_item.GetMetadata()
    # add additional metadata from kwargs
    if kwargs:
        mp_metadata.update(kwargs)

    # add metadata to otio item metadata
    for key, value in mp_metadata.items():
        otio_item.metadata.update({key: value})


def create_otio_timeline(resolve_project):

    # get current timeline
    self.project_fps = resolve_project.GetSetting("timelineFrameRate")
    timeline = resolve_project.GetCurrentTimeline()

    # convert timeline to otio
    otio_timeline = _create_otio_timeline(
        resolve_project, timeline, self.project_fps)

    # loop all defined track types
    for track_type in list(self.track_types.keys()):
        # get total track count
        track_count = timeline.GetTrackCount(track_type)

        # loop all tracks by track indexes
        for track_index in range(1, int(track_count) + 1):
            # get current track name
            track_name = timeline.GetTrackName(track_type, track_index)

            # convert track to otio
            otio_track = create_otio_track(
                track_type, track_name)

            # get all track items in current track
            current_track_items = timeline.GetItemListInTrack(
                track_type, track_index)

            # loop available track items in current track items
            for track_item in current_track_items:
                # skip offline track items
                if track_item.GetMediaPoolItem() is None:
                    continue

                # calculate real clip start
                clip_start = track_item.GetStart() - timeline.GetStartFrame()

                add_otio_gap(
                    clip_start, otio_track, track_item, timeline)

                # create otio clip and add it to track
                otio_clip = create_otio_clip(track_item)

                if not isinstance(otio_clip, list):
                    otio_track.append(otio_clip)
                else:
                    for index, clip in enumerate(otio_clip):
                        if index == 0:
                            otio_track.append(clip)
                        else:
                            # add previous otio track to timeline
                            otio_timeline.tracks.append(otio_track)
                            # convert track to otio
                            otio_track = create_otio_track(
                                track_type, track_name)
                            add_otio_gap(
                                clip_start, otio_track,
                                track_item, timeline)
                            otio_track.append(clip)

            # add track to otio timeline
            otio_timeline.tracks.append(otio_track)

    return otio_timeline


def write_to_file(otio_timeline, path):
    otio.adapters.write_to_file(otio_timeline, path)
