""" compatibility OpenTimelineIO 0.12.0 and older
"""

import os
import re
import json
import opentimelineio as otio
from . import utils
import clique

TRACK_TYPES = {
    "video": otio.schema.TrackKind.Video,
    "audio": otio.schema.TrackKind.Audio
}


def create_otio_rational_time(frame, fps):
    """
    Creates an OpenTimelineIO (OTIO) RationalTime object based on a frame

    Args:
        frame (int): The frame to create the OTIO RationalTime from.
        fps (float): The frames per second (FPS) of the timeline.

    Returns:
        otio.opentime.RationalTime: The created OpenTimelineIO RationalTime
            object.

    Examples:
        # Create an OTIO RationalTime from a frame
        otio_rational_time = create_otio_rational_time(frame, fps)
    """
    return otio.opentime.RationalTime(
        float(frame),
        float(fps)
    )


def create_otio_time_range(start_frame, frame_duration, fps):
    """
    Creates an OpenTimelineIO (OTIO) TimeRange object based on a start frame
    and a frame duration.

    Args:
        start_frame (int): The start frame of the time range.
        frame_duration (int): The duration of the time range.
        fps (float): The frames per second (FPS) of the timeline.

    Returns:
        otio.opentime.TimeRange: The created OpenTimelineIO TimeRange object.

    Examples:
        # Create an OTIO TimeRange from a start frame and a frame duration
        otio_time_range = create_otio_time_range(
            start_frame, frame_duration, fps)
    """
    return otio.opentime.TimeRange(
        start_time=create_otio_rational_time(start_frame, fps),
        duration=create_otio_rational_time(frame_duration, fps)
    )


def create_otio_reference(media_pool_item):
    """
    Creates an OpenTimelineIO (OTIO) Reference object based on a Resolve
    media pool item.

    Args:
        media_pool_item (resolve.MediaPoolItem): The Resolve media pool item
            to create the OTIO Reference from.

    Returns:
        otio.schema.ExternalReference: The created OpenTimelineIO Reference
            object.

    Examples:
        # Create an OTIO Reference from a Resolve media pool item
        otio_reference = create_otio_reference(media_pool_item)
    """
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
    """
    Creates a list of OpenTimelineIO (OTIO) Marker objects based
    on Resolve track item markers.

    Args:
        track_item (resolve.TimelineItem): The Resolve track item
            containing the markers.
        fps (float): The frames per second (FPS) of the timeline.

    Returns:
        list: A list of OTIO Marker objects representing
            the markers of the track item.

    Examples:
        # Create OTIO markers from Resolve track item markers
        otio_markers = create_otio_markers(track_item, fps)
    """
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


def create_otio_clip(track_item, main_fps):
    """
    Creates an OpenTimelineIO (OTIO) Clip object based on a Resolve track item.

    Args:
        track_item (resolve.TimelineItem): The Resolve track item
            to create the OTIO Clip from.
        main_fps (float): The main frames per second (FPS) of the timeline.

    Returns:
        Any[otio.Clip, list]:
            - If the track item is of type "Audio", a list of OTIO Clip
                objects is returned, each representing an audio channel.
            - If the track item is not of type "Audio", a single OTIO Clip
                object is returned.

    Examples:
        # Create an OTIO Clip from a Resolve track item
        otio_clip = create_otio_clip(track_item, main_fps)
    """

    media_pool_item = track_item.GetMediaPoolItem()
    _mp_clip_property = media_pool_item.GetClipProperty

    # timeline fps should be used as default for timeline items
    name = track_item.GetName()

    media_reference = create_otio_reference(media_pool_item)
    source_range = create_otio_time_range(
        int(track_item.GetLeftOffset()),
        int(track_item.GetDuration()),
        main_fps
    )

    if _mp_clip_property("Type") == "Audio":
        return_clips = []
        audio_channels = _mp_clip_property("Audio Ch")
        for channel in range(int(audio_channels)):
            clip = otio.schema.Clip(
                name=f"{name}_{channel}",
                source_range=source_range,
                media_reference=media_reference
            )
            for marker in create_otio_markers(track_item, main_fps):
                clip.markers.append(marker)
            return_clips.append(clip)
        return return_clips
    else:
        clip = otio.schema.Clip(
            name=name,
            source_range=source_range,
            media_reference=media_reference
        )
        for marker in create_otio_markers(track_item, main_fps):
            clip.markers.append(marker)

        return clip


def create_otio_gap(gap_start, clip_start, tl_start_frame, fps):
    """
    Creates an OpenTimelineIO gap object.

    Args:
        gap_start (int): The start time of the gap.
        clip_start(int): The start time of the clip.
        tl_start_frame (int): The start frame of the timeline.
        fps (float): The frame rate of the timeline.

    Returns:
        otio.schema.Gap: The created OpenTimelineIO gap object.

    """
    return otio.schema.Gap(
        source_range=create_otio_time_range(
            gap_start,
            (clip_start - tl_start_frame) - gap_start,
            fps
        )
    )


def _create_otio_timeline(timeline, main_fps):
    """
    Creates an OpenTimelineIO timeline object based on the given timeline.

    Args:
        timeline (resolve.Timeline): The timeline object to create
            the OTIO timeline from.
        main_fps (float): The main frame rate of the timeline.

    Returns:
        otio.schema.Timeline: The created OpenTimelineIO timeline object.

    """
    metadata = _get_timeline_metadata(timeline, main_fps)

    start_time = create_otio_rational_time(
        timeline.GetStartFrame(), main_fps)

    otio_timeline = otio.schema.Timeline(
        name=timeline.GetName(),
        global_start_time=start_time,
        metadata=metadata
    )
    return otio_timeline


def _get_timeline_metadata(timeline, main_fps):
    """
    Retrieves the metadata of a timeline.

    Args:
        timeline (resolve.Timeline): The timeline object to
            retrieve metadata from.
        main_fps (float): The main frame rate of the timeline.

    Returns:
        dict: A dictionary containing the metadata of the timeline.

    """
    metadata = {}
    metadata.update(dict(timeline.GetSetting().items()))

    metadata.update({
        "width": int(timeline.GetSetting("timelineResolutionWidth")),
        "height": int(timeline.GetSetting("timelineResolutionHeight")),
    })

    # get frame rate from timeline and override main fps if available
    metadata["frameRate"] = main_fps

    # add pixel aspect ratio to metadata
    metadata["pixelAspect"] = _get_pixel_aspect_ratio(
        timeline.GetSetting("timelinePixelAspectRatio")
    )

    return metadata


def _get_metadata_media_pool_item(media_pool_item):
    """
    Retrieves the metadata of a media pool item.

    Args:
        media_pool_item (resolve.MediaPoolItem): The media pool item to
            retrieve metadata from.

    Returns:
        dict: A dictionary containing the metadata of the media pool item.

    """
    data = {}
    data.update(dict(media_pool_item.GetMetadata().items()))
    _property = media_pool_item.GetClipProperty() or {}
    for name, value in _property.items():
        if "Resolution" in name and value != "":
            width, height = value.split("x")
            data.update({
                "width": int(width),
                "height": int(height)
            })
        if "PAR" in name and value != "":
            data["pixelAspect"] = _get_pixel_aspect_ratio(value)

    return data


def _get_pixel_aspect_ratio(value):
    """Converts pixel aspect ratio to float value

    Value can be string `square` or `1:1` or `1.0`

    Args:
        value (str): pixel aspect ratio value

    Returns:
        float: pixel aspect ratio
    """
    try:
        return float(value)
    except ValueError:
        return float(1)


def create_otio_track(track_type, track_name):
    """
    Creates an OpenTimelineIO track object based on the given track type
    and track name.

    Args:
        track_type (str): The type of the track.
        track_name (str): The name of the track.

    Returns:
        otio.schema.Track: The created OpenTimelineIO track object.

    """
    return otio.schema.Track(
        name=track_name,
        kind=TRACK_TYPES[track_type]
    )


def add_otio_gap(clip_start, otio_track, track_item, timeline, main_fps):
    """Add gap to otio track if needed

    Args:
        clip_start (int): start frame of the clip
        otio_track (otio.schema.Track): otio track
        track_item (resolve.TimelineItem): resolve timeline item
        timeline (resolve.Timeline): resolve timeline
        main_fps (float): main fps of the timeline
    """
    # if gap between track start and clip start
    if clip_start > otio_track.available_range().duration.value:
        # create gap and add it to track
        otio_track.append(
            create_otio_gap(
                otio_track.available_range().duration.value,
                track_item.GetStart(),
                timeline.GetStartFrame(),
                main_fps
            )
        )


def add_otio_metadata(otio_item, media_pool_item, **kwargs):
    """Add metadata to otio item

    Args:
        otio_item (otio.schema.Item): otio item
        media_pool_item (resolve.MediaPoolItem): resolve media pool item
        **kwargs: additional metadata
    """
    # get metadata from media pool item
    mp_metadata = media_pool_item.GetMetadata()
    # add additional metadata from kwargs
    if kwargs:
        mp_metadata.update(kwargs)

    # add metadata to otio item metadata
    for key, value in mp_metadata.items():
        otio_item.metadata.update({key: value})


def create_otio_timeline(resolve_project):
    """
    Creates an OpenTimelineIO timeline object based
    on the given Resolve project.

    Args:
        resolve_project (resolve.Project): The Resolve project to create
            the OTIO timeline from.

    Returns:
        otio.schema.Timeline: The created OpenTimelineIO timeline object.

    """

    # get current timeline
    main_fps = resolve_project.GetSetting("timelineFrameRate")
    timeline = resolve_project.GetCurrentTimeline()

    frame_rate = timeline.GetSetting("timelineFrameRate")
    if frame_rate:
        main_fps = float(frame_rate)

    # convert timeline to otio
    otio_timeline = _create_otio_timeline(
        timeline, main_fps)

    # loop all defined track types
    for track_type in list(TRACK_TYPES.keys()):
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
                    clip_start, otio_track, track_item, timeline, main_fps)

                # create otio clip and add it to track
                otio_clip = create_otio_clip(track_item, main_fps)

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
                            # add gap if needed
                            add_otio_gap(
                                clip_start,
                                otio_track,
                                track_item,
                                timeline,
                                main_fps
                            )
                            otio_track.append(clip)

            # add track to otio timeline
            otio_timeline.tracks.append(otio_track)

    return otio_timeline


def write_to_file(otio_timeline, path):
    """
    Writes the given OpenTimelineIO timeline to a file.

    Args:
        otio_timeline (otio.schema.Timeline): The OpenTimelineIO timeline
            to write to a file.
        path (str): The path to write the timeline to.
    """
    otio.adapters.write_to_file(otio_timeline, path)
