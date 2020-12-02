import opentimelineio as otio


TRACK_TYPES = {
    "video": otio.schema.TrackKind.Video,
    "audio": otio.schema.TrackKind.Audio
}


def create_rational_time(frame, fps):
    return otio.opentime.RationalTime(
        float(frame),
        float(fps)
    )


def create_time_range(start_frame, frame_duration, fps):
    return otio.opentime.TimeRange(
        start_time=create_rational_time(start_frame, fps),
        duration=create_rational_time(frame_duration, fps)
    )


def create_reference(media_pool_item):
    return otio.schema.ExternalReference(
        target_url=media_pool_item.GetClipProperty(
            "File Path").get("File Path"),
        available_range=create_time_range(
            media_pool_item.GetClipProperty("Start").get("Start"),
            media_pool_item.GetClipProperty("Frames").get("Frames"),
            media_pool_item.GetClipProperty("FPS").get("FPS")
        )
    )


def create_markers(track_item, frame_rate):
    track_item_markers = track_item.GetMarkers()
    markers = []
    for marker_frame in track_item_markers:
        markers.append(
            otio.schema.Marker(
                name=track_item_markers[marker_frame]["name"],
                marked_range=create_time_range(
                    marker_frame,
                    track_item_markers[marker_frame]["duration"],
                    frame_rate
                ),
                color=track_item_markers[marker_frame]["color"].upper(),
                metadata={
                    "Resolve": {
                        "note": track_item_markers[marker_frame]["note"]
                    }
                }
            )
        )
    return markers


def create_clip(track_item):
    media_pool_item = track_item.GetMediaPoolItem()
    frame_rate = media_pool_item.GetClipProperty("FPS").get("FPS")
    clip = otio.schema.Clip(
        name=track_item.GetName(),
        source_range=create_time_range(
            track_item.GetLeftOffset(),
            track_item.GetDuration(),
            frame_rate
        ),
        media_reference=create_reference(media_pool_item)
    )
    for marker in create_markers(track_item, frame_rate):
        clip.markers.append(marker)
    return clip


def create_gap(gap_start, clip_start, tl_start_frame, frame_rate):
    return otio.schema.Gap(
        source_range=create_time_range(
            gap_start,
            (clip_start - tl_start_frame) - gap_start,
            frame_rate
        )
    )


def create_timeline(timeline):
    return otio.schema.Timeline(name=timeline.GetName())


def create_track(track_type, track_name):
    return otio.schema.Track(
        name=track_name,
        kind=TRACK_TYPES[track_type]
    )


def create_complete_otio_timeline(project):
    # get current timeline
    timeline = project.GetCurrentTimeline()

    # convert timeline to otio
    otio_timeline = create_timeline(timeline)

    # loop all defined track types
    for track_type in list(TRACK_TYPES.keys()):
        # get total track count
        track_count = timeline.GetTrackCount(track_type)

        # loop all tracks by track indexes
        for track_index in range(1, int(track_count) + 1):
            # get current track name
            track_name = timeline.GetTrackName(track_type, track_index)

            # convert track to otio
            otio_track = create_track(
                track_type, "{}{}".format(track_name, track_index))

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

                # if gap between track start and clip start
                if clip_start > otio_track.available_range().duration.value:
                    # create gap and add it to track
                    otio_track.append(
                        create_gap(
                            otio_track.available_range().duration.value,
                            track_item.GetStart(),
                            timeline.GetStartFrame(),
                            project.GetSetting("timelineFrameRate")
                        )
                    )

                # create otio clip and add it to track
                otio_track.append(create_clip(track_item))

            # add track to otio timeline
            otio_timeline.tracks.append(otio_track)


def get_clip_with_parents(track_item_data):
    """
    Return otio objects for timeline, track and clip

    Args:
        track_item_data (dict): track_item_data from list returned by
                                resolve.get_current_track_items()

    Returns:
        dict: otio clip with parent objects

    """

    track_item = track_item_data["clip"]["item"]
    timeline = track_item_data["timeline"]
    track_type = track_item_data["track"]["type"]
    track_name = track_item_data["track"]["name"]
    track_index = track_item_data["track"]["index"]

    # convert timeline to otio
    otio_timeline = create_timeline(timeline)
    # convert track to otio
    otio_track = create_track(
        track_type, "{}{}".format(track_name, track_index))

    # create otio clip
    otio_clip = create_clip(track_item)

    # add it to track
    otio_track.append(otio_clip)

    # add track to otio timeline
    otio_timeline.tracks.append(otio_track)

    return {
        "otioTimeline": otio_timeline,
        "otioTrack": otio_track,
        "otioClip": otio_clip
    }


def save(otio_timeline, path):
    otio.adapters.write_to_file(otio_timeline, path)
